# AI Fiction — 完整生命周期设计文档 v4

> 从 v3 演进：新增三层篇幅规划、卷结构、势力系统、角色动态成长、动态关系网络、
> 情绪曲线、主题管理、知识库检索、多线叙事、时间线管理等 10 大优化点。

---

## 一、核心理念

```
这不是一个"一键生成小说"的工具。
这是一个陪着你从零开始，一步步把故事养大的创作伙伴。

每一个环节都是真实的、持续的、可迭代的。
不存在"生成完事"，只有"生成了→看了→调了→再生→继续写"。

v4 关键升级：
  结构上有"卷"——告别扁平章节，长篇也能驾驭
  角色会"成长"——不是静态档案，而是随剧情演变的鲜活人物
  关系在"流动"——师徒可能反目，宿敌可能和解，时间线会记录一切
  世界有"势力"——门派、家族、帝国，不再是孤零零的个体
  故事有"心跳"——情绪曲线可视化，节奏尽在掌控
```

---

## 二、完整生命周期 4 大阶段

```
┌──────────────────────────────────────────────────────────────────┐
│                     故事创作生命周期                               │
│                                                                  │
│  📋 设定期          ✍️ 写作期          🔍 打磨期         📦 交付期  │
│  (向导引导)        (AI辅助)          (AI审查)          (一键导出)  │
│                                                                  │
│  书名梗概           逐章写作           连贯性审查         TXT      │
│  世界观             内容编辑           角色一致性          EPUB     │
│  角色阵容           上下文管理         节奏审查            HTML     │
│  势力/组织          质量评估           全局润色            DOCX     │
│  卷·章大纲          版本管理           伏笔回收                     │
│  伏笔规划           动态关系追踪       时间线验证                     │
│  篇幅规划                                                          │
│  情绪曲线                                                          │
│  主题/母题                                                         │
│                                                                  │
│  ─────→             ─────→            ─────→             ─────→   │
│                                                                  │
│  每条内容：         每章写完：         全写完后：         满意后：   │
│  AI 出→我看→调      立即可看           全扫描一遍          导出成品   │
│  任何一步都能        不满意的重写       发现问题自动修      分享发布   │
│  回退重新做                                          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 三、设定期 — 创作向导

```
我吐一个字 → AI 出内容 → 我确认/微调 → 永久入库 → 下一步

全程真实数据写入 Project/Character/WorldSetting/Outline/Faction 等表，
不存在"草稿"，每步完成即刻生效、即刻可见。
```

### 向导流程全景

```
仪表盘 → 创建新项目

  Step 0 · 灵感输入
  ┌────────────────────────────────────────────────────────┐
  │ "我想写一本修仙小说，废柴逆袭，带点经商元素"              │
  │                                        [AI 出方案]     │
  └────────────────────────────────────────────────────────┘
    → AI 出 3~5 个故事方案卡片，选一个进入向导

  ╔══════════════════════════════════════════════════════════════════╗
  ║                                                                  ║
  ║  Step 1 · 书名、梗概 & 篇幅规划                                   ║
  ║  ┌────────────────────────────────────────────────────────┐      ║
  ║  │ 书名：[归墟剑尊            ]  [✏️]  [♻️重生成]         │      ║
  ║  │ 类型：仙侠                                       │      ║
  ║  │                                                          │      ║
  ║  │ ─── 三层篇幅规划 ───                                      │      ║
  ║  │                                                          │      ║
  ║  │ 全书目标字数： ├────────────●──────┤ 50万字               │      ║
  ║  │             10万                          100万           │      ║
  ║  │                                                          │      ║
  ║  │ 📊 自动分配方案（可手动调整每卷）：                         │      ║
  ║  │ ┌──────────────────────────────────────────────────┐     │      ║
  ║  │ │ 卷名         章节数    每章字数   总字数    占比    │     │      ║
  ║  │ │ 卷一·青云之始  30章   3500字   10.5万   21%    │     │      ║
  ║  │ │ 卷二·归墟风云  35章   3500字   12.3万   25%    │     │      ║
  ║  │ │ 卷三·天劫降临  40章   3750字   15.0万   30%    │     │      ║
  ║  │ │ 卷四·剑尊归来  35章   3700字   13.0万   26%    │     │      ║
  ║  │ │                  合计：               50.8万         │     │      ║
  ║  │ └──────────────────────────────────────────────────┘     │      ║
  ║  │                                      [+添加卷]            │      ║
  ║  │                                                          │      ║
  ║  │ ─── 故事梗概 ───                                          │      ║
  ║  │ ┌──────────────────────────────────────────────────┐     │      ║
  ║  │ │ 青云宗外门弟子林牧，天生废灵根，因意外获得……     │     │      ║
  ║  │ │                                                  │     │      ║
  ║  │ └──────────────────────────────────────────────────┘     │      ║
  ║  │                                                          │      ║
  ║  │ ─── 写作风格 ───                                          │      ║
  ║  │ Tags: [热血] [白描] [爽文] [+添加]                        │      ║
  ║  │ 描述：快节奏、多短句、注重大场面描写……                     │      ║
  ║  │ 视角：[第三人称 ▾]   节奏：[快节奏 ▾]                     │      ║
  ║  │                                                          │      ║
  ║  │ [♻️重新生成]              [✅确认，创建项目]               │      ║
  ║  └────────────────────────────────────────────────────────┘      ║
  ║       ↓ 创建 Project 入库，仪表盘立即可见                        ║
  ║                                                                  ║
  ║  Step 2 · 世界观 + 主题                                          ║
  ║  ┌────────────────────────────────────────────────────────┐      ║
  ║  │ 🌍 地理环境   📜 历史背景                                │      ║
  ║  │ 🏛 社会结构   ⚡ 力量体系                                │      ║
  ║  │ 🎭 文化习俗   🔒 特殊规则                                │      ║
  ║  │          [展开编辑]  [展开编辑]                          │      ║
  ║  │                                                          │      ║
  ║  │ ─── 主题与母题 🆕 ───                                     │      ║
  ║  │ 核心主题：自由 vs 责任                                     │      ║
  ║  │ 次要主题：[权力的代价] [成长的阵痛] [信任与背叛] [+添加]    │      ║
  ║  │                                                          │      ║
  ║  │ 反复出现的意象/母题：                                     │      ║
  ║  │  🗡️ 剑形胎记 → 身份的象征                                │      ║
  ║  │  🌊 归墟之海 → 万物归源                                  │      ║
  ║  │  ⛰️ 青云山 → 起点也是终点                                │      ║
  ║  │                                          [+添加母题]      │      ║
  ║  │                                                          │      ║
  ║  │ [♻️重新生成]              [✅确认世界观]                   │      ║
  ║  └────────────────────────────────────────────────────────┘      ║
  ║       ↓ 写入 WorldSetting + Project.themes/motifs               ║
  ║                                                                  ║
  ║  Step 3 · 角色阵容 + 势力                                       ║
  ║  ┌────────────────────────────────────────────────────────┐      ║
  ║  │ 👤 角色阵容                        🏛 势力/组织 🆕      │      ║
  ║  │ ┌──────────────────┐    ┌─────────────────────────┐   │      ║
  ║  │ │ [林牧] [玄尘子]   │    │ 🏔 青云宗（仙道门派）     │   │      ║
  ║  │ │ [萧凌云] [苏婉儿] │    │ 🏴 暗影阁（暗组织）      │   │      ║
  ║  │ │ [+添加角色]       │    │ 👑 天玄帝国（凡人国度）   │   │      ║
  ║  │ │         [展开全部]│    │ 🐉 龙族（上古种族）      │   │      ║
  ║  │ └──────────────────┘    │             [+新建势力]   │   │      ║
  ║  │                          └─────────────────────────┘   │      ║
  ║  │                                                          │      ║
  ║  │ ─── 选中角色：林牧 ───                                    │      ║
  ║  │ 性格 / 背景 / 动机 / 行为模式 / 语言风格 / 情感表达        │      ║
  ║  │                                                          │      ║
  ║  │ ─── 🆕 成长弧线 ───                                       │      ║
  ║  │ ① 初始阶段 ── 废灵根、被人看不起、内心自卑                 │      ║
  ║  │    能力：练气一层 · 所属：青云宗·外门                      │      ║
  ║  │ ② 觉醒阶段 ── 意外获得剑尊传承、开始建立自信               │      ║
  ║  │    能力：筑基 · 所属：青云宗·内门                          │      ║
  ║  │ ③ 成长阶段 ── 经历磨难、能力提升、形成自己的道             │      ║
  ║  │    能力：金丹→元婴 · 所属：青云宗·长老                     │      ║
  ║  │ ④ 巅峰阶段 ── 站在巅峰、面对终极抉择                       │      ║
  ║  │    能力：化神 · 所属：独立                                  │      ║
  ║  │ ⑤ 归宿阶段 ── 最终选择、结局                               │      ║
  ║  │    能力：大乘 · 所属：归墟                                  │      ║
  ║  │                                         [+添加阶段]        │      ║
  ║  │                                                          │      ║
  ║  │ ─── 🆕 动态关系网络 ───                                    │      ║
  ║  │ 林牧 ↔ 萧凌云：                                           │      ║
  ║  │  卷一 外门大比  → 竞争对手                                  │      ║
  ║  │  卷二 正面冲突  → 宿敌                                     │      ║
  ║  │  卷三 共同抗敌  → 互相理解                                 │      ║
  ║  │  卷四 最终对决  → 亦敌亦友                                 │      ║
  ║  │                                                          │      ║
  ║  │ ─── 选中势力：青云宗 ───                                   │      ║
  ║  │ 层级：外门弟子 → 内门弟子 → 核心弟子 → 长老 → 掌门         │      ║
  ║  │ 信条：以剑问道，以心证道                                   │      ║
  ║  │ 总部：青云山 · 青霄峰                                      │      ║
  ║  │ 势力关系：暗影阁（敌对）│ 天玄帝国（中立）│ 龙族（联盟）    │      ║
  ║  │                                                          │      ║
  ║  │ [♻️重新生成]              [✅确认角色与势力]                │      ║
  ║  └────────────────────────────────────────────────────────┘      ║
  ║       ↓ 创建 Character × N + Faction × M                        ║
  ║                                                                  ║
  ║  Step 4 · 卷章大纲 + 情绪曲线 + 伏笔                              ║
  ║  ┌────────────────────────────────────────────────────────┐      ║
  ║  │ ─── 🆕 全书情绪曲线 ───                                   │      ║
  ║  │                                                          │      ║
  ║  │ 张力 ▲                                                   │      ║
  ║  │     │        ╱╲        ╱╲╱╲                              │      ║
  ║  │     │    ╱╲╱    ╲    ╱        ╲                          │      ║
  ║  │     │  ╱            ╲╱            ╲                       │      ║
  ║  │     │╱                              ╲                     │      ║
  ║  │     └────────────────────────────────→ 章节               │      ║
  ║  │     卷一（起）  卷二（承） 卷三（转） 卷四（合）            │      ║
  ║  │                                                          │      ║
  ║  │ 拖拽节点调整每章张力  │  高潮标注 ⭐ │  低谷标注 ▼           │      ║
  ║  │                                                          │      ║
  ║  │ ─── 卷·章大纲 ───                                         │      ║
  ║  │                                                          │      ║
  ║  │ ▼ 卷一「青云之始」  10.5万字   30章   占21%                │      ║
  ║  │   情绪曲线：低→中→小高潮                                   │      ║
  ║  │   主题：引入世界观、建立人物                                │      ║
  ║  │   ├ 第1章  废柴的日常       3500字  ▲2 宗门测试、受嘲笑…  │      ║
  ║  │   ├ 第2章  命运转折         3500字  ▲4 罚入禁地…  ⭐关键  │      ║
  ║  │   ├ 第3章  传承觉醒         3500字  ▲5 获得剑尊传承…      │      ║
  ║  │   └ …                                                    │      ║
  ║  │                                                          │      ║
  ║  │ ▼ 卷二「归墟风云」  12.3万字   35章   占25%                │      ║
  ║  │   情绪曲线：上升→波动→高潮                                  │      ║
  ║  │   主题：势力冲突、角色关系深化                              │      ║
  ║  │   └ …                                                    │      ║
  ║  │                                                          │      ║
  ║  │ ─── 🆕 多线叙事配置 ───                                    │      ║
  ║  │ 主线：林牧视角（60%）                                      │      ║
  ║  │ 支线A：萧凌云视角（20%）                                   │      ║
  ║  │ 支线B：苏婉儿视角（15%）                                   │      ║
  ║  │ 暗线：幕后黑手视角（5%）       [+添加叙事线]                │      ║
  ║  │                                                          │      ║
  ║  │ ─── 伏笔清单 ───                                          │      ║
  ║  │ 🟡 剑形胎记   3章埋→28章揭                                  │      ║
  ║  │ 🟡 玄尘子沉默 5章埋→18章揭                                  │      ║
  ║  │ + 添加伏笔                                                │      ║
  ║  │                                                          │      ║
  ║  │  质量要求：[标准 ▾]（strict/standard/loose）               │      ║
  ║  │  创造力：  [████████░░]  70%                               │      ║
  ║  │  角色一致性：[██████████]  95%                              │      ║
  ║  │  世界观约束：[████████░░]  80%                              │      ║
  ║  │                                                          │      ║
  ║  │ [♻️重新生成]        [✅确认大纲，开始写作]                  │      ║
  ║  └────────────────────────────────────────────────────────┘      ║
  ║       ↓ 创建 Volume + Outline + OutlineNode + Foreshadowing     ║
  ║       ↓ + Chapter × N(状态=planned) + TensionCurve             ║
  ║                                                                  ║
  ╚══════════════════════════════════════════════════════════════════╝

  ↓

  进入写作期 — 所有设定就绪，N 章的 Chapter 记录已创建（状态=planned）
```

---

## 四、写作期 — 逐章 AI 协作

进入项目工作台，已有完整大纲 + N 章空白章节。

```
工作台 = 左侧卷·章列表 + 中间编辑器 + 右侧 AI 面板 + 动态关系追踪

┌─ 卷·章导航 ──────┐  ┌─ 内容编辑 ──────────┐  ┌─ AI 面板 ────────┐
│                   │  │                      │  │                  │
│ ├ 卷一·青云之始   │  │                      │  │ ✍️ 写这一章       │
│ │  ├ 第1章 ✅  3500│  │                      │  │ ♻️ 重写           │
│ │  ├ 第2章 ✅  3480│  │   [富文本编辑器]      │  │ ✨ 润色           │
│ │  ├ 第3章 🔄 1200│  │                      │  │ 🔍 检查质量       │
│ │  ├ 第4章 ⏳  ---│  │   第3章正文内容…      │  │                  │
│ │  └ …             │  │                      │  │ ── z 精准控制 ── │
│ ├ 卷二·归墟风云   │  │                      │  │ 本章字数 ▾       │
│ │  └ …             │  │                      │  │ 情绪张力 ████░   │
│ │                   │  │                      │  │ 创造力  ████░    │
│ │ 📊 全书进度 12%   │  │                      │  │                  │
│ │ 已写 6万字/50万  │  │                      │  │ 角色状态快照     │
│ │                   │  │                      │  │  林牧：筑基·内门 │
│ │ [⚡生成本章]      │  │                      │  │                  │
│ │ [⚡生成整卷]      │  │                      │  │ 当前关系：       │
│ │ [⚡生成全部]      │  │                      │  │  林牧↔萧凌云:宿敌│
│ └──────────────────┘  └──────────────────────┘  └──────────────────┘
```

### 写作模式

**① 逐章交互式写作**（推荐）
```
点"写第3章" → AI 写 → 5~30秒出内容 → 即时显示在编辑器
  → 看了不满意 → 点"重写" → 生成新版本
  → 看了还行但想改改 → 编辑器直接修改文字
  → 满意 → 点"完成" → 自动更新角色状态快照 + 关系演变记录
```

**② 按卷批量写作** 🆕
```
点"生成本卷所有章" → 按卷顺序逐章生成
  → 每章写完自动更新上下文（角色状态、关系、时间线）
  → 可见进度条，可随时中断
```

**③ 全书批量写作**
```
点"一键生成全部 N 章" → 后台逐个生成
  → 可以离开，回来看结果
  → 每章独立版本，不喜欢的单独重写
```

### 每章写作时 AI 带上的上下文（知识库检索 🆕）

```
写第 10 章时，AI 自动按相关性检索，不是把所有设定塞进 context：

  硬上下文（必带）：
    ✅ 本章大纲节点的写作指南 + 情绪张力目标
    ✅ 本章需要埋/揭的伏笔提示
    ✅ 所属卷的卷概要 + 卷主题

  软上下文（按相关性 + 时效性检索，类似 RAG）：
    ✅ 最近 3 章完整内容（滚动窗口）
    ✅ 本卷涉及角色档案（4~6人）+ 当前状态快照
    ✅ 本卷涉及势力（2~3个）的当前状态
    ✅ 最近 5 次关系变化事件
    ✅ 当前时间线位置 ± 5章内的事件
    ✅ 本章所属叙事线 + 最近交汇点信息
    ✅ 世界观六维度约束卡（动态压缩摘要，非原文）

  相关性排序算法：
    - 高频出场角色 > 低频角色
    - 本卷势力 > 其他势力
    - 近期事件 > 远古事件
    - 当前叙事线 > 其他叙事线
```

### 章节配置（每章可独立设置）

```
本章目标字数：[3500 ▾]（继承卷级默认 / 自定义）
情绪张力目标：▲▲▲▲△（继承卷级曲线 / 自定义）
写作风格：     继承项目全局 / 本章自定义
视角切换：     继承全局 / 继承叙事线 / 本章自定义
```

### 动态关系追踪 🆕

```
写作过程中，AI 识别到关系变化时自动记录：

事件：第 10 章，林牧在外门大比击败萧凌云
  → 关系更新：林牧↔萧凌云：暗中的竞争对手 → 公开的宿敌
  → 状态快照：林牧从"练气九层→筑基"
  → 用户可确认/修改/拒绝此更新

事件：第 25 章，林牧与萧凌云并肩对抗魔修
  → 关系更新：林牧↔萧凌云：宿敌 → 微妙的理解
  → 用户可确认/修改/拒绝此更新

所有关系变化形成可见的关系演变时间线。
```

---

## 五、打磨期

全书所有章节标"已完成"后：

```
[🔍 开始全面审查]
  → 连续性检查（时间线、道具、地点、是否有矛盾）
  → 角色一致性（言行是否符合设定 + 成长弧线是否合理）
  → 情节逻辑（因果是否成立，势力关系是否自洽）
  → 节奏分析（情绪曲线是否符合设计，哪些章太拖、哪些章太赶）
  → 伏笔回收验证（埋了的是否都揭了，有无遗漏）
  → 多线叙事一致性检查（交汇点时间线是否对齐）
  → 主题一致性（核心主题是否贯穿全书）

AI 输出审查报告 → 逐条修复 / 批量自动修复

[✨ 全局润色]
  → 按严重程度分组修复
  → 统一文风
  → 消除重复用语
  → 强化主题/母题呼应

[🕐 时间线验证]
  → 全书中所有事件的时间点位
  → 检测同一角色同一时间出现在两地的矛盾
  → 检测跨叙事线的时间错位
```

---

## 六、交付期

```
导出格式：TXT / HTML / EPUB / DOCX
导出选项：
  ☑ 包含大纲
  ☑ 包含角色介绍（含角色档案 + 成长历程）
  ☑ 包含势力介绍
  ☐ 包含备注
  ☑ 卷目录结构
```

---

## 七、数据模型设计

### 7.1 模型总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据模型关系图                            │
│                                                                 │
│  Project ───────────────────────────────────────────────────┐   │
│  │  target_total_words, themes[], motifs[],                  │   │
│  │  narrative_lines[], wizard_step                          │   │
│  │                                                          │   │
│  ├── Volume (1:N)                                           │   │
│  │   │  volume_number, title, summary, theme,               │   │
│  │   │  target_words, tension_curve[],                      │   │
│  │   │  chapter_range_start, chapter_range_end              │   │
│  │   │                                                     │   │
│  │   └── OutlineNode (1:N)                                │   │
│  │       │  chapter_number, title, summary,                │   │
│  │       │  key_events[], target_words, tension_level      │   │
│  │       │  narrative_line (FK), volume (FK)              │   │
│  │       │                                                │   │
│  ├── WorldSetting (1:1)                                    │   │
│  │                                                         │   │
│  ├── Character (1:N)                                       │   │
│  │   │  growth_stages[], current_faction_id                │   │
│  │   │                                                     │   │
│  │   ├── CharacterStateSnapshot (1:N)  🆕                  │   │
│  │   │   volume_id, chapter_id, position,                  │   │
│  │   │   ability_level, mental_state, items[],              │   │
│  │   │   faction_id, faction_rank                          │   │
│  │   │                                                     │   │
│  │   └── RelationshipEvent (N:N)  🆕                        │   │
│  │       character_a_id, character_b_id,                   │   │
│  │       chapter_id, trigger_event,                        │   │
│  │       old_relation, new_relation                        │   │
│  │                                                         │   │
│  ├── Faction (1:N)  🆕                                      │   │
│  │   │  name, type, headquarters, territory,               │   │
│  │   │  core_creed, hierarchy[],                           │   │
│  │   │  faction_relations[]                                │   │
│  │   │                                                     │   │
│  │   └── FactionRelation (N:N)  🆕                         │   │
│  │       faction_a_id, faction_b_id,                       │   │
│  │       relation_type, timeline_changes[]                 │   │
│  │                                                         │   │
│  ├── Outline (1:1)                                         │   │
│  │   └── ForeshadowingPlan (1:N)                          │   │
│  │                                                         │   │
│  ├── Chapter (1:N) — 章节内容                               │   │
│  │   │  content, word_count, status, tension_actual        │   │
│  │   │  narrative_line                                     │   │
│  │   │                                                     │   │
│  │   └── TimelineEvent (1:N)  🆕                            │   │
│  │       narrative_line, time_point, description           │   │
│  │                                                         │   │
│  └── StoryStateTrail (1:N) — 全局状态追踪                   │   │
│                                                                 │
│  🆕 = v4 新增模型                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Project 模型

```python
# 新增字段
class Project(Base):
    # === 🆕 三层篇幅规划 ===
    target_total_words: int = 500000          # 全书目标总字数
    word_count_breakdown: dict = {}           # {"volume_1": 105000, "volume_2": 123000, ...}

    # === 🆕 主题与母题 ===
    core_theme: str = ""                      # 核心主题，如"自由 vs 责任"
    secondary_themes: list = []               # ["权力的代价", "成长的阵痛", ...]
    motifs: list = []                         # [
                                              #   {"name": "剑形胎记", "meaning": "身份象征", "first_appear": 3, "resolve": 28},
                                              #   {"name": "归墟之海", "meaning": "万物归源", "first_appear": 5, "resolve": 50}
                                              # ]

    # === 🆕 多线叙事 ===
    narrative_lines: list = []                # [
                                              #   {"id": "main", "name": "林牧主线", "pov_character_id": "ch_001", "ratio": 60},
                                              #   {"id": "sub_a", "name": "萧凌云支线", "pov_character_id": "ch_003", "ratio": 20},
                                              #   {"id": "sub_b", "name": "苏婉儿支线", "pov_character_id": "ch_004", "ratio": 15},
                                              #   {"id": "dark", "name": "幕后暗线", "pov_character_id": None, "ratio": 5}
                                              # ]

    # === 原有 ===
    title: str
    genre: str
    target_length: str                        # 仍保留向后兼容，对应 "short"/"medium"/"long"/"epic"
    story_brief: str                          # 500字故事梗概
    writing_style: dict                       # {tags: [], description, perspective, pace}
    wizard_step: int                          # 1~4
    status: str                               # "planning"/"writing"/"polishing"/"completed"
```

### 7.3 Volume 模型 🆕

```python
class Volume(Base):
    """卷/篇 — v4 新增，位于 Project 与 OutlineNode 之间"""
    __tablename__ = "volumes"

    id: str                                   # UUID
    project_id: str                           # FK → Project
    volume_number: int                        # 卷序号 (1, 2, 3, ...)
    title: str                                # 卷标题，如"青云之始"
    subtitle: str = ""                        # 副标题
    summary: str                              # 卷概要，描述本卷整体内容
    theme: str = ""                           # 卷主题，如"引入世界观、建立人物关系"

    # === 篇幅 ===
    target_words: int = 105000               # 本卷目标字数
    default_chapter_words: int = 3500        # 本卷默认每章字数
    chapter_count: int = 30                   # 本卷章节数

    # === 情绪曲线 ===
    tension_curve: list = []                  # [
                                              #   {"chapter": 1, "tension": 2, "label": "开篇"},
                                              #   {"chapter": 15, "tension": 8, "label": "小高潮·外门大比"},
                                              #   {"chapter": 30, "tension": 9, "label": "卷末高潮"}
                                              # ]
    emotional_arc_description: str = ""       # 情绪弧线文字描述："低→中→小高潮"

    # === 章范围 ===
    chapter_range_start: int                  # 起始章节号（全书统一编号）
    chapter_range_end: int                    # 结束章节号

    # === 叙事线分配 ===
    narrative_line_distribution: dict = {}    # {"main": 20, "sub_a": 7, "sub_b": 3}  本章数分配

    # === 顺序 ===
    sort_order: int                          # 排序

    created_at: datetime
    updated_at: datetime
```

### 7.4 OutlineNode 模型（改造）

```python
class OutlineNode(Base):
    """大纲节点 — v4 改造：新增 volume_id, narrative_line, tension_level, target_words"""
    __tablename__ = "outline_nodes"

    id: str
    outline_id: str                           # FK → Outline
    volume_id: str                            # 🆕 FK → Volume
    parent_id: str = None                     # 父节点（用于子章节）

    chapter_number: int                       # 全书统一章节号（跨卷递增）
    volume_chapter_number: int                # 🆕 卷内章节号 (1~N)
    title: str                                # 章节标题
    summary: str                              # 章节概要
    key_events: list = []                     # ["宗门测试", "受嘲笑", "罚入禁地"]

    # === 🆕 情绪 ===
    tension_level: int = 5                    # 张力等级 1~10，可视化情绪曲线的数据源

    # === 🆕 篇幅 ===
    target_words: int = 3500                 # 本章目标字数

    # === 🆕 叙事线 ===
    narrative_line: str = "main"             # 所属叙事线 ID

    # === 🆕 本章涉及要素（用于知识库检索）===
    featured_character_ids: list = []        # 本章出场角色
    featured_faction_ids: list = []          # 本章涉及势力
    featured_location_ids: list = []         # 本章涉及地点

    # === 原有 ===
    emotional_arc: str = ""                   # 情绪描述文本（保留）
    is_key_chapter: bool = False             # 是否关键章节
    sort_order: int

    created_at: datetime
    updated_at: datetime
```

### 7.5 Faction 模型 🆕

```python
class Faction(Base):
    """势力/组织 — v4 新增"""
    __tablename__ = "factions"

    id: str
    project_id: str                           # FK → Project
    name: str                                 # 势力名称，如"青云宗"
    faction_type: str                         # 类型：sect(门派) / family(家族) / empire(帝国)
                                              #      / guild(商会) / dark_org(暗组织) / race(种族)
                                              #      / clan(宗族) / academy(学院) / other

    # === 基本信息 ===
    description: str = ""                     # 势力描述
    headquarters: str = ""                    # 总部位置，如"青云山·青霄峰"
    territory: str = ""                       # 势力范围描述

    # === 理念与结构 ===
    core_creed: str = ""                      # 核心理念/信条，如"以剑问道，以心证道"
    hierarchy: list = []                      # 层级结构
                                              # [
                                              #   {"rank": 1, "title": "外门弟子", "description": "入门修行者"},
                                              #   {"rank": 2, "title": "内门弟子", "description": "核心培养对象"},
                                              #   {"rank": 3, "title": "核心弟子", "description": "宗主亲传"},
                                              #   {"rank": 4, "title": "长老", "description": "宗门决策层"},
                                              #   {"rank": 5, "title": "掌门", "description": "最高领袖"}
                                              # ]
    notable_members: list = []                # 重要成员 ID 列表 ["ch_001", "ch_002"]

    # === 发展时间线 ===
    faction_timeline: list = []               # [
                                              #   {"chapter": 1, "event": "青云宗外门大比"},
                                              #   {"chapter": 15, "event": "青云宗参与正魔大战"},
                                              #   {"chapter": 40, "event": "青云宗被迫搬迁"}
                                              # ]

    # === 视觉 ===
    emblem_description: str = ""              # 徽标/标志描述
    color_scheme: str = ""                    # 代表色

    created_at: datetime
    updated_at: datetime
```

### 7.6 FactionRelation 模型 🆕

```python
class FactionRelation(Base):
    """势力关系 — v4 新增，动态可演变"""
    __tablename__ = "faction_relations"

    id: str
    project_id: str                           # FK → Project
    faction_a_id: str                         # FK → Faction
    faction_b_id: str                         # FK → Faction

    relation_type: str                        # 当前关系：alliance(联盟) / hostility(敌对)
                                              #          / vassal(附属) / neutrality(中立)
                                              #          / rivalry(竞争) / cooperation(合作)

    timeline_changes: list = []               # 关系演变时间线
                                              # [
                                              #   {"chapter": 1, "old": "neutrality", "new": "hostility",
                                              #    "trigger": "外门大比冲突", "description": "青云宗与暗影阁弟子起冲突"},
                                              #   {"chapter": 30, "old": "hostility", "new": "alliance",
                                              #    "trigger": "共同对抗天劫", "description": "两大势力暂时联手"}
                                              # ]

    created_at: datetime
    updated_at: datetime
```

### 7.7 Character 模型（改造）

```python
class Character(Base):
    """角色 — v4 改造：新增成长弧线、势力归属"""
    __tablename__ = "characters"

    id: str
    project_id: str                           # FK → Project
    name: str
    role_type: str                            # protagonist / antagonist / supporting / mentor / love_interest / comic_relief / other

    # === 基础档案 ===
    personality: str = ""                     # 性格描述
    background: str = ""                      # 背景故事
    motivation: str = ""                      # 核心动机
    behavior_pattern: str = ""                # 行为模式
    language_style: str = ""                  # 语言风格
    emotional_expression: str = ""            # 情感表达方式
    appearance: str = ""                      # 外貌描述

    # === 🆕 势力归属 ===
    primary_faction_id: str = None            # 主要所属势力 FK → Faction
    faction_rank: str = None                  # 在势力中的职位，如"外门弟子"
    faction_history: list = []                # 势力变动历史
                                              # [
                                              #   {"chapter": 1, "faction_id": "f_001", "rank": "外门弟子"},
                                              #   {"chapter": 10, "faction_id": "f_001", "rank": "内门弟子"}
                                              # ]

    # === 🆕 成长弧线 ===
    growth_arc: str = ""                      # 成长弧线文字描述（保留兼容）
    growth_stages: list = []                  # 🆕 结构化成长阶段
                                              # [
                                              #   {
                                              #     "stage": 1, "name": "初始阶段",
                                              #     "description": "废灵根、被人看不起、内心自卑",
                                              #     "ability_level": "练气一层",
                                              #     "faction_id": "f_001",
                                              #     "faction_rank": "外门弟子",
                                              #     "trigger_chapter": 1,
                                              #     "end_chapter": 5
                                              #   },
                                              #   {
                                              #     "stage": 2, "name": "觉醒阶段",
                                              #     "description": "意外获得传承、开始建立自信",
                                              #     "ability_level": "筑基",
                                              #     "faction_id": "f_001",
                                              #     "faction_rank": "内门弟子",
                                              #     "trigger_chapter": 6,
                                              #     "end_chapter": 15
                                              #   },
                                              #   ...
                                              # ]

    # === 原有关系统计 ===
    relationships: list = []                  # 🆕 保留为快照视图，实际动态数据走 RelationshipEvent

    created_at: datetime
    updated_at: datetime
```

### 7.8 CharacterStateSnapshot 模型 🆕

```python
class CharacterStateSnapshot(Base):
    """角色状态快照 — v4 新增，记录角色在特定时间点的状态"""
    __tablename__ = "character_state_snapshots"

    id: str
    character_id: str                         # FK → Character
    project_id: str                           # FK → Project

    # === 定位 ===
    volume_id: str                            # FK → Volume
    chapter_id: str                           # FK → Chapter (snapshot 产生于哪一章之后)
    chapter_number: int                       # 章节号（冗余方便查询）
    snapshot_label: str = ""                  # 快照标签，如"外门大比前"/"传承觉醒后"

    # === 状态 ===
    position: str = ""                        # 当前位置
    ability_level: str = ""                   # 能力等级，如"筑基中期"
    mental_state: str = ""                    # 心理状态，如"自信但谨慎"
    physical_state: str = ""                  # 身体状态，如"轻伤"

    # === 归属 ===
    faction_id: str = None                    # 当前所属势力
    faction_rank: str = None                  # 当前势力职位

    # === 装备 ===
    important_items: list = []                # ["残破的古剑", "师父的玉佩"]

    # === 备注 ===
    notes: str = ""

    created_at: datetime
```

### 7.9 RelationshipEvent 模型 🆕

```python
class RelationshipEvent(Base):
    """关系变化事件 — v4 新增，替代静态 relationships JSON"""
    __tablename__ = "relationship_events"

    id: str
    project_id: str                           # FK → Project
    character_a_id: str                       # FK → Character
    character_b_id: str                       # FK → Character

    chapter_id: str                           # FK → Chapter (事件发生在哪一章)
    chapter_number: int                       # 章节号（冗余）

    # === 关系变化 ===
    old_relation: str                         # 之前的关系，如"陌生人"
    new_relation: str                         # 之后的关系，如"竞争对手"

    # === 事件 ===
    trigger_event: str                        # 触发事件，如"外门大比林牧击败萧凌云"
    description: str = ""                     # 详细描述
    relation_type: str = ""                   # 关系类型标签：friend / enemy / rival / mentor / lover / family / ally / neutral / complicated

    # === 强度 ===
    intensity: int = 5                        # 关系强度 1~10

    created_at: datetime
```

### 7.10 TimelineEvent 模型 🆕

```python
class TimelineEvent(Base):
    """时间线事件 — v4 新增"""
    __tablename__ = "timeline_events"

    id: str
    project_id: str
    chapter_id: str
    narrative_line: str = "main"              # 所属叙事线

    time_point: str                           # 时间点描述，如"第3天·寅时" / "入宗后第47天"
    absolute_day: int = None                  # 绝对天数 (Day 1 = 故事开始)
    description: str                          # 事件描述

    related_character_ids: list = []          # 涉及角色
    related_faction_ids: list = []            # 涉及势力
    related_location_ids: list = []           # 涉及地点

    is_major_event: bool = False              # 是否关键事件（大战、转折、角色死亡/出场）
    event_type: str = ""                      # event_type：battle(战斗) / meeting(会面) / death(死亡)
                                              #            / birth(出生) / departure(离开) / arrival(到达)
                                              #            / revelation(揭示) / ceremony(仪式)

    created_at: datetime
```

### 7.11 Chapter 模型（改造）

```python
class Chapter(Base):
    """章节 — v4 改造：新增叙事线、实际张力"""
    __tablename__ = "chapters"

    id: str
    project_id: str
    outline_node_id: str                      # FK → OutlineNode
    volume_id: str                            # 🆕 FK → Volume

    chapter_number: int
    title: str
    content: str = ""
    word_count: int = 0                       # 实际字数
    target_words: int = 3500                 # 🆕 目标字数

    status: str                               # planned / writing / completed / archived

    narrative_line: str = "main"              # 🆕 所属叙事线

    # === 质量 ===
    quality_score: int = None                 # AI 质量评分
    tension_actual: int = None                # 🆕 实际张力评级（写完后分析）

    version: int = 1
    created_at: datetime
    updated_at: datetime
```

### 7.12 表结构变更总览

| 表 | v3 状态 | v4 变更 | 优先级 |
|----|---------|---------|--------|
| `Project` | 基础字段 | + target_total_words, themes[], motifs[], narrative_lines[] | P0 |
| `Volume` 🆕 | 不存在 | 新建表（卷结构、篇幅、情绪曲线） | P0 |
| `OutlineNode` | 扁平的章列表 | + volume_id, tension_level, narrative_line, key_events[], featured_* 等 | P0 |
| `Faction` 🆕 | 不存在 | 新建表（势力/组织） | P0 |
| `FactionRelation` 🆕 | 不存在 | 新建表（势力动态关系） | P1 |
| `Character` | 基础角色档案 | + growth_stages[], faction_id, faction_rank | P0 |
| `CharacterStateSnapshot` 🆕 | 不存在 | 新建表（角色状态快照） | P1 |
| `RelationshipEvent` 🆕 | 不存在 | 新建表（动态关系） | P1 |
| `TimelineEvent` 🆕 | 不存在 | 新建表（时间线） | P2 |
| `Chapter` | 基础章节 | + volume_id, narrative_line, tension_actual | P0 |
| `WorldSetting` | 六维度 | 不变 | - |
| `Outline` | 大纲主表 | 不变 | - |
| `ForeshadowingPlan` | 伏笔 | 不变（可后续关联 volume_id） | - |
| `StoryStateTrail` | 已有 | 不变（后期关联 TimelineEvent） | - |

---

## 八、API 设计

### 8.1 向导阶段 API

```
POST /api/v1/projects
Body: { genre, target_length, target_total_words?, story_suggestion?, interests? }
→ 创建 Project + 空 WorldSetting + 默认 Volume 框架
→ asyncio 后台生成书名梗概 + 篇幅分配方案 → 更新 Project
→ 返回 { project_id }

POST /api/v1/projects/{id}/wizard/step/{step}
step ∈ {world, characters, outline}

world:
  → 后台生成世界观六维度 + 主题/母题 → 写入 WorldSetting + Project.themes/motifs

characters:
  → 后台生成角色+关系+势力 → 创建 Character × N + Faction × M
  → 为每个角色生成成长弧线(growth_stages)

outline:
  → 后台生成大纲+伏笔+情绪曲线+叙事线分配
  → 创建 Volume × N + OutlineNode × N + ForeshadowingPlan + Chapter × N(planned)

GET /api/v1/projects/{id}/wizard/status/{task_id}
→ { status, progress, progress_message }
```

### 8.2 篇幅规划 API 🆕

```
GET  /api/v1/projects/{id}/word-plan
→ { target_total_words, volumes: [{ id, title, target_words, chapter_count, default_chapter_words }], breakdown[] }

PUT  /api/v1/projects/{id}/word-plan
Body: { target_total_words, volumes: [{ id, target_words, chapter_count, default_chapter_words }] }
→ 更新篇幅分配（支持拖拽滑块调整）
```

### 8.3 卷管理 API 🆕

```
GET    /api/v1/projects/{id}/volumes              → Volume[]
POST   /api/v1/projects/{id}/volumes              → Volume (新建卷)
PUT    /api/v1/projects/{id}/volumes/{vol_id}     → Volume (更新卷)
DELETE /api/v1/projects/{id}/volumes/{vol_id}     → 删除卷（级联删除关联章节）

PUT    /api/v1/projects/{id}/volumes/reorder
Body: [{ id, sort_order }]                        → 重新排序卷
```

### 8.4 势力管理 API 🆕

```
GET    /api/v1/projects/{id}/factions              → Faction[] (含势力关系)
POST   /api/v1/projects/{id}/factions              → Faction
PUT    /api/v1/projects/{id}/factions/{f_id}       → Faction
DELETE /api/v1/projects/{id}/factions/{f_id}       → 删除势力

POST   /api/v1/projects/{id}/factions/{f_id}/relations
Body: { target_faction_id, relation_type }         → FactionRelation (新建势力关系)

PUT    /api/v1/projects/{id}/faction-relations/{fr_id}
Body: { relation_type, trigger_event, chapter_number } → 更新势力关系
```

### 8.5 角色成长与状态 API 🆕

```
GET    /api/v1/projects/{id}/characters/{ch_id}/growth     → 成长弧线 + 所有快照
PUT    /api/v1/projects/{id}/characters/{ch_id}/growth     → 更新 growth_stages

GET    /api/v1/projects/{id}/characters/{ch_id}/snapshots  → CharacterStateSnapshot[]
POST   /api/v1/projects/{id}/characters/{ch_id}/snapshots  → 新建状态快照

# 自动快照：章节完成后 AI 检测到状态变化 → 生成快照 → 用户确认
POST   /api/v1/projects/{id}/chapters/{ch_id}/complete
→ 完成后端自动检测角色状态变化 → 生成待确认快照 → 返回变化列表
```

### 8.6 动态关系 API 🆕

```
GET    /api/v1/projects/{id}/relationships                    → 当前所有角色间关系（实时计算）
GET    /api/v1/projects/{id}/relationships/timeline           → 关系演变时间线
       ?char_a={id}&char_b={id}                               → 筛选特定角色对

GET    /api/v1/projects/{id}/relationship-events              → RelationshipEvent[]
POST   /api/v1/projects/{id}/relationship-events              → 新建关系事件
PUT    /api/v1/projects/{id}/relationship-events/{re_id}      → 修改关系事件
DELETE /api/v1/projects/{id}/relationship-events/{re_id}      → 删除关系事件
```

### 8.7 情绪曲线 API 🆕

```
GET    /api/v1/projects/{id}/tension-curve                    → 全书情绪曲线数据
       ?volume_id={id}                                        → 筛选特定卷

PUT    /api/v1/projects/{id}/tension-curve
Body: { volumes: [{ id, tension_curve: [{ chapter, tension, label }] }] }
→ 批量更新情绪曲线

PUT    /api/v1/projects/{id}/volumes/{vol_id}/tension-curve   → 更新单卷情绪曲线
```

### 8.8 时间线 API 🆕

```
GET    /api/v1/projects/{id}/timeline                         → TimelineEvent[]
       ?narrative_line={id}                                    → 按叙事线筛选
       ?chapter_range=10-20                                    → 按章范围筛选

POST   /api/v1/projects/{id}/timeline/validate                → 执行时间线一致性检查
→ { conflicts: [{ type, description, suggestions }] }
```

### 8.9 写作期 API（改造）

```
GET  /api/v1/projects/{id}/chapters          → 章节列表（含 volume_id, narrative_line, tension_actual）
POST /api/v1/projects/{id}/generation/start  → 批量生成（支持 volume_id 参数：只生成某卷）
POST /api/v1/projects/{id}/generation/chapter → 单章生成
    Body: { chapter_id, precision_config: { tension_target? } }
```

### 8.10 API 路由变更总览

| 路由 | 变更类型 | 优先级 |
|------|---------|--------|
| `POST /projects` | 改造：接收篇幅参数 | P0 |
| `POST /wizard/step/{step}` | 改造：step 逻辑升级 | P0 |
| `/projects/{id}/volumes/*` | 🆕 新增 CRUD | P0 |
| `/projects/{id}/word-plan` | 🆕 新增 | P0 |
| `/projects/{id}/factions/*` | 🆕 新增 | P0 |
| `/projects/{id}/faction-relations/*` | 🆕 新增 | P1 |
| `/projects/{id}/characters/{id}/growth` | 🆕 新增 | P0 |
| `/projects/{id}/characters/{id}/snapshots` | 🆕 新增 | P1 |
| `/projects/{id}/relationships` | 🆕 新增 | P1 |
| `/projects/{id}/relationship-events` | 🆕 新增 | P1 |
| `/projects/{id}/tension-curve` | 🆕 新增 | P1 |
| `/projects/{id}/timeline` | 🆕 新增 | P2 |

---

## 九、前端文件规划

```
新增页面：
  pages/ProjectWizardPage.tsx                # 向导主页（含新步骤）

新增组件：
  components/wizard/
    WizardStepTitleBrief.tsx                 # Step 1：书名梗概 + 篇幅规划
    WizardWordPlanPanel.tsx    🆕            # 三层篇幅规划面板（滑块+表格）
    WizardStepWorld.tsx                      # Step 2：世界观 + 主题母题
    WizardThemeMotifPanel.tsx  🆕            # 主题与母题编辑器
    WizardStepCharacters.tsx                 # Step 3：角色 + 势力
    WizardFactionPanel.tsx     🆕            # 势力管理面板
    WizardFactionEditor.tsx    🆕            # 单势力编辑面板
    WizardCharacterGrowthPanel.tsx 🆕        # 角色成长弧线编辑器
    WizardRelationshipPanel.tsx 🆕           # 动态关系网络可视化
    WizardStepOutline.tsx                    # Step 4：卷章大纲 + 情绪曲线 + 伏笔
    WizardVolumePanel.tsx      🆕            # 卷管理面板
    WizardTensionCurvePanel.tsx 🆕           # 情绪曲线可视化编辑器（可拖拽）
    WizardNarrativeLinesPanel.tsx 🆕         # 多线叙事配置
    WizardStepProgress.tsx                   # 顶栏步骤条
    WizardStepActions.tsx                    # 底部操作栏

新增页面/组件：
  pages/WorkbenchPage.tsx                    # 工作台（写作期主界面）
  components/workbench/
    VolumeChapterNav.tsx       🆕            # 卷·章导航树
    FactionOverview.tsx        🆕            # 势力总览面板
    RelationshipTimeline.tsx   🆕            # 关系演变时间线视图
    CharacterStatePanel.tsx    🆕            # 角色当前状态面板
    TimelineView.tsx           🆕            # 时间线可视化视图（P2）
    TensionCurveWidget.tsx     🆕            # 情绪曲线小部件
    ThemeMotifTracker.tsx      🆕            # 主题母题追踪

改造：
  pages/CreateProjectPage.tsx                # 新增篇幅选择
  routes/index.tsx                           # + 新路由
  services/
    wizardApi.ts                             # 改造
    volumeApi.ts               🆕
    factionApi.ts              🆕
    characterGrowthApi.ts      🆕
    relationshipApi.ts         🆕
    tensionCurveApi.ts         🆕
    timelineApi.ts             🆕
  stores/
    useWizardStore.ts                        # 大幅改造
    useVolumeStore.ts          🆕
    useFactionStore.ts         🆕
    useRelationshipStore.ts    🆕

删除：
  所有 blueprint_* 相关文件
```

---

## 十、优先级规划

### P0（必须做）— 基础架构，不做小说质量上不去

| 序号 | 优化点 | 具体工作 | 影响范围 |
|------|--------|---------|---------|
| 1 | 三层篇幅规划 | Project 加字段，新建 WordPlanPanel，API | 1个模型改造 + 1个新组件 |
| 2 | 卷/篇层级结构 | 新建 Volume 模型，OutlineNode 改造，卷管理 API + 组件 | 1个新模型 + 1个模型改造 + 5个组件 |
| 3 | 势力/组织系统 | 新建 Faction + FactionRelation 模型，势力管理 API + 组件 | 2个新模型 + 4个组件 |
| 4 | 角色成长 | Character 加 growth_stages，CharacterStateSnapshot 模型，成长弧线编辑器 | 1个模型改造 + 1个新模型 + 2个组件 |

### P1（应该做）— 显著提升 AI 生成质量

| 序号 | 优化点 | 具体工作 | 影响范围 |
|------|--------|---------|---------|
| 5 | 动态关系网络 | RelationshipEvent 模型，关系追踪 API，关系时间线视图 | 1个新模型 + 3个组件 |
| 6 | 情绪曲线 | Volume.tension_curve，OutlineNode.tension_level，TensionCurvePanel（可拖拽） | 2个模型字段 + 2个组件 |
| 7 | 主题与母题 | Project.themes/motifs，WizardThemeMotifPanel，写作期追踪器 | 2个字段 + 2个组件 |

### P2（可以做）— 锦上添花，后续迭代

| 序号 | 优化点 | 具体工作 | 影响范围 |
|------|--------|---------|---------|
| 8 | 时间线管理 | TimelineEvent 模型，时间线验证 API，TimelineView 可视化 | 1个新模型 + 1个组件 |
| 9 | 知识库检索 | 改写 context 组装逻辑（相关性排序 + 动态压缩） | 后端生成逻辑改造 |
| 10 | 多线叙事 | Project.narrative_lines，OutlineNode.narrative_line，NarrativeLinesPanel | 2个字段 + 1个组件 |

### 推荐迭代顺序

```
Phase 1 (Day 1-5):  P0 — 篇幅规划 + 卷结构 + 势力系统 + 角色成长
Phase 2 (Day 6-9):  P1 — 动态关系 + 情绪曲线 + 主题母题
Phase 3 (Day 10+):  P2 — 时间线 + 知识库检索 + 多线叙事
```

---

## 十一、完整用户时间线 v4

```
Day 1  上午：说"我想写修仙小说" → AI 方案 → 选了一个
        → Step 1 书名梗概 + 拖拽全书字数滑块 → 50万字 → 确认
        下午：Step 2 世界观六维度 + 设定核心主题"自由 vs 责任" → 确认
        → Step 3 角色 + 势力：青云宗·暗影阁·天玄帝国 → 确认
        → 每个角色自动生成成长弧线 → 微调

Day 2  上午：Step 4 卷大纲出来（4卷140章）
        → 拖拽情绪曲线，调整每章张力
        → 配置多线叙事：主线60% + 支线A 20% + 支线B 15% + 暗线5%
        → 确认大纲，开始写作

        下午：写第1~3章，看着不错
        → 写第4章时 AI 自动检测：林牧从"练气一层→筑基"
        → 弹出角色状态变化确认：✅ 接受
        → 写第10章时 AI 提示：林牧↔萧凌云 关系从"竞争对手→宿敌"
        → 弹出关系变化确认：✅ 接受
        → 点"生成整卷卷一" → 去睡觉

Day 3  起床：AI 生成了卷一全部 30章 → 快速翻一遍
        → 第7章情绪张力偏低，手动调到 ▲▲▲▲
        → 第15章关系演变不对，回退重写
        → 卷一完成！点"生成整卷卷二" → 后台继续

Day 4  🔍 全面审查 → 发现 12 个问题
        → 时间线矛盾 2 个：林牧同一天出现在两地 → 手动修正
        → 角色言行不一致 3 个 → 自动修复
        → 伏笔未回收 1 个 → 补充揭伏笔章节
        ✨ 全局润色完成
        📦 导出 EPUB（含卷目录 + 角色成长历程 + 势力图鉴）
        → 发到 Kindle → 完美！
```

---

## 十二、10 个优化点速查

| # | 优化点 | 核心动作 | 优先级 |
|---|--------|---------|--------|
| 1 | 📏 三层篇幅规划 | Project + target_total_words, Volume + target_words, OutlineNode + target_words | P0 |
| 2 | 📚 卷/篇层级 | 新建 Volume 模型，Outline ↔ Volume ↔ OutlineNode | P0 |
| 3 | 🏛 势力/组织 | 新建 Faction + FactionRelation | P0 |
| 4 | 🎭 角色成长 | Character + growth_stages, 新建 CharacterStateSnapshot | P0 |
| 5 | 🔗 动态关系 | 新建 RelationshipEvent（替代静态 JSON） | P1 |
| 6 | 🎵 情绪曲线 | Volume + tension_curve, OutlineNode + tension_level, 可视化编辑器 | P1 |
| 7 | 🎯 主题/母题 | Project + themes/motifs | P1 |
| 8 | 📖 时间线管理 | 新建 TimelineEvent + 验证 API（与 StoryStateTrail 配合） | P2 |
| 9 | 🧩 知识库检索 | 改写 context 组装逻辑（相关性排序 + 动态压缩） | P2 |
| 10 | 🌿 多线叙事 | Project + narrative_lines, OutlineNode + narrative_line | P2 |

---

> v4 设计完成。下一步：按 P0→P1→P2 顺序进入开发。
