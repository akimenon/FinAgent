from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routes import companies, financials, agent_query


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down")


app = FastAPI(
    title="Financial Analysis API",
    description="Multi-agent financial analysis system",
    version="1.0.0",
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

# Include routers
app.include_router(companies.router)
app.include_router(financials.router)
app.include_router(agent_query.router)


@app.get("/")
async def root():
    return {"message": "Financial Analysis API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
