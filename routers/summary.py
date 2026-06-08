"""每日总结相关 API 路由"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import DailySummary
from services.summary_service import summary_service

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("/today")
async def get_today_summary(db: AsyncSession = Depends(get_session)):
    """获取今日总结（如果已生成）"""
    today = date.today().isoformat()
    result = await db.execute(
        select(DailySummary).where(DailySummary.date == today)
    )
    summary = result.scalar_one_or_none()

    if not summary:
        return {
            "date": today,
            "has_summary": False,
            "summary_text": None,
            "suggestions": [],
            "completed_tasks": [],
            "memos": [],
        }

    return {
        "date": summary.date,
        "has_summary": True,
        "summary_text": summary.summary_text,
        "suggestions": summary.suggestions or [],
        "completed_tasks": summary.completed_tasks or [],
        "memos": summary.memos or [],
        "created_at": summary.created_at.isoformat(),
    }


@router.post("/generate")
async def generate_summary(db: AsyncSession = Depends(get_session)):
    """触发今日总结生成"""
    data = await summary_service.get_today_data(db)

    # 如果没有完成任务和笔记，返回提示
    if not data["completed_tasks"] and not data["memos"]:
        return {
            "message": "今天还没有完成任务或记录笔记，暂无总结可生成。",
            "data": data,
            "summary": None,
        }

    summary = await summary_service.generate_summary(db)
    return {
        "message": "总结生成成功",
        "summary": {
            "date": summary.date,
            "summary_text": summary.summary_text,
            "suggestions": summary.suggestions or [],
            "completed_count": len(data["completed_tasks"]),
            "memo_count": len(data["memos"]),
        },
    }


@router.get("/history")
async def get_summary_history(limit: int = 7, db: AsyncSession = Depends(get_session)):
    """获取历史总结"""
    result = await db.execute(
        select(DailySummary).order_by(DailySummary.date.desc()).limit(limit)
    )
    summaries = result.scalars().all()

    return [
        {
            "date": s.date,
            "summary_text": s.summary_text[:200] if s.summary_text else None,
            "completed_count": len(s.completed_tasks or []),
            "memo_count": len(s.memos or []),
        }
        for s in summaries
    ]
