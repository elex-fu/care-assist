from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db.session import engine
from app.core.exceptions import BusinessException
from app.api import auth, members, home, indicators, reports, ai_conversations


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
