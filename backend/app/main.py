"""FastAPI application factory. Runs under uvicorn locally and under AWS Lambda (Mangum) behind API Gateway."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from .api.routes import router
from .config import get_settings


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="AI Scheduling Reliability API", version=s.app_version)
    app.add_middleware(CORSMiddleware, allow_origins=list(s.cors_origins), allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.include_router(router)
    return app


app = create_app()
handler = Mangum(app, lifespan="off")   # Lambda entry point
