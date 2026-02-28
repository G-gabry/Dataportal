from fastapi import APIRouter
from app.api.v1 import auth, sources, urls, items, jobs, settings, schemas_config, debug

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sources.router, prefix="/sources", tags=["Sources"])
api_router.include_router(urls.router, prefix="/urls", tags=["Discovered URLs"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Scrape Jobs"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(schemas_config.router, prefix="/schemas", tags=["Item Schemas"])
api_router.include_router(debug.router, prefix="/debug", tags=["Debug"])
