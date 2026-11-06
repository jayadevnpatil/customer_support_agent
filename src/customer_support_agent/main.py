from fastapi import FastAPI

from customer_support_agent.api import health
from customer_support_agent.api.error_handlers import register_error_handlers
from customer_support_agent.core.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()

    app = FastAPI(title="Customer Support Agent", version="0.1.0")
    app.state.settings = settings
    app.include_router(health.router)
    register_error_handlers(app=app)
    return app
