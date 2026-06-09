"""PARA 任务笔记一体化系统 - FastAPI 应用入口"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

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


# ─── 登录验证中间件 ───
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    from routers.auth import require_auth

    if settings.app_password:
        # 不需要验证的路径
        public_paths = {"/login", "/api/auth/login", "/api/auth/check", "/static"}
        if not any(request.url.path.startswith(p) for p in public_paths):
            if not require_auth(request):
                if request.url.path.startswith("/api/"):
                    from fastapi.responses import JSONResponse
                    return JSONResponse(status_code=401, content={"detail": "未登录"})
                return RedirectResponse(url="/login")
    return await call_next(request)


@app.get("/login")
async def login_page():
    """返回登录页面"""
    return FileResponse("static/login.html")

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
