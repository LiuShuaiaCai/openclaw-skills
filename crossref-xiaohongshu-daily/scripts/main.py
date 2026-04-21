"""
CrossRef 每日学术数据抓取与可视化脚本
- 从 CrossRef API 抓取当天发布的期刊文章
- 从本地数据库补充期刊 JCR/CAS 分区信息（支持 SQLite 或 MySQL）
- 生成多维度可视化图表，保存到 charts/{date}/ 目录
- 每天随机选择 3 种图表类型，保证新鲜感
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib import rcParams
import platform
import numpy as np
import seaborn as sns
import os
import json
import sys
import random
import sqlite3

# ──────────────────────────────────────────────
# 字体配置（跨平台）
# ──────────────────────────────────────────────
if platform.system() == 'Windows':
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
elif platform.system() == 'Darwin':
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'DejaVu Sans']
else:
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'DejaVu Sans']

rcParams['axes.unicode_minus'] = False

# ──────────────────────────────────────────────
# 数据库配置（SQLite / MySQL 双模式）
# ──────────────────────────────────────────────
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")  # "sqlite" 或 "mysql"
# 向上走一层目录，从 scripts/ 定位到 skill 根目录
SKILL_ROOT = os.path.dirname(os.path.dirname(__file__))
SQLITE_PATH = os.path.join(SKILL_ROOT, "data", "crossref_data.db")

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "express",
    "charset": "utf8mb4"
}

def get_db_connection():
    """获取数据库连接，支持 SQLite 和 MySQL"""
    if DB_TYPE == "mysql":
        try:
            import pymysql
            conn = pymysql.connect(**MYSQL_CONFIG)
            return conn
        except Exception as e:
            print(f"[WARN] MySQL 连接失败: {e}")
            return None
    else:
        # SQLite 模式
        if not os.path.exists(SQLITE_PATH):
            print(f"[WARN] SQLite 数据库不存在: {SQLITE_PATH}")
            return None
        try:
            conn = sqlite3.connect(SQLITE_PATH)
            return conn
        except Exception as e:
            print(f"[WARN] SQLite 连接失败: {e}")
            return None

# ──────────────────────────────────────────────
# 内置国家列表（SQLite 不可用时的备选）
# ──────────────────────────────────────────────
BUILTIN_COUNTRIES = [
    "China", "United States", "United Kingdom", "Germany", "France",
    "Japan", "South Korea", "India", "Brazil", "Canada", "Australia",
    "Italy", "Spain", "Netherlands", "Switzerland", "Sweden", "Poland",
    "Iran", "Turkey", "Russia", "Mexico", "Taiwan", "Singapore",
    "Hong Kong", "Belgium", "Denmark", "Austria", " Norway",
    "Finland", "Ireland", "Israel", "New Zealand", "Czech Republic",
    "Portugal", "Greece", "Hungary", "Argentina", "Chile", "Colombia",
    "Egypt", "Saudi Arabia", "Thailand", "Vietnam", "Malaysia", "Indonesia",
    "Pakistan", "Bangladesh", "Nigeria", "South Africa", "Morocco"
]

# ──────────────────────────────────────────────
# CrossRef API 抓取
# ──────────────────────────────────────────────
ROWS_PER_PAGE = 1000

def fetch_crossref_articles(from_date: str, to_date: str) -> list:
    """
    从 CrossRef 抓取指定日期范围内发布的期刊文章。
    返回原始 items 列表。
    """
    all_items = []
    cursor = "*"

    while True:
        url = (
            f"https://api.crossref.org/works?"
            f"filter=from-pub-date:{from_date},until-pub-date:{to_date},type:journal-article"
            f"&rows={ROWS_PER_PAGE}&cursor={cursor}"
            f"&select=title,DOI,published-online,publisher,type,ISSN,URL,"
            f"container-title,short-container-title,author"
            f"&mailto=your_email@example.com"
        )
        print(f"[FETCH] {url[:120]}...")
        try:
            resp = requests.get(url, timeout=30)
        except requests.RequestException as e:
            print(f"[ERROR] 请求异常: {e}")
            break

        if resp.status_code != 200:
            print(f"[ERROR] HTTP {resp.status_code}")
            break

        data = resp.json().get("message", {})
        items = data.get("items", [])
        if not items:
            break

        all_items.extend(items)
        print(f"[FETCH] 已抓取 {len(all_items)} 条")
        cursor = data.get("next-cursor", None)
        if not cursor:
            break

        time.sleep(0.2)

    return all_items


# ──────────────────────────────────────────────
# 数据处理
# ──────────────────────────────────────────────
def process_articles(items: list) -> pd.DataFrame:
    rows = []
    for item in items:
        title = (item.get("title") or [""])[0]
        journal = (item.get("container-title") or [""])[0]
        journal_short = (item.get("short-container-title") or [""])[0]
        doi = item.get("DOI", "")
        publisher = item.get("publisher", "")
        url = item.get("URL", "")
        issn = (item.get("ISSN") or [""])[0]
        article_type = item.get("type", "")

        pub_date = ""
        pub_online = item.get("published-online", {}).get("date-parts", [])
        if pub_online and len(pub_online[0]) >= 3:
            y, m, d = pub_online[0][0], pub_online[0][1], pub_online[0][2]
            pub_date = f"{y}-{m:02d}-{d:02d}"

        rows.append({
            "title": title,
            "journal": journal,
            "journal_short": journal_short,
            "doi": doi,
            "publisher": publisher,
            "url": url,
            "issn": issn,
            "published_date": pub_date,
            "type": article_type,
            "author": item.get("author", []),
        })
    return pd.DataFrame(rows)


def extract_countries_fuzzy(df: pd.DataFrame) -> pd.Series:
    """从作者归属中模糊匹配国家名，文章级去重后汇总。"""
    conn = get_db_connection()
    if conn is None:
        # 使用内置列表
        countries = BUILTIN_COUNTRIES
    else:
        try:
            if DB_TYPE == "mysql":
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM countries")
                countries = [row[0] for row in cursor.fetchall()]
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM countries")
                countries = [row[0] for row in cursor.fetchall()]
                cursor.close()
            conn.close()
        except Exception as e:
            print(f"[WARN] 无法读取 countries 表: {e}")
            countries = BUILTIN_COUNTRIES

    country_set = {c.lower().strip() for c in countries}
    country_list = []

    for _, row in df.iterrows():
        authors = row.get("author") or []
        if not isinstance(authors, list):
            continue
        matched = set()
        for author in authors:
            for aff in author.get("affiliation", []):
                for place in aff.get("place", []):
                    for c in country_set:
                        if c in place.lower():
                            matched.add(c.title())
                            break
                name_lower = aff.get("name", "").lower()
                for c in country_set:
                    if c in name_lower:
                        matched.add(c.title())
                        break
        country_list.extend(list(matched))

    return pd.Series(country_list)


def add_journal_info(df: pd.DataFrame, batch_size: int = 500) -> pd.DataFrame:
    """从数据库补充期刊 JCR/CAS 分区信息；数据库不可用时原样返回。"""
    conn = get_db_connection()
    if conn is None:
        df['jcr_section'] = None
        df['cas_section'] = None
        df['domain_class'] = None
        df['second_domain_class'] = None
        return df

    issns = df['issn'].dropna().unique().tolist()
    if not issns:
        conn.close()
        return df

    chunks = [issns[i:i + batch_size] for i in range(0, len(issns), batch_size)]
    journal_info = pd.DataFrame()

    try:
        for chunk in chunks:
            placeholders = ','.join(['?'] * len(chunk))  # SQLite 占位符
            query = f"""
                SELECT issn, jcr_section, cas_section, domain_class, second_domain_class
                FROM journals
                WHERE issn IN ({placeholders})
            """
            if DB_TYPE == "mysql":
                # MySQL 用 %s 占位符
                placeholders = ','.join(['%s'] * len(chunk))
                query = f"""
                    SELECT issn, jcr_section, cas_section, domain_class, second_domain_class
                    FROM journals
                    WHERE issn IN ({placeholders})
                """
                part = pd.read_sql(query, conn, params=tuple(chunk))
            else:
                part = pd.read_sql(query, conn, params=tuple(chunk))
            journal_info = pd.concat([journal_info, part], ignore_index=True)
    except Exception as e:
        print(f"[WARN] 期刊查询异常: {e}")
    finally:
        conn.close()

    if not journal_info.empty:
        df = df.merge(journal_info, how='left', on='issn')
    else:
        df['jcr_section'] = None
        df['cas_section'] = None
        df['domain_class'] = None
        df['second_domain_class'] = None

    return df


# ──────────────────────────────────────────────
# 图表保存工具
# ──────────────────────────────────────────────
def save_chart(fig, title: str, save_dir: str = "charts", dpi: int = 200) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    dir_path = os.path.join(save_dir, today)
    os.makedirs(dir_path, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in (' ', '_') else "_" for c in title)
    file_name = safe_title.replace(' ', '_') + ".png"
    file_path = os.path.join(dir_path, file_name)

    fig.savefig(file_path, dpi=dpi, bbox_inches='tight')
    plt.close('all')
    print(f"[SAVE] {file_path}")
    return file_path


# ──────────────────────────────────────────────
# 可视化函数（每个函数返回保存路径）
# ──────────────────────────────────────────────
def plot_bar_horizontal(series: pd.Series, title: str, xlabel: str, ylabel: str,
                        top_n: int = 10, save_dir: str = "charts") -> str:
    series = series.dropna().astype(str).str.strip()
    series = series[series != ""]
    data = series.value_counts(dropna=True)[:top_n]
    if data.empty:
        return ""

    labels = [l[:22] + "…" if len(l) > 22 else l for l in data.index]
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = sns.color_palette("tab20", len(data))
    sns.barplot(x=data.values, y=labels, hue=labels, palette=colors, ax=ax, legend=False)

    ax.set_title(title, fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)

    for i, v in enumerate(data.values):
        ax.text(v + max(data.values) * 0.01, i, str(v), color='black', va='center', fontsize=10)

    ax.xaxis.grid(True, linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)
    sns.despine(left=True, bottom=False)
    plt.tight_layout(pad=3)
    return save_chart(plt, title, save_dir)


def plot_bar(data: pd.Series, title: str, xlabel: str, ylabel: str,
             top_n: int = 10, save_dir: str = "charts") -> str:
    cmap = colormaps['viridis']
    colors = cmap(np.linspace(0.3, 0.9, top_n))

    fig, ax = plt.subplots(figsize=(12, 6))
    s = data.sort_values(ascending=False).head(top_n)
    if s.empty:
        return ""

    bars = ax.bar(range(len(s)), s.values, color=colors, edgecolor='grey', linewidth=0.5)
    for i, (idx, v) in enumerate(s.items()):
        ax.text(i, v + max(s) * 0.01, f'{v}', ha='center', va='bottom', fontsize=9, fontweight='semibold')

    short_labels = [n[:20] + '…' if len(n) > 20 else n for n in s.index]
    ax.set_xticks(range(len(s)))
    ax.set_xticklabels(short_labels, rotation=45, ha='right', fontsize=9)
    ax.set_xlabel(xlabel, fontsize=11, labelpad=10)
    ax.set_ylabel(ylabel, fontsize=11, labelpad=10)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(axis='y', alpha=0.3)
    plt.subplots_adjust(bottom=0.25)
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    return save_chart(plt, title, save_dir)


def plot_pie(data: pd.Series, title: str, top_n: int = 10, save_dir: str = "charts") -> str:
    data = data.dropna()
    data = data[data.astype(str).str.strip() != ""]
    counts = data.value_counts()
    if counts.empty:
        return ""

    if len(counts) > top_n:
        top_counts = counts[:top_n].copy()
        top_counts["Other"] = counts[top_n:].sum()
    else:
        top_counts = counts.copy()

    labels = [l[:20] + "…" if len(l) > 20 else l for l in top_counts.index]
    labels_with_count = [f"{n} ({c})" for n, c in zip(labels, top_counts.values)]
    colors = sns.color_palette("tab10", len(top_counts))
    total = top_counts.sum()

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        top_counts,
        labels=labels_with_count,
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        pctdistance=0.8,
        textprops={'fontsize': 10},
        wedgeprops={'linewidth': 1, 'edgecolor': 'white', 'width': 0.5}
    )
    ax.legend(wedges, [l for l in top_counts.index],
              title="Categories", loc="upper center",
              bbox_to_anchor=(0.5, -0.1), fontsize=9,
              title_fontsize=11, frameon=False, ncol=2)
    ax.set_title(f"{title} (n={total})", fontsize=15, fontweight="bold", pad=25)
    plt.tight_layout(pad=3)
    return save_chart(plt, title, save_dir)


def plot_heatmap(df: pd.DataFrame, index_col: str, columns_col: str,
                 xlabel: str, ylabel: str, title: str,
                 top_n: int = 20, save_dir: str = "charts") -> str:
    df = df.dropna(subset=[index_col, columns_col])
    df = df[df[index_col].astype(str).str.strip() != ""]
    df = df[df[columns_col].astype(str).str.strip() != ""]
    pivot = df.groupby([index_col, columns_col]).size().unstack(fill_value=0)
    if pivot.empty:
        return ""

    top_cols = pivot.sum(axis=0).sort_values(ascending=False).head(top_n).index
    top_rows = pivot.sum(axis=1).sort_values(ascending=False).head(top_n * 2).index
    pivot = pivot.loc[top_rows, top_cols]
    pivot.index = [i[:20] + '…' if len(i) > 20 else i for i in pivot.index]
    pivot.columns = [c[:20] + '…' if len(c) > 20 else c for c in pivot.columns]

    plt.figure(figsize=(12, 8))
    sns.set(style="whitegrid")
    sns.heatmap(pivot, annot=True, fmt='d', cmap='YlGnBu',
                linewidths=0.5, linecolor='gray',
                cbar_kws={'label': 'Article Count'})
    plt.title(title, fontsize=16, fontweight='bold')
    plt.ylabel(ylabel, fontsize=12)
    plt.xlabel(xlabel, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout(pad=3)
    return save_chart(plt, title, save_dir)


# ──────────────────────────────────────────────
# 统计摘要（用于文案生成）
# ──────────────────────────────────────────────
def build_stats_summary(df: pd.DataFrame) -> dict:
    """构建统计摘要字典，用于传递给文案生成脚本。"""
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_articles": len(df),
        "top_publishers": [],
        "top_journals": [],
        "domain_distribution": {},
        "jcr_distribution": {},
        "cas_distribution": {},
        "country_distribution": {},
    }

    # 出版社 Top10
    if 'publisher' in df.columns:
        top_pub = df['publisher'].value_counts().head(10)
        summary["top_publishers"] = [{"name": k, "count": int(v)} for k, v in top_pub.items()]

    # 期刊 Top10
    if 'journal_short' in df.columns:
        top_j = df['journal_short'].value_counts().head(10)
        summary["top_journals"] = [{"name": k, "count": int(v)} for k, v in top_j.items()]

    # 学科分布
    if 'domain_class' in df.columns:
        dist = df['domain_class'].value_counts().head(10)
        summary["domain_distribution"] = {k: int(v) for k, v in dist.items() if pd.notna(k) and k != ""}

    # JCR 分区
    if 'jcr_section' in df.columns:
        jcr = df['jcr_section'].value_counts()
        summary["jcr_distribution"] = {k: int(v) for k, v in jcr.items() if pd.notna(k) and k != ""}

    # CAS 分区
    if 'cas_section' in df.columns:
        cas = df['cas_section'].value_counts()
        summary["cas_distribution"] = {k: int(v) for k, v in cas.items() if pd.notna(k) and k != ""}

    return summary


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────
def run(target_date: str = None, save_dir: str = "charts") -> dict:
    """
    主入口。
    target_date: 'YYYY-MM-DD'，默认为昨天
    save_dir: 图表保存根目录
    返回: {"images": [...路径列表], "stats": {...统计摘要}}
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  CrossRef 每日抓取  |  日期: {target_date}")
    print(f"  数据库模式: {DB_TYPE.upper()}")
    print(f"{'='*60}\n")

    # 1. 抓取数据
    items = fetch_crossref_articles(target_date, target_date)
    if not items:
        print("[WARN] 未抓取到任何数据，退出。")
        return {"images": [], "stats": {}}

    # 2. 处理数据
    df = process_articles(items)
    df = add_journal_info(df)
    print(f"\n[INFO] 数据处理完成，共 {len(df)} 条记录\n")

    # 3. 随机选择 3 种图表类型
    images = []

    # 定义可选的图表类型
    available_charts = []

    # 期刊发文榜（横向柱状）
    p = plot_bar_horizontal(
        df[df['jcr_section'].notna()]['journal_short'] if 'jcr_section' in df.columns else df['journal_short'],
        "Top 20 JCR Journals by Article Count", "Article Count", "Journal Name", 20, save_dir
    )
    if p:
        available_charts.append({"path": p, "title": "Top 20 JCR Journals by Article Count", "type": "bar_horizontal"})

    # 出版社发文榜（柱状）
    p = plot_bar(
        df.groupby('publisher').size(),
        "Top 10 Publishers by Article Count", "Publisher Name", "Article Count", 10, save_dir
    )
    if p:
        available_charts.append({"path": p, "title": "Top 10 Publishers by Article Count", "type": "bar"})

    # 学科分布（饼图）
    if 'domain_class' in df.columns:
        p = plot_pie(df['domain_class'], "Discipline Distribution (Domain Class)", 10, save_dir)
        if p:
            available_charts.append({"path": p, "title": "Discipline Distribution", "type": "pie"})

    # JCR 分区（饼图）
    if 'jcr_section' in df.columns:
        p = plot_pie(df['jcr_section'], "JCR Section Distribution", 10, save_dir)
        if p:
            available_charts.append({"path": p, "title": "JCR Section Distribution", "type": "pie"})

    # CAS 分区（饼图）
    if 'cas_section' in df.columns:
        p = plot_pie(df['cas_section'], "CAS Section Distribution", 10, save_dir)
        if p:
            available_charts.append({"path": p, "title": "CAS Section Distribution", "type": "pie"})

    # 期刊×学科热力图
    if 'domain_class' in df.columns:
        p = plot_heatmap(df, 'domain_class', 'journal',
                         'Journal Name', 'Domain Class',
                         'Top 20 Journals by Discipline Heatmap', 20, save_dir)
        if p:
            available_charts.append({"path": p, "title": "Top 20 Journals by Discipline Heatmap", "type": "heatmap"})

    # 出版社×学科热力图
    if 'domain_class' in df.columns:
        p = plot_heatmap(df, 'domain_class', 'publisher',
                         'Publisher Name', 'Domain Class',
                         'Top 20 Publisher by Discipline Heatmap', 20, save_dir)
        if p:
            available_charts.append({"path": p, "title": "Top 20 Publisher by Discipline Heatmap", "type": "heatmap"})

    # 国家分布（饼图）
    country_counts = extract_countries_fuzzy(df)
    if not country_counts.empty:
        p = plot_pie(country_counts, "First-Author Country Distribution", 10, save_dir)
        if p:
            available_charts.append({"path": p, "title": "First-Author Country Distribution", "type": "pie"})

    # 按类型分组
    bar_horizontal_charts = [c for c in available_charts if c["type"] == "bar_horizontal"]
    bar_charts = [c for c in available_charts if c["type"] == "bar"]
    pie_heatmap_charts = [c for c in available_charts if c["type"] in ("pie", "heatmap")]

    # 确保3种不同类型：1个横向柱状 + 1个柱状 + 1个饼图/热力图
    images = []
    if bar_horizontal_charts:
        images.append(random.choice(bar_horizontal_charts))
    if bar_charts:
        images.append(random.choice(bar_charts))
    if pie_heatmap_charts:
        images.append(random.choice(pie_heatmap_charts))

    # 如果某个类型为空，补充其他类型
    if len(images) < 3:
        used_paths = {img["path"] for img in images}
        remaining = [c for c in available_charts if c["path"] not in used_paths]
        while len(images) < 3 and remaining:
            images.append(random.choice(remaining))
            used_paths.add(images[-1]["path"])
            remaining = [c for c in remaining if c["path"] not in used_paths]

    print(f"\n[INFO] 已选择 3 种不同类型图表（共生成 {len(available_charts)} 张）")
    for i, img in enumerate(images, 1):
        print(f"  {i}. {img['title']} [{img['type']}]")

    # 4. 统计摘要（使用全部数据）
    stats = build_stats_summary(df)
    stats["images"] = images

    # 5. 保存 manifest
    today = datetime.now().strftime("%Y-%m-%d")
    manifest_path = os.path.join(save_dir, today, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump({"stats": stats, "images": images}, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVE] manifest -> {manifest_path}")

    print(f"\n[DONE] 随机选取 {len(images)} 张图表")
    return {"images": images, "stats": stats}


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    dir_arg = sys.argv[2] if len(sys.argv) > 2 else "charts"
    result = run(target_date=date_arg, save_dir=dir_arg)
    print("\n随机选择的图片列表:")
    for img in result["images"]:
        print(f"  - {img['path']}  [{img['type']}]")
