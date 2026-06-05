from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.llm_provider import LLMProvider
from app.api.deps import get_current_user
from app.llm import refresh_provider_cache

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
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.sort_order))
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
    refresh_provider_cache()
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
    refresh_provider_cache()
    return {"provider": provider}


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "供应商不存在")
    await db.delete(provider)
    return {"success": True}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "供应商不存在")

    from app.llm.base import LLMMessage
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
            url = (provider.base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
            resp = await client.post(url, headers=headers, json={
                "model": provider.model,
                "messages": [{"role": "user", "content": "回复 ok"}],
                "max_tokens": 5,
            })
            data = resp.json()
            if resp.status_code == 200:
                return {"success": True, "model": data.get("model", provider.model)}
            return {"success": False, "error": data.get("error", {}).get("message", str(data))}
    except Exception as e:
        return {"success": False, "error": str(e)}
