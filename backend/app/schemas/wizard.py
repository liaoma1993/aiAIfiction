from pydantic import BaseModel

class StorySuggestRequest(BaseModel):
    inspiration: str
    genres: str = ""

class ProjectPlanChatRequest(BaseModel):
    messages: list[dict]
    genres: str = ""
    current_draft: dict = {}

class WriteChapterRequest(BaseModel):
    mode: str = "append"
    instruction: str = ""
    controls: dict = {}
    preview: bool = False

class ReviseChapterRequest(BaseModel):
    mode: str = "polish"
    instruction: str = ""
    selection: str = ""
    controls: dict = {}
    apply: bool = False
    resolved_issue_index: int | None = None
    resolved_issue: str = ""

class RepairFromReviewRequest(BaseModel):
    review_result: dict
    review_scope: str = ""
    apply: bool = True
    reaudit: bool = False
    resume_chapters: list[int] = []

class SplitChapterRequest(BaseModel):
    target_words: int = 3500
    apply: bool = True

class ExportManuscriptRequest(BaseModel):
    scope: str = "volume"  # volume / arc
    volume_id: str
    arc_name: str = ""
    format: str = "md"  # md / txt / json
    include_empty: bool = False

class AdjustOutlineRequest(BaseModel):
    instruction: str
    arc_index: int | None = None
    apply: bool = True
    adjust_scope: str = "outline"  # outline / summary_only

class AdjustOutlineChatRequest(BaseModel):
    messages: list[dict]
    arc_index: int | None = None
    adjust_scope: str = "outline"  # outline / summary_only

class ApplyDraftRequest(BaseModel):
    draft_type: str
    payload: dict

class ApplyStateRequest(BaseModel):
    payload: dict

class ApplyStoryRequest(BaseModel):
    title: str
    genre: str = ""
    brief: str = ""
    tags: list[str] = []
    total_words: int = 300000
    planning_messages: list[dict] = []
    planning_suggestions: list[dict] = []
    selected_draft: dict = {}

class GenerateRequest(BaseModel):
    char_count: int = 6
    faction_count: int = 3

class ExpandVolumeArcsRequest(BaseModel):
    arc_strategy: str = "标准长篇策划"
    arc_density: str = "标准弧线"
    style_focus: str = "主线清晰，角色自然成长"
    length_control: str = "按全书体量和本卷复杂度自主判断"
    clear_existing_chapters: bool = False

class ExpandArcRequest(BaseModel):
    arc_index: int = 0
    pacing: str = "medium"
    event_density: str = "medium"
    expansion_scale: str = "standard"
    chapter_ids: list[str] | None = None
    readability_mode: str = "easy"
    controls: dict = {}

class ReviseVolumeArcRequest(BaseModel):
    arc_index: int = 0
    action: str = "重写"
    instruction: str = ""
    regenerate_chapters: bool = False

class AuditChapterRequest(BaseModel):
    chapter_id: str
