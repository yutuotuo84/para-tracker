"""SQLAlchemy 数据模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticktick_id = Column(String(64), unique=True, nullable=True)
    name = Column(String(255), nullable=False)
    para_category = Column(String(20), nullable=True)  # 01-Projects/02-Areas/03-Resources/04-Archives
    color = Column(String(20), default="#6366f1")
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    tasks = relationship("Task", back_populates="project")

    def __repr__(self):
        return f"<Project {self.name} ({self.para_category})>"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticktick_id = Column(String(64), unique=True, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="todo")  # todo / done
    completed_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    priority = Column(Integer, default=0)  # 0=none, 1=low, 3=medium, 5=high
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    project = relationship("Project", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.title} [{self.status}]>"

    def to_para_tags(self) -> list[str]:
        """根据任务的项目和标签生成建议的 PARA 标签"""
        tags = []
        if self.project and self.project.para_category:
            para_path = f"{self.project.para_category}/{self.project.name}"
            tags.append(para_path)
        if self.tags:
            tags.extend(self.tags)
        return tags


class Memo(Base):
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flomo_id = Column(String(64), unique=True, nullable=True)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    source = Column(String(20), default="free_write")  # task_completion / free_write
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Memo #{self.id} [{self.source}]>"


class ParaTag(Base):
    __tablename__ = "para_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_path = Column(String(255), unique=True, nullable=False)  # e.g. "01-Projects/网站开发"
    category = Column(String(20), nullable=False)  # 01-Projects/02-Areas/03-Resources/04-Archives
    label = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("para_tags.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    children = relationship("ParaTag", backref="parent", remote_side=[id], cascade="all")

    def __repr__(self):
        return f"<ParaTag {self.full_path}>"


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    completed_tasks = Column(JSON, default=list)
    memos = Column(JSON, default=list)
    summary_text = Column(Text, nullable=True)
    suggestions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(20), nullable=False)  # task / memo / project
    entity_id = Column(String(64), nullable=True)
    action = Column(String(20), nullable=False)  # sync / create / update / delete
    status = Column(String(20), default="success")  # success / failed
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
