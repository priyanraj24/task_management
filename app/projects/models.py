from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ProjectUser(Base):
    __tablename__ = "project_users"
    __hidden_fields__ = {"is_deleted", "deleted_at"}

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="project_assignments")
    user = relationship("User", foreign_keys=[user_id], back_populates="project_assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String)
    status = Column(String(20), default="planned")
    start_date = Column(Date)
    end_date = Column(Date)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", foreign_keys=[created_by], back_populates="created_projects")
    project_assignments = relationship("ProjectUser", back_populates="project", lazy="joined")
    tasks = relationship("Task", back_populates="project")

    @property
    def assignees(self):
        return [pa.user for pa in self.project_assignments if not pa.is_deleted]

    @property
    def assignee_ids(self):
        return [pa.user_id for pa in self.project_assignments if not pa.is_deleted]

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
