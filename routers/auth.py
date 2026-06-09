"""认证和同步相关 API 路由"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_session
from services.ticktick_service import ticktick_client, TICKTICK_OAUTH_AUTH
from services.flomo_service import flomo_client
from services.summary_service import summary_service
from services.para_service import seed_para_tags

router = APIRouter(prefix="/api", tags=["auth"])

# 简单的内存 session 存储（单用户足够）
_session_token: str | None = None


def require_auth(request: Request):
    """验证请求是否已登录（被 middleware 调用）"""
    if not settings.app_password:
        return True  # 未设置密码，不验证
    token = request.cookies.get("session")
    return token == _session_token


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str = ""


@router.post("/auth/login")
async def login(req: LoginRequest, response: Response):
    """登录验证"""
    global _session_token
    if req.password == settings.app_password:
        _session_token = secrets.token_hex(32)
        response.set_cookie(
            key="session",
            value=_session_token,
            httponly=True,
            max_age=86400 * 30,  # 30天
            samesite="lax",
        )
        return LoginResponse(success=True, message="登录成功")
    raise HTTPException(status_code=401, detail="密码错误")


@router.post("/auth/logout")
async def logout(response: Response):
    """退出登录"""
    global _session_token
    _session_token = None
    response.delete_cookie("session")
    return {"message": "已退出"}


@router.get("/auth/check")
async def check_auth(request: Request):
    """检查是否已登录"""
    return {"authenticated": require_auth(request)}


class TickTickPasswordAuth(BaseModel):
    username: str
    password: str


class TickTickOAuth(BaseModel):
    client_id: str
    client_secret: str
    auth_code: str


class FlomoConfig(BaseModel):
    api_url: str


class AIConfig(BaseModel):
    api_key: str
    api_base: str = ""
    model: str = "gpt-4o-mini"


@router.get("/auth/ticktick/url")
async def get_oauth_url():
    """获取 TickTick OAuth 授权 URL"""
    if not settings.ticktick_client_id:
        return {"url": None, "error": "未配置 Client ID"}
    url = (
        f"{TICKTICK_OAUTH_AUTH}?"
        f"client_id={settings.ticktick_client_id}&"
        f"redirect_uri={settings.ticktick_redirect_uri}&"
        f"response_type=code"
    )
    return {"url": url}


@router.post("/auth/ticktick/oauth")
async def auth_ticktick_oauth(config: TickTickOAuth):
    """使用 OAuth2 授权码认证 TickTick"""
    success = await ticktick_client.authenticate_oauth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=settings.ticktick_redirect_uri,
        auth_code=config.auth_code,
    )
    if not success:
        raise HTTPException(status_code=401, detail="TickTick 认证失败")
    return {"message": "TickTick OAuth 认证成功"}


@router.post("/auth/ticktick/password")
async def auth_ticktick_password(config: TickTickPasswordAuth):
    """使用密码登录 TickTick (V2 Session API)"""
    success = await ticktick_client.authenticate_password(
        username=config.username,
        password=config.password,
    )
    if not success:
        raise HTTPException(status_code=401, detail="TickTick 登录失败，请检查用户名密码")
    return {"message": "TickTick 登录成功"}


@router.get("/auth/ticktick/status")
async def ticktick_status():
    return {"authenticated": ticktick_client.authenticated}


@router.post("/auth/flomo")
async def auth_flomo(config: FlomoConfig):
    if not config.api_url.strip():
        raise HTTPException(status_code=400, detail="Flomo API URL 不能为空")
    flomo_client.configure(config.api_url)
    return {"message": "Flomo API 已配置"}


@router.get("/auth/flomo/status")
async def flomo_status():
    return {"enabled": flomo_client.enabled}


@router.post("/auth/ai")
async def auth_ai(config: AIConfig):
    summary_service.configure(config.api_key, config.api_base, config.model)
    return {"message": "AI 摘要已配置"}


@router.get("/auth/ai/status")
async def ai_status():
    return {"enabled": summary_service.enabled, "model": summary_service.model}


@router.post("/sync/run")
async def run_sync(db: AsyncSession = Depends(get_session)):
    """手动触发全量同步"""
    results = {}
    if ticktick_client.authenticated:
        projects = await ticktick_client.sync_projects(db)
        tasks = await ticktick_client.sync_tasks(db)
        results["projects"] = projects
        results["tasks"] = tasks
    else:
        results["error"] = "TickTick 未认证"

    await seed_para_tags(db)
    results["para_seeded"] = True

    return {"message": "同步完成", "results": results}


@router.get("/sync/status")
async def sync_status():
    return {
        "ticktick": ticktick_client.authenticated,
        "flomo": flomo_client.enabled,
        "ai_summary": summary_service.enabled,
    }
