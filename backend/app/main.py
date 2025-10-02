from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import os
from .database import engine, Base
from .routers import auth, admin, documents, dashboard, security

app = FastAPI()

# Add session middleware
SECRET_KEY = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Create database tables
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(documents.router, tags=["documents"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(security.router, tags=["security"])

@app.get("/")
async def root():
    return {"message": "Document Security API"}
