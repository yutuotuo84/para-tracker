"""每日总结生成服务"""

import logging
from datetime import date, datetime
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import DailySummary, Memo, Task

logger = logging.getLogger(__name__)


class SummaryService:
    """每日总结服务"""

    def __init__(self):
        self.openai_api_key: str = ""
        self.openai_base_url: str = "https://api.openai.com/v1"
        self.model: str = "gpt-4o-mini"
        self.enabled: bool = False

    def configure(self, api_key: str, base_url: str = "", model: str = "gpt-4o-mini"):
        self.openai_api_key = api_key
        self.enabled = bool(api_key)
        if base_url:
            self.openai_base_url = base_url.rstrip("/")
        if model:
            self.model = model
        logger.info(f"AI 摘要 {'已启用' if self.enabled else '未启用 (将使用模板)'}")

    async def get_today_data(self, db: AsyncSession, target_date: date | None = None) -> dict:
        """获取指定日期的任务和笔记数据"""
        d = target_date or date.today()
        start = datetime(d.year, d.month, d.day)
        end = datetime(d.year, d.month, d.day, 23, 59, 59)

        # 查询今日完成的任务
        tasks_result = await db.execute(
            select(Task).where(
                Task.status == "done",
                Task.completed_at >= start,
                Task.completed_at <= end,
            ).order_by(Task.completed_at)
        )
        completed_tasks = tasks_result.scalars().all()

        # 查询今日创建的笔记
        memos_result = await db.execute(
            select(Memo).where(
                Memo.created_at >= start,
                Memo.created_at <= end,
            ).order_by(Memo.created_at)
        )
        today_memos = memos_result.scalars().all()

        # 查询待办任务
        pending_result = await db.execute(
            select(Task).where(Task.status == "todo").order_by(Task.priority.desc())
        )
        pending_tasks = pending_result.scalars().all()

        return {
            "date": d.isoformat(),
            "completed_tasks": [
                {"title": t.title, "completed_at": t.completed_at.isoformat() if t.completed_at else ""}
                for t in completed_tasks
            ],
            "memos": [
                {"content": m.content[:200], "tags": m.tags, "source": m.source}
                for m in today_memos
            ],
            "pending_tasks": [
                {"title": t.title, "priority": t.priority}
                for t in pending_tasks[:10]
            ],
        }

    def _build_template_summary(self, data: dict) -> str:
        """使用模板生成简单总结（无 AI 时的后备方案）"""
        lines = [f"## {data['date']} 日总结\n"]

        # 完成任务
        completed = data["completed_tasks"]
        lines.append(f"### ✅ 今日完成 ({len(completed)} 项)")
        if completed:
            for t in completed:
                lines.append(f"- {t['title']}")
        else:
            lines.append("- 今日无完成任务")

        # 笔记
        memos = data["memos"]
        lines.append(f"\n### 📝 今日记录 ({len(memos)} 条)")
        if memos:
            for m in memos:
                tag_str = " ".join(f"#{t}" for t in (m["tags"] or []))
                lines.append(f"- {m['content'][:100]} {tag_str}")
        else:
            lines.append("- 今日无笔记记录")

        # 待办建议
        pending = data["pending_tasks"]
        lines.append(f"\n### 📋 待处理 ({len(pending)} 项)")
        if pending:
            for t in pending[:5]:
                lines.append(f"- {t['title']}")
        else:
            lines.append("- 暂无待办任务")

        lines.append("\n---\n> 自动生成 | 使用 `dotenv` 配置 AI API 密钥可获取更智能的总结")
        return "\n".join(lines)

    async def _build_ai_summary(self, data: dict) -> tuple[str, list[str]]:
        """调用 AI 生成智能总结和建议"""
        if not self.enabled:
            summary = self._build_template_summary(data)
            return summary, ["暂无建议 — 配置 AI 密钥后可获得智能建议。"]

        prompt = f"""你是一个个人生产力助手。根据用户今天的数据，生成一份简洁的每日总结。

今日日期: {data['date']}

已完成任务 ({len(data['completed_tasks'])}项):
{chr(10).join(f"- {t['title']}" for t in data['completed_tasks']) or '- 无'}

今日笔记 ({len(data['memos'])}条):
{chr(10).join(f"- {m['content'][:100]}" for m in data['memos']) or '- 无'}

待办任务 ({len(data['pending_tasks'])}项):
{chr(10).join(f"- {t['title']}" for t in data['pending_tasks'][:10]) or '- 无'}

请提供(用中文):
1. **今日亮点**: 1-2句话总结今日最有价值的完成事项
2. **明日建议**: 3-5条明日应该优先处理的事项建议及理由

注意: 简洁有洞察力，不要啰嗦。"""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.openai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 800,
                    },
                )
                if resp.is_success:
                    result = resp.json()
                    text = result["choices"][0]["message"]["content"]
                    # 从文本中提取总结和建议
                    summary = text
                    suggestions = []

                    if "**明日建议**" in text:
                        parts = text.split("**明日建议**")
                        summary = parts[0].strip()
                        suggestion_text = parts[1] if len(parts) > 1 else ""
                        suggestions = [
                            line.strip().lstrip("-1234567890. ")
                            for line in suggestion_text.split("\n")
                            if line.strip() and not line.strip().startswith("#")
                        ][:5]

                    return summary, suggestions
                else:
                    logger.error(f"AI API 错误: {resp.status_code}")
                    return self._build_template_summary(data), []
        except Exception as e:
            logger.error(f"AI 请求失败: {e}")
            return self._build_template_summary(data), []

    async def generate_summary(self, db: AsyncSession,
                                target_date: date | None = None) -> DailySummary:
        """生成并保存每日总结"""
        d = target_date or date.today()
        data = await self.get_today_data(db, d)

        summary_text, suggestions = await self._build_ai_summary(data)

        # 查找是否已有今天的总结
        existing = await db.execute(
            select(DailySummary).where(DailySummary.date == d.isoformat())
        )
        summary = existing.scalar_one_or_none()

        if summary:
            summary.summary_text = summary_text
            summary.suggestions = suggestions
            summary.completed_tasks = [t["title"] for t in data["completed_tasks"]]
            summary.memos = data["memos"]
            summary.updated_at = datetime.now()
        else:
            summary = DailySummary(
                date=d.isoformat(),
                completed_tasks=[t["title"] for t in data["completed_tasks"]],
                memos=data["memos"],
                summary_text=summary_text,
                suggestions=suggestions,
            )
            db.add(summary)

        await db.commit()
        await db.refresh(summary)
        return summary


summary_service = SummaryService()
