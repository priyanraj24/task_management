from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __hidden_fields__ = {"password_hash"}
    __unique_fields__ = ["email"]

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String(20), default="employee", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_projects = relationship("Project", foreign_keys="Project.created_by", back_populates="creator")
    assigned_projects = relationship("Project", foreign_keys="Project.assigned_to", back_populates="manager")
    created_tasks = relationship("Task", foreign_keys="Task.created_by", back_populates="creator")
    assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to", back_populates="assignee")
    uploaded_attachments = relationship("Attachment", back_populates="uploader")
