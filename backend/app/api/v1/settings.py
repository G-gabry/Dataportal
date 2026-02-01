from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.models.setting import Setting
from app.models.user import User
from app.schemas.setting import SettingResponse, SettingUpdate, AIConfigResponse, AIConfigUpdate
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()


@router.get("/ai-config", response_model=AIConfigResponse)
def get_ai_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get AI configuration settings"""
    setting = db.query(Setting).filter(Setting.key == "ai_config").first()
    if not setting:
        raise HTTPException(status_code=404, detail="AI config not found")
    return AIConfigResponse(**setting.value)


@router.put("/ai-config", response_model=AIConfigResponse)
def update_ai_config(
    config_data: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update AI configuration settings (admin only)"""
    setting = db.query(Setting).filter(Setting.key == "ai_config").first()
    if not setting:
        raise HTTPException(status_code=404, detail="AI config not found")

    # Update only provided fields
    current_value = setting.value.copy()

    if config_data.default_provider:
        current_value["default_provider"] = config_data.default_provider
    if config_data.default_model:
        current_value["default_model"] = config_data.default_model
    if config_data.task_config:
        for task, config in config_data.task_config.items():
            if task in current_value["task_config"]:
                current_value["task_config"][task].update(config.model_dump(exclude_unset=True))

    setting.value = current_value
    db.commit()
    db.refresh(setting)

    return AIConfigResponse(**setting.value)


@router.get("/scraping-config")
def get_scraping_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get scraping configuration settings"""
    setting = db.query(Setting).filter(Setting.key == "scraping_config").first()
    if not setting:
        raise HTTPException(status_code=404, detail="Scraping config not found")
    return setting.value


@router.put("/scraping-config")
def update_scraping_config(
    config_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Update scraping configuration settings (admin only)"""
    setting = db.query(Setting).filter(Setting.key == "scraping_config").first()
    if not setting:
        raise HTTPException(status_code=404, detail="Scraping config not found")

    # Merge with existing config
    current_value = setting.value.copy()
    current_value.update(config_data)

    setting.value = current_value
    db.commit()
    db.refresh(setting)

    return setting.value


@router.get("/available-models")
def get_available_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of available AI models"""
    setting = db.query(Setting).filter(Setting.key == "ai_config").first()
    if not setting:
        raise HTTPException(status_code=404, detail="AI config not found")

    providers = setting.value.get("providers", {})
    models = []

    for provider, config in providers.items():
        for model in config.get("models", []):
            models.append({
                "provider": provider,
                "model": model,
                "is_default": (
                    provider == setting.value.get("default_provider") and
                    model == setting.value.get("default_model")
                )
            })

    return {"models": models}
