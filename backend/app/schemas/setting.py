from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime


class SettingResponse(BaseModel):
    id: UUID
    key: str
    value: Dict[str, Any]
    description: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: Dict[str, Any]


# AI Configuration specific schemas
class ModelConfig(BaseModel):
    models: List[str]
    default_model: str


class TaskConfig(BaseModel):
    provider: str
    model: str
    batch_size: Optional[int] = None


class AIConfigResponse(BaseModel):
    default_provider: str
    default_model: str
    providers: Dict[str, ModelConfig]
    task_config: Dict[str, TaskConfig]


class AIConfigUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    task_config: Optional[Dict[str, TaskConfig]] = None


class ItemSchemaResponse(BaseModel):
    id: UUID
    item_type: str
    schema_json: Dict[str, Any]
    classification_prompt: Optional[str]
    extraction_prompt: Optional[str]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ItemSchemaUpdate(BaseModel):
    schema_json: Optional[Dict[str, Any]] = None
    classification_prompt: Optional[str] = None
    extraction_prompt: Optional[str] = None
