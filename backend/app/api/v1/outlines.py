from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.outline import Outline, OutlineNode
from app.models.volume import Volume
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/outline", tags=["outline"])


class OutlineNodeData(BaseModel):
    volume_id: str
    chapter_number: int
    volume_chapter_number: int
    title: str = ""
    summary: str = ""
    key_events: list[str] = []
    tension_level: int = 5
    target_words: int = 3500
    narrative_line: str = "main"
    is_key_chapter: bool = False
    featured_character_ids: list[str] = []
    featured_faction_ids: list[str] = []


class CreateOutlineRequest(BaseModel):
    nodes: list[OutlineNodeData]


@router.get("")
async def get_outline(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Outline).where(Outline.project_id == project_id))
    outline = result.scalar_one_or_none()
    if not outline:
        outline = Outline(project_id=project_id)
        db.add(outline)
        await db.flush()
    nodes_result = await db.execute(
        select(OutlineNode).where(OutlineNode.outline_id == outline.id).order_by(OutlineNode.sort_order)
    )
    return {"outline": outline, "nodes": nodes_result.scalars().all()}


@router.post("")
async def create_outline(
    project_id: str, body: CreateOutlineRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Outline).where(Outline.project_id == project_id))
    outline = result.scalar_one_or_none()
    if outline:
        await db.execute(select(OutlineNode).where(OutlineNode.outline_id == outline.id))
        existing = (await db.execute(select(OutlineNode).where(OutlineNode.outline_id == outline.id))).scalars().all()
        for node in existing:
            await db.delete(node)
    else:
        outline = Outline(project_id=project_id)
        db.add(outline)
        await db.flush()

    for i, node_data in enumerate(body.nodes):
        node = OutlineNode(
            outline_id=outline.id,
            sort_order=i,
            **node_data.model_dump(),
        )
        db.add(node)
    await db.flush()
    nodes_result = await db.execute(
        select(OutlineNode).where(OutlineNode.outline_id == outline.id).order_by(OutlineNode.sort_order)
    )
    return {"outline": outline, "nodes": nodes_result.scalars().all()}


@router.put("/nodes/{node_id}")
async def update_outline_node(
    project_id: str, node_id: str, body: OutlineNodeData,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OutlineNode).where(OutlineNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(404, "大纲节点不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(node, field, value)
    await db.flush()
    return {"node": node}
