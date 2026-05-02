from contextlib import asynccontextmanager

from fastapi import FastAPI

from basicvids_history.db import create_db_and_tables
from basicvids_history.routers.history import router as history_router
from basicvids_history.routers.root import router as root_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="BasicVids History", lifespan=lifespan)

app.include_router(history_router, prefix="/api/v1")
app.include_router(root_router)
