from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VideoWatchHistory(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("video_id", "user_id", name="uq_watch_history_video_user"),)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    video_id: str = Field(index=True, max_length=100)
    user_id: int = Field(index=True)
    last_position_seconds: float | None = Field(default=None, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    completed: bool = Field(default=False)
    view_count: int = Field(default=1, ge=1)
    first_viewed_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
    last_viewed_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
    updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        default_factory=utc_now,
        nullable=False,
    )
