from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import init_db
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.audits import router as audits_router
from app.api.drift import router as drift_router
from app.api.remediation import router as remediation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    yield

def create_app() -> FastAPI:
    """Factory creating configured FastAPI instance for data quality auditor."""
    app = FastAPI(
        title="Data Quality Auditor API",
        description="AI data quality auditor profiling tabular datasets for completeness, statistical anomalies, PII leaks, and distribution drift with automated remediation suggestions.",
        version=settings.VERSION,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global health endpoint
    @app.get("/api/health")
    def health_check():
        return {
            "status": "healthy",
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "demo_mode": settings.DEMO_MODE,
        }

    # Mount API routers under /api
    app.include_router(auth_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    app.include_router(audits_router, prefix="/api")
    app.include_router(drift_router, prefix="/api")
    app.include_router(remediation_router, prefix="/api")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Redact sensitive error strings if any
        err_msg = str(exc)
        if settings.LLM_API_KEY and len(settings.LLM_API_KEY) > 4:
            err_msg = err_msg.replace(settings.LLM_API_KEY, "[REDACTED]")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": err_msg},
        )

    return app

# Export top-level app instance for uvicorn entrypoint (app.main:app)
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
