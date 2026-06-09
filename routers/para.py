"""PARA 标签相关 API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import User
from routers.auth import get_current_user
from services.para_service import get_tag_tree, create_tag, update_tag, delete_tag, search_tags

router = APIRouter(prefix="/api/para", tags=["para"])


class CreateTagRequest(BaseModel):
    full_path: str
    label: str | None = None


@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_session),
                    user: User = Depends(get_current_user)):
    """获取 PARA 标签树"""
    tree = await get_tag_tree(db, user_id=user.id)
    return tree


@router.post("/tags")
async def add_tag(req: CreateTagRequest,
                  db: AsyncSession = Depends(get_session),
                  user: User = Depends(get_current_user)):
    """创建新标签"""
    if not req.full_path or req.full_path.strip() == "":
        raise HTTPException(status_code=400, detail="标签路径不能为空")

    tag = await create_tag(db, req.full_path.strip(), req.label, user_id=user.id)
    return {
        "id": tag.id,
        "full_path": tag.full_path,
        "category": tag.category,
        "label": tag.label,
    }


class UpdateTagRequest(BaseModel):
    label: str


@router.put("/tags/{tag_id}")
async def edit_tag(tag_id: int, req: UpdateTagRequest,
                   db: AsyncSession = Depends(get_session)):
    """修改标签名称"""
    if not req.label or req.label.strip() == "":
        raise HTTPException(status_code=400, detail="标签名称不能为空")

    try:
        tag = await update_tag(db, tag_id, req.label.strip())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "id": tag.id,
        "full_path": tag.full_path,
        "category": tag.category,
        "label": tag.label,
    }


@router.delete("/tags/{tag_id}")
async def remove_tag(tag_id: int, db: AsyncSession = Depends(get_session)):
    """删除标签"""
    await delete_tag(db, tag_id)
    return {"message": "已删除"}


@router.get("/tags/search")
async def search(q: str,
                 db: AsyncSession = Depends(get_session),
                 user: User = Depends(get_current_user)):
    """搜索标签"""
    tags = await search_tags(db, q, user_id=user.id)
    return [
        {
            "id": t.id,
            "full_path": t.full_path,
            "category": t.category,
            "label": t.label,
        }
        for t in tags
    ]
