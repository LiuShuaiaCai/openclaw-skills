---
name: "crossref-xiaohongshu-daily"
description: |
  从 CrossRef 抓取当天发布的学术文章，进行多维度数据分析，生成图片，
  配文后自动发布到小红书。

  触发场景：
  - "帮我抓取今天的学术新文章"
  - "生成今日学术速报"
  - "今天的论文有哪些"
  - "学术动态日报"
  - "帮我做学术资讯分享"
  - "今日学术热点"
  - "最新学术论文"
  - "帮我生成小红书学术内容"
  - "发布今日学术日报到小红书"
  - "自动生成学术图文并发布"
  - "CrossRef 每日报告"
  - "安装小红书MCP"
  - "配置xhs-mcp"
---

# CrossRef 学术日报 → 小红书自动发布 Skill

> 一键完成：CrossRef 抓取 → 数据可视化 → 文案生成 → 小红书发布

---

## 工作流总览

```
Step 1  从 CrossRef 抓取当日学术文章
   ↓
Step 2  数据清洗 + 期刊信息补充（支持 SQLite 或 MySQL）
   ↓
Step 3  生成 3 张精选可视化图表（PNG）+ manifest.json（每天随机选3种不同类型）
   ↓
Step 3.5  生成封面图（互动式悬念提问风格，随机选用模板）
   ↓
Step 4  AI 整合 3 个维度生成 1 篇小红书文案（标题/正文/问题/标签）
   ↓
Step 4.5  网上核实内容（确保数据准确，无虚假信息）
   ↓
Step 5  安装 xhs-mcp → 扫码登录 → --mode combined 发布 1 篇笔记
```

> 📌 每日只发 **1 篇**笔记，内容整合 8 个维度的核心发现。

---

## Step 3.5 — 生成封面图（简单日报风格）

**风格定位**：简洁、专业、数据感。学术日报风格，清晰明了。

### 模板库（随机选用）

| 编号 | 背景色 | 文案模板 | 风格 |
|:---:|--------|----------|------|
| 1 | 薄荷绿 | "📊 今日学术日报\nX篇论文发布" | 简洁数据 |
| 2 | 浅蓝白 | "🔬 Academic Daily\n今日学术速报" | 简洁专业 |
| 3 | 淡灰白 | "论文发布日报\nX篇新研究" | 简洁数据 |
| 4 | 浅绿白 | "📚 学术发布\nDaily Report" | 简洁专业 |
| 5 | 暖黄底 | "今日学术\nX篇论文发布" | 简洁数据 |
| 6 | 银灰渐变 | "Academic Report\n今日论文发布" | 简洁专业 |
| 7 | 青绿渐变 | "📊 学术日报\nX篇新发布" | 简洁数据 |
| 8 | 浅紫白 | "🔍 论文速报\nDaily Paper Report" | 简洁专业 |
| 9 | 薰衣草紫 | "学术发布\nDaily Academic" | 简洁专业 |
| 10 | 墨绿渐变 | "🔬 Academic Daily\nDaily Report" | 简洁专业 |

### 生成规则

1. **随机选择**：每次从模板库中随机选用1套
2. **浅色背景**：必须使用浅色/柔和渐变背景
3. **大字体居中**：主文案要大、醒目、居中
4. **简洁为主**：文案以数据为主（X篇论文），不做悬念提问
5. **尺寸**：**3:4 竖版**（推荐 1024x1360）
6. **风格**：简洁干净，留白充足，适合移动端展示，数据感强
7. ⚠️ **必须使用 `image_gen` 工具生成**，禁止使用本地 matplotlib 合成封面图
   - 若 `image_gen` 队列超时，重试1次，仍失败则告知用户跳过封面，不降级为本地生成

### 执行命令

```bash
# 调用 image_gen 工具生成封面图
# prompt 示例（根据随机模板替换文案和颜色）
prompt: "Xiaohongshu cover, soft mint green gradient background, Chinese text 'AI论文数量超过医学了？' large centered, thinking emoji 🤔, clean minimalist academic design"

# 保存到封面图目录
output_dir: "generated-images"
size: "1365x1024"
n: 1
```

### 封面图集成

生成封面图后，将其作为**第一张图**加入到发布图片列表中：
- 位置：3张分析图的**最前面**
- 发布时按顺序：封面图 → 3张分析图（共4张）

---

## Step 1 — 环境检测

```powershell
# 检测 Python
python --version
# 检测关键依赖
python -c "import requests, pandas, matplotlib, seaborn, PIL; print('OK')"
```

---

## Step 2 — 运行主脚本，生成图表

```bash
# 抓取昨天数据（默认）
python scripts/main.py

# 抓取指定日期
python scripts/main.py 2026-04-19

# 指定输出目录
python scripts/main.py 2026-04-19 charts
```

**每天随机选择 3 种图表类型**（保证新鲜感，避免审美疲劳）：

| 类型 | 图种 | 文件名 |
|------|------|--------|
| 饼图（3选1） | 学科分布 | `Discipline_Distribution__Domain_Class_.png` |
| | JCR 分区 | `JCR_Section_Distribution.png` |
| | CAS 分区 | `CAS_Section_Distribution.png` |
| 横向柱状 | 期刊发文榜 Top20 | `Top_20_JCR_Journals_by_Article_Count.png` |
| 柱状图 | 出版社发文榜 Top10 | `Top_10_Publishers_by_Article_Count.png` |
| 热力图（2选1） | 期刊×学科 | `Top_20_Journals_by_Discipline_Heatmap.png` |
| | 出版社×学科 | `Top_20_Publisher_by_Discipline_Heatmap.png` |

**输出目录结构（每天 3 张图 + 封面图 = 4 张）：**

```
charts/
└── 2026-04-19/
    ├── Top_20_JCR_Journals_by_Article_Count.png
    ├── Discipline_Distribution__Domain_Class_.png
    ├── Top_20_Publisher_by_Discipline_Heatmap.png
    └── manifest.json
```

---

## Step 3 — 生成小红书文案

Agent 基于 `manifest.json` 中的统计数据，用 AI 生成高质量文案。

### 文案生成要求

**每日只生成 1 篇整合笔记**，内容涵盖 **3 个维度**的核心发现：

1. **风格**：不死板说教，要有趣但不失严谨，语气像在和朋友分享有趣发现
2. **角度**：以讨论口吻，**不要以教学者姿态**
3. **结构**：
   - 标题：**用 emoji + 疑问/感叹/反问式吸引点击，⚠️ 严禁使用陈述句**
     - ✅ 正确示例：`😱 一天7千+篇论文！医学发文量又霸榜首？真相来了🤔`、`📊 昨天7291篇，Q1居然占了一半？`、`🔬 期刊战场有多卷？这组数据让我惊了！`
     - ❌ 错误示例：`📚 昨天7291篇新论文，医学发文量又霸榜了？🔬`（前半段是陈述，后半段仅是弱疑问，吸引力不够）
     - 规则：标题须有强烈情绪钩子，疑问/惊讶/反差感三选一，emoji 前置
   - 正文（**≤ 1000 字符**，xhs-mcp `--content` 限制；段落分明，有洞察而不是堆数据）
   - 互动问题（真诚提问，引导用户留言讨论）
   - 话题标签（5-8个）
   - **数据来源**（固定放在正文最后）：`📊 数据来源：CrossRef（YYYY-MM-DD 共 N 篇）`
4. **必须抛出一个问题** 与用户互动

每天选 3 种图表类型，Agent 根据实际选中的类型生成文案：

| 图表类型 | 内容侧重 | 互动方向 |
|---------|---------|---------|
| 期刊发文榜（横向柱状） | 哪些期刊今天最活跃，有没有意外 | 你常投哪本？ |
| 出版社发文榜（柱状） | 出版社格局与学术马太效应 | 投稿看出版社名气吗？ |
| 学科分布（饼图） | 哪个方向最热，有无冷门惊喜 | 你的领域在哪？ |
| JCR/CAS 分区（饼图） | 高区间占比与现实投稿策略 | 你们单位有分区要求吗？ |
| 学科热力图 | 期刊×学科交叉的"深色格子"发现 | 发现哪个意外组合？ |
| 出版社×学科热力图 | 哪家出版社在哪个领域最强 | 投稿选对出版社了吗？ |

**输出文件：**
- `charts/{date}/copywriting_input.json` — AI 生成源文件
- `charts/{date}/copywriting.json` — 每图一篇（分条模式）
- `charts/{date}/copywriting_combined.json` — **每日整合版**（1篇汇总8个维度，用于 --mode combined）

### AI 生成后写入 JSON

由于直接用工具写入含中文复杂字符的 JSON 可能出现编码问题，建议两步走：

```bash
# 1. Agent 将生成的 JSON 写入源文件到工作目录
# 2. 用 Python helper 脚本安全序列化到目标路径
python scripts/write_copywriting.py charts/{date}/copywriting.json charts/{date}/copywriting_input.json
```

---

## Step 4.5 — 内容核实（非常重要）

⚠️ **发布前必须核实内容真实性，避免传播虚假信息！**

### 核实清单

1. **数据核实**
   - CrossRef 返回的论文数量是否合理（如有异常波动需说明）
   - 期刊名、出版社名是否准确（避免乱码/错误翻译）
   - 排名数据是否与图表一致

2. **文案核实**
   - 标题中的数据是否准确（如 "医学发文量第一" 是否有数据支撑）
   - 百分比/数字是否有夸大或误导
   - 是否有无依据的推测性结论

3. **网上交叉验证（可选但推荐）**
   - 对于重大发现（如 "某领域首次突破"），用 WebSearch 确认
   - 核实论文 DOI 是否真实存在
   - 确认期刊/出版社名称的正确性

### 处理原则

| 情况 | 处理方式 |
|------|----------|
| 数据有明显异常 | 在文案中注明 "数据来源：CrossRef" 并说明局限性 |
| 无法核实的信息 | 删除或改为模糊表述 |
| 涉及具体论文结论 | 明确标注 "据 CrossRef 元数据显示"，避免断言式表述 |
| 发现虚假信息 | 立即停止发布，修正后再发布 |

---

## Step 4 — 发布模式说明

**重要：每日发布 1 篇笔记，整合 3 个维度的精华数据。**
- **封面图 + 3 张精选分析图**（共 4 张）合并到 **1 篇**小红书笔记
- 文案整合 3 个维度的核心发现，1 条有参与感的互动问题
- 调用 `--mode combined` 模式自动合并所有图表

---

## Step 5 — 小红书发布（xhs-mcp）

### 4.1 安装 xhs-mcp

```bash
npm i -g xhs-mcp
```

### 4.2 扫码登录（弹出浏览器）

```bash
npx xhs-mcp login --timeout 120
```

执行后会：
1. 启动 Puppeteer Chromium 浏览器（非无头模式）
2. 自动打开小红书登录页面
3. **用户用小红书 App 扫码登录**（或账号密码）
4. 登录成功后 Cookie 自动保存

> ⚠️ 首次使用需先安装 Puppeteer 浏览器：
> ```bash
> npx xhs-mcp browser
> ```

### 4.3 验证登录状态

```bash
npx xhs-mcp status
```

### 4.4 登录过期 → 自动打开浏览器扫码

**发布前脚本会自动检测登录状态**：
- `loggedIn: true` → 直接发布
- `loggedIn: false` → 自动执行 `npx xhs-mcp login`，弹出浏览器等待用户扫码，扫码成功后再发布

> 无需手动操作，脚本自动处理。Cookie 有效期约 30 天，过期后发布时自动弹窗重扫。

### 5.4 发布笔记

#### 预览模式（推荐先执行）

```bash
python scripts/publish_xhs.py charts/2026-04-19/copywriting.json --mode preview
```

#### 整合发布（每日正式模式）

```bash
python scripts/publish_xhs.py charts/2026-04-19/copywriting_combined.json --mode combined --manifest charts/2026-04-19/manifest.json
```

> **推荐模式**：封面图 + 3张图自动合并到 1 篇笔记，每日只发 1 篇。

#### 发布单条（调试用）

```bash
python scripts/publish_xhs.py charts/2026-04-19/copywriting.json --mode single --index 0
```

#### 批量发布（多篇发布模式，不推荐）

```bash
python scripts/publish_xhs.py charts/2026-04-19/copywriting.json --mode batch
```

### 4.5 Agent 执行发布

当脚本生成 `publish_task.md` 后，Agent 读取文件内容，依次调用 `xhs_create_note` MCP 工具：

```
title        → 笔记标题（≤20字）
desc         → 正文（含互动问题）
image_paths  → [image_path]（原始图表路径，无水印）
topics       → 话题标签列表（不含 # 号）
```

每条发布间隔 **≥ 30 秒**，避免触发小红书频率限制。

---

## 完整一键执行命令

```bash
DATE=$(date +%Y-%m-%d)  # 或手动指定: DATE=2026-04-19

# Step 1~3: 抓取 + 出图 + 统计
python scripts/main.py $DATE charts

# Step 4: 生成文案（Agent 在此步骤用 AI 生成高质量文案）
# Agent 生成 JSON → 保存到 charts/$DATE/copywriting_input.json
python scripts/write_copywriting.py charts/$DATE/copywriting.json charts/$DATE/copywriting_input.json

# Step 5: 安装 xhs-mcp（如尚未安装）
npm i -g xhs-mcp

# Step 6: 扫码登录（弹出浏览器，用户扫码）
npx xhs-mcp login --timeout 120

# Step 7: 预览确认（可选）
python scripts/publish_xhs.py charts/$DATE/copywriting_combined.json --mode preview

# Step 8: 整合发布（每日模式：封面+3图合并为1篇）
python scripts/publish_xhs.py charts/$DATE/copywriting_combined.json --mode combined --manifest charts/$DATE/manifest.json
```

---

## 自动化调度

在 WorkBuddy 中创建自动化任务（每日 8:00 执行）：

**Automation Prompt：**
```
使用 crossref-xiaohongshu-daily skill，
执行今日学术日报的完整流程：
抓取昨天的 CrossRef 数据 → 随机生成 3 种精选图表 → 生成封面图
→ 用 AI 生成小红书文案（整合3个维度为1篇）
→ 扫码登录小红书 → 用 --mode combined 模式发布1篇整合笔记到小红书。
工作目录: E:/WorkBuddyProjects
图表输出目录: E:/WorkBuddyProjects/charts
```

**调度规则：** `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=8;BYMINUTE=0`

---

## 数据库配置说明

本 Skill 支持两种数据库模式：**SQLite（推荐）** 或 **MySQL**。

### 模式一：SQLite（推荐，无需安装数据库）

1. **导出 MySQL 数据到 SQLite**：

```bash
# 安装依赖
pip install pymysql

# 运行迁移脚本
python scripts/mysql_to_sqlite.py
```

2. **配置**（默认已配置，无需修改）：

脚本会自动查找 `data/crossref_data.db`，无需额外配置。

3. **表结构**：

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `journals` | 期刊信息 | issn, jcr_section, cas_section, domain_class |
| `countries` | 国家列表 | name |

### 模式二：MySQL（可选）

1. **配置连接**（在 `scripts/main.py` 中修改）：

```python
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "your_password",
    "database": "express",
    "charset": "utf8mb4"
}
```

2. **设置数据库类型**：

```python
DB_TYPE = "mysql"  # 或通过环境变量设置
```

### 数据库功能

| 功能 | 需要数据库 | 说明 |
|------|----------|------|
| 期刊 JCR/CAS 分区信息 | ✅ | 补充分区饼图数据 |
| 学科分类 | ✅ | 补充学科热力图数据 |
| 国家分布 | ✅（可选） | 也可使用内置列表 |
| 期刊发文榜 | ❌ | 直接从 CrossRef 数据生成 |
| 出版社发文榜 | ❌ | 直接从 CrossRef 数据生成 |

**注意**：即使没有数据库，核心图表（期刊榜、出版社榜）仍可正常生成。

---

## 踩坑经验

- CrossRef API 不传 `mailto` 参数会被限流，`main.py` 中已加入，请替换为真实邮箱
- `subjects` 字段覆盖率低，可通过期刊名进行学科推断
- xhs-mcp publish CLI 的 `--media` 参数支持逗号分隔多图（绝对路径），`--title` 有 40 宽度单位限制（含emoji计双字节）
- xhs-mcp publish CLI 在 subprocess 中调用时，必须用 list 形式传参 `["node", "path\\to\\xhs-mcp.cjs", "publish", ...]`，避免 shell=True + 字符串拼接导致的参数解析问题
- xhs-mcp 的 Puppeteer 浏览器自动化可能因网络/页面加载慢超时，脚本内置自动重试（最多3次，指数退避）
- 小红书发布每条间隔建议 ≥ 30 秒，每日发布数量建议 ≤ 10 条，避免被限流
- AI 生成含中文的 JSON 时，建议通过 `write_copywriting.py` helper 脚本写入，避免直接工具写入导致编码问题
- xhs-mcp `login` 命令会弹出独立的 Puppeteer 浏览器窗口，用户在窗口内完成扫码
- 安装 xhs-mcp 后首次运行若提示缺少浏览器，运行 `npx xhs-mcp browser` 安装 Chromium
- **publish_xhs.py 已内置登录检测**：发布前自动检查 `loggedIn` 状态，未登录则自动弹出浏览器扫码，无需手动操作
- xhs-mcp `--content` 参数限制 **1000 字符**，文案正文需控制在此范围内；脚本内置自动截断保护
- **MySQL → SQLite 迁移**：使用 `mysql_to_sqlite.py` 脚本导出数据，SQLite 默认路径为 `data/crossref_data.db`
- **DB_TYPE 环境变量**：可通过设置 `DB_TYPE=mysql` 或 `DB_TYPE=sqlite` 切换数据库模式
- **封面图必须用 image_gen 工具生成**：禁止降级为本地 matplotlib 合成，本地生成的封面质量差；若 image_gen 超时可重试1次，仍失败则告知用户
- **封面图必须放入 selected_images 第一位**：`copywriting_combined.json` 的 `selected_images` 数组中，封面图路径须排在最前面，否则发布时封面图不会出现
- **标题严禁陈述句**：标题必须是疑问、感叹或反问式，需有强烈情绪钩子（惊讶/反差/好奇）；纯陈述句即使加了？也不够，需有悬念感
