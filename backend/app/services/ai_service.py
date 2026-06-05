from app.llm.base import LLMMessage
from app.llm import get_llm
import json
import re

SYSTEM_ARCHITECT = "你是一位资深小说结构顾问，精通三幕式、英雄之旅、起承转合、24章结构等叙事架构理论。你设计的故事结构必须经得起推敲——每一部分有明确的叙事使命，每一段情节有不可替代的结构功能。你擅长识别叙事薄弱点并提出加固方案。关键铁律：你永远只输出一条故事线，不提供备选方案、不设计平行路线、不展示'如果选A则……如果选B则……'。始终用中文回复。回复必须是合法的 JSON。"

SYSTEM_DESIGNER = "你是资深世界观与人物塑造专家，深谙托尔金式世界构建法和角色弧光理论。你创造的每个世界都有内在运行逻辑，每个角色都有内在矛盾、成长轨迹和独特的语言指纹。你厌恶扁平化角色和拼凑式世界观。始终用中文回复。回复必须是合法的 JSON。"

SYSTEM_WRITER = "你是一位成熟的类型小说家，擅长场景写作、对话设计、情绪节奏把控和读者心理操控。你的文字有画面感、有温度、有呼吸感。你从不写填空式段落，每一句话都在推进故事或深化人物。你信奉'展示而非讲述'，用动作和细节传达情绪。始终用中文回复。回复必须是合法的 JSON。"

SYSTEM_EDITOR = "你是一位资深文学编辑，眼光毒辣，擅长发现叙事断裂、逻辑矛盾、角色崩塌和节奏失衡。你会毫不留情地指出问题，同时给出精准的修改建议。始终用中文回复。回复必须是合法的 JSON。"

DE_AI_FICTION_RULES = """
去 AI 味硬规则：
- 从上一章结尾的具体状态直接开场，不要重新介绍世界观，不要用总结句开场。
- 用动作、对话、感官细节表现心理，避免“他知道/他明白/他意识到/他感到”式解释。
- 禁止模板句：“这不是……而是……”“仿佛……”“某种……”“命运的齿轮”“更大的风暴”“真正的”“前所未有的”。
- 每个重要场景必须有实际阻力、误判、迟疑、打断、代价或不完整胜利。
- 对话要有潜台词，允许答非所问、停顿、半句话、打断和沉默；不要像信息问答。
- 每个场景至少保留一个不解释的具体细节，让世界有毛边。
- 章末钩子必须落在具体物件、声音、动作、发现或一句话上，禁止抽象悬念。
- 段落节奏要有变化，允许短句、碎句和单句段；不要每段都工整圆滑。
- 保留少量生活杂音、脏细节、不完美动作和身体感，不要把所有句子润得过于漂亮。
- 只写 POV 角色能感知或推断的内容，不能突然进入其他角色内心。
"""

PUNCTUATION_RULES = """
中文小说标点硬规则：
- 正文统一使用中文标点：，。！？；：、“”‘’（）。不要在中文句子里混用英文逗号、句号、问号、感叹号。
- 人物对白使用中文双引号：“……”。对白中的对白再使用中文单引号：‘……’。不要使用英文直引号。
- 省略号只用“……”，不要写“...”“。。。”“………”；一段里不要频繁用省略号代替停顿。
- 破折号只用“——”，用于突然打断、话锋转折、插入说明；不要连续堆成“————”，不要每段都用。
- 感叹号和问号要克制；不要用“！！！”“？？？”“！？！？”。强烈情绪优先靠动作和对白表现。
- 不要逗号一路拖到底。动作完成、场景转折、信息落点用句号断开，让读者容易读。
- 对话提示语标点要规范：他说：“走。” 或 “走。”他说。不要写成 他说,“走”。
- [HOOK]、[NEW_CHARACTERS] 这两个系统标记必须保持英文方括号原样。
"""

STORY_SUGGESTIONS_PROMPT = """
用户想写小说，灵感是：{inspiration}
类型偏好：{genres}

请生成 3-5 个不同的故事方案。每个方案不是简单的情节变体，而是从不同的叙事入口、不同的核心冲突引擎出发的独立构想。

每个方案包含：
- title: 书名（12字以内，有辨识度，避免陈词滥调）
- genre: 类型标签
- brief: 300字故事梗概，必须写清：核心冲突引擎（什么在驱动故事）、主角的内在矛盾（渴望 vs 恐惧）、故事的独特卖点（和同类型的区别）
- tags: 风格标签列表（如 热血/逆袭/悬疑/虐心/幽默 等）
- total_words: 建议总字数。只有在故事体量已经清楚时才填写数字；不确定时填 null，不要默认 500000

直接返回 JSON 数组，不要任何其他文字：
[{{"title":"...","genre":"...","brief":"...","tags":["...","..."],"total_words":null}}, ...]
"""

PROJECT_CHAT_PROMPT = """
你是小说项目策划助手。用户正在创建新小说项目，需要通过多轮对话把零散想法整理成可执行的项目方案。

当前模式：{intent}
类型偏好：{genres}
当前会话记录：
{messages}

当前草案：
{current_draft}

工作方式：
- 先吸收用户最新补充，不要让用户每次从头描述。
- 第一优先级是守住用户已经给出的核心：主角身份、核心矛盾、类型、世界规则、关键关系不能擅自漂移。发散只能在“同一故事引擎”内发散，不能把故事改成另一个项目。
- 每轮都必须先判断作品体量：短篇 / 中篇 / 长篇 / 超长篇连载。根据体量调整问题重点：
  - 短篇：只锁定一个核心事件、一个人物转折、一个结尾反转或余味，不设计庞大世界观。
  - 中篇：设计清楚开端、转折、高潮、结局，副线最多 1-2 条。
  - 长篇：必须规划长期驱动力、分卷/阶段递进、反派压力升级、主角成长阶梯、伏笔回收链和读者持续追更点。
  - 超长篇连载：必须设计可持续扩展的世界规则、势力格局、阶段性目标、长期终局、章节群爽点循环，避免只靠一个脑洞撑全书。
- 如果当前模式是 chat：像真实策划编辑一样继续沟通，优先加固当前 project_draft；最多问 1-3 个关键问题。不要每轮都另起炉灶，不要给一堆互相无关的点子。
- 如果当前模式是 generate：基于全部对话正式整理 3-6 个可选择方案；候选方案必须共享用户核心诉求，但在核心冲突引擎、主角身份、叙事入口、篇幅规划或卖点上有明显区别。
- 不要给空泛写作课，要把问题落到主角、核心冲突、卖点、世界规则、读者爽点、长线悬念、情感关系、反派压力、结尾期待、分卷阶段、伏笔回收。
- 必须指出当前方案最需要固定的 1-3 个决定，方便用户继续聊；至少一个决定必须和“篇幅/长线结构”有关，除非用户明确要短篇。
- 允许保留未定项，但要明确写出“待定”。
- 你的语气要像在和作者一起推项目：先复述你抓到的核心，再指出哪里还不够能撑住篇幅，然后提出具体可选的细节方向，不要像报告。

发散边界：
- 好的发散：把同一个核心变成更尖锐的冲突、更意外的角色关系、更有代价的世界规则、更长远的阶段目标。
- 坏的发散：换主角、换题材、换故事目标、堆设定名词、只给“更黑暗/更热血/更宏大”这种空标签。
- 每次给 detail_options 时，必须是能直接填进当前草案的具体选项，例如“主角先用替身身份获利，第三阶段才发现自己也被替换过”，不要写“加强冲突”。

返回 JSON：
{{
  "assistant_reply": "给用户看的中文回复，先总结已理解内容，再给出下一步建议或问题，300字以内",
  "needs_user_input": true,
  "next_questions": ["最值得继续确认的问题，0-3条"],
  "detail_options": ["可点击补充的方向建议，0-5条，例如'让主角更功利一点'"],
  "project_draft": {{
    "title": "暂定书名，12字以内",
    "genre": "类型",
    "length_type": "短篇/中篇/长篇/超长篇连载/待定",
    "reader_promise": "读者为什么会追下去：爽点、悬念、情绪钩子或题材卖点，80字以内",
    "core_engine": "一句话写清故事持续运转的核心冲突引擎",
    "boundary_locks": ["已经固定、后续不能随意偏离的设定或方向"],
    "brief": "500字以内项目梗概，写清主角、核心冲突引擎、内在矛盾、长线悬念、独特卖点",
    "long_term_plan": {{
      "endgame": "故事最终要抵达的终局或真相；短篇也要写清结尾指向",
      "stage_plan": ["按篇幅给出2-6个阶段/分卷递进，每项写清目标、压力升级和阶段钩子"],
      "foreshadowing_payoffs": ["重要伏笔及预期回收方向，0-5条"]
    }},
    "tags": ["风格标签"],
    "total_words": null,
    "open_questions": ["还需要用户确认的问题"]
  }},
  "suggestions": [
    {{"title":"方案1书名","genre":"类型","length_type":"长篇/短篇等","reader_promise":"追读承诺","core_engine":"核心冲突引擎","brief":"300字以内独立方案，写清主角、核心冲突、卖点和长线方向","long_term_plan":{{"endgame":"终局","stage_plan":["阶段1","阶段2"],"foreshadowing_payoffs":["伏笔1"]}},"tags":["标签"],"total_words":null}},
    {{"title":"方案2书名","genre":"类型","length_type":"长篇/短篇等","reader_promise":"追读承诺","core_engine":"核心冲突引擎","brief":"300字以内独立方案，必须和方案1有明显区别","long_term_plan":{{"endgame":"终局","stage_plan":["阶段1","阶段2"],"foreshadowing_payoffs":["伏笔1"]}},"tags":["标签"],"total_words":null}},
    {{"title":"方案3书名","genre":"类型","length_type":"长篇/短篇等","reader_promise":"追读承诺","core_engine":"核心冲突引擎","brief":"300字以内独立方案，必须和前两个有明显区别","long_term_plan":{{"endgame":"终局","stage_plan":["阶段1","阶段2"],"foreshadowing_payoffs":["伏笔1"]}},"tags":["标签"],"total_words":null}}
  ]
}}

注意：
- chat 模式下 suggestions 可以为空数组或只返回当前草案；generate 模式下 suggestions 必须 3-6 个。
- total_words 必须和 length_type 匹配：短篇 1-5万，中篇 5-15万，长篇 30-120万，超长篇连载 120万以上；如果信息不足填 null，不要默认 30万。
- 对未知字段保持 JSON 合法，不要输出 Markdown，不要把 JSON 写进代码块。
"""

WORLD_SETTING_PROMPT = """
用户的小说信息：
书名：{title}
类型：{genre}
故事梗概：{brief}
核心主题：{core_theme}

请生成世界观设定，包含以下六个维度，每个维度 300-500 字。关键要求——这六个维度必须互相咬合，不能各自孤立：

1. geography: 地形地貌描述。写异地文明时要从地理推导文化——山怎么形成的？水往哪流？资源在哪里？
2. social_structure: 社会结构与权力模型。必须体现 geography 的制约（如山脉阻隔→诸侯割据，资源集中在河域→中央集权）
3. power_system: 力量/科技/魔法体系。写明代价与限制——任何力量体系没有代价就没有戏剧张力
4. history: 关键历史事件。必须包含至少一个创伤性事件（战争/灾难/背叛），它至今仍在影响社会结构和文化心理
5. culture: 文化习俗与价值观。必须反映 power_system 的特征和 history 的影响（如修炼体系→实力崇拜文化，大灾变→集体主义）
6. special_rules: 世界的特殊法则。必须与 history 中的重大事件有因果关系

额外要求：
- world_logic: 300字"世界运行逻辑"综述——写清各维度如何相互作用，这个世界"为什么是这样"而不是"为什么有这些"
- hard_rules: 6-10条硬约束。必须是写作时绝对不能违反的世界规则，例如能力代价、信息边界、死亡/复活限制、组织规则、时间线规则。
- tone_rules: 5-8条文风氛围。必须能直接指导正文质感，例如叙事视角、幽默/压抑比例、对白锋利度、感官描写密度、节奏气质。
- constraints: 5-8条生成限制。必须明确写作时要避开的内容或边界，例如禁止机械降神、禁止忽略代价、禁止临时新增万能设定、禁止偏离核心题材。

返回 JSON：
{{
  "geography": {{"content":"地形描述..."}},
  "social_structure": {{"content":"社会结构..."}},
  "power_system": {{"content":"力量体系..."}},
  "history": {{"content":"历史背景..."}},
  "culture": {{"content":"文化习俗..."}},
  "special_rules": {{"content":"特殊规则..."}},
  "world_logic": {{"content":"世界运行逻辑综述..."}},
  "hard_rules": ["硬约束1"],
  "tone_rules": ["文风氛围1"],
  "constraints": ["生成限制1"]
}}
"""

CHARACTERS_PROMPT = """
小说信息：书名《{title}》，类型{genre}，梗概：{brief}，主题：{core_theme}
已有角色档案（必须先对照，避免重复造人）：
{existing_characters_summary}

生成 {char_count} 个角色。拒绝扁平化——每个角色必须有内在矛盾、语言指纹、行为模式和弧光预设。

每个角色返回以下字段，深度要求大幅提升：
- name: 角色名
- role_type: 角色类型，用中文自由填写，不要输出英文枚举。常见值可用：主角/男主/女主/反派/配角/导师/恋人/盟友/竞争者/路人/特殊角色。也可以根据作品需要创造更准确的中文类型，例如“吐槽担当”“高维观察者”“社死推动者”。
- personality: 150字人格画像——不只是标签（"外向"），而是写出矛盾性（"表面热情但内心冷漠"）
- background: 200字背景——不只写事件，而要写"因为A事件→形成了B信念→现在的人设"
- motivation: 100字深层动机——区分"想要的目标"和"真正的需求"
- inner_conflict: 100字内在矛盾——他最纠结的是什么？两个不可调和的欲望/价值观？
- language_fingerprint: 100字语言指纹——说话习惯/口头禅/句式偏好/语速/用词特征。每个角色的对话应该能被读者不看名字就认出来
- behavior_pattern: 100字行为模式——压力下如何反应？开心时如何表现？面对权威的态度？小动作/微表情特征？
- emotional_expression: 80字情感表达方式——外放还是内敛？如何掩饰真实情绪？
- appearance: 100字外貌——不只写长相，要写"从外貌能看到什么经历"
- faction_rank: 在势力中的职位
- growth_arc_preset: 150字弧光预设——起始状态→转变契机→中间拉扯→最终状态
- relationship_dynamics: 与至少2个其他角色的具体关系动态，不是"朋友"而是"表面尊敬但内心嫉妒他在修炼上的天赋"
- 不能重复生成已有角色名单中的同名角色；如果必须补充同类角色，只能通过调整关系、阵营、成长阶段或视角来扩展，而不是再造一个同名同质角色。
- 如果已有角色已经覆盖某个关键功能位（主角/反派/导师/恋人/配角），新角色必须承担新的叙事功能，不允许重复填充同一功能位。
- 当已有角色档案和本次设定冲突时，以已有角色档案为准，输出时要自然绕开冲突而不是硬改名字。

需包含1个主角功能位，以及若干反派、配角或其他中文类型。role_type 必须使用中文。
直接返回 JSON 数组，不要其他文字。
"""

FACTIONS_PROMPT = """
小说信息：书名《{title}》，类型{genre}，梗概：{brief}，主题：{core_theme}

生成 {faction_count} 个势力。拒绝孤立设计——每个势力必须在博弈网络中定位，势力间关系必须有机而非标签化。

每个势力返回：
- name: 势力名
- faction_type: 势力/组织类型，用中文自由填写，不要输出英文枚举。常见值可用：门派/家族/帝国/暗组织/种族/商会/公司/学校/官方机构/民间团体/高维组织。也可以根据作品需要创造更准确的中文类型，例如“吃瓜群”“观测部门”“社死直播平台”。
- description: 200字——不只写"是什么"，要写"为什么是这个样子"（历史成因）
- core_creed: 150字核心理念——真正驱动这个势力的信仰/利益逻辑
- headquarters: 总部地点与地理政治意义
- hierarchy: 内部权力结构 [{{"rank":1,"title":"职位","description":"权力范围与晋升条件"}}]
- core_conflict_of_interest: 150字——该势力争夺的核心资源/目标是什么？与哪个势力直接竞争？
- internal_faction_cracks: 100字——内部的分歧派系/潜在裂痕，为未来背叛/分裂埋伏笔
- reputation_and_reality: 100字——外界的印象 vs 内部的真相
- strength_trajectory: 50字——该势力在全书过程中的实力变化趋势（上升/衰落/崩解）

此外，整体返回 cross_faction_matrix 字段：每两个势力之间的具体关系动态描述。不只是"敌对"而是精确到"表面贸易盟友但争夺同一处矿脉，当前处于冷战状态，贸易条款中藏了情报条款"。

返回 JSON：
{{"factions":[{{...}}],"cross_faction_matrix":[{{"faction_a":"势力A名","faction_b":"势力B名","relationship":"200字关系描述","tension_level":7,"volatility":"高/中/低"}}]}}
"""

OUTLINE_PLAN_PROMPT = """
你是小说结构师。规划全书卷结构——只设计一条故事线，不要生成备选方案或多条平行路线。

前提设定：
- 书名《{title}》，类型{genre}，梗概：{brief}，主题：{core_theme}，目标{total_words}字
- 角色：{characters_summary}
- 势力：{forces_summary}

在分卷之前，先设计全书的"叙事引擎"层面：

1. 核心驱动力——什么力量在不可逆地推动故事前进？不是"主角想变强"，而是具体的时间压力、空间限制、规则约束。例如："封印每月削弱10%，主角必须在第8卷前集齐7个碎片，否则世界将不可逆地坍缩"
2. 赌注升级阶梯——每卷失败的代价递增：个人命运 → 团队存亡 → 势力格局 → 世界安危
3. 信息差管理——读者 vs 角色 vs 叙述者分别知道什么？哪些真相在哪个节点揭露？设计至少3层"知道的人不知道，不知道的人以为知道"的信息差
4. 角色关系演变曲线——全书角色关系不是每卷定一次，而是一条连续变化的曲线。用前卷关系状态作为后卷的起点
5. 伏笔链条——设计至少3条跨卷伏笔，标明种下时机和揭晓时机

卷间连贯规则：
1. 每一卷的 summary 开头必须明确承接上一卷结尾的核心状态（角色处境、势力格局、情感关系、未解悬念）
2. 角色的能力/性格/关系在卷之间要有累积变化，不能每卷归零
3. 势力格局的变化要跨卷延续——上一卷结盟了，下一卷就不能再敌对当没发生过
4. 伏笔可以跨卷种下和回收，全书事件要有因果链
5. 每卷必须有明确的叙事使命——"如果删掉这一卷，整个故事就不成立"

自主决定分几卷。每个卷应该是一个完整的叙事阶段，有独立的起承转合。卷数取决于故事的自然结构——短篇可能2-3卷，史诗可能5-8卷。不要让字数限制你，故事的自然转折点在哪里，卷就在哪里断开。只输出一份volumes列表，卷号连续唯一。

字数硬性要求：
- story_overview 至少 1000 字（全书故事弧线概述），不能低于此字数。这是全书最重要的部分，决定了后续所有创作的质量。
- 每卷 outline 至少 1000 字（本卷大纲），每卷 summary 至少 400 字（本卷概要）。
- 如果 AI 觉得自己写不够，就补充：因果链细节、角色状态变化、势力格局演变、伏笔铺垫、主题呼应。

🚫 绝对禁止：不要在 volumes 数组中放两套方案。反面示例（绝对不要这样做）：
❌ "volumes":[卷1,卷2,卷3, 卷1,卷2,卷3]  ← 这是两套方案合并，错误
✅ "volumes":[卷1,卷2,卷3,卷4,卷5]           ← 这是一条线5卷，正确
如果你不确定某个卷是否应该加入，问自己：这个卷是上一卷的直接延续吗？不是就删掉。

返回 JSON：（volumes 数组必须是一条线、连续卷号、每个卷号只出现一次）
{{
  "narrative_engine": {{
    "core_driver": "200字核心驱动力描述",
    "stakes_escalation": "各卷赌注升级说明",
    "information_asymmetry": "信息差设计",
    "relationship_evolution_curve": "角色关系演变曲线概述",
    "foreshadowing_chain": "跨卷伏笔链条"
  }},
  "story_overview": "1000字全书故事弧线概述，写清贯穿全书的因果链和主题",
  "volumes": [
    {{
      "volume_number": 1,
      "title": "卷名",
      "narrative_mission": "本卷叙事使命——在全书结构中承担什么功能",
      "summary": "400字概要，开头必须承接上一卷结尾状态",
      "theme": "卷主题",
      "outline": "1000字本卷大纲，用叙事阶段描述（如'开篇阶段''发展阶段''转折阶段''高潮阶段'）而非定死章节号。不要写'第X章至第Y章'，因为具体章数要后续才能确定。",
      "target_words": 105000,
      "default_chapter_words": 3500,
      "chapter_count": 30,
      "emotional_arc_description": "低→中→高→回落→爆发",
      "stakes_level": "个人/团队/势力/世界",
      "volume_cliffhanger": "卷末钩子——本卷结束时悬念/反转/未解冲突"
    }}
  ],
  "foreshadowing": [
    {{ "name": "伏笔名", "description": "100字", "plant_stage": "播种时机（叙事阶段而非章节号）", "reveal_stage": "揭晓时机（叙事阶段而非章节号）", "payoff_type": "揭秘/反转/情感爆发" }}
  ],
  "key_events": [
    {{ "description": "事件描述", "event_type": "battle/encounter/twist/revelation/emotional_climax", "time_point": "叙事阶段而非章节号", "is_major": true, "cascade_consequences": "事件引起的连锁反应" }}
  ]
}}

只输出一条故事线，volumes按卷号严格递增，不要重复卷号。直接返回JSON。
"""

EXPAND_VOLUME_ARCS_PROMPT = """
你是小说叙事架构师。根据卷内容和用户指定的展开策略，拆分为几条故事弧线。

书名《{title}》，类型{genre}
本卷名：{volume_title}
本卷大纲：{volume_outline}
角色：{characters_summary}
势力：{factions_summary}
本卷共 {chapter_count} 章。

用户指定的弧线展开策略：
- 弧线策略：{arc_strategy}
- 弧线密度：{arc_density}
- 风格偏向：{style_focus}
- 长篇/短篇控制：{length_control}

策略解释：
- 长篇连载型：弧线要体现长期爽点、阶段目标、误判、铺垫、余波和升级空间，不能像短篇一样一笔带过。
- 短篇紧凑型：减少支线，把每条弧线都压在核心冲突和关键转折上。
- 轻松单元剧型：允许每条弧线形成相对完整的小事件，但必须服务全卷主线，不要变成散段子。
- 主线强推进型：每条弧线都要明显推进主线危机、对抗、规则发现或目标进度。
- 群像展开型：每条弧线要明确哪个角色/组织获得戏份和变化，避免只有主角单线。

密度解释：
- 少量弧线：3-4条，边界大，推进快。
- 标准弧线：4-6条，兼顾推进和铺垫。
- 丰富弧线：6-8条，适合长篇连载、群像、赛事、升级流。
- 超细拆分：8条以上，适合复杂卷、多线并行或需要精细铺垫的长篇。

核心原则——弧线不是平均切蛋糕：
- 每条弧线必须有不可替代的叙事功能，如果两条弧线可以互换位置就没区分好
- 弧线之间的边界是"质变点"——角色处境或信息状态发生了不可逆的变化
- 弧线长度取决于该段情节需要的叙事空间，不要强求均匀
- 每条弧线必须写清“如果删掉这一段，全卷会缺什么”，避免水剧情
- 每条弧线必须有明确的开局状态、终点状态和给下一弧线留下的承接条件

网文弧线要求——不要写成深奥场景小说：
- 弧线必须是事件链，不是情绪散文。写清“目标 -> 阻力 -> 主角行动 -> 结果 -> 更大麻烦”。
- 每条弧线至少设计3个可见事件，例如报到被卡、会议交锋、群众堵门、资料造假、项目爆雷、上级试探、同事甩锅、对手反击。
- 每条弧线要有阶段反馈：小胜、小亏、打脸、反转、笑点、爽点、线索落地、关系变化至少3次。
- 少用抽象词：理想主义、制度表演、信念摇晃、时代洪流、灰色秩序。必须改成具体人、具体规则、具体材料、具体现场。
- 世界观/制度/势力只能通过冲突事件展示，不能长篇讲道理。
- 如果是长篇连载前期，优先通俗、直接、强追读，不要慢热铺陈。

根据卷大纲的复杂度和节奏，你自己判断最合适的弧线数量。每条弧线返回：
- name: 弧线名称（8字内，要有辨识度）
- narrative_function: 叙事功能——"主线推进"/"角色深化"/"世界观展开"/"伏笔铺设"/"节奏缓冲"/"高潮爆发"
- emotional_color: 情感基调（如"压抑中带着希望"、"热血与背叛交织"、"绝望中寻光"）
- description: 400-600字弧线完整叙事概要，必须写清：主角短期目标、核心对手/阻力、三次以上具体事件升级、每次升级后的即时反馈、弧线起止状态（起点和终点的质变）、与其他弧线的承接关系（为什么不换顺序）。禁止只写情绪变化和主题阐释。
- opening_state: 本弧线开局状态，精确到主角处境、核心未解问题、读者已知信息
- ending_state: 本弧线终点状态，精确到主角处境变化、信息变化、关系变化、未解问题
- irreplaceable_value: 本弧线不可替代的价值，说明删掉后全卷会缺什么
- protagonist_change: 主角在本弧线的认知/能力/处境/关系变化
- character_focus: 本弧线重点角色，2-5个，写角色名和功能
- foreshadowing_plan: 本弧线伏笔计划，写清铺设/推进/回收
- chapter_start: 起始章号
- chapter_end: 结束章号
- chapter_count: 包含章数
- tension_curve: 张力变化描述（如"中→攀升→高→轻微回落→爆发"）
- key_milestones: 关键节点，3-5个，每个写清该节点的情绪价值和叙事意义
- dependence_on_previous: 对前一条弧线的具体依赖（本弧线第1条则为"无"）
- payoff_for_next: 为本卷后续弧线铺设的钩子（本弧线最后1条则写"本卷收束"）

返回 JSON 数组，不要其他文字。
"""

REVISE_VOLUME_ARC_PROMPT = """
你是小说叙事架构师。根据用户要求，只调整指定的一条故事弧线，保持它与前后弧线连续。

书名《{title}》，类型{genre}
本卷名：{volume_title}
本卷大纲：{volume_outline}
角色：{characters_summary}
势力：{factions_summary}

上一条弧线：{previous_arc}
当前弧线：{current_arc}
下一条弧线：{next_arc}

调整动作：{action}
调整要求：{instruction}

要求：
- 只返回调整后的当前弧线，不要返回数组，不要返回其他文字。
- 必须保留当前弧线在全卷中的位置，不要跳到其他剧情段。
- 如果是“重写”，重做弧线的冲突链、质变点和伏笔计划，但不能破坏前后承接。
- 如果是“拉长”，增加误判、铺垫、角色反应、后果和支线压力，不要只加废话。
- 如果是“压缩”，删掉可省略过渡，把弧线收束到核心冲突、关键转折和必要余波。
- 按网文追读改写：必须有短期目标、具体对手/阻力、事件升级、阶段反馈和章末承接。不要把弧线写成“主角看见某种现象后心态变化”的文学说明。
- 少用抽象词：理想主义、制度表演、信念地基、时代洪流、灰色秩序。必须落到具体事：谁卡了流程、哪份材料有问题、哪场会被怼、谁当众甩锅、主角怎么破局。
- 必须输出中文字段。

返回 JSON 对象，字段：
{{
  "name": "8字内弧线名",
  "narrative_function": "主线推进/角色深化/世界观展开/伏笔铺设/节奏缓冲/高潮爆发",
  "emotional_color": "情感基调",
  "description": "400-600字弧线完整叙事概要，必须包含目标、阻力、事件升级、即时反馈和弧线终点",
  "opening_state": "本弧线开局状态",
  "ending_state": "本弧线终点状态",
  "irreplaceable_value": "删掉后全卷会缺什么",
  "protagonist_change": "主角变化",
  "character_focus": ["角色名：功能"],
  "foreshadowing_plan": ["铺设/推进/回收：具体伏笔"],
  "chapter_start": 数字,
  "chapter_end": 数字,
  "chapter_count": 数字,
  "tension_curve": "张力变化",
  "key_milestones": ["关键节点1", "关键节点2", "关键节点3"],
  "dependence_on_previous": "对上一弧线的依赖",
  "payoff_for_next": "给下一弧线的钩子"
}}
"""

EXPAND_ARC_CHAPTERS_PROMPT = """
你是小说叙事策划师。把一条弧线展开为连续流畅的章节目录。

书名《{title}》，类型{genre}
本卷名：{volume_title}
本卷大纲（仅供参考）：{volume_outline}

核心任务：展开 → {arc_name}
弧线叙事功能：{narrative_function}
弧线情感基调：{emotional_color}
弧线概要：{arc_description}
张力曲线：{tension_curve}
关键节点：{key_milestones}

上一条弧线的结尾状态（本弧线第1章从这里开始）：
{previous_arc_ending}

对前一条弧线的依赖：{dependence_on_previous}
为本卷后续弧线铺设的钩子需求：{payoff_for_next}

角色：{characters_summary}
势力：{factions_summary}

节奏：{pacing}  事件密度：{event_density}
展开长度：{expansion_scale}
长度策略：{expansion_desc}
内部章数区间：{chapter_range_guidance}

章节数量判断准则——不要吝啬章节，宁可多不要少：

节奏对章数的直接影响：
- 缓慢/生活流：每章聚焦1-2个场景，重在氛围渲染、心理描写、日常细节。弧线概要中每200字内容至少分配1章。
- 适中：每章2-3个场景，日常与事件交替。弧线概要中每250字内容至少分配1章。
- 紧凑：每章3-5个场景，快速推进。弧线概要中每350字内容至少分配1章。

弧线复杂度对章数的影响：
- 如果弧线涉及3层以上冲突演变，至少需要相应层数×3章来充分展开
- 如果弧线涉及角色身份重构/价值观转变，至少需要2-3章来展现转变过程
- 如果弧线有新的重要角色登场，需要至少1章来建立读者对该角色的认知
- 每个关键节点至少用1-2章展开，节点之间的过渡也需要章节
- 情绪曲线中的每个拐点（如"压抑→突破→狂喜→冷静→孤勇"有4个拐点），至少用1章来呈现

章数底线：
- 任何有实质内容的弧线不少于6章。只有纯粹的过渡/缓冲弧线才可低于6章。
- 如果按上述准则计算出的章数超过10章，那就用10+章——不要为了凑整数压缩内容。

根据上述准则和“展开长度”，你自己判断最合适的章节数量。不要机械等于原弧线的 chapter_count；原弧线章数只是粗略估计。给出具体章数时，在内心确认：每章是否只承载了单次情感转变？每层的冲突演变是否有足够空间？读者能否在没有足够铺垫的情况下接受角色转变？
- 短展开：保留核心转折，压缩过渡和支线，但不能跳过因果。
- 标准展开：完整呈现弧线起承转合，关键节点有铺垫和余波。
- 长展开：增加误判、反复、支线压力、人物关系推进和阶段性小高潮。
- 细写展开：拆开每个关键节点，让事件前置铺垫、现场执行、后果余震都有独立章节空间。

网文拆章硬规则——优先“追读”，不要写成深奥场景小说：
- 每章先确定一个读者能立刻看懂的短目标：主角要办成什么、躲开什么、证明什么、占到什么便宜。
- 每章必须有外部阻力：有人拦、制度卡、信息差、误会、期限、利益冲突或当场翻车。不要只写主角“感受变化”。
- 每章必须有即时反馈：小胜、小亏、打脸、反转、笑点、尴尬、获得线索、关系推进至少一种。
- 世界观和制度设定只能通过“办事过程中的麻烦和结果”露出，不要用象征、映射、长段说明去解释。
- 少写“理想主义摇晃、信念地基、制度表演”等抽象词；改成具体事件：谁说了什么、哪份材料被改、哪个章盖不上、谁被当场难住。
- 章节标题要像网文章节标题，直接、有悬念、有事件感，不要过度文艺。
- 前20万字不要慢热。每3章至少出现一次明显升级：更大的麻烦、更硬的对手、更直接的利益损失或更强的期待。
- 禁止把 summary 写成意象赏析、主题阐释、文学评论。summary 是给写正文用的任务单。

首章特别要求——如果是全书第1章，summary 的 ②场景序列 中必须包含一个"开篇场景"，写明：
- 开篇第一句话的建议方向（优先悬念/冲突/反常结果，不要意境感开场）
- 开篇需要自然嵌入的世界观信息（门派/社会/力量体系的基本轮廓）
- 主角的出场方式——通过动作而非介绍，让读者通过他在做什么来认识他

每章返回，summary 字段升级为"场景蓝图"而非简单梗概：
- chapter_number: 章号
- title: 章节名（10字内，有吸引力）
- summary: 220-320字章节任务单，结构化包含：
  ① 开场状态（时间/地点/在场角色/情绪基调）
  ② 本章短目标（主角这一章具体要办成什么）
  ③ 核心冲突（谁阻止/什么规则卡住/误会或期限是什么）
  ④ 场景序列（2-4个场景，每个写清：地点→在场角色→冲突动作→结果）
  ⑤ 即时反馈（爽点/笑点/打脸/小胜/小亏/线索落地/关系推进）
  ⑥ 章末钩子（具体到一句话、一个物件、一条消息、一次敲门、一个新麻烦）
- connects_from: 上一章结尾的状态（本弧线第1章则承接上一条弧线的结尾），精确到角色状态和未解问题
- connects_to: 本章结尾状态，为下一章埋钩子，精确到角色状态和新悬疑
- key_events: 核心事件列表（2-4个）
- minor_events: 小事件/日常/伏笔铺垫（2-3个）
- characters_in_chapter: 出场角色名列表
- tension_level: 1-10张力值
- narrative_line: "主线"/"副线A"/"副线B"
- is_key_chapter: 是否为转折章节
- scene_count: 场景数

核心规则——章节连贯性：
1. 每章从上一章结尾状态开始，本弧线第1章必须从「上一条弧线的结尾状态」切入
2. 角色行为要有因果链：上一章的决策→下一章的后果，不能从天而降
3. 情绪要有延续：上一章的情绪高点不能突然归零，高潮后要有余震
4. 每一章的结尾必须留下悬念或推力——读者必须有理由翻页
5. 章节之间有明确的"所以……然后呢？"逻辑链
6. 场景切换要有锚定——每次换场景，用一句感官描述（声音/气味/光线）让读者立刻知道到了哪里

返回 JSON 数组，不要其他文字。
"""

WRITE_CHAPTER_PROMPT = """
你是小说作家。续写第{chapter_number}章正文，必须和上一章结尾无缝衔接。

书名《{title}》，类型{genre}
全书梗概：{brief}
本卷大纲：{volume_outline}
本章是第{chapter_number}章，标题：{chapter_title}

本章场景蓝图：
{chapter_summary}

本集出场角色档案：
{characters_summary}

势力格局：
{factions_summary}

上一章的状态：
{previous_ending}

故事当前状态快照：
{story_state_snapshot}

【阅读难度与表达模式】
{readability_guidance}

【前20万字追读策略】
{early_grip_guidance}

【标点规范】
{punctuation_rules}

【连续性硬闸】
动笔前必须先在内部核对这些事实，正文中不输出核对过程：
- 生死状态不能反转：已死亡、失踪、重伤、被囚、离场的角色，必须有明确铺垫和因果才能再次出场。
- 身份、出身、阵营、职位以角色档案和势力格局为准，不能为了制造反转临时改成掌门之女、长老、卧底等身份。
- 上章承诺、伤势、携带物、秘密、债务、误会、钩子必须在本章有回应或被明确延后。
- 新角色不能只为送情报而来；若必须登场，要有来处、动机、代价，并登记到 [NEW_CHARACTERS]。
- 如果本章蓝图与角色档案、上章状态冲突，优先服从角色档案和上章状态，并在剧情中自然绕开冲突。

作家技法要求——这不是填表，这是创作：

【网文可读性第一优先级】
- 先让读者看懂，再考虑质感。不要为了“高级”“深刻”“有画面”牺牲爽感、清晰度和节奏。
- 少用象征、隐喻、映射、主题总结、长心理独白。把抽象变化改成具体事件：谁来了、说了什么、主角怎么应对、结果怎样。
- 每个场景都要有明确目的：办事、试探、谈判、躲避、反击、误会升级、拿线索、被打脸。没有目的的环境描写直接删。
- 每个自然段尽量只表达一个动作、一次反应或一个信息点。长段落要拆短。
- 重要信息用简单句写清楚：谁要什么，谁不让，代价是什么，主角下一步怎么办。
- 读者不需要反复琢磨才能明白当前剧情。伏笔可以藏，当前目标和冲突不能藏。

【连载吸引力硬规则】
- 每章必须让读者至少获得一种明确反馈：爽点、笑点、社死反馈、反转、危机解除、关系推进、新能力试用、新线索落地。
- 每1500字左右必须出现一次可感知的小推进，不能连续大段解释设定、回忆背景或空泛心理活动。
- 主角每章必须主动做选择或采取行动，不能只是被信息推着走。
- 冲突要短周期闭环：本章提出的一个小问题，最好本章解决或部分解决，同时抛出更想看的新问题。
- 前20万字尤其不能慢热。世界观、规则、组织、反派都要通过具体事件和结果呈现，不要先上设定课。
- 轻松娱乐向章节要让读者“看主角怎么整活/翻车/反向解决”，不是只看剧情说明。

【开篇判断】本章在全书中处于什么位置：
- 如果是全书第1章（卷1弧线1第1章）：必须写一个完整的开场——建立世界观、引入主角、种下核心冲突。用有力的第一句话拽住读者，前500字让人感知这是什么样的世界。
- 如果是某卷的第1章（但不是全书第1章）：需要一段简短过渡，快速锚定读者在新卷的时空位置，但不用重新介绍世界观和角色。示例开局："从北境回来已是第三个月。林缺站在铁剑门山门前，发现门匾换了。"——一句话接上卷、拉进新卷。
- 如果是某条弧线的第1章（但不是卷的第1章）：直接从上一弧线的结尾状态切入，不需要过渡，不需要重新介绍——读者刚读完上一条弧线。
- 如果是弧线内部的续章：无缝衔接，从上一章结尾处继续。

世界观的交代要有机地融入叙事——不要写"这个世界有三大宗门"，而要通过角色动作和对话体现。例如"山门石阶上只站了两个人，往年收徒至少站三排"——门派衰落立现。

【展示而非讲述，但不要过度文学化】用动作、对话、结果传达信息。感官细节只服务场景定位，不要连篇写光影、气味、意象。禁止写"他感到恐惧"——改为"他把报告纸捏皱了，半天没递出去"。禁止写"制度像一张网"——改为"窗口里的人把表推回来，只说少一个章"。

【对话驱动】对话要短、准、有冲突。可以有潜台词，但关键信息必须让读者听懂。一个逼问，一个闪躲；一个要办事，一个拿规矩卡人；一个装傻，一个拆穿。绝不要写成领导讲话或作者说明书。

【场景切换】场景切换时用一句话说明“到了哪里、谁在、要办什么”，必要时补一个简单环境锚点即可。

【节奏控制】紧张段落用短句、快节奏。过渡段落也不能散，最多几句就回到事件。关键转折前可以延迟，但延迟要靠动作和阻力，不靠空泛心理。

【去 AI 味规则】
{de_ai_rules}

【POV约束】本章POV角色：{pov_character}。只能写这个角色感知到的、想到的、回忆起的。不能写其他角色内心独白。如果POV角色没看到/没听到/不知道的事，不能写。

【章末钩子】正文结束后，另起一行写 [HOOK] 加1-3句话悬念钩子。钩子要具体——不是"他不知道前方有什么"，而是"楼梯口传来他昨晚才听过的那阵咳嗽声，可是那个人应该已经死了"。钩子驱动读者翻下一章。

【新角色登记】正文中如果引入了不在角色档案中的新角色（哪怕是只出场一次的配角——铁匠、店小二、路人侠客、反派手下、传信人等），必须在 [HOOK] 之后另起一行写 [NEW_CHARACTERS]，列出本章新登场的角色。每行一个角色，格式：角色名: 50字以内的简要描述（身份/性格特征/与主线关系）。例如：
[NEW_CHARACTERS]
李铁锤: 边城铁匠，沉默寡言，与李世一有旧交
云游僧: 路过的神秘僧人，给了主角一句隐晦的预言
如果你完全没引入新角色（极罕见），写 [NEW_CHARACTERS] 无

写作要求：
- 从上一章结尾的状态直接开始，场景/情绪/时间必须无缝衔接
- 不要输出"第X章"或章节标题——系统另行显示
- 角色性格和说话方式要和角色档案一致，每个角色的语言指纹必须体现
- 如已有内容（{written_so_far}字），从断点处接续，不要重复已有内容
- 如无已有内容，续写不少于{min_words}字
"""

CHAPTER_AUDIT_PROMPT = """
你是小说编辑。请审计以下新写的章节是否与上一章衔接连贯。

上一章结尾状态：
{previous_ending}

上一章钩子：
{previous_hook}

故事当前状态快照：
{story_state_snapshot}

本章正文：
{chapter_content}

请从以下维度逐一检查：

1. 场景连续性——时间、地点、天气、光照是否自然衔接？如果上一章结尾是深夜暴雨、山顶洞穴内，本章开头不能出现"阳光明媚的街市"
2. 角色状态连续性——上一章受伤的角色本章是否有体现？疲劳、情绪、携带物品是否有延续？不能上一章断了右臂本章就用两只手打架
3. 对话连续性——上一章未说完的话题是否被捡起？承诺是否被兑现？不能上一章A说"明天告诉你真相"本章就失忆了
4. 悬念回应——上一章钩子是否被回应？不能钩子是一封信的内容，本章直接跳过
5. 信息一致性——本章有没有和上一章矛盾的地方？A上一章说不知道某个秘密，本章脱口而出？
6. 情绪连续性——上一章的情绪基调是否自然过渡？不能上一章悲痛欲绝，本章若无其事
7. 角色行为逻辑——角色的决策和行为是否符合其性格档案和当前处境？不能胆小鬼突然变莽夫
8. 文笔质量——有没有"填充式"段落？（写了200字但对剧情/角色/氛围没有任何推进）。有没有过于抽象的情感描写？（应该用具体动作替代"他感到悲伤"）
9. 去 AI 味——有没有模板句、抽象总结、过度解释心理、过于工整圆滑的段落、泛泛而谈的悬念？是否有具体动作、感官锚点、生活杂音、误判/迟疑/代价？
10. 易懂度——读者能否一遍读懂当前地点、在场人物、目标、冲突和因果？有没有设定名词堆叠、主语不清、动作线跳跃？
11. 标点规范——中文标点、对话引号、省略号、破折号、问号感叹号是否规范？有没有英文标点混入、逗号拖长句、重复感叹问号？
12. 读者视角——第一次读本章的读者会卡在哪里？有哪些句子需要回看？哪些信息作者知道但读者不知道？

输出限制：
- 必须返回完整合法 JSON，不要 Markdown，不要代码块。
- 所有文本值必须用中文。
- reader_confusions 最多 3 条，每条不超过 60 字。
- issues 最多 5 条，description 和 fix_suggestion 各不超过 90 字。
- 每条 issue 必须尽量给出 target_text：从本章正文中截取可精确定位的原文短句/短语，优先 6-40 字。没有可定位原文才返回空字符串。
- fix_mode 用中文判断后的英文枚举：sentence=只需替换一句/短语；paragraph=需要重写所在段；context=牵涉前后文逻辑，不能只修一句。
- highlights 最多 3 条，每条不超过 50 字。
- suggested_rewrite 不超过 180 字；如果没有必要，返回空字符串。
- 不要大段引用原文，只写问题位置和修改方向，避免输出过长导致 JSON 截断。

返回 JSON：
{{
  "passed": true/false,
  "overall_score": 1-10,
  "scores": {{"readability":1-10,"punctuation":1-10,"dialogue":1-10,"scene_clarity":1-10,"character_consistency":1-10,"hook":1-10,"ai_flavor":1-10}},
  "reader_confusions": ["读者可能看不懂的点"],
  "issues": [
    {{"severity":"critical/high/low","dimension":"1.场景连续性","target_text":"正文中可精确定位的原文短句","fix_mode":"sentence/paragraph/context","description":"具体问题描述，引用原文证据","fix_suggestion":"具体修改建议，包括可替换的写法"}}
  ],
  "highlights": ["写得好的地方"],
  "suggested_rewrite": "如有需要，提供3-5句关键段落的修改示例"
}}
"""

EXPAND_VOLUME_OUTLINE_PROMPT = """
你是小说分卷大纲补写师。当前全书分卷已经确定，但某一卷的 outline 缺失、过短或只是占位文字。

全书信息：
- 书名：《{title}》
- 类型：{genre}
- 故事梗概：{brief}
- 核心主题：{core_theme}
- 角色：{characters_summary}
- 势力：{factions_summary}

全书叙事引擎：
{narrative_engine}

当前卷数据：
{volume_data}

前后卷简要：
{neighbor_volumes}

请只补写当前卷的详细大纲，不要重排卷号，不要输出多套方案。

要求：
- outline 至少 900 字。
- 必须写清本卷开局承接上一卷什么状态，中段冲突如何升级，高潮如何爆发，结尾如何把读者推向下一卷。
- 必须包含角色关系变化、反派压力、关键反转、伏笔播种/回收、制度/世界规则的推进。
- 不要写“详细描述”“约1000字本卷大纲”“待补充”“略”这类占位文字。
- 不要定死每一章编号，可以按“开篇阶段/发展阶段/转折阶段/高潮阶段/收束阶段”描述。

返回 JSON：
{{
  "outline": "900字以上的本卷详细大纲"
}}
"""

REVIEW_CHAPTERS_PROMPT = """
你是资深文学评审编辑。请全方位评审以下小说的写作质量。

书名《{title}》，类型{genre}，全书梗概：{brief}

角色档案：
{characters_summary}

势力格局：
{factions_summary}

本次评审范围：{review_scope}

被评审的章节内容：
{chapters_content}

请从以下 10 个维度逐一评审，每个维度给出评分（1-10分）和具体分析：

1. 情节逻辑 —— 因果链是否完整？有没有"凭空出现"的转折？章节之间的因果驱动是否自然？有没有逻辑断层（前一章A说不知道X，后一章脱口而出X）？
2. 角色一致性 —— 每个角色的行为是否符合其性格档案？说话风格是否一致（语言指纹）？情绪反应是否符合其设定？有没有角色"突然降智"或"性格突变"？
3. 节奏与结构 —— 叙事节奏是否合理？有没有"赶场"（两个重大事件之间没有过渡）或"注水"（200字能写完的事写了800字）？高潮与低压的分布是否合理？
4. 对话质量 —— 对话是否有潜台词？是否有"说明书式"的信息交换？每个角色说话是否有辨识度？对话是否有推拉感（不是一问一答）？
5. 描写密度 —— 场景是否用感官锚定（声音/气味/光线/温度）？关键场景是否有足够的细节让读者沉浸？有没有"白描"式的空洞叙述？
6. 情感线 —— 角色的情感变化是否有铺垫？高潮段落的情绪渲染是否到位？读者能否共情？有没有情感"跳崖"（毫无铺垫的剧烈情绪）？
7. 伏笔与回收 —— 已种下的伏笔是否有跟进？有没有"悬而未决"的谜题太久没提及？
8. 设定一致性 —— 有没有违反世界观设定的描写？力量体系/社会规则是否自洽？
9. 叙事视角 —— POV是否保持一致？有没有"上帝视角"突然闯入？角色不知道的信息是否被错误地描述为角色已知？
10. 阅读体验 —— 章节结尾是否有翻页动力？钩子是否有力？整体阅读是否有"停不下来"的感觉？

【章节结构评审边界】
- 不要因为两个章节发生在同一地点、同一天、同一场会议、同一次走访或同一场景链里，就建议“合并章节”。网文连载允许连续多章发生在同一场景，只要每章有独立目标、阻力、转折、信息增量和章末钩子。
- 默认保留现有章节编号和章节边界。除非出现极端问题（单章不足800字、完全重复、没有任何新信息且无法补救），否则禁止提出“合并第X-Y章”。
- 如果发现两章功能重复，应建议：重分配两章的叙事任务、给其中一章增加新阻力/新信息/人物关系推进/章末钩子，而不是合章。
- 如果发现感情线跳跃，应建议在现有章节内补一次实体见面、动作互动或共同处理具体麻烦；不要通过腾出篇幅、合并章节来解决。
- 修改建议必须面向“现有章节怎么改”，例如“第8章保留民怨线索，第9章改成体制内求助受挫并补沈若云见面”，不要写“合并第8-9章为1章”。

对每个发现的问题，必须给出：
- 具体章节号和引用的原文证据（至少引用一句话）
- 严重程度：致命/严重/轻微
- 具体修改建议

总体评分不简单地平均——逻辑漏洞和角色崩塌的权重更高。

返回 JSON：
{{
  "overall_score": 1-10,
  "summary": "200字总体评审意见",
  "dimensions": [
    {{"name":"1.情节逻辑","score":7,"comment":"100字分析"}}
  ],
  "critical_issues": [
    {{"dimension":"情节逻辑","chapter":3,"evidence":"原文引用...","severity":"致命","description":"问题描述","fix_suggestion":"修改建议"}}
  ],
  "high_issues": [...],
  "low_issues": [...],
  "strengths": ["本书优点1", "优点2"],
  "writing_tips": ["针对本书的3-5条具体写作提升建议"]
}}
"""

REVIEW_REPAIR_PLAN_PROMPT = """
你是小说连续性修复主编。请把评审报告转成可执行的逐章修复计划。

作品信息：
书名《{title}》，类型{genre}
全书梗概：{brief}

角色档案：
{characters_summary}

势力格局：
{factions_summary}

评审范围：{review_scope}

评审报告 JSON：
{review_result}

当前章节索引：
{chapter_index}

工作目标：
- 不是重新写一条新故事线，而是在保留原章节主要意图的前提下修复断裂。
- 默认保留现有章节编号和章节边界，禁止把“合并章节”作为修复方案。两个章节可以发生在同一场景、同一地点、同一次会议或同一天内，只要章节功能不同即可。
- 如果评审报告提出“合并第X-Y章”，修复时要转译为“保留两章但重新分配功能”：一章承担线索/压力/误判，另一章承担求助/碰壁/关系推进/钩子。
- 致命问题优先：生死矛盾、身份错位、阵营错位、时间线错位、机械降神。
- 对跨章节矛盾，要明确“以哪一个事实为准”，并说明需要修改哪些章节来补因果。
- 如果某个角色身份与档案冲突，默认以角色档案为准，除非评审报告明确说应修改档案。
- 对突兀出现的信息工具人，要补前置铺垫、动机、代价，或删除/合并到已有角色。

返回 JSON：
{{
  "diagnosis": "150字以内，总结这次稿子为什么崩",
  "global_constraints": [
    "后续修复和写作都必须遵守的硬约束，例如：穆森第2章若已死亡，第5章不能以活人身份出现"
  ],
  "repair_order_reason": "为什么按这个顺序修",
  "tasks": [
    {{
      "chapter": 5,
      "priority": "critical/high/medium",
      "issue_type": "生死矛盾/身份错位/阵营错位/因果断裂/机械降神/铺垫不足/其他",
      "issue_summary": "本章具体问题",
      "canon_to_keep": ["必须保留为准的事实"],
      "changes_required": ["本章必须修改的具体点"],
      "bridge_to_previous": "如何承接上文，不让下章偏离",
      "bridge_to_next": "修完后给后文留下什么状态",
      "must_not_do": ["修复时禁止做的事"],
      "verification_points": ["修完后用来复查的清单"]
    }}
  ]
}}
"""

EXPAND_VOLUME_PROMPT = """
你是小说叙事策划师。根据已有设定和用户配置，把卷大纲展开为详细的章节目录和剧情规划。

书名《{title}》，类型{genre}
全书梗概：{brief}
本卷名：{volume_title}
本卷概要：{volume_summary}
本卷大纲：{volume_outline}
本卷主题：{volume_theme}
角色：{characters_summary}
势力：{factions_summary}

叙事节奏：{pacing}
事件密度：{event_density}
分支数量：{subplot_count}

生成 {chapter_count} 章。每章 summary 字段升级为场景蓝图：
- title: 章节名（10字内）
- summary: 300字场景蓝图：
  ① 开场状态
  ② 场景序列（2-4个场景含地点/角色/冲突/目的）
  ③ 情绪曲线
  ④ 章末状态
  ⑤ 衔接钩子
- key_events: 核心事件（2-4个）
- minor_events: 小事件/日常/伏笔（2-3个）
- characters_in_chapter: 出场角色名列表
- tension_level: 1-10
- narrative_line: "main"/"subplot_a"/"subplot_b"
- is_key_chapter: 是否为转折章节
- scene_count: 场景数

叙事要求：
- 节奏{pacing}：{pacing_desc}
- 事件密度{event_density}：{event_desc}
- 每3-4章安排一个小高潮或反转
- 主线与支线交替，保持{main_ratio}%主线
- 角色成长要有渐进感，不能一步登天
- 日常/过渡章节不能少，让世界有呼吸感
- 本章登场的角色必须从已有角色列表中选择
- 章节之间有明确的"所以……然后呢？"逻辑链

返回 JSON 数组，不要其他文字。
"""

CHAPTER_REVISION_PROMPT = """
你是成熟类型小说编辑。请根据用户指定的模式处理章节文本。

作品信息：
书名《{title}》，类型：{genre}
章节：第{chapter_number}章 {chapter_title}
章节蓝图：{chapter_summary}
上章/上承：{previous_ending}
本章写作控制：{controls}
评审修复约束：{repair_context}

处理模式：{mode}
用户额外要求：{instruction}

当前正文：
{content}

选中片段（如为空则处理全文）：
{selection}

要求：
- 保持人物设定、上承启下、世界观约束一致。
- 标点必须规范：中文正文统一用中文标点；对白用中文引号；省略号只用“……”；破折号只用“——”；不要堆叠“！！！/？？？”；不要用逗号把整段拖成一句。
- 处理模式说明：
  - quality_light_fix：只做轻量质量修复，修标点、断句、难懂句、AI味、衔接不清，不改变核心剧情。
  - make_easy：改得更易懂，拆长句、补清动作主体、降低信息密度、让因果更直接。
  - dialogue_natural：对白更自然，去掉说明书问答，让角色说话更短、更有潜台词、更符合语言指纹。
  - punctuation_fix：只修标点和断句，不改剧情和措辞风格。
  - de_ai：去 AI 味，只降低模板感和解释腔，不改变剧情。
  - add_scene_texture：增强画面感，增加少量动作、感官、生活细节和场景阻力，不扩写成新事件。
  - strengthen_hook：增强章末钩子，让结尾落在具体声音、物件、动作、发现或一句话上。
  - strengthen_readthrough：增强前20万字追读感，重做开场抓力、短周期目标、爽点/笑点/反转反馈、主角主动性和章末翻页钩子；允许小幅重排段落和补一两个短场景，但不能改变主线事实。
  - audit_full_rewrite：根据审计报告重写整章，逐条修复审计问题；保留本章核心剧情、人物关系、关键线索、章节功能和章末钩子，不新增大剧情，不合并章节，不改已成事实。
  - target_sentence_fix：只修复“选中片段”这一句或短语。输出只能是替换后的片段，不要输出整章，不要带前后原文。
  - target_paragraph_fix：只重写“选中片段”这个段落。输出只能是替换后的段落，不要输出整章。
  - target_context_fix：深修“选中片段”这个局部文本块，适合物品突然出现、动机缺铺垫、人物关系跳跃、线索承接断裂。可以在选中块内部补1-3句前置动作/携带交代/现场反应/因果桥，但输出只能是替换后的局部文本块，不要输出整章。
- 如果存在评审修复约束，必须逐条落实；生死、身份、阵营、时间线矛盾必须优先修，不允许用梦境、幻觉、替身、失忆等廉价解释糊弄过去。
- 修复跨章节问题时，本章开头要能接住上章结尾，本章结尾要给下章留下稳定状态。
- 不要提前揭露伏笔，不要随意新增核心设定。
- 如果是续写，只输出新增正文。
- 如果是重写/润色/修复/扩写/缩写，输出处理后的正文或片段。
- 文字要自然、连贯、有画面感，避免解释腔。
- 如果处理模式是 strengthen_readthrough：优先让第一屏有事件、人物动作或异常结果；删除拖慢追读的说明段；把设定改成事件中的代价/反馈；让主角至少做一次主动选择；结尾必须是具体可视钩子，不要抽象悬念。
- 如果处理模式是 audit_full_rewrite：输出完整重写后的本章正文。必须显式解决审计报告中的严重问题；对物品突然出现、动机缺铺垫、关系跳跃、因果断裂等问题，要在合理位置补前置铺垫和可见动作；语言保持通俗易懂，不要写成评审说明。
- 如果处理模式是 de_ai / humanize / 去AI味：只降低 AI 味，不改变剧情；删除解释性心理总结；减少抽象词和模板句；打散过于整齐的段落节奏；对话更短、更绕、更不完整；增加少量具体、粗粝、非功能性细节；保留原剧情、关键动作、线索、章末钩子；不新增事件，不改人物关系，不把文字润成散文。
- 如果处理模式以 target_ 开头：严格只处理选中片段。不能改选择范围外的文字，不能解释改法，不能返回 Markdown。句子级问题优先用更朴素、物理上成立、读者一眼能懂的表达替换，例如把不合理修辞改成具体动作或状态。
- 如果是 target_context_fix：不要只润色目标句，必须解决用户指出的根因。例如“照相机突然出现”要在选中块靠前位置补出包、借相机、胶卷数量、为什么此刻带着它等可见准备信息；同时保留原有事件走向，不新增大剧情。
- 重点压制这些表达：他知道、他明白、他意识到、这不是……而是……、仿佛、某种、命运的齿轮、更大的风暴、真正的、前所未有的、空气中弥漫着。

返回 JSON：
{{"content":"处理后的正文","summary":"本次改动摘要","change_notes":["改动点1","改动点2"]}}
"""

STATE_EXTRACT_PROMPT = """
你是小说连续性编辑。请从刚写完的章节中提取需要进入长期记忆的状态变化。

章节信息：
第{chapter_number}章 {chapter_title}
章节蓝图：{chapter_summary}

正文：
{content}

返回 JSON：
{{
  "facts":["新增事实"],
  "character_changes":[{{"name":"角色名","change":"状态/关系/能力/情绪变化"}}],
  "foreshadowing_updates":[{{"name":"伏笔名","status":"播种/推进/回收","detail":"说明"}}],
  "faction_changes":[{{"name":"势力名","change":"变化"}}],
  "timeline_events":[{{"time_point":"本章","description":"事件","event_type":"event","is_major":false}}],
  "next_must_follow":["下一章必须承接的点"]
}}
"""

CHAPTER_BLUEPRINT_PROMPT = """
你是小说结构师。请为即将写作的章节生成可执行蓝图，蓝图必须服务于全书因果链和当前卷的叙事使命。

全局故事上下文：
{story_context}

章节信息：
{chapter_context}

要求：
- 明确本章的开场状态、场景序列、主要冲突、转折点、章末状态、下一章钩子。
- 给出本章必须出现的关键事件、必须避开的内容、情绪曲线、节奏建议。
- 识别本章与上一章、上一卷、当前伏笔之间的因果关系。
- 蓝图必须服务于去 AI 味写作：每个场景都要有可观察动作、具体阻力、感官锚点、潜台词或不完整胜利，避免抽象心理解释和总结式悬念。
- 输出要短但可执行，避免空泛理论。

返回 JSON：
{{
  "opening_state":"...",
  "scene_beats":[{{"scene":1,"location":"...","characters":["..."],"purpose":"...","conflict":"...","emotion":"..."}}],
  "main_conflict":"...",
  "turning_point":"...",
  "ending_hook":"...",
  "must_include":["..."],
  "must_not_include":["AI腔模板句","抽象总结式悬念","无阻力顺滑推进"],
  "foreshadowing_tasks":["..."],
  "causality_links":[{{"cause":"...","effect":"...","source":"...","target":"..."}}],
  "rhythm_profile":{{"tension":5,"emotion":5,"action":5,"reveal":5,"relationship":5}},
  "continuity_checks":{{"connects_from_ok":true,"world_rules_ok":true,"character_voice_ok":true,"timeline_ok":true}},
  "summary":"120字章节蓝图概述"
}}
"""

GENERATE_STATE_SUMMARY_PROMPT = """
你是小说连续性编辑。请把最新章节内容压缩成长期记忆快照。

全局上下文：
{story_context}

章节信息：
{chapter_context}

正文：
{content}

要求：
- 提取影响后续写作的新增事实、角色状态变化、关系变化、势力变化、时间线事件、伏笔推进和下一章必须承接点。
- 以长期记忆为目标，不要重复正文细节。

返回 JSON：
{{
  "facts":["..."],
  "character_changes":[{{"name":"...","change":"...","current_state":{{}}}}],
  "foreshadowing_updates":[{{"name":"...","status":"...","detail":"...","reveal_stage":"..."}}],
  "faction_changes":[{{"name":"...","change":"...","current_state":{{}}}}],
  "timeline_events":[{{"time_point":"...","description":"...","event_type":"event","is_major":false}}],
  "next_must_follow":["..."],
  "causality_links":[{{"cause":"...","effect":"...","chapter_from":1,"chapter_to":2}}],
  "hard_constraints_violations":[]
}}
"""

SPLIT_CHAPTER_PROMPT = """
你是小说分章编辑。请把一章过长正文拆成多个自然章节，每章目标约 {target_words} 字。

作品信息：
书名《{title}》，类型：{genre}
原章节：第{chapter_number}章 {chapter_title}
原章节摘要：
{chapter_summary}

拆分原则：
- 按场景、冲突阶段、信息揭露和情绪转折拆，不要机械按字数切。
- 每一章应接近 {target_words} 字；允许 3000-5200 字范围。
- 严禁拆出几百字、1000字左右的短章。除最后一章外，任何 segment.content 不得低于 2800 字。
- 如果某个自然断点前内容不足 2800 字，必须继续向后合并到下一个场景；如果最后一段不足 2200 字，必须并入前一章。
- 宁可少拆一章，也不要拆出碎片短章。
- 章节名要短、有类型小说味，10字以内，不能都叫“一”“二”。
- 每段正文必须保持原文顺序，不新增剧情，不删除关键情节，不改人物关系。
- 每段结尾要有自然钩子；如果原文中间没有强钩子，就选一个状态变化、发现、对话中断或行动决定作为切点。
- 不要输出解释，不要输出 Markdown。

原正文：
{content}

返回 JSON：
{{
  "segments": [
    {{
      "title": "章节名",
      "summary": "120字以内本章摘要",
      "connects_from": "承接上一章/上一段的状态，80字以内",
      "connects_to": "本章结尾给下一章留下的状态或钩子，80字以内",
      "hook": "1句具体钩子",
      "content": "本段完整正文"
    }}
  ]
}}
"""

SPLIT_CHAPTER_META_PROMPT = """
你是小说分章编辑。请为已经完成的章节切片补全章节元信息。

作品信息：
书名《{title}》，类型：{genre}
原章节：第{chapter_number}章 {chapter_title}
目标字数：每章约 {target_words} 字

你将看到按顺序切好的多个正文片段。你的任务是只为每个片段生成章节元信息，不要改写正文，不要补写正文，不要删减正文。

严格要求：
- 结果中的 segments 数量必须和输入片段数完全一致，顺序必须一一对应。
- title 要短，10字以内。
- summary 120字以内。
- connects_from 要承接上一段状态。
- connects_to 要写当前段结尾给下一段留下的状态。
- hook 是一句具体钩子。
- 不要输出 Markdown，不要解释。

片段列表：
{segments}

返回 JSON：
{{
  "segments": [
    {{
      "title": "章节名",
      "summary": "120字以内本章摘要",
      "connects_from": "承接上一段的状态，80字以内",
      "connects_to": "本段结尾给下一段留下的状态，80字以内",
      "hook": "1句具体钩子"
    }}
  ]
}}
"""

ADJUST_OUTLINE_PROMPT = """
你是小说连载期的大纲修订师。当前作品已经进入章节写作阶段，不能像新书一样推倒重来。

项目：
- 书名：《{title}》
- 类型：{genre}
- 简介：{brief}
- 核心主题：{core_theme}

用户调整要求：
{instruction}

当前卷与章节数据：
{outline_payload}

修订铁律：
1. 已写正文是既成事实，不能要求覆盖或否定已经写出的核心事件。
2. 可以调整卷概要、卷大纲、故事弧线描述、未写章节蓝图、后续章节标题和摘要。
3. 对已写章节，只能补充“摘要/记忆/承接说明”，不能改变正文已经发生的事实。
4. 如果用户要求和已写正文冲突，必须在 warnings 里指出，并给出折中方案。
5. 后续章节必须承接最近已写章节的结尾、角色状态、伏笔和未解悬念。
6. 不要生成两套方案，只输出一套可执行修订。
7. 如果当前卷与章节数据里的 adjust_scope 是 summary_only，只返回 volume_patch.summary；不要返回 arcs 和 chapters 的实质修改。

返回 JSON：
{{
  "reasoning_summary": "200字以内说明这次怎么调整、为什么这样调",
  "volume_patch": {{
    "title": "可选，新卷名",
    "summary": "可选，新卷概要",
    "outline": "可选，新卷大纲",
    "theme": "可选，新主题",
    "emotional_arc_description": "可选，新情绪弧线"
  }},
  "arcs": [
    {{
      "index": 0,
      "name": "弧线名",
      "description": "弧线概要",
      "tension_curve": "张力曲线",
      "key_milestones": ["关键节点"],
      "narrative_function": "叙事功能",
      "emotional_color": "情绪色彩",
      "dependence_on_previous": "对前文依赖",
      "payoff_for_next": "给后续留下的回收点"
    }}
  ],
  "chapters": [
    {{
      "chapter_number": 12,
      "title": "章节名",
      "summary": "章节摘要/蓝图概要",
      "connects_from": "承接上一章的状态",
      "connects_to": "章末钩子/后续状态",
      "key_events": ["关键事件"],
      "minor_events": ["支线/伏笔"],
      "blueprint": {{
        "opening_state": "开场状态",
        "summary": "章节蓝图",
        "scene_beats": [],
        "ending_hook": "章末钩子",
        "must_include": [],
        "foreshadowing_tasks": [],
        "rhythm_profile": {{}}
      }}
    }}
  ],
  "warnings": ["如果有冲突或不能直接改的地方，写在这里"]
}}
"""

ADJUST_OUTLINE_CHAT_PROMPT = """
你是小说连载期的卷轴大纲沟通助手。你的任务不是直接改稿，而是通过对话把用户的零散意见整理成一条可执行的调整指令。

项目：
- 书名：《{title}》
- 类型：{genre}
- 简介：{brief}
- 核心主题：{core_theme}

调整范围：{adjust_scope}
范围说明：
- summary_only：只调整卷故事大概/卷概要，不改卷名、弧线、章节数量、章节蓝图和正文。
- outline：可以调整本卷概要、后续弧线、章节蓝图和承接关系，但不能覆盖已写正文。

当前卷与章节数据：
{outline_payload}

当前对话：
{messages}

沟通要求：
1. 像网文责编一样沟通，直接、具体、可执行；不要写文学赏析。
2. 重点帮助用户把“太文艺、太绕、不够爽、不够抓人、前20万字不吸引人”等感受，翻译成可执行的大纲调整方向。
3. 不要默认建议合并章节；同一场景可以跨多个章节，只要章节功能不同。
4. 如果用户意见还不够清楚，最多追问 1-2 个关键问题。
5. consolidated_instruction 必须能直接传给大纲调整接口。

返回 JSON：
{{
  "assistant_reply": "给用户看的回复，120-260字，说明你理解到的调整方向，并可追问关键问题",
  "consolidated_instruction": "整理后的最终调整要求，适合直接执行。必须包含调整范围、保留内容、要强化什么、要避免什么。",
  "next_questions": ["可选追问1", "可选追问2"]
}}
"""


class AIService:
    def _strip_json_fence(self, text: str) -> str:
        text = (text or "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def _extract_json_candidate(self, text: str) -> str:
        text = self._strip_json_fence(text)
        starts = [idx for idx in [text.find("{"), text.find("[")] if idx >= 0]
        if not starts:
            return text
        start = min(starts)
        opening = text[start]
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escape = False
        end = -1
        for idx in range(start, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "\"":
                    in_string = False
                continue
            if ch == "\"":
                in_string = True
            elif ch == opening:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    end = idx + 1
                    break
        return text[start:end] if end > start else text[start:]

    def _escape_json_string_newlines(self, text: str) -> str:
        result = []
        in_string = False
        escape = False
        for ch in text:
            if in_string:
                if escape:
                    result.append(ch)
                    escape = False
                    continue
                if ch == "\\":
                    result.append(ch)
                    escape = True
                    continue
                if ch == "\"":
                    result.append(ch)
                    in_string = False
                    continue
                if ch == "\n":
                    result.append("\\n")
                    continue
                if ch == "\r":
                    result.append("\\r")
                    continue
                if ch == "\t":
                    result.append("\\t")
                    continue
                if ord(ch) < 32:
                    continue
                result.append(ch)
                continue
            result.append(ch)
            if ch == "\"":
                in_string = True
        return "".join(result)

    def _parse_json_text(self, text: str):
        candidate = self._extract_json_candidate(text)
        attempts = [
            candidate,
            re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", candidate),
            re.sub(r",\s*([}\]])", r"\1", candidate),
        ]
        attempts.append(self._escape_json_string_newlines(attempts[-1]))
        attempts.append(re.sub(r",\s*([}\]])", r"\1", attempts[-1]))
        last_error = None
        for item in attempts:
            try:
                return json.loads(item)
            except json.JSONDecodeError as exc:
                last_error = exc
        raise last_error or json.JSONDecodeError("Invalid JSON", candidate, 0)

    def _normalize_chinese_punctuation(self, text: str) -> str:
        text = text or ""
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"…{3,}", "……", text)
        text = re.sub(r"—{3,}", "——", text)
        text = re.sub(r"[!！]{2,}", "！", text)
        text = re.sub(r"[?？]{2,}", "？", text)
        text = re.sub(r"[!！][?？]|[?？][!！]", "？！", text)
        text = re.sub(r"\s+([，。！？；：])", r"\1", text)

        replacements = {
            ",": "，",
            "?": "？",
            "!": "！",
            ";": "；",
        }
        for old, new in replacements.items():
            text = re.sub(rf"(?<=[\u4e00-\u9fff])\{old}", new, text)
            text = re.sub(rf"\{old}(?=[\u4e00-\u9fff])", new, text)
        text = re.sub(r"(?<=[\u4e00-\u9fff])\.(?=[\s\n]|$|[\u4e00-\u9fff])", "。", text)
        text = re.sub(r"(?<=[\u4e00-\u9fff]):(?=[\u4e00-\u9fff“”])", "：", text)
        text = re.sub(r"\"([^\"\n]*[\u4e00-\u9fff][^\"\n]*)\"", r"“\1”", text)
        text = re.sub(r"([\u4e00-\u9fff])\s+([“‘])", r"\1\2", text)
        text = re.sub(r"([”’])\s+([\u4e00-\u9fff])", r"\1\2", text)
        text = re.sub(r"([，；：])([。！？])", r"\2", text)
        text = re.sub(r"([。！？])([。！？])+", r"\1", text)
        return text

    def _clean_chapter_text(self, text: str) -> str:
        text = self._strip_json_fence(text)
        if text.startswith("{") or text.startswith("["):
            try:
                data = self._parse_json_text(text)
                if isinstance(data, dict) and "content" in data:
                    return self._clean_chapter_text(str(data.get("content") or ""))
                if isinstance(data, str):
                    return self._clean_chapter_text(data)
            except json.JSONDecodeError:
                pass
        return self._normalize_chinese_punctuation(text)

    async def _ask(self, prompt: str, system: str = SYSTEM_ARCHITECT, max_tokens: int = 128000, **kwargs) -> dict:
        llm = await get_llm()
        formatted = prompt.format(**kwargs)
        try:
            return await llm.chat_json([LLMMessage(role="user", content=formatted)], system=system, max_tokens=max_tokens)
        except json.JSONDecodeError:
            resp = await llm.chat([LLMMessage(role="user", content=formatted)], system=system, temperature=0.7, max_tokens=max_tokens)
            content = self._strip_json_fence(resp.content)
            try:
                return self._parse_json_text(content)
            except json.JSONDecodeError:
                raise RuntimeError(f"AI 返回格式异常: {content[:300]}")

    async def _ask_list(self, prompt: str, system: str = SYSTEM_ARCHITECT, **kwargs) -> list[dict]:
        result = await self._ask(prompt, system=system, **kwargs)
        if isinstance(result, list):
            return result
        for key in result:
            if isinstance(result[key], list):
                return result[key]
        return [result]

    async def generate_story_suggestions(self, inspiration: str, genres: str = "") -> list[dict]:
        result = await self._ask(STORY_SUGGESTIONS_PROMPT, system=SYSTEM_ARCHITECT, inspiration=inspiration, genres=genres or "不限")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "suggestions" in result:
            return result["suggestions"]
        return [result]

    async def chat_project_plan(self, messages: list[dict], genres: str = "", current_draft: dict | None = None, intent: str = "chat") -> dict:
        return await self._ask(
            PROJECT_CHAT_PROMPT,
            system=SYSTEM_ARCHITECT,
            messages=json.dumps(messages, ensure_ascii=False, indent=2),
            genres=genres or "不限",
            current_draft=json.dumps(current_draft or {}, ensure_ascii=False, indent=2),
            intent=intent,
        )

    async def generate_world_setting(self, title: str, genre: str, brief: str, core_theme: str = "") -> dict:
        return await self._ask(WORLD_SETTING_PROMPT, system=SYSTEM_DESIGNER, title=title, genre=genre, brief=brief, core_theme=core_theme or "待定")

    async def generate_characters(self, title: str, genre: str, brief: str, core_theme: str, char_count: int = 6, existing_characters_summary: str = "") -> list[dict]:
        return await self._ask_list(
            CHARACTERS_PROMPT,
            system=SYSTEM_DESIGNER,
            title=title,
            genre=genre,
            brief=brief,
            core_theme=core_theme or "待定",
            char_count=char_count,
            existing_characters_summary=existing_characters_summary or "无",
        )

    async def generate_factions(self, title: str, genre: str, brief: str, core_theme: str, faction_count: int = 3) -> dict:
        return await self._ask(FACTIONS_PROMPT, system=SYSTEM_DESIGNER, title=title, genre=genre, brief=brief, core_theme=core_theme or "待定", faction_count=faction_count)

    async def generate_outline_plan(self, title: str, genre: str, brief: str, core_theme: str, total_words: int, characters_summary: str, factions_summary: str) -> dict:
        return await self._ask(OUTLINE_PLAN_PROMPT, system=SYSTEM_ARCHITECT,
            title=title, genre=genre, brief=brief, core_theme=core_theme or "待定",
            total_words=total_words,
            characters_summary=characters_summary, forces_summary=factions_summary)

    async def expand_volume_outline(self, title: str, genre: str, brief: str, core_theme: str, characters_summary: str, factions_summary: str, narrative_engine: dict, volume_data: dict, neighbor_volumes: list[dict]) -> dict:
        return await self._ask(
            EXPAND_VOLUME_OUTLINE_PROMPT,
            system=SYSTEM_ARCHITECT,
            max_tokens=8192,
            title=title,
            genre=genre,
            brief=brief or "",
            core_theme=core_theme or "待定",
            characters_summary=characters_summary,
            factions_summary=factions_summary,
            narrative_engine=json.dumps(narrative_engine or {}, ensure_ascii=False, indent=2),
            volume_data=json.dumps(volume_data or {}, ensure_ascii=False, indent=2),
            neighbor_volumes=json.dumps(neighbor_volumes or [], ensure_ascii=False, indent=2),
        )

    async def expand_volume_arcs(
        self,
        title: str,
        genre: str,
        volume_title: str,
        volume_outline: str,
        characters_summary: str,
        factions_summary: str,
        chapter_count: int,
        arc_strategy: str = "标准长篇策划",
        arc_density: str = "标准弧线",
        style_focus: str = "主线清晰，角色自然成长",
        length_control: str = "按全书体量和本卷复杂度自主判断",
    ) -> list[dict]:
        return await self._ask_list(EXPAND_VOLUME_ARCS_PROMPT, system=SYSTEM_ARCHITECT, max_tokens=16384,
            title=title, genre=genre,
            volume_title=volume_title, volume_outline=volume_outline,
            characters_summary=characters_summary, factions_summary=factions_summary,
            chapter_count=chapter_count,
            arc_strategy=arc_strategy,
            arc_density=arc_density,
            style_focus=style_focus,
            length_control=length_control)

    async def revise_volume_arc(
        self,
        title: str,
        genre: str,
        volume_title: str,
        volume_outline: str,
        characters_summary: str,
        factions_summary: str,
        previous_arc: dict,
        current_arc: dict,
        next_arc: dict,
        action: str,
        instruction: str = "",
    ) -> dict:
        result = await self._ask(REVISE_VOLUME_ARC_PROMPT, system=SYSTEM_ARCHITECT, max_tokens=8192,
            title=title, genre=genre,
            volume_title=volume_title, volume_outline=volume_outline,
            characters_summary=characters_summary, factions_summary=factions_summary,
            previous_arc=json.dumps(previous_arc or {}, ensure_ascii=False, indent=2),
            current_arc=json.dumps(current_arc or {}, ensure_ascii=False, indent=2),
            next_arc=json.dumps(next_arc or {}, ensure_ascii=False, indent=2),
            action=action,
            instruction=instruction or "按动作要求调整，保持前后承接")
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and result and isinstance(result[0], dict):
            return result[0]
        raise RuntimeError("AI 返回弧线格式异常")

    async def expand_arc_chapters(self, title: str, genre: str, volume_title: str, volume_outline: str, arc_name: str, arc_description: str, tension_curve: str, key_milestones: list, previous_arc_ending: str, characters_summary: str, factions_summary: str, pacing: str = "medium", event_density: str = "medium", expansion_scale: str = "standard", chapter_range_guidance: str = "按弧线复杂度自主判断", narrative_function: str = "", emotional_color: str = "", dependence_on_previous: str = "", payoff_for_next: str = "") -> list[dict]:
        pacing_map = {
            "slow": ("缓慢", "生活流节奏，重心理描写与环境氛围，场景停留时间更长"),
            "medium": ("适中", "主线稳步推进，日常与冲突交替，保持阅读节奏感"),
            "fast": ("紧凑", "核心冲突快速展开，保持高张力，场景切得快但逻辑不能断"),
        }
        event_map = {
            "low": ("稀疏", "以日常对话和心理描写为主，少量关键冲突，注重氛围和人物"),
            "medium": ("适中", "日常与关键事件自然交替，每章至少一个推动力"),
            "high": ("密集", "情节紧凑，几乎每章有核心事件，多线程并进但不乱"),
        }
        scale_map = {
            "compact": ("短展开", "只展开核心冲突链，删去可省略过渡，适合想快速进入下一弧线"),
            "standard": ("标准展开", "完整展开弧线起承转合，关键节点有足够铺垫和后果"),
            "long": ("长展开", "拉长人物、支线、误判和压力升级，让弧线更像连载段落"),
            "detailed": ("细写展开", "把关键节点拆细，现场、反应、余波都给章节空间，适合重要主线弧线"),
        }
        pacing_label, pacing_desc = pacing_map.get(pacing, pacing_map["medium"])
        event_label, event_desc = event_map.get(event_density, event_map["medium"])
        scale_label, scale_desc = scale_map.get(expansion_scale, scale_map["standard"])

        return await self._ask_list(EXPAND_ARC_CHAPTERS_PROMPT, system=SYSTEM_ARCHITECT, max_tokens=128000,
            title=title, genre=genre,
            volume_title=volume_title, volume_outline=volume_outline,
            arc_name=arc_name, arc_description=arc_description,
            tension_curve=tension_curve, key_milestones=str(key_milestones),
            previous_arc_ending=previous_arc_ending,
            characters_summary=characters_summary, factions_summary=factions_summary,
            pacing=pacing_label, pacing_desc=pacing_desc,
            event_density=event_label, event_desc=event_desc,
            expansion_scale=scale_label, expansion_desc=scale_desc,
            chapter_range_guidance=chapter_range_guidance,
            narrative_function=narrative_function, emotional_color=emotional_color,
            dependence_on_previous=dependence_on_previous, payoff_for_next=payoff_for_next)

    async def expand_volume(self, title: str, genre: str, brief: str, volume_title: str, volume_summary: str, volume_outline: str, volume_theme: str, characters_summary: str, factions_summary: str, chapter_count: int, chapter_words: int, pacing: str = "medium", event_density: str = "medium", subplot_count: int = 2) -> list[dict]:
        pacing_map = {
            "slow": ("缓慢", "生活流节奏，重心理描写与环境氛围"),
            "medium": ("适中", "主线稳步推进，日常与冲突交替"),
            "fast": ("紧凑", "核心冲突快速展开，保持张力"),
        }
        event_map = {
            "low": ("稀疏", "以日常对话和心理描写为主，少量关键冲突"),
            "medium": ("适中", "日常与关键事件自然交替"),
            "high": ("密集", "情节紧凑，几乎每章有核心事件"),
        }
        pacing_label, pacing_desc = pacing_map.get(pacing, pacing_map["medium"])
        event_label, event_desc = event_map.get(event_density, event_map["medium"])
        main_ratio = {"slow": 55, "medium": 65, "fast": 80}.get(pacing, 65)

        return await self._ask_list(EXPAND_VOLUME_PROMPT, system=SYSTEM_ARCHITECT, max_tokens=128000,
            title=title, genre=genre, brief=brief or "",
            volume_title=volume_title, volume_summary=volume_summary,
            volume_outline=volume_outline, volume_theme=volume_theme,
            characters_summary=characters_summary, factions_summary=factions_summary,
            chapter_count=chapter_count, chapter_words=chapter_words,
            pacing=pacing_label, pacing_desc=pacing_desc,
            event_density=event_label, event_desc=event_desc,
            subplot_count=subplot_count, main_ratio=main_ratio)

    async def write_chapter(self, title: str, genre: str, brief: str, chapter_number: int, chapter_title: str, chapter_summary: str, volume_outline: str, characters_summary: str, factions_summary: str, min_words: int = 3000, written_so_far: int = 0, previous_ending: str = "无（这是第一章）", story_state_snapshot: str = "无（这是第一章）", pov_character: str = "主角", readability_guidance: str = "按成熟类型小说的清晰度写作。", early_grip_guidance: str = "非前20万字章节，按当前章节功能正常推进。") -> tuple[str, str, list[dict]]:
        llm = await get_llm()
        prompt = WRITE_CHAPTER_PROMPT.format(
            title=title, genre=genre, brief=brief or "",
            volume_outline=volume_outline, chapter_number=chapter_number,
            chapter_title=chapter_title, chapter_summary=chapter_summary,
            characters_summary=characters_summary, factions_summary=factions_summary,
            min_words=min_words, written_so_far=written_so_far,
            previous_ending=previous_ending,
            story_state_snapshot=story_state_snapshot,
            pov_character=pov_character,
            readability_guidance=readability_guidance,
            early_grip_guidance=early_grip_guidance,
            punctuation_rules=PUNCTUATION_RULES.strip(),
            de_ai_rules=DE_AI_FICTION_RULES.strip(),
        )
        resp = await llm.chat([LLMMessage(role="user", content=prompt)], system=SYSTEM_WRITER, max_tokens=16384)
        text = self._clean_chapter_text(resp.content)
        hook = ""
        new_characters = []
        if "[NEW_CHARACTERS]" in text:
            parts = text.rsplit("[NEW_CHARACTERS]", 1)
            after_new_char = parts[1].strip()
            text = parts[0].strip()
            new_char_lines = []
            for line in after_new_char.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if "[HOOK]" in line:
                    hook_part = line
                    if "[HOOK]" in line:
                        hp = line.split("[HOOK]", 1)
                        new_char_lines.append(hp[0].strip())
                        hook = hp[1].strip() if len(hp) > 1 else ""
                    continue
                if line == "无" or line == "无。":
                    continue
                if ":" in line:
                    name, desc = line.split(":", 1)
                    new_characters.append({"name": name.strip(), "description": desc.strip(), "role_type": "配角"})
        elif "[HOOK]" in text:
            parts = text.rsplit("[HOOK]", 1)
            text = parts[0].strip()
            hook = parts[1].strip() if len(parts) > 1 else ""
            if "[NEW_CHARACTERS]" in hook:
                hp = hook.split("[NEW_CHARACTERS]", 1)
                hook = hp[0].strip()
                for line in hp[1].strip().split("\n"):
                    line = line.strip()
                    if not line or line == "无" or line == "无。":
                        continue
                    if ":" in line:
                        name, desc = line.split(":", 1)
                        new_characters.append({"name": name.strip(), "description": desc.strip(), "role_type": "配角"})
        return text, hook, new_characters

    async def audit_chapter(self, previous_ending: str, previous_hook: str, story_state_snapshot: str, chapter_content: str) -> dict:
        try:
            return await self._ask(CHAPTER_AUDIT_PROMPT, system=SYSTEM_EDITOR, max_tokens=8192,
                previous_ending=previous_ending, previous_hook=previous_hook or "无",
                story_state_snapshot=story_state_snapshot, chapter_content=chapter_content)
        except Exception as exc:
            return {
                "passed": False,
                "overall_score": 0,
                "scores": {
                    "readability": 0,
                    "punctuation": 0,
                    "dialogue": 0,
                    "scene_clarity": 0,
                    "character_consistency": 0,
                    "hook": 0,
                    "ai_flavor": 0,
                },
                "reader_confusions": ["本次质检返回被截断或格式不完整，未能可靠解析。"],
                "issues": [
                    {
                        "severity": "high",
                        "dimension": "质检结果",
                        "description": "AI 质检没有返回完整 JSON，章节正文已保留。",
                        "fix_suggestion": "可重新发起质检；写作任务不应因此失败。",
                    }
                ],
                "highlights": [],
                "suggested_rewrite": "",
                "audit_error": "质检返回格式不完整",
                "raw_error": str(exc)[:200],
            }

    async def review_chapters(self, title: str, genre: str, brief: str, characters_summary: str, factions_summary: str, review_scope: str, chapters_content: str) -> dict:
        return await self._ask(REVIEW_CHAPTERS_PROMPT, system=SYSTEM_EDITOR, max_tokens=16384,
            title=title, genre=genre, brief=brief or "",
            characters_summary=characters_summary, factions_summary=factions_summary,
            review_scope=review_scope, chapters_content=chapters_content)

    async def plan_review_repair(self, title: str, genre: str, brief: str, characters_summary: str, factions_summary: str, review_scope: str, review_result: dict, chapter_index: list[dict]) -> dict:
        return await self._ask(REVIEW_REPAIR_PLAN_PROMPT, system=SYSTEM_EDITOR, max_tokens=16384,
            title=title, genre=genre, brief=brief or "",
            characters_summary=characters_summary, factions_summary=factions_summary,
            review_scope=review_scope,
            review_result=json.dumps(review_result or {}, ensure_ascii=False, indent=2),
            chapter_index=json.dumps(chapter_index or [], ensure_ascii=False, indent=2))

    async def revise_chapter(self, title: str, genre: str, chapter_number: int, chapter_title: str, chapter_summary: str, content: str, mode: str, instruction: str = "", selection: str = "", previous_ending: str = "", controls: dict | None = None, repair_context: str = "") -> dict:
        result = await self._ask(CHAPTER_REVISION_PROMPT, system=SYSTEM_WRITER, max_tokens=16384,
            title=title, genre=genre, chapter_number=chapter_number,
            chapter_title=chapter_title or "", chapter_summary=chapter_summary or "",
            content=content or "", mode=mode, instruction=instruction or "无",
            selection=selection or "无", previous_ending=previous_ending or "无",
            controls=json.dumps(controls or {}, ensure_ascii=False),
            repair_context=repair_context or "无")
        if isinstance(result, dict) and isinstance(result.get("content"), str):
            result["content"] = self._normalize_chinese_punctuation(result["content"])
        return result

    async def extract_state_changes(self, chapter_number: int, chapter_title: str, chapter_summary: str, content: str) -> dict:
        return await self._ask(STATE_EXTRACT_PROMPT, system=SYSTEM_EDITOR, max_tokens=8192,
            chapter_number=chapter_number, chapter_title=chapter_title or "",
            chapter_summary=chapter_summary or "", content=content or "")

    async def generate_chapter_blueprint(self, story_context: dict, chapter_context: dict) -> dict:
        return await self._ask(CHAPTER_BLUEPRINT_PROMPT, system=SYSTEM_ARCHITECT, max_tokens=8192,
            story_context=json.dumps(story_context, ensure_ascii=False),
            chapter_context=json.dumps(chapter_context, ensure_ascii=False))

    async def adjust_outline(self, title: str, genre: str, brief: str, core_theme: str, instruction: str, outline_payload: dict) -> dict:
        return await self._ask(
            ADJUST_OUTLINE_PROMPT,
            system=SYSTEM_ARCHITECT,
            max_tokens=16384,
            title=title,
            genre=genre,
            brief=brief or "",
            core_theme=core_theme or "待定",
            instruction=instruction or "请根据已写内容校准后续大纲",
            outline_payload=json.dumps(outline_payload or {}, ensure_ascii=False, indent=2),
        )

    async def chat_adjust_outline(self, title: str, genre: str, brief: str, core_theme: str, messages: list[dict], adjust_scope: str, outline_payload: dict) -> dict:
        return await self._ask(
            ADJUST_OUTLINE_CHAT_PROMPT,
            system=SYSTEM_ARCHITECT,
            max_tokens=8192,
            title=title,
            genre=genre,
            brief=brief or "",
            core_theme=core_theme or "待定",
            messages=json.dumps(messages or [], ensure_ascii=False, indent=2),
            adjust_scope=adjust_scope or "outline",
            outline_payload=json.dumps(outline_payload or {}, ensure_ascii=False, indent=2),
        )

    async def summarize_state(self, story_context: dict, chapter_context: dict, content: str) -> dict:
        return await self._ask(GENERATE_STATE_SUMMARY_PROMPT, system=SYSTEM_EDITOR, max_tokens=8192,
            story_context=json.dumps(story_context, ensure_ascii=False),
            chapter_context=json.dumps(chapter_context, ensure_ascii=False),
            content=content or "")

    async def split_chapter(self, title: str, genre: str, chapter_number: int, chapter_title: str, chapter_summary: str, content: str, target_words: int = 3500) -> dict:
        return await self._ask(SPLIT_CHAPTER_PROMPT, system=SYSTEM_EDITOR, max_tokens=32768,
            title=title, genre=genre, chapter_number=chapter_number,
            chapter_title=chapter_title or "", chapter_summary=chapter_summary or "",
            content=content or "", target_words=target_words)

    async def split_chapter_metadata(self, title: str, genre: str, chapter_number: int, chapter_title: str, segments: list[dict], target_words: int = 3500) -> dict:
        return await self._ask(SPLIT_CHAPTER_META_PROMPT, system=SYSTEM_EDITOR, max_tokens=16384,
            title=title, genre=genre, chapter_number=chapter_number,
            chapter_title=chapter_title or "", segments=json.dumps(segments or [], ensure_ascii=False, indent=2),
            target_words=target_words)
