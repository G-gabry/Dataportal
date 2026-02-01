from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin, Token
from app.schemas.source import SourceCreate, SourceUpdate, SourceResponse, SourceListResponse
from app.schemas.discovered_url import DiscoveredURLResponse, DiscoveredURLUpdate, DiscoveredURLListResponse
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.schemas.job import ScrapeJobCreate, ScrapeJobResponse, ScrapeJobListResponse
from app.schemas.setting import SettingUpdate, SettingResponse, AIConfigResponse

__all__ = [
    "PaginatedResponse",
    "MessageResponse",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "SourceCreate",
    "SourceUpdate",
    "SourceResponse",
    "SourceListResponse",
    "DiscoveredURLResponse",
    "DiscoveredURLUpdate",
    "DiscoveredURLListResponse",
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "ItemListResponse",
    "ScrapeJobCreate",
    "ScrapeJobResponse",
    "ScrapeJobListResponse",
    "SettingUpdate",
    "SettingResponse",
    "AIConfigResponse",
]
