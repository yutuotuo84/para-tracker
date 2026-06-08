"""TickTick API 集成服务 (直接 HTTP API 调用)"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Project, Task

logger = logging.getLogger(__name__)

TICKTICK_API_BASE = "https://api.ticktick.com"
TICKTICK_OAUTH_AUTH = "https://ticktick.com/oauth/authorize"
TICKTICK_OAUTH_TOKEN = "https://ticktick.com/oauth/token"


class TickTickClient:
    """TickTick API 客户端 (HTTP API 直连，无需 C 扩展)"""

    def __init__(self):
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.authenticated: bool = False
        self._session: httpx.AsyncClient | None = None

    async def _get_session(self) -> httpx.AsyncClient:
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=15)
        return self._session

    async def authenticate_oauth(self, client_id: str, client_secret: str,
                                  redirect_uri: str, auth_code: str) -> bool:
        """使用 OAuth2 授权码换取 Token"""
        try:
            client = await self._get_session()
            resp = await client.post(TICKTICK_OAUTH_TOKEN, json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
            if resp.is_success:
                data = resp.json()
                self.access_token = data.get("access_token", "")
                self.refresh_token = data.get("refresh_token", "")
                self.authenticated = bool(self.access_token)
                logger.info("TickTick OAuth 认证成功")
                return True
            else:
                logger.error(f"OAuth token 换取失败: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"OAuth 认证异常: {e}")
            return False

    async def authenticate_password(self, username: str, password: str) -> bool:
        """使用用户名密码登录 (V2 Session API)"""
        try:
            client = await self._get_session()
            resp = await client.post(
                f"{TICKTICK_API_BASE}/api/v2/user/signin",
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json", "User-Agent": "PARA-Tracker/1.0"},
            )
            if resp.is_success:
                data = resp.json()
                self.access_token = data.get("token", "")
                self.authenticated = bool(self.access_token)

                # 保存 cookies 用于后续请求
                cookies = resp.cookies
                if cookies:
                    self._session = httpx.AsyncClient(
                        timeout=15,
                        cookies=cookies,
                        headers={
                            "User-Agent": "PARA-Tracker/1.0",
                            "Content-Type": "application/json",
                        },
                    )
                else:
                    # Fallback: 使用 token header
                    self._session = httpx.AsyncClient(
                        timeout=15,
                        headers={
                            "User-Agent": "PARA-Tracker/1.0",
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.access_token}",
                        },
                    )

                logger.info("TickTick 密码登录成功")
                return True
            else:
                logger.error(f"TickTick 登录失败: {resp.status_code} {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"TickTick 登录异常: {e}")
            return False

    async def _api_get(self, path: str) -> list | dict | None:
        """GET 请求 TickTick API"""
        if not self.authenticated:
            return None
        try:
            client = await self._get_session()
            resp = await client.get(f"{TICKTICK_API_BASE}{path}")
            if resp.is_success:
                return resp.json()
            logger.warning(f"GET {path} 失败: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"GET {path} 异常: {e}")
            return None

    async def _api_post(self, path: str, data: dict = None) -> dict | None:
        """POST 请求 TickTick API"""
        if not self.authenticated:
            return None
        try:
            client = await self._get_session()
            resp = await client.post(f"{TICKTICK_API_BASE}{path}", json=data or {})
            if resp.is_success:
                return resp.json()
            logger.warning(f"POST {path} 失败: {resp.status_code} {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"POST {path} 异常: {e}")
            return None

    async def sync_projects(self, db: AsyncSession) -> int:
        """同步项目列表"""
        data = await self._api_get("/open/v1/project")
        if not data:
            return 0

        synced = 0
        for proj in (data if isinstance(data, list) else []):
            tid = str(proj.get("id", ""))
            existing = await db.execute(
                select(Project).where(Project.ticktick_id == tid)
            )
            if not existing.scalar_one_or_none():
                db.add(Project(
                    ticktick_id=tid,
                    name=proj.get("name", "未命名项目"),
                ))
                synced += 1

        await db.commit()
        logger.info(f"同步了 {synced} 个项目")
        return synced

    async def sync_tasks(self, db: AsyncSession) -> int:
        """同步任务列表"""
        data = await self._api_get("/open/v1/task")
        if not data:
            return 0

        synced = 0
        for t in (data if isinstance(data, list) else []):
            ticktick_id = str(t.get("id", ""))
            existing = await db.execute(
                select(Task).where(Task.ticktick_id == ticktick_id)
            )
            task = existing.scalar_one_or_none()

            # 查找项目映射
            project_id = None
            project_guid = t.get("projectId", "")
            if project_guid:
                proj = await db.execute(
                    select(Project).where(Project.ticktick_id == project_guid)
                )
                p = proj.scalar_one_or_none()
                if p:
                    project_id = p.id

            status = "done" if t.get("status") == 2 else "todo"
            completed_at = None
            if status == "done" and t.get("completedTime"):
                try:
                    completed_at = datetime.fromtimestamp(t["completedTime"] / 1000)
                except (ValueError, OSError):
                    pass

            due_date = None
            if t.get("dueDate"):
                try:
                    due_date = datetime.fromtimestamp(t["dueDate"] / 1000)
                except (ValueError, OSError):
                    pass

            tags_list = t.get("tags", []) or []

            if task:
                await db.execute(
                    update(Task).where(Task.id == task.id).values(
                        title=t.get("title", task.title),
                        status=status,
                        completed_at=completed_at,
                        due_date=due_date,
                        tags=tags_list,
                        project_id=project_id or task.project_id,
                        updated_at=datetime.now(),
                    )
                )
            else:
                db.add(Task(
                    ticktick_id=ticktick_id,
                    project_id=project_id,
                    title=t.get("title", "未命名任务"),
                    content=t.get("content", ""),
                    status=status,
                    completed_at=completed_at,
                    due_date=due_date,
                    tags=tags_list,
                    priority=t.get("priority", 0),
                ))
                synced += 1

        await db.commit()
        logger.info(f"同步了 {synced} 个任务")
        return synced

    async def complete_task_api(self, ticktick_id: str, project_id: str = "") -> bool:
        """在 TickTick 上完成任务"""
        if project_id:
            path = f"/open/v1/project/{project_id}/task/{ticktick_id}/complete"
        else:
            path = f"/open/v1/task/{ticktick_id}/complete"
        result = await self._api_post(path)
        return result is not None

    async def create_task_api(self, title: str, priority: int = 0,
                               due_date: datetime | None = None,
                               tags: list[str] | None = None) -> str | None:
        """在 TickTick 上创建任务，返回任务 ID"""
        payload = {
            "title": title,
            "priority": priority,
        }
        if due_date:
            payload["dueDate"] = int(due_date.timestamp() * 1000)
        if tags:
            payload["tags"] = tags
        result = await self._api_post("/open/v1/task", payload)
        if result:
            return result.get("id")
        return None


# 全局单例
ticktick_client = TickTickClient()
