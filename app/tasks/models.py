from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __hidden_fields__ = {"is_deleted", "deleted_at"}

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="task_assignments")
    user = relationship("User", foreign_keys=[user_id], back_populates="task_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String)
    status = Column(String(20), default="todo", nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    due_date = Column(Date)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    task_assignments = relationship("TaskAssignment", back_populates="task", lazy="joined")
    attachments = relationship("Attachment", back_populates="task")
    history = relationship("TaskHistory", back_populates="task")

    @property
    def assignees(self):
        return [ta.user for ta in self.task_assignments if not ta.is_deleted]

    @property
    def assignee_ids(self):
        return [ta.user_id for ta in self.task_assignments if not ta.is_deleted]

    def to_dict(self):
        from app.database import BASE_HIDDEN
        hidden = BASE_HIDDEN | self.__class__.__hidden_fields__
        result = {}
        from sqlalchemy import inspect
        for c in inspect(self.__class__).mapper.column_attrs:
            if c.key in hidden:
                continue
            v = getattr(self, c.key)
            from datetime import datetime, date
            if isinstance(v, (datetime, date)):
                v = v.isoformat()
            result[c.key] = v
        result["assigned_to"] = [{"id": u.id, "name": u.name, "role": u.role} for u in self.assignees]
        return result


class TaskHistory(Base):
    __hidden_fields__ = {"is_deleted", "deleted_at"}
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    old_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="history")


class Attachment(Base):
    __tablename__ = "attachments"
    __hidden_fields__ = {"file_path", "stored_filename"}

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="attachments")
    uploader = relationship("User", back_populates="uploaded_attachments")
