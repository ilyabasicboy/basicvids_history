from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, col, delete, select

from basicvids_history.auth import CurrentUser, get_current_user
from basicvids_history.db import get_session
from basicvids_history.models.history import (
    VideoWatchHistoryDeleteResponse,
    VideoWatchHistoryList,
    VideoWatchHistoryPublic,
    VideoWatchHistoryUpsert,
)
from basicvids_history.rate_limit import client_identifier, enforce_rate_limit
from basicvids_history.schemas.history import VideoWatchHistory


router = APIRouter(tags=["History"], prefix="/history")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_user_history_row(session: Session, video_id: str, user_id: int) -> VideoWatchHistory | None:
    return session.exec(
        select(VideoWatchHistory).where(
            VideoWatchHistory.video_id == video_id,
            VideoWatchHistory.user_id == user_id,
        )
    ).first()


@router.put("/videos/{video_id}", response_model=VideoWatchHistoryPublic)
async def upsert_video_watch_history(
    video_id: str,
    data: VideoWatchHistoryUpsert,
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> VideoWatchHistory:
    await enforce_rate_limit("upsert_history_ip", client_identifier(request), 180, 60)
    await enforce_rate_limit("upsert_history_user", f"user:{current_user.id}", 180, 60)

    history_row = get_user_history_row(session, video_id, current_user.id)
    now = utc_now()

    if not history_row:
        history_row = VideoWatchHistory(
            video_id=video_id,
            user_id=current_user.id,
            last_position_seconds=data.last_position_seconds,
            duration_seconds=data.duration_seconds,
            completed=data.completed,
            view_count=1,
            first_viewed_at=now,
            last_viewed_at=now,
        )
    else:
        history_row.last_position_seconds = data.last_position_seconds
        history_row.duration_seconds = data.duration_seconds
        history_row.completed = data.completed
        history_row.view_count += 1
        history_row.last_viewed_at = now
        history_row.updated_at = now

    session.add(history_row)
    session.commit()
    session.refresh(history_row)
    return history_row


@router.get("/videos/", response_model=VideoWatchHistoryList)
async def list_video_watch_history(
    offset: int = 0,
    limit: int = Query(default=20, le=100),
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> VideoWatchHistoryList:
    statement = (
        select(VideoWatchHistory)
        .where(VideoWatchHistory.user_id == current_user.id)
        .order_by(col(VideoWatchHistory.last_viewed_at).desc())
        .offset(offset)
        .limit(limit)
    )
    items = session.exec(statement).all()
    return VideoWatchHistoryList(
        items=[VideoWatchHistoryPublic.model_validate(item) for item in items],
        count=len(items),
    )


@router.get("/videos/{video_id}", response_model=VideoWatchHistoryPublic)
async def get_video_watch_history(
    video_id: str,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> VideoWatchHistory:
    history_row = get_user_history_row(session, video_id, current_user.id)
    if not history_row:
        raise HTTPException(status_code=404, detail="Watch history entry not found")
    return history_row


@router.delete("/videos/{video_id}", response_model=VideoWatchHistoryDeleteResponse)
async def delete_video_watch_history(
    video_id: str,
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> VideoWatchHistoryDeleteResponse:
    await enforce_rate_limit("delete_history_item_user", f"user:{current_user.id}", 60, 60)
    history_row = get_user_history_row(session, video_id, current_user.id)
    if not history_row:
        raise HTTPException(status_code=404, detail="Watch history entry not found")

    session.delete(history_row)
    session.commit()
    return VideoWatchHistoryDeleteResponse(message="Watch history entry deleted successfully")


@router.delete("/videos/", response_model=VideoWatchHistoryDeleteResponse)
async def clear_video_watch_history(
    request: Request,
    session: Session = Depends(get_session),
    current_user: CurrentUser = Depends(get_current_user),
) -> VideoWatchHistoryDeleteResponse:
    await enforce_rate_limit("clear_history_user", f"user:{current_user.id}", 10, 60)
    session.exec(delete(VideoWatchHistory).where(VideoWatchHistory.user_id == current_user.id))
    session.commit()
    return VideoWatchHistoryDeleteResponse(message="Watch history cleared successfully")
