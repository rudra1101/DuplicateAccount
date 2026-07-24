from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.duplicate import router as duplicate_router
from app.api.upload import router as upload_router
from app.api.review import router as review_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.detect import router as detect_router

app = FastAPI(title="IdentityAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(duplicate_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(detect_router, prefix="/api")

@app.get("/")
def home():
    return {
        "message": "IdentityAI Backend Running 🚀"
    }