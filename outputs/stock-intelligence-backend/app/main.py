from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.analyze import router as analyze_router
from app.api.routers.concall_transcript import router as concall_transcript_router
from app.api.routers.news_sentiment import router as news_sentiment_router
from app.core.config import get_settings
from app.infrastructure.database import Base, engine
from app.infrastructure.seed_data import seed_database


def create_app() -> FastAPI:
    settings = get_settings()

    Base.metadata.create_all(bind=engine)
    seed_database()

    app = FastAPI(title=settings.app_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(analyze_router)
    app.include_router(news_sentiment_router)
    app.include_router(concall_transcript_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
