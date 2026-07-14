from datetime import datetime, date, timezone

from sqlalchemy import create_engine, inspect, Column, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine,
)


BASE_HIDDEN = {"is_deleted", "deleted_at", "updated_at"}


class BaseModel:
    __hidden_fields__ = set()

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        hidden = BASE_HIDDEN | self.__hidden_fields__
        result = {}
        for c in inspect(self.__class__).mapper.column_attrs:
            if c.key in hidden:
                continue
            v = getattr(self, c.key)
            if isinstance(v, (datetime, date)):
                v = v.isoformat()
            result[c.key] = v
        return result

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        timestamp = int(self.deleted_at.timestamp())
        for field in getattr(self, "__unique_fields__", []):
            current = getattr(self, field)
            if current:
                setattr(self, field, f"{current}_deleted_{timestamp}")


Base = declarative_base(cls=BaseModel)





def paginate(query, page: int, limit: int):
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return items, total


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
