from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.wizard import (
    AdjustOutlineChatRequest,
    AdjustOutlineRequest,
    ApplyDraftRequest,
    ApplyStateRequest,
    ApplyStoryRequest,
    AuditChapterRequest,
    ExpandArcRequest,
    ExpandVolumeArcsRequest,
    ExportManuscriptRequest,
    GenerateRequest,
    ProjectPlanChatRequest,
    RepairFromReviewRequest,
    ReviseChapterRequest,
    ReviseVolumeArcRequest,
    SplitChapterRequest,
    StorySuggestRequest,
    WriteChapterRequest,
)
from app.services.wizard import (
    chapters,
    outline_arcs,
    project_creation,
    reviews_repairs,
    tasks_health,
    world_entities,
)


router = APIRouter(prefix="/projects/{project_id}/wizard", tags=["wizard"])

@router.post("/suggest-stories")
async def suggest_stories(project_id: str, body: StorySuggestRequest, user: User=Depends(get_current_user)):
    return await project_creation.suggest_stories(project_id=project_id, body=body, user=user)

@router.post("/project-plan-chat")
async def project_plan_chat(project_id: str, body: ProjectPlanChatRequest, user: User=Depends(get_current_user)):
    return await project_creation.project_plan_chat(project_id=project_id, body=body, user=user)

@router.post("/apply-story")
async def apply_story(project_id: str, body: ApplyStoryRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await project_creation.apply_story(project_id=project_id, body=body, user=user, db=db)

@router.post("/generate-world")
async def generate_world(project_id: str, user: User=Depends(get_current_user)):
    return await world_entities.generate_world(project_id=project_id, user=user)

@router.post("/generate-world-draft")
async def generate_world_draft(project_id: str, user: User=Depends(get_current_user)):
    return await world_entities.generate_world_draft(project_id=project_id, user=user)

@router.post("/generate-characters")
async def generate_characters(project_id: str, body: GenerateRequest, user: User=Depends(get_current_user)):
    return await world_entities.generate_characters(project_id=project_id, body=body, user=user)

@router.post("/generate-characters-draft")
async def generate_characters_draft(project_id: str, body: GenerateRequest, user: User=Depends(get_current_user)):
    return await world_entities.generate_characters_draft(project_id=project_id, body=body, user=user)

@router.post("/export-manuscript")
async def export_manuscript(project_id: str, body: ExportManuscriptRequest, user: User=Depends(get_current_user)):
    return await chapters.export_manuscript(project_id=project_id, body=body, user=user)

@router.post("/expand-volume-arcs/{volume_id}")
async def expand_volume_arcs(project_id: str, volume_id: str, body: ExpandVolumeArcsRequest | None=None, user: User=Depends(get_current_user)):
    return await outline_arcs.expand_volume_arcs(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/expand-arc-chapters/{volume_id}")
async def expand_arc_chapters(project_id: str, volume_id: str, body: ExpandArcRequest, user: User=Depends(get_current_user)):
    return await outline_arcs.expand_arc_chapters(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/revise-volume-arc/{volume_id}")
async def revise_volume_arc(project_id: str, volume_id: str, body: ReviseVolumeArcRequest, user: User=Depends(get_current_user)):
    return await outline_arcs.revise_volume_arc(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/batch-write-arc/{volume_id}")
async def batch_write_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User=Depends(get_current_user)):
    return await chapters.batch_write_arc(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/write-chapter/{chapter_id}")
async def write_chapter(project_id: str, chapter_id: str, body: WriteChapterRequest | None=None, user: User=Depends(get_current_user)):
    return await chapters.write_chapter(project_id=project_id, chapter_id=chapter_id, body=body, user=user)

@router.post("/split-chapter/{chapter_id}")
async def split_chapter(project_id: str, chapter_id: str, body: SplitChapterRequest | None=None, user: User=Depends(get_current_user)):
    return await chapters.split_chapter(project_id=project_id, chapter_id=chapter_id, body=body, user=user)

@router.post("/generate-outline")
async def generate_outline(project_id: str, user: User=Depends(get_current_user)):
    return await outline_arcs.generate_outline(project_id=project_id, user=user)

@router.post("/generate-outline-draft")
async def generate_outline_draft(project_id: str, user: User=Depends(get_current_user)):
    return await outline_arcs.generate_outline_draft(project_id=project_id, user=user)

@router.post("/generate-story-bible")
async def generate_story_bible(project_id: str, user: User=Depends(get_current_user)):
    return await outline_arcs.generate_story_bible(project_id=project_id, user=user)

@router.post("/audit-chapter/{chapter_id}")
async def audit_chapter(project_id: str, chapter_id: str, user: User=Depends(get_current_user)):
    return await reviews_repairs.audit_chapter(project_id=project_id, chapter_id=chapter_id, user=user)

@router.post("/diagnose-chapter/{chapter_id}")
async def diagnose_chapter(project_id: str, chapter_id: str, user: User=Depends(get_current_user)):
    return await reviews_repairs.diagnose_chapter(project_id=project_id, chapter_id=chapter_id, user=user)

@router.get("/narrative-graph/{volume_id}")
async def narrative_graph(project_id: str, volume_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await chapters.narrative_graph(project_id=project_id, volume_id=volume_id, user=user, db=db)

@router.post("/normalize-volume-chapters/{volume_id}")
async def normalize_volume_chapters(project_id: str, volume_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await chapters.normalize_volume_chapters(project_id=project_id, volume_id=volume_id, user=user, db=db)

@router.post("/review-arc/{volume_id}")
async def review_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User=Depends(get_current_user)):
    return await reviews_repairs.review_arc(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/review-arc-structure/{volume_id}")
async def review_arc_structure(project_id: str, volume_id: str, body: ExpandArcRequest, user: User=Depends(get_current_user)):
    return await reviews_repairs.review_arc_structure(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/review-chapter-blueprints/{volume_id}")
async def review_chapter_blueprints(project_id: str, volume_id: str, body: ExpandArcRequest, user: User=Depends(get_current_user)):
    return await reviews_repairs.review_chapter_blueprints(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/review-volume/{volume_id}")
async def review_volume(project_id: str, volume_id: str, user: User=Depends(get_current_user)):
    return await reviews_repairs.review_volume(project_id=project_id, volume_id=volume_id, user=user)

@router.post("/repair-from-review/{volume_id}")
async def repair_from_review(project_id: str, volume_id: str, body: RepairFromReviewRequest, user: User=Depends(get_current_user)):
    return await reviews_repairs.repair_from_review(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/review-project-structure")
async def review_project_structure(project_id: str, user: User=Depends(get_current_user)):
    return await reviews_repairs.review_project_structure(project_id=project_id, user=user)

@router.post("/adjust-outline/{volume_id}")
async def adjust_outline(project_id: str, volume_id: str, body: AdjustOutlineRequest, user: User=Depends(get_current_user)):
    return await outline_arcs.adjust_outline(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/adjust-outline-chat/{volume_id}")
async def adjust_outline_chat(project_id: str, volume_id: str, body: AdjustOutlineChatRequest, user: User=Depends(get_current_user)):
    return await outline_arcs.adjust_outline_chat(project_id=project_id, volume_id=volume_id, body=body, user=user)

@router.post("/revise-chapter/{chapter_id}")
async def revise_chapter(project_id: str, chapter_id: str, body: ReviseChapterRequest, user: User=Depends(get_current_user)):
    return await reviews_repairs.revise_chapter(project_id=project_id, chapter_id=chapter_id, body=body, user=user)

@router.post("/extract-state/{chapter_id}")
async def extract_state(project_id: str, chapter_id: str, apply: bool=False, user: User=Depends(get_current_user)):
    return await chapters.extract_state(project_id=project_id, chapter_id=chapter_id, apply=apply, user=user)

@router.post("/apply-draft")
async def apply_draft(project_id: str, body: ApplyDraftRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await project_creation.apply_draft(project_id=project_id, body=body, user=user, db=db)

@router.post("/apply-state/{chapter_id}")
async def apply_state(project_id: str, chapter_id: str, body: ApplyStateRequest, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await chapters.apply_state(project_id=project_id, chapter_id=chapter_id, body=body, user=user, db=db)

@router.get("/task/{task_id}")
async def poll_task(project_id: str, task_id: str):
    return await tasks_health.poll_task(project_id=project_id, task_id=task_id)

@router.get("/tasks")
async def project_tasks(project_id: str, user: User=Depends(get_current_user)):
    return await tasks_health.project_tasks(project_id=project_id, user=user)

@router.get("/state-ledger")
async def project_state_ledger(project_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.project_state_ledger(project_id=project_id, user=user, db=db)

@router.get("/project-health")
async def project_health(project_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.project_health(project_id=project_id, user=user, db=db)

@router.get("/world-rule-audit")
async def world_rule_audit(project_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.world_rule_audit(project_id=project_id, user=user, db=db)

@router.get("/prompt-modules")
async def prompt_modules(project_id: str, user: User=Depends(get_current_user)):
    return await tasks_health.prompt_modules(project_id=project_id, user=user)

@router.get("/context-preview")
async def generation_context_preview(project_id: str, chapter_id: str | None=None, volume_id: str | None=None, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.generation_context_preview(project_id=project_id, chapter_id=chapter_id, volume_id=volume_id, user=user, db=db)

@router.get("/impact/chapter/{chapter_id}")
async def chapter_change_impact(project_id: str, chapter_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.chapter_change_impact(project_id=project_id, chapter_id=chapter_id, user=user, db=db)

@router.post("/cancel-task/{task_id}")
async def cancel_task_endpoint(project_id: str, task_id: str, user: User=Depends(get_current_user)):
    return await tasks_health.cancel_task_endpoint(project_id=project_id, task_id=task_id, user=user)

@router.post("/retry-task/{task_id}")
async def retry_task(project_id: str, task_id: str, user: User=Depends(get_current_user), db: AsyncSession=Depends(get_db)):
    return await tasks_health.retry_task(project_id=project_id, task_id=task_id, user=user, db=db)
