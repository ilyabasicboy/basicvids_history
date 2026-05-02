from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field as PydanticField


class VideoWatchHistoryUpsert(BaseModel):
    last_position_seconds: float | None = PydanticField(default=None, ge=0)
    duration_seconds: float | None = PydanticField(default=None, ge=0)
    completed: bool = False


class VideoWatchHistoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    user_id: int
    last_position_seconds: float | None = None
    duration_seconds: float | None = None
    completed: bool
    view_count: int
    first_viewed_at: datetime
    last_viewed_at: datetime
    created_at: datetime
    updated_at: datetime


class VideoWatchHistoryList(BaseModel):
    items: list[VideoWatchHistoryPublic]
    count: int


class VideoWatchHistoryDeleteResponse(BaseModel):
    message: str
