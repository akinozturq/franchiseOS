from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.auth import router as auth_router
from backend.app.api.departments import router as departments_router
from backend.app.api.transactions import router as transactions_router
from backend.app.api.commission_tiers import router as commission_tiers_router
from backend.app.api.reconciliation import router as reconciliation_router
from backend.app.api.roles import router as roles_router
from backend.app.api.categories import router as categories_router
from backend.app.api.employees import router as employees_router
from backend.app.api.bonus import router as bonus_router
from backend.app.api.branches import router as branches_router
from backend.app.api.users import router as users_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.period_closures import router as period_closures_router
from backend.app.api.notifications import router as notifications_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Franchise / Bayi Kademeli Komisyon, Prim ve Mutabakat Sistemi (FAZ 4)",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(branches_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(departments_router, prefix=settings.API_V1_STR)
app.include_router(transactions_router, prefix=settings.API_V1_STR)
app.include_router(commission_tiers_router, prefix=settings.API_V1_STR)
app.include_router(reconciliation_router, prefix=settings.API_V1_STR)
app.include_router(roles_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(employees_router, prefix=settings.API_V1_STR)
app.include_router(bonus_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(period_closures_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
