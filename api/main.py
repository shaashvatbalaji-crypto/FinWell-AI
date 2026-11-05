from fastapi import FastAPI

from api.routes.upload import router as upload_router
from api.routes.documents import router as documents_router


app = FastAPI(
    title="FinWell AI API",
    description="Backend API for financial document ingestion and retrieval.",
    version="1.0.0",
)


@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "message": "FinWell AI API is running.",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "success": True,
        "status": "healthy",
    }


# PDF upload and ingestion endpoint
app.include_router(
    upload_router,
    prefix="/api",
    tags=["Document Upload"],
)


# Retrieve uploaded documents for a user
app.include_router(
    documents_router,
    prefix="/api",
    tags=["Documents"],
)