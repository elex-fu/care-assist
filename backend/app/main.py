from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.db.session import engine
from app.core.exceptions import BusinessException
from app.api import auth, members, home, indicators, reports, ai_conversations, hospitals, vaccines, reminders, health_events, search, ws, medications, export, summary
from app.config import settings

# Initialize Sentry if DSN is configured
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release="care-assist@0.1.0",
        traces_sample_rate=1.0 if settings.DEBUG else 0.1,
        profiles_sample_rate=1.0 if settings.DEBUG else 0.1,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown
    await engine.dispose()


app = FastAPI(
    title="Care Assist API",
    description="Family Intelligent Health Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.biz_code, "message": exc.detail, "data": None},
    )


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(home.router, prefix="/api")
app.include_router(indicators.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(ai_conversations.router, prefix="/api")
app.include_router(hospitals.router, prefix="/api")
app.include_router(vaccines.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
app.include_router(health_events.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(medications.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(summary.router, prefix="/api")

app.mount("/static", StaticFiles(directory="static"), name="static")
