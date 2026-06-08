"""笔记相关 API 路由"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Memo, Task, Project
from services.flomo_service import flomo_client

router = APIRouter(prefix="/api/memos", tags=["memos"])


class CreateMemoRequest(BaseModel):
    content: str
    tags: list[str] = []
    task_id: Optional[int] = None
    source: str = "free_write"


class CreateTaskMemoRequest(BaseModel):
    content: str
    tags: list[str] = []
    task_id: int


@router.get("")
async def list_memos(
    source: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """获取笔记列表"""
    query = select(Memo).order_by(Memo.created_at.desc()).limit(limit)
    if source:
        query = select(Memo).where(Memo.source == source).order_by(Memo.created_at.desc()).limit(limit)

    result = await db.execute(query)
    memos = result.scalars().all()

    return [
        {
            "id": m.id,
            "content": m.content,
            "tags": m.tags or [],
            "task_id": m.task_id,
            "source": m.source,
            "created_at": m.created_at.isoformat(),
        }
        for m in memos
    ]


@router.post("")
async def create_memo(
    req: CreateMemoRequest,
    db: AsyncSession = Depends(get_session),
):
    """创建自由笔记"""
    memo = await flomo_client.sync_memo_to_db(
        db=db,
        content=req.content,
        tags=req.tags,
        source=req.source,
        task_id=req.task_id,
    )

    return {
        "id": memo.id,
        "content": memo.content,
        "tags": memo.tags,
        "source": memo.source,
        "created_at": memo.created_at.isoformat(),
    }


@router.post("/from-task")
async def create_task_memo(
    req: CreateTaskMemoRequest,
    db: AsyncSession = Depends(get_session),
):
    """为完成任务创建感想笔记"""
    # 验证任务存在
    result = await db.execute(select(Task).where(Task.id == req.task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 构建完整内容
    full_content = f"## ✅ 完成: {task.title}\n\n{req.content}"

    # 合并任务自身的标签和项目 PARA 标签到笔记标签中
    para_tags = []
    if task.project_id:
        proj = await db.execute(select(Project).where(Project.id == task.project_id))
        p = proj.scalar_one_or_none()
        if p and p.para_category:
            para_tags.append(f"{p.para_category}/{p.name}")
    all_tags = list(dict.fromkeys(para_tags + (task.tags or []) + req.tags))

    memo = await flomo_client.sync_memo_to_db(
        db=db,
        content=full_content,
        tags=all_tags,
        source="task_completion",
        task_id=req.task_id,
    )

    return {
        "id": memo.id,
        "content": memo.content,
        "tags": memo.tags,
        "task_id": memo.task_id,
        "source": memo.source,
        "created_at": memo.created_at.isoformat(),
    }


class UpdateMemoRequest(BaseModel):
    content: str
    tags: list[str] = []


@router.put("/{memo_id}")
async def update_memo(
    memo_id: int,
    req: UpdateMemoRequest,
    db: AsyncSession = Depends(get_session),
):
    """修改笔记内容"""
    result = await db.execute(select(Memo).where(Memo.id == memo_id))
    memo = result.scalar_one_or_none()
    if not memo:
        raise HTTPException(status_code=404, detail="笔记不存在")

    memo.content = req.content
    memo.tags = req.tags
    await db.commit()
    await db.refresh(memo)

    return {
        "id": memo.id,
        "content": memo.content,
        "tags": memo.tags,
        "task_id": memo.task_id,
        "source": memo.source,
        "created_at": memo.created_at.isoformat(),
    }


@router.delete("/{memo_id}")
async def delete_memo(memo_id: int, db: AsyncSession = Depends(get_session)):
    """删除笔记"""
    result = await db.execute(select(Memo).where(Memo.id == memo_id))
    memo = result.scalar_one_or_none()
    if not memo:
        raise HTTPException(status_code=404, detail="笔记不存在")

    await db.delete(memo)
    await db.commit()
    return {"message": "已删除"}
