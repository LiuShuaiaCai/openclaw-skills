"""
小红书文案生成脚本
- 读取 manifest.json 中的统计数据和图片信息
- 针对每张图片，调用 LLM 生成匹配的小红书文案
- 输出 copywriting.json（含每张图片对应的标题/正文/话题标签/互动问题）

用法:
    python generate_copywriting.py <manifest_path> [output_dir]
    e.g.:  python generate_copywriting.py charts/2026-04-19/manifest.json charts/2026-04-19
"""

import json
import os
import sys
from datetime import datetime

# ──────────────────────────────────────────────
# 图表类型 → 文案模板映射
# 每个模板描述了：该图讲什么数据、关注什么视角、抛什么互动问题
# ──────────────────────────────────────────────

CHART_PROMPTS = {
    "bar_horizontal": {
        "scene": "期刊发文量排行榜",
        "focus": "哪些期刊今天发文最多、它们属于什么领域",
        "question_hint": "你关注的方向在哪本期刊上发表？你觉得发文量多说明什么？",
        "tone": "好奇探索+数据党",
    },
    "bar": {
        "scene": "出版社发文量排行榜",
        "focus": "头部出版社今日发文数量、出版社格局与学术生态",
        "question_hint": "你投稿时会优先考虑哪家出版社？为什么？",
        "tone": "轻松讨论+真实经验分享",
    },
    "pie": {
        "scene": "分布饼图（学科/JCR分区/CAS分区/国家）",
        "focus": "占比最高的几个类别、有没有出乎意料的发现",
        "question_hint": "这个分布和你预想的一样吗？有没有哪个比例让你惊讶？",
        "tone": "共鸣引发+轻反思",
    },
    "heatmap": {
        "scene": "期刊×学科/出版社×学科热力图",
        "focus": "哪个组合最热、冷门与热门之间的反差",
        "question_hint": "你发现了什么规律？哪个交叉点让你觉得意外？",
        "tone": "侦探解谜+知识分享",
    },
}

DEFAULT_PROMPT = {
    "scene": "学术数据可视化",
    "focus": "今日全球最新论文发布动态",
    "question_hint": "你今天有看到哪个方向特别活跃？",
    "tone": "求知探索",
}

# ──────────────────────────────────────────────
# 文案生成逻辑（规则型，不依赖外部 LLM API）
# AI Agent 在读取本文件后会接管这部分逻辑
# ──────────────────────────────────────────────

def build_copywriting_prompt(img_info: dict, stats: dict) -> str:
    """
    构建给 AI 的提示词，让 AI 生成文案。
    如果在 Agent 环境中运行，Agent 会读取此 prompt 并直接生成文案。
    如果独立运行，则输出 prompt 供手动调用。
    """
    chart_type = img_info.get("type", "")
    img_title = img_info.get("title", "")
    tmpl = CHART_PROMPTS.get(chart_type, DEFAULT_PROMPT)

    date_str = stats.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = stats.get("total_articles", 0)

    # 构造数据摘要文本
    data_snippet = ""
    if chart_type == "bar_horizontal" or chart_type == "bar":
        top_j = stats.get("top_journals", [])[:5]
        top_p = stats.get("top_publishers", [])[:5]
        data_snippet = (
            f"今日发文量 Top5 期刊: " +
            ", ".join(f"{x['name']}({x['count']}篇)" for x in top_j) +
            "\n出版社 Top5: " +
            ", ".join(f"{x['name']}({x['count']}篇)" for x in top_p)
        )
    elif chart_type == "pie":
        if "Domain" in img_title or "Discipline" in img_title:
            dist = stats.get("domain_distribution", {})
        elif "JCR" in img_title:
            dist = stats.get("jcr_distribution", {})
        elif "CAS" in img_title:
            dist = stats.get("cas_distribution", {})
        elif "Country" in img_title:
            dist = stats.get("country_distribution", {})
        else:
            dist = {}
        top5 = list(dist.items())[:5]
        data_snippet = "分布 Top5: " + ", ".join(f"{k}({v}篇)" for k, v in top5)
    elif chart_type == "heatmap":
        data_snippet = "热力图展示了期刊/出版社与学科的交叉发文情况。"

    prompt = f"""你是一位有趣又严谨的学术科普博主，正在为小红书写一篇学术日报笔记。

今日数据概况:
- 日期: {date_str}
- 今日全球新发论文总数: {total} 篇
- 当前图表: {img_title}（类型: {tmpl['scene']}）
- 数据摘要: {data_snippet}

请为这张图写一段小红书文案，要求:
1. 【风格】不要死板说教，要有趣但不失严谨，语气像在和朋友分享有趣发现
2. 【角度】不要以教学者姿态，而是以"我也在研究这个，来一起看看"的讨论口吻
3. 【结构】
   - 标题（20字以内，带emoji，抓眼球）
   - 正文（200-350字，段落间留空行，适当加emoji，不堆砌数据，讲出有趣洞察）
   - 一个互动问题（真诚提问，引导用户留言，参考方向: {tmpl['question_hint']}）
   - 话题标签（5-8个，#学术 #论文 #科研 相关）
4. 【关注点】重点聚焦 {tmpl['focus']}
5. 【语调】{tmpl['tone']}

请直接输出文案内容，格式如下:
【标题】...
【正文】...
【互动问题】...
【标签】...
"""
    return prompt


def generate_copywriting_rules(img_info: dict, stats: dict) -> dict:
    """
    规则型文案生成（兜底方案，Agent 优先接管此逻辑）。
    返回结构化文案 dict。
    """
    chart_type = img_info.get("type", "")
    img_title = img_info.get("title", "")
    date_str = stats.get("date", datetime.now().strftime("%Y-%m-%d"))
    total = stats.get("total_articles", 0)

    # ── 标题模板
    title_map = {
        "bar_horizontal": "\U0001f4ca 今天哪本期刊最卷？" + date_str + "全球发文榜单出炉",
        "bar":            "\U0001f3ed 谁是今日出版界发文大户？数据说话！",
        "pie":            "\U0001f967 今日论文大摸底——学科/分区分布一图看懂",
        "heatmap":        "\U0001f525 学科x期刊热力图：哪个组合最烫手？",
    }
    title = title_map.get(chart_type, "\U0001f4da 今日全球学术速报 | " + date_str)

    # ── 正文核心数据提取
    top_journals = stats.get("top_journals", [])[:3]
    top_publishers = stats.get("top_publishers", [])[:3]
    domain_dist = stats.get("domain_distribution", {})
    top_domain = list(domain_dist.items())[:3]
    jcr_dist = stats.get("jcr_distribution", {})
    cas_dist = stats.get("cas_distribution", {})

    if chart_type == "bar_horizontal":
        body = (
            f"今天 CrossRef 收录了 **{total}** 篇新文章，\n"
            f"我顺手跑了一下各期刊的发文量，结果有点出乎意料👀\n\n"
            f"发文量 Top3：\n" +
            "\n".join(f"🥇/{chr(0x1F948+i)} {j['name']}（{j['count']} 篇）" for i, j in enumerate(top_journals)) +
            f"\n\n你会发现，头部期刊的发文节奏非常稳定，\n"
            f"但排行里也混入了一些"非典型"选手——\n"
            f"你猜猜哪家期刊今天最让人意外？👇"
        )
        question = "你平时关注的领域，主要发在哪本期刊？感觉今天榜单符合你的预期吗？"

    elif chart_type == "bar":
        body = (
            f"说起出版社，大家脑海里可能先想到几个老牌巨头，\n"
            f"但今天的数据打了我一个小小的问号🤔\n\n"
            f"今日出版社发文 Top3：\n" +
            "\n".join(f"  {j['name']}：{j['count']} 篇" for j in top_publishers) +
            f"\n\n头部集中度挺高的，这背后折射出学术出版的马太效应。\n"
            f"不过细看你会发现，一些小出版社也在某些细分领域悄悄发力。"
        )
        question = "投稿时你会把出版社名气作为重要参考吗？还是期刊分区优先？"

    elif chart_type == "pie":
        if "Country" in img_title:
            country_dist = stats.get("country_distribution", {})
            top_c = list(country_dist.items())[:3]
            body = (
                f"今天我扒了一下 {total} 篇论文的第一作者归属国，\n"
                f"国家分布图出来之后……某些结果让我挺感慨的。\n\n"
                f"Top3 发文国：\n" +
                "\n".join(f"  {c}：{n} 篇" for c, n in top_c) +
                "\n\n学术产出的地理分布，某种程度上也是科研生态的缩影。\n"
                "你觉得这个格局在未来5年会变吗？"
            )
            question = "你所在的国家/机构，在今天的榜单里排第几？你怎么看这个分布？"

        elif "JCR" in img_title:
            q1 = jcr_dist.get("Q1", 0)
            q2 = jcr_dist.get("Q2", 0)
            body = (
                f"JCR 分区是很多人投稿时的重要参考，\n"
                f"今天 {total} 篇里，Q1 占了 {q1} 篇，Q2 占了 {q2} 篇。\n\n"
                f"从比例来看，高区间期刊今天发文不少，\n"
                f"但 Q3/Q4 的绝对数量其实也不容忽视——\n"
                f"毕竟不是每个方向都有那么多 Q1 期刊可选。"
            )
            question = "你平时投稿会把 JCR 分区设为硬性门槛吗？还是看 IF 或者领域口碑？"

        elif "CAS" in img_title:
            body = (
                f"中科院分区在国内科研圈影响力很大，\n"
                f"今天我看了下 {total} 篇文章里各分区的分布……\n\n"
                f"一区二区合计约占多数，但三四区的数量同样庞大。\n"
                f"这不禁让我想：大量三四区论文背后，\n"
                f"有多少是'迫不得已'的选择，又有多少其实是垂直细分领域的精华？"
            )
            question = "你们单位/学校对中科院分区有硬性要求吗？你怎么看这种考核方式？"

        else:
            top3_domain = "、".join(f"{k}({v}篇)" for k, v in top_domain)
            body = (
                f"今天拉了一张学科分布图，\n"
                f"发文量前三的领域是：{top3_domain}。\n\n"
                f"不同学科的节奏差异其实挺明显的，\n"
                f"有的领域几乎每天都在"轰炸"，\n"
                f"有的方向则以月/季度为节奏。\n"
                f"你所在的方向属于哪种？"
            )
            question = "看到自己领域的数量，你是觉得'卷死了'还是'还好还好'？"

    elif chart_type == "heatmap":
        body = (
            f"热力图看起来很花，但仔细盯着看会发现不少门道👀\n\n"
            f"图里每个格子代表某个学科×期刊（或出版社）的交叉发文量，\n"
            f"颜色越深，今天发的越多。\n\n"
            f"有几个"深色格子"特别引人注意——\n"
            f"某些学科和特定期刊之间好像有默契，几乎垄断了该领域的发文。\n"
            f"而另一些组合，颜色浅得几乎消失，是真的冷门，还是被忽略的宝藏？"
        )
        question = "你在热力图里找到自己领域了吗？有没有发现什么意想不到的"深色格子"？"

    else:
        body = (
            f"今天全球一共新发了 {total} 篇期刊论文，\n"
            f"CrossRef 作为全球最大的 DOI 注册机构，收录了相当完整的数据。\n\n"
            f"我跑了个脚本把今天的数据拉下来分析了一圈，\n"
            f"发现了不少有趣的小规律——感兴趣的朋友来一起探讨！"
        )
        question = "你是第一次看这类学术动态数据吗？有什么特别想了解的维度？"

    tags = [
        "#学术", "#论文", "#科研日常", "#文献检索",
        "#CrossRef", "#学术速报", "#期刊投稿", "#今日学术"
    ]
    if "JCR" in img_title:
        tags.append("#JCR分区")
    if "CAS" in img_title:
        tags.append("#中科院分区")
    if "Country" in img_title:
        tags.append("#全球科研")

    return {
        "image_path": img_info.get("path", ""),
        "image_title": img_title,
        "chart_type": chart_type,
        "title": title,
        "body": body,
        "question": question,
        "tags": tags,
        "prompt_for_ai": build_copywriting_prompt(img_info, stats),
    }


def run(manifest_path: str, output_dir: str = None) -> list:
    """
    主入口。
    读取 manifest.json，为每张图生成文案，输出 copywriting.json。
    返回文案列表。
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    stats = manifest.get("stats", {})
    images = manifest.get("images", [])

    if output_dir is None:
        output_dir = os.path.dirname(manifest_path)

    results = []
    for img in images:
        cw = generate_copywriting_rules(img, stats)
        results.append(cw)
        print(f"[CW] {img.get('title', '')} -> 文案生成完成")

    # 保存
    out_path = os.path.join(output_dir, "copywriting.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVE] copywriting.json -> {out_path}")

    # 同时生成可读 markdown
    md_path = os.path.join(output_dir, "copywriting_preview.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# 小红书文案预览 — {stats.get('date', '')}\n\n")
        f.write(f"> 今日总发文量：**{stats.get('total_articles', 0)}** 篇\n\n---\n\n")
        for idx, cw in enumerate(results, 1):
            f.write(f"## {idx}. {cw['image_title']}\n\n")
            f.write(f"**图片路径**: `{cw['image_path']}`\n\n")
            f.write(f"### 标题\n{cw['title']}\n\n")
            f.write(f"### 正文\n{cw['body']}\n\n")
            f.write(f"### 互动问题\n{cw['question']}\n\n")
            f.write(f"### 标签\n{' '.join(cw['tags'])}\n\n")
            f.write("---\n\n")
    print(f"[SAVE] copywriting_preview.md -> {md_path}")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_copywriting.py <manifest.json路径> [输出目录]")
        sys.exit(1)
    manifest_arg = sys.argv[1]
    output_arg = sys.argv[2] if len(sys.argv) > 2 else None
    run(manifest_arg, output_arg)
