from sqlmodel import Session, delete
import httpx
import pytest

from basicvids_history.auth import CurrentUser, get_current_user
from basicvids_history.schemas.history import VideoWatchHistory
from basicvids_history.tests import app, engine


pytestmark = pytest.mark.anyio


async def request(method: str, url: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


def user(user_id: int = 1, is_admin: bool = False) -> CurrentUser:
    return CurrentUser(
        id=user_id,
        username=f"user-{user_id}",
        first_name="Test",
        last_name="Viewer",
        email=f"user-{user_id}@example.com",
        is_admin=is_admin,
        email_confirmed=True,
    )


def set_current_user(current_user: CurrentUser) -> None:
    async def override_get_current_user():
        return current_user

    app.dependency_overrides[get_current_user] = override_get_current_user


class BaseTestHistory:
    def setup_method(self):
        set_current_user(user())
        with Session(engine) as session:
            session.exec(delete(VideoWatchHistory))
            session.commit()


class TestHistory(BaseTestHistory):
    method_url = "/api/v1/history/videos"

    async def create_history_entry(self, video_id: str = "video-1", position: float = 42):
        response = await request(
            "PUT",
            f"{self.method_url}/{video_id}",
            json={
                "last_position_seconds": position,
                "duration_seconds": 100,
                "completed": False,
            },
        )
        return response.json()

    async def test_upsert_history_creates_entry(self):
        response = await request(
            "PUT",
            f"{self.method_url}/video-1",
            json={
                "last_position_seconds": 42,
                "duration_seconds": 100,
                "completed": False,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["video_id"] == "video-1"
        assert body["user_id"] == 1
        assert body["last_position_seconds"] == 42
        assert body["duration_seconds"] == 100
        assert body["completed"] is False
        assert body["view_count"] == 1

    async def test_upsert_history_updates_same_entry(self):
        await self.create_history_entry()

        response = await request(
            "PUT",
            f"{self.method_url}/video-1",
            json={
                "last_position_seconds": 88,
                "duration_seconds": 100,
                "completed": True,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["last_position_seconds"] == 88
        assert body["completed"] is True
        assert body["view_count"] == 2

    async def test_list_history_orders_by_last_viewed_at_desc(self):
        await self.create_history_entry("video-1", 10)
        await self.create_history_entry("video-2", 20)

        response = await request("GET", f"{self.method_url}/")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert body["items"][0]["video_id"] == "video-2"
        assert body["items"][1]["video_id"] == "video-1"

    async def test_get_history_entry(self):
        created = await self.create_history_entry()

        response = await request("GET", f"{self.method_url}/{created['video_id']}")

        assert response.status_code == 200
        assert response.json()["video_id"] == created["video_id"]

    async def test_get_history_entry_not_found(self):
        response = await request("GET", f"{self.method_url}/missing-video")

        assert response.status_code == 404

    async def test_delete_history_entry(self):
        created = await self.create_history_entry()

        response = await request("DELETE", f"{self.method_url}/{created['video_id']}")

        assert response.status_code == 200
        assert response.json() == {"message": "Watch history entry deleted successfully"}

    async def test_clear_history(self):
        await self.create_history_entry("video-1")
        await self.create_history_entry("video-2")

        response = await request("DELETE", f"{self.method_url}/")

        assert response.status_code == 200
        assert response.json() == {"message": "Watch history cleared successfully"}

        response = await request("GET", f"{self.method_url}/")
        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_history_is_user_scoped(self):
        await self.create_history_entry("video-1")
        set_current_user(user(user_id=2))

        response = await request("GET", f"{self.method_url}/")

        assert response.status_code == 200
        assert response.json()["count"] == 0

    async def test_history_requires_authentication(self):
        app.dependency_overrides.pop(get_current_user, None)

        response = await request(
            "PUT",
            f"{self.method_url}/video-1",
            json={
                "last_position_seconds": 42,
                "duration_seconds": 100,
                "completed": False,
            },
        )

        assert response.status_code == 401
