from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base
from .database import engine
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):

    Base.metadata.create_all(
        bind=engine
    )

    yield


app = FastAPI(
    title="Enterprise Authentication Service",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(router)


@app.get("/health")
def health():

    return {
        "service": "auth-service",
        "status": "healthy",
    }