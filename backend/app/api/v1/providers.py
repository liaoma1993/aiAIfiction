from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.llm_provider import LLMProvider
from app.api.deps import get_current_user
from app.llm import async_refresh_provider_cache, _provider_from_config
from app.llm.base import LLMMessage
from app.services.llm_call_logger import llm_call_context

router = APIRouter(prefix="/providers", tags=["providers"])


class CreateProviderRequest(BaseModel):
    name: str = ""
    provider_type: str = "openai"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    is_active: bool = False
    sort_order: int = 0


class UpdateProviderRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


@router.get("")
async def list_providers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.sort_order, LLMProvider.created_at))
    return {"providers": result.scalars().all()}


@router.post("")
async def create_provider(
    body: CreateProviderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = LLMProvider(**body.model_dump())
    db.add(provider)
    await db.flush()
    await db.commit()
    await async_refresh_provider_cache()
    return {"provider": provider}


@router.put("/{provider_id}")
async def update_provider(
    provider_id: str,
    body: UpdateProviderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "供应商不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(provider, field, value)
    await db.flush()
    await db.commit()
    await async_refresh_provider_cache()
    return {"provider": provider}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "供应商不存在")
    await db.delete(provider)
    await db.commit()
    await async_refresh_provider_cache()
    return {"success": True}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "供应商不存在")

    try:
        llm = _provider_from_config({
            "provider_type": provider.provider_type,
            "model": provider.model,
            "api_key": provider.api_key,
            "base_url": provider.base_url,
        })
        with llm_call_context(function_name="test_provider", project_name="模型管理"):
            resp = await llm.chat([LLMMessage(role="user", content="回复 ok")], max_tokens=8)
        return {"success": True, "model": resp.model or provider.model, "reply": resp.content[:50]}
    except Exception as e:
        return {"success": False, "error": str(e)}
