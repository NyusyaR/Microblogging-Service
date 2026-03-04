from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from service_app.database import create_tables
from service_app.router import medias_router, tweets_router, users_router

FRONT_DIR = Path("dist")


@asynccontextmanager
async def lifespan(app: FastAPI):  # контекстный менеджер
    await create_tables()
    print("База готова")
    yield
    print("Выключение")


app = FastAPI(
    lifespan=lifespan,
    title="MicrobloggingService",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


router = APIRouter(prefix="/api")
router.include_router(tweets_router, tags=["tweets"])
router.include_router(medias_router, tags=["medias"])
router.include_router(users_router, tags=["users"])
app.include_router(router)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
