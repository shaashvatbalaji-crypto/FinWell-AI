from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.upload import router as upload_router
from api.routes.documents import router as documents_router
from api.routes.auth import router as auth_router
from api.routes.transactions import router as transactions_router
from api.routes.accounts import router as accounts_router
from api.routes.analytics import router as analytics_router
from api.routes.ai import router as ai_router
from api.routes.reconciliation import router as reconciliation_router


app = FastAPI(
    title="FinWell AI API",
    description="Backend API for financial document ingestion and retrieval.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# User registration and login
app.include_router(
    auth_router,
    prefix="/api",
)


app.include_router(
    transactions_router,
    prefix="/api",
    tags=["Transactions"],
)

# Financial account endpoints
app.include_router(
    accounts_router,
    prefix="/api",
    tags=["Accounts"],
)

app.include_router(
    analytics_router,
    prefix="/api",
    tags=["Financial Analytics"],
)

app.include_router(ai_router, prefix="/api", tags=["AI Assistant"])

app.include_router(
    reconciliation_router,
    prefix="/api",
    tags=["Reconciliation"],
)