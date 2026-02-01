from fastapi import APIRouter
from app.api.public import programs, scholarships, conferences, exchanges, search

public_router = APIRouter()

public_router.include_router(programs.router, prefix="/programs", tags=["Public - Programs"])
public_router.include_router(scholarships.router, prefix="/scholarships", tags=["Public - Scholarships"])
public_router.include_router(conferences.router, prefix="/conferences", tags=["Public - Conferences"])
public_router.include_router(exchanges.router, prefix="/exchanges", tags=["Public - Exchanges"])
public_router.include_router(search.router, prefix="/search", tags=["Public - Search"])
