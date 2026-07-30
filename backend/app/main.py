from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.review import router as review_router
from app.api.upload import router as upload_router
from app.api.duplicate import router as duplicate_router
from app.api.detect import router as detect_router
from app.api.dashboard import router as dashboard_router

app = FastAPI(
    title="Duplicate Account Detection API",
    version="1.0.0",
    description="AI-powered Duplicate Account Detection Platform",
)

# Allow React frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#dashboard
app.include_router(
    dashboard_router,
    prefix="/api",
)

# Health Check
app.include_router(
    health_router,
    prefix="/api",
)

# Upload API
app.include_router(
    upload_router,
    prefix="/api",
)

# Duplicate Detection API
app.include_router(
    duplicate_router,
    prefix="/api",
)

# Review Queue API
app.include_router(
    review_router,
    prefix="/api",
)

# Detect API
app.include_router(
    detect_router,
    prefix="/api",
)


@app.get("/")
def root():
    return {
        "message": "Duplicate Account Detection API is running 🚀"
    }