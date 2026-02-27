"""
VM Service - Dynamic IP lookup for Firecrawl VM with retry logic.

Handles:
- Getting current external IP of the Firecrawl VM
- Retry logic for transient failures
- Caching to avoid repeated API calls
"""
import time
from typing import Optional
from functools import lru_cache
from datetime import datetime, timedelta

from app.config import settings


class VMServiceError(Exception):
    """Exception for VM service errors"""
    pass


class VMService:
    """Service for managing Firecrawl VM connection"""

    _cached_ip: Optional[str] = None
    _cache_timestamp: Optional[datetime] = None
    _cache_ttl = timedelta(minutes=5)  # Cache IP for 5 minutes

    @classmethod
    def get_firecrawl_ip(cls, max_retries: int = 3, retry_delay: int = 10) -> str:
        """
        Get the current external IP of the Firecrawl VM.

        Uses Google Cloud Compute API to dynamically fetch the IP,
        with caching and retry logic.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Seconds to wait between retries

        Returns:
            The external IP address of the VM

        Raises:
            VMServiceError: If unable to get IP after all retries
        """
        # Check cache first
        if cls._cached_ip and cls._cache_timestamp:
            if datetime.now() - cls._cache_timestamp < cls._cache_ttl:
                return cls._cached_ip

        for attempt in range(max_retries):
            try:
                ip = cls._fetch_vm_ip()
                # Update cache
                cls._cached_ip = ip
                cls._cache_timestamp = datetime.now()
                return ip
            except Exception as e:
                print(f"[VMService] Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        raise VMServiceError(
            f"Failed to get Firecrawl VM IP after {max_retries} attempts"
        )

    @classmethod
    def _fetch_vm_ip(cls) -> str:
        """Fetch VM IP from Google Cloud Compute API"""
        try:
            from google.cloud import compute_v1

            client = compute_v1.InstancesClient()
            instance = client.get(
                project=settings.GCP_PROJECT_ID,
                zone=settings.GCP_ZONE,
                instance=settings.FIRECRAWL_VM_NAME,
            )

            # Get external IP from network interfaces
            if instance.network_interfaces:
                for interface in instance.network_interfaces:
                    if interface.access_configs:
                        for access_config in interface.access_configs:
                            if access_config.nat_i_p:
                                return access_config.nat_i_p

            raise VMServiceError("No external IP found for VM")

        except ImportError:
            # Fallback if google-cloud-compute not installed
            print("[VMService] google-cloud-compute not installed, using fallback IP")
            return cls._get_fallback_ip()
        except Exception as e:
            print(f"[VMService] Error fetching VM IP: {e}")
            # Try fallback
            return cls._get_fallback_ip()

    @classmethod
    def _get_fallback_ip(cls) -> str:
        """
        Fallback IP - use environment variable or default.
        This allows manual override when GCP API isn't available.
        """
        import os
        fallback = os.environ.get("FIRECRAWL_VM_IP", "34.18.134.41")
        print(f"[VMService] Using fallback IP: {fallback}")
        return fallback

    @classmethod
    def get_firecrawl_base_url(cls) -> str:
        """Get the full base URL for Firecrawl API"""
        ip = cls.get_firecrawl_ip()
        return f"http://{ip}:3002"

    @classmethod
    def clear_cache(cls):
        """Clear the IP cache to force a fresh lookup"""
        cls._cached_ip = None
        cls._cache_timestamp = None

    @classmethod
    def health_check(cls) -> bool:
        """Check if Firecrawl VM is reachable"""
        import httpx

        try:
            base_url = cls.get_firecrawl_base_url()
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{base_url}/")
                return response.status_code < 500
        except Exception as e:
            print(f"[VMService] Health check failed: {e}")
            return False
