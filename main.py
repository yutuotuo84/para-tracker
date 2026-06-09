"""PARA 任务笔记一体化系统 - FastAPI 应用入口"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from database import init_db
from services.para_service import seed_para_tags

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def sync_loop():
    """后台定时同步任务"""
    from database import async_session_factory
    from services.ticktick_service import ticktick_client

    while True:
        try:
            if ticktick_client.authenticated:
                async with async_session_factory() as db:
                    await ticktick_client.sync_projects(db)
                    await ticktick_client.sync_tasks(db)
                    logger.info("后台定时同步完成")
        except Exception as e:
            logger.warning(f"后台同步出错: {e}")

        await asyncio.sleep(settings.sync_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("正在初始化数据库...")
    await init_db()

    # 初始化 PARA 种子标签
    from database import async_session_factory
    async with async_session_factory() as db:
        await seed_para_tags(db)

    # 启动后台同步
    task = asyncio.create_task(sync_loop())
    logger.info(f"PARA Tracker 已启动，监听端口 {settings.app_port}")

    yield

    # 清理
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="PARA Tracker",
    description="滴答清单 + Flomo 笔记一体化管理系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册路由
from routers import auth, tasks, memos, para, summary
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(memos.router)
app.include_router(para.router)
app.include_router(summary.router)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """返回主页面"""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",       # 监听本地，由 nginx 反向代理
        port=settings.app_port,
        reload=False,            # 生产模式必须关闭
    )
