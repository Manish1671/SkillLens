import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import attempts, auth, health, me, problems, skills, target_profiles, topics
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging_config import setup_logging
from app.core.startup import validate_production_settings

logger = logging.getLogger(__name__)

setup_logging()
validate_production_settings()

app = FastAPI(
    title="SkillLens API",
    version="0.1.0",
    description="Evidence-based adaptive learning platform API",
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("app_error code=%s detail=%s", exc.code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "code": "validation_error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unexpected_server_error")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "code": "internal_error",
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(topics.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(attempts.router, prefix="/api")
app.include_router(target_profiles.router, prefix="/api")
app.include_router(me.router, prefix="/api")
