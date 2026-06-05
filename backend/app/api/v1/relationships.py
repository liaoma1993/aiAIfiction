from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.relationship_event import RelationshipEvent
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/relationships", tags=["relationships"])


class CreateRelationshipEventRequest(BaseModel):
    character_a_id: str
    character_b_id: str
    chapter_id: str | None = None
    chapter_number: int = 0
    old_relation: str
    new_relation: str
    trigger_event: str
    description: str = ""
    relation_type: str = ""
    intensity: int = 5


@router.get("")
async def list_relationships(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RelationshipEvent)
        .where(RelationshipEvent.project_id == project_id)
        .order_by(RelationshipEvent.chapter_number)
    )
    return {"events": result.scalars().all()}


@router.post("")
async def create_relationship_event(
    project_id: str, body: CreateRelationshipEventRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    event = RelationshipEvent(project_id=project_id, **body.model_dump())
    db.add(event)
    await db.flush()
    return {"event": event}


@router.delete("/{event_id}")
async def delete_relationship_event(project_id: str, event_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RelationshipEvent).where(RelationshipEvent.id == event_id, RelationshipEvent.project_id == project_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "关系事件不存在")
    await db.delete(event)
    return {"success": True}
