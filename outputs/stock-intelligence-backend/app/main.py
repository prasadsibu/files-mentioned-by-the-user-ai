import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.analyze import router as analyze_router
from app.api.routers.concall_transcript import router as concall_transcript_router
from app.api.routers.news_sentiment import router as news_sentiment_router
from app.core.config import get_settings
from app.infrastructure.database import Base, engine
from app.ai.finbert_sentiment import initialize_finbert_classifier

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    Base.metadata.create_all(bind=engine)
    app = FastAPI(title=settings.app_name, version="1.0.0")

    logger.info("CORS origins = %s", settings.cors_origins)
    print("CORS origins =", settings.cors_origins)

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

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize FinBERT model at application startup."""
        logger.info("Starting up application")
        try:
            initialize_finbert_classifier()
        except Exception as exc:
            logger.warning("FinBERT init failed: %s", exc)
        logger.info("Application startup complete")

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
