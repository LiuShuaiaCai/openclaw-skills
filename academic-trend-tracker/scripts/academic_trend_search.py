#!/usr/bin/env python3
"""
学术热点追踪脚本
从多个数据源搜索学术热点，返回结构化数据
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# CrossRef API 配置
CROSSREF_BASE = "https://api.crossref.org/works"

# arXiv API 配置
ARXIV_BASE = "https://export.arxiv.org/api/query"

def search_crossref(query: str, days: int = 7, rows: int = 100) -> List[Dict]:
    """
    从 CrossRef 搜索近期论文

    Args:
        query: 搜索关键词
        days: 近几天内的论文
        rows: 返回数量

    Returns:
        论文列表
    """
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = datetime.now().strftime("%Y-%m-%d")

    params = {
        "query": query,
        "from-pub-date": from_date,
        "until-pub-date": to_date,
        "rows": rows,
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,author,published,subject,journal-name,publisher"
    }

    try:
        response = requests.get(CROSSREF_BASE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        papers = []
        for item in data.get("message", {}).get("items", []):
            paper = {
                "doi": item.get("DOI", ""),
                "title": " ".join(item.get("title", [])),
                "journal": item.get("journal-name", ""),
                "publisher": item.get("publisher", ""),
                "subjects": item.get("subject", []),
                "published": item.get("published", {}).get("date-parts", [[]])[0]
            }

            # 提取第一作者
            authors = item.get("author", [])
            if authors:
                paper["first_author"] = authors[0].get("family", "")

            papers.append(paper)

        return papers
    except Exception as e:
        print(f"CrossRef API 错误: {e}")
        return []


def search_arxiv(query: str, max_results: int = 50) -> List[Dict]:
    """
    从 arXiv 搜索论文

    Args:
        query: 搜索关键词
        max_results: 最大结果数

    Returns:
        论文列表
    """
    params = {
        "search_query": query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    try:
        response = requests.get(ARXIV_BASE, params=params, timeout=30)
        response.raise_for_status()

        # 解析 XML 响应
        papers = []
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            paper = {
                "arxiv_id": entry.find("atom:id", ns).text.split("/")[-1] if entry.find("atom:id", ns) is not None else "",
                "title": entry.find("atom:title", ns).text.strip() if entry.find("atom:title", ns) is not None else "",
                "summary": entry.find("atom:summary", ns).text.strip() if entry.find("atom:summary", ns) is not None else "",
                "published": entry.find("atom:published", ns).text if entry.find("atom:published", ns) is not None else ""
            }

            # 提取作者
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns)
                if name is not None:
                    authors.append(name.text)
            paper["authors"] = authors

            # 提取分类
            categories = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term")
                if term:
                    categories.append(term)
            paper["categories"] = categories

            papers.append(paper)

        return papers
    except Exception as e:
        print(f"arXiv API 错误: {e}")
        return []


def analyze_trends(papers: List[Dict]) -> Dict:
    """
    分析论文趋势

    Args:
        papers: 论文列表

    Returns:
        趋势分析结果
    """
    if not papers:
        return {"total": 0, "subjects": {}, "journals": {}}

    # 统计学科分布
    subjects_count = {}
    for paper in papers:
        for subject in paper.get("subjects", []):
            subjects_count[subject] = subjects_count.get(subject, 0) + 1

    # 统计期刊分布
    journals_count = {}
    for paper in papers:
        journal = paper.get("journal", "Unknown")
        journals_count[journal] = journals_count.get(journal, 0) + 1

    return {
        "total": len(papers),
        "subjects": dict(sorted(subjects_count.items(), key=lambda x: x[1], reverse=True)),
        "journals": dict(sorted(journals_count.items(), key=lambda x: x[1], reverse=True)[:10])
    }


def generate_report(trends: Dict, papers: List[Dict]) -> str:
    """
    生成分析报告

    Args:
        trends: 趋势分析结果
        papers: 论文列表

    Returns:
        报告文本
    """
    report = []
    report.append(f"# 学术热点分析报告")
    report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"\n## 统计概览")
    report.append(f"- 总论文数: {trends['total']}")
    report.append(f"- 涉及期刊: {len(trends['journals'])}")

    report.append(f"\n## 热门学科 Top 10")
    for i, (subject, count) in enumerate(trends["subjects"].items(), 1):
        report.append(f"{i}. {subject}: {count}篇")

    report.append(f"\n## 热门期刊 Top 10")
    for i, (journal, count) in enumerate(trends["journals"].items(), 1):
        report.append(f"{i}. {journal}: {count}篇")

    if papers:
        report.append(f"\n## 最新论文推荐")
        for i, paper in enumerate(papers[:5], 1):
            title = paper.get("title", "N/A")[:80]
            report.append(f"\n{i}. {title}...")
            if paper.get("doi"):
                report.append(f"   DOI: {paper['doi']}")
            if paper.get("arxiv_id"):
                report.append(f"   arXiv: {paper['arxiv_id']}")

    return "\n".join(report)


def main():
    """主函数"""
    print("🔍 学术热点追踪分析")
    print("=" * 50)

    # 示例：搜索 AI+医学 相关论文
    query = "AI medicine"
    days = 7

    print(f"\n📊 搜索关键词: {query}")
    print(f"📅 时间范围: 近{days}天")

    # 从 CrossRef 搜索
    print("\n🌐 从 CrossRef 获取数据...")
    crossref_papers = search_crossref(query, days=days, rows=100)
    print(f"✅ 获取到 {len(crossref_papers)} 篇论文")

    # 从 arXiv 搜索
    print("\n🌐 从 arXiv 获取数据...")
    arxiv_papers = search_arxiv(query, max_results=50)
    print(f"✅ 获取到 {len(arxiv_papers)} 篇论文")

    # 合并并分析
    all_papers = crossref_papers + arxiv_papers
    trends = analyze_trends(all_papers)

    # 生成报告
    report = generate_report(trends, all_papers)
    print("\n" + report)

    # 保存结果
    output_file = f"academic_trend_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "trends": trends,
            "papers": all_papers[:20]  # 只保存前20篇
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
