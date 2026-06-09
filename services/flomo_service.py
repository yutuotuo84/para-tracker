"""Flomo API 集成服务"""

import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from models import Memo

logger = logging.getLogger(__name__)


class FlomoClient:
    """Flomo 专属记录 API 客户端"""

    def __init__(self):
        self.api_url: str = ""
        self.enabled: bool = False

    def configure(self, api_url: str):
        """配置 Flomo API URL"""
        self.api_url = api_url.strip().rstrip("/") + "/"
        self.enabled = bool(api_url.strip())
        logger.info(f"Flomo API {'已配置' if self.enabled else '未配置'}")

    async def create_memo(self, content: str, tags: list[str] | None = None) -> str | None:
        """创建 Flomo 笔记，返回 flomo_id"""
        if not self.enabled:
            logger.warning("Flomo API 未配置，跳过")
            return None

        # 构建带标签的内容
        full_content = content
        if tags:
            tag_str = " ".join(f"#{t}" for t in tags)
            full_content = f"{content}\n\n{tag_str}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.api_url,
                    json={"content": full_content},
                )
                if resp.is_success:
                    logger.info(f"Flomo 笔记创建成功: {content[:50]}...")
                    # Flomo API 返回格式不确定，尝试提取 ID
                    data = resp.json()
                    return data.get("id", str(datetime.now().timestamp()))
                else:
                    logger.error(f"Flomo API 错误: {resp.status_code} {resp.text}")
                    return None
        except Exception as e:
            logger.error(f"Flomo API 请求失败: {e}")
            return None

    async def sync_memo_to_db(self, db: AsyncSession, content: str,
                               tags: list[str], source: str = "free_write",
                               task_id: int | None = None,
                               user_id: int = 1) -> Memo:
        """创建笔记并保存到本地数据库"""
        flomo_id = await self.create_memo(content, tags)

        memo = Memo(
            flomo_id=flomo_id,
            content=content,
            tags=tags or [],
            task_id=task_id,
            source=source,
            user_id=user_id,
        )
        db.add(memo)
        await db.commit()
        await db.refresh(memo)
        return memo


# 全局单例
flomo_client = FlomoClient()
