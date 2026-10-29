# main.py
from fastapi import FastAPI

from customer_support_agent.api import health


def create_app() -> FastAPI:
    app = FastAPI(title="Customer Support Agent", version="0.1.0")
    app.include_router(health.router)
    return app
