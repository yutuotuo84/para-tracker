"""任务相关 API 路由"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Task, Project, Memo, User
from routers.auth import get_current_user
from services.ticktick_service import ticktick_client

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    title: str
    content: str = ""
    priority: int = 0  # 0=none, 1=low, 3=medium, 5=high
    due_date: str | None = None
    tags: list[str] = []
    project_id: int | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    priority: int | None = None
    due_date: str | None = None
    tags: list[str] | None = None


@router.put("/{task_id}")
async def update_task(task_id: int, req: UpdateTaskRequest,
                      db: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """编辑任务"""
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_values = {}
    if req.title is not None:
        if not req.title.strip():
            raise HTTPException(status_code=400, detail="任务标题不能为空")
        update_values["title"] = req.title.strip()
    if req.content is not None:
        update_values["content"] = req.content
    if req.priority is not None:
        update_values["priority"] = req.priority
    if req.tags is not None:
        update_values["tags"] = req.tags
    if req.due_date is not None:
        try:
            update_values["due_date"] = datetime.fromisoformat(req.due_date) if req.due_date else None
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效")

    if update_values:
        update_values["updated_at"] = datetime.now()
        await db.execute(update(Task).where(Task.id == task_id).values(**update_values))
        await db.commit()

    # 重新读取并返回
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one()
    return {
        "id": task.id,
        "title": task.title,
        "content": task.content,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "tags": task.tags or [],
        "status": task.status,
    }


@router.post("")
async def create_task(req: CreateTaskRequest,
                      db: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """创建新任务"""
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="任务标题不能为空")

    due_date = None
    if req.due_date:
        try:
            due_date = datetime.fromisoformat(req.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，请使用 ISO 格式")

    task = Task(
        title=req.title.strip(),
        content=req.content,
        priority=req.priority,
        due_date=due_date,
        tags=req.tags,
        project_id=req.project_id,
        status="todo",
        user_id=user.id,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 同步到 TickTick（如果已认证）
    if ticktick_client.authenticated:
        await ticktick_client.create_task_api(
            title=task.title,
            priority=task.priority,
            due_date=due_date,
            tags=task.tags or [],
        )

    return {
        "id": task.id,
        "title": task.title,
        "priority": task.priority,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "tags": task.tags or [],
        "status": task.status,
        "created_at": task.created_at.isoformat(),
    }


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    project_id: Optional[int] = None,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取任务列表"""
    query = select(Task).where(Task.user_id == user.id)
    if status:
        query = query.where(Task.status == status)
    if project_id:
        query = query.where(Task.project_id == project_id)
    query = query.order_by(Task.priority.desc(), Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        {
            "id": t.id,
            "ticktick_id": t.ticktick_id,
            "title": t.title,
            "content": t.content,
            "status": t.status,
            "priority": t.priority,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "project_id": t.project_id,
            "tags": t.tags or [],
            "para_tags": t.to_para_tags(),
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


@router.get("/recent-tags")
async def recent_tags(db: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """获取最近使用的标签（从任务和笔记中收集）"""
    # 从任务的 tags 中收集最近 20 条有标签的记录
    task_result = await db.execute(
        select(Task.tags).where(
            Task.user_id == user.id,
            Task.tags.isnot(None), Task.tags != "[]"
        ).order_by(Task.created_at.desc()).limit(20)
    )
    # 从笔记的 tags 中收集
    memo_result = await db.execute(
        select(Memo.tags).where(
            Memo.user_id == user.id,
            Memo.tags.isnot(None), Memo.tags != "[]"
        ).order_by(Memo.created_at.desc()).limit(20)
    )

    seen = set()
    tags_list = []
    for row in task_result.scalars().all():
        for tag in (row or []):
            if tag and tag not in seen:
                seen.add(tag)
                tags_list.append(tag)
    for row in memo_result.scalars().all():
        for tag in (row or []):
            if tag and tag not in seen:
                seen.add(tag)
                tags_list.append(tag)

    return tags_list[:10]


@router.post("/{task_id}/toggle")
async def toggle_task(task_id: int,
                      db: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """切换任务完成/未完成状态"""
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    now = datetime.now()

    if task.status == "done":
        # 恢复到未完成
        await db.execute(
            update(Task).where(Task.id == task_id).values(
                status="todo", completed_at=None, updated_at=now
            )
        )
        await db.commit()
        return {"action": "uncompleted", "task_id": task_id}
    else:
        # 标记完成
        await db.execute(
            update(Task).where(Task.id == task_id).values(
                status="done", completed_at=now, updated_at=now
            )
        )
        await db.commit()

        # 同步到 TickTick
        if task.ticktick_id:
            await ticktick_client.complete_task(task.ticktick_id)

        # 获取项目 PARA 标签
        para_tags = []
        if task.project_id:
            proj = await db.execute(select(Project).where(Project.id == task.project_id))
            p = proj.scalar_one_or_none()
            if p and p.para_category:
                para_tags.append(f"{p.para_category}/{p.name}")

        return {
            "action": "completed",
            "task": {"id": task.id, "title": task.title},
            "suggested_tags": para_tags + (task.tags or []),
        }


@router.delete("/{task_id}")
async def delete_task(task_id: int,
                      db: AsyncSession = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """删除任务"""
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 同时删除关联笔记
    await db.execute(delete(Memo).where(Memo.task_id == task_id))
    await db.delete(task)
    await db.commit()
    return {"message": "已删除"}


@router.get("/recently-completed")
async def recently_completed(
    since: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """获取最近完成的任务"""
    query = select(Task).where(Task.status == "done", Task.user_id == user.id).order_by(Task.completed_at.desc()).limit(20)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "project_id": t.project_id,
        }
        for t in tasks
    ]
