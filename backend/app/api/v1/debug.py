from fastapi import APIRouter
import httpx
import os

router = APIRouter()


@router.get("/firecrawl")
async def debug_firecrawl():
    """Test connectivity from Cloud Run to Firecrawl VM"""
    result = {
        "env": {
            "FIRECRAWL_VM_IP": os.environ.get("FIRECRAWL_VM_IP", "NOT SET"),
            "FIRECRAWL_BASE_URL": os.environ.get("FIRECRAWL_BASE_URL", "NOT SET"),
            "GCP_PROJECT_ID": os.environ.get("GCP_PROJECT_ID", "NOT SET"),
            "GCP_ZONE": os.environ.get("GCP_ZONE", "NOT SET"),
            "FIRECRAWL_VM_NAME": os.environ.get("FIRECRAWL_VM_NAME", "NOT SET"),
        },
        "vm_service": {},
        "connectivity": {},
    }

    # Test VMService IP resolution
    try:
        from app.services.vm_service import VMService
        VMService.clear_cache()
        ip = VMService.get_firecrawl_ip()
        base_url = VMService.get_firecrawl_base_url()
        result["vm_service"] = {"success": True, "ip": ip, "base_url": base_url}
    except Exception as e:
        result["vm_service"] = {"success": False, "error": str(e)}
        base_url = f"http://{os.environ.get('FIRECRAWL_VM_IP', '34.18.134.41')}:3002"

    # Test HTTP connectivity to Firecrawl
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/")
            result["connectivity"] = {
                "success": True,
                "status_code": response.status_code,
                "url": f"{base_url}/",
                "response": response.text[:200],
            }
    except Exception as e:
        result["connectivity"] = {
            "success": False,
            "url": f"{base_url}/",
            "error": str(e),
        }

    return result
