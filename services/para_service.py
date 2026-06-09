"""PARA 标签管理器"""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import ParaTag


# 初始四大分类
INITIAL_CATEGORIES = [
    ("01-Projects", "Projects", "有明确目标和截止日期的短期项目", 1),
    ("02-Areas", "Areas", "长期负责的生活/工作领域", 2),
    ("03-Resources", "Resources", "感兴趣的主题和参考资源", 3),
    ("04-Archives", "Archives", "已完成或不再活跃的内容", 4),
]


async def seed_para_tags(db: AsyncSession, user_id: int = 1):
    """初始化 PARA 四大分类标签"""
    for cat, label, _, order in INITIAL_CATEGORIES:
        exists = await db.execute(
            select(ParaTag).where(ParaTag.category == cat, ParaTag.user_id == user_id)
        )
        if not exists.scalars().first():
            tag = ParaTag(
                full_path=f"{cat}/",
                category=cat,
                label=label,
                sort_order=order,
                user_id=user_id,
            )
            db.add(tag)
    await db.commit()


async def get_tag_tree(db: AsyncSession, user_id: int = 1) -> list[dict]:
    """获取完整的 PARA 标签树"""
    result = await db.execute(
        select(ParaTag)
        .where(ParaTag.user_id == user_id)
        .order_by(ParaTag.sort_order, ParaTag.label)
    )
    tags = result.scalars().all()

    # 构建树形结构
    root = []
    for tag in tags:
        if tag.parent_id is None:
            children = [t for t in tags if t.parent_id == tag.id]
            root.append({
                "id": tag.id,
                "full_path": tag.full_path,
                "category": tag.category,
                "label": tag.label,
                "children": [
                    {
                        "id": c.id,
                        "full_path": c.full_path,
                        "category": c.category,
                        "label": c.label,
                    }
                    for c in children
                ],
            })
    return root


async def create_tag(db: AsyncSession, full_path: str, label: str | None = None,
                     user_id: int = 1) -> ParaTag:
    """创建新的 PARA 标签"""
    category = full_path.split("/")[0] if "/" in full_path else full_path
    tag_label = label or full_path.split("/")[-1]

    # 查找父标签（种子标签 full_path 带尾部斜杠，如 "01-Projects/"）
    parent_path = "/".join(full_path.split("/")[:-1])
    parent = None
    if parent_path:
        # 先试不带斜杠，再试带斜杠
        result = await db.execute(
            select(ParaTag).where(ParaTag.full_path == parent_path, ParaTag.user_id == user_id)
        )
        parent = result.scalar_one_or_none()
        if not parent:
            result = await db.execute(
                select(ParaTag).where(ParaTag.full_path == f"{parent_path}/", ParaTag.user_id == user_id)
            )
            parent = result.scalar_one_or_none()

    tag = ParaTag(
        full_path=full_path,
        category=category,
        label=tag_label,
        parent_id=parent.id if parent else None,
        user_id=user_id,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(db: AsyncSession, tag_id: int, new_label: str) -> ParaTag:
    """修改标签名称"""
    result = await db.execute(select(ParaTag).where(ParaTag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise ValueError("标签不存在")

    # 更新 label 和 full_path
    tag.label = new_label
    parts = tag.full_path.split("/")
    if len(parts) >= 2:
        tag.full_path = f"{parts[0]}/{new_label}"
    else:
        tag.full_path = f"{tag.category}/{new_label}"
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag_id: int):
    """删除标签及其子标签"""
    await db.execute(delete(ParaTag).where(ParaTag.id == tag_id))
    await db.commit()


async def search_tags(db: AsyncSession, query: str, user_id: int = 1) -> list[ParaTag]:
    """搜索标签"""
    result = await db.execute(
        select(ParaTag).where(
            ParaTag.user_id == user_id,
            ParaTag.full_path.ilike(f"%{query}%"),
        )
    )
    return result.scalars().all()
