#!/usr/bin/env python3
"""
CrossRef 当日文章抓取脚本
用法: python fetch_crossref.py --date 2026-04-18 --rows 100 --output result.json
"""

import argparse
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta

def fetch_crossref_works(date: str, rows: int = 100, offset: int = 0, mailto: str = "workbuddy@example.com") -> dict:
    """从 CrossRef API 获取指定日期的文章"""
    base_url = "https://api.crossref.org/works"
    
    params = urllib.parse.urlencode({
        "filter": f"from-pub-date:{date},until-pub-date:{date}",
        "rows": rows,
        "offset": offset,
        "select": "DOI,title,author,published,subject,container-title,publisher,type,created",
        "mailto": mailto
    })
    
    url = f"{base_url}?{params}"
    
    print(f"正在请求: {url[:100]}...")
    
    req = urllib.request.Request(url, headers={"User-Agent": f"Python/3 (mailto:{mailto})"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP 错误: {e.code} - {e.reason}")
        return {"error": str(e), "status": e.code}
    except urllib.error.URLError as e:
        print(f"URL 错误: {e.reason}")
        return {"error": str(e), "status": "url_error"}

def fetch_all_works(date: str, rows: int = 100, mailto: str = "workbuddy@example.com", max_total: int = 1000) -> list:
    """获取指定日期的所有文章（自动分页）"""
    all_items = []
    offset = 0
    
    while offset < max_total:
        result = fetch_crossref_works(date, rows, offset, mailto)
        
        if "error" in result:
            print(f"获取失败: {result['error']}")
            break
        
        items = result.get("message", {}).get("items", [])
        
        if not items:
            break
        
        all_items.extend(items)
        print(f"已获取 {len(all_items)} 条记录...")
        
        if len(items) < rows:
            break
        
        offset += rows
        time.sleep(0.5)  # 避免请求过于频繁
    
    return all_items

def parse_date(date_parts: list) -> str:
    """解析 CrossRef 的 date-parts 格式"""
    if not date_parts or not date_parts[0]:
        return "Unknown"
    parts = date_parts[0]
    return f"{parts[0]}-{parts[1]:02d}-{parts[2]:02d}" if len(parts) >= 3 else "Unknown"

def analyze_articles(articles: list) -> dict:
    """分析文章数据，返回统计信息"""
    stats = {
        "total": len(articles),
        "by_subject": {},
        "by_publisher": {},
        "by_type": {},
        "by_journal": {},
        "top_authors": {},
        "top_affiliations": {}
    }
    
    for article in articles:
        # 学科统计
        subjects = article.get("subject", [])
        for subject in subjects:
            stats["by_subject"][subject] = stats["by_subject"].get(subject, 0) + 1
        
        # 出版商统计
        publisher = article.get("publisher", "Unknown")
        stats["by_publisher"][publisher] = stats["by_publisher"].get(publisher, 0) + 1
        
        # 类型统计
        article_type = article.get("type", "Unknown")
        stats["by_type"][article_type] = stats["by_type"].get(article_type, 0) + 1
        
        # 期刊统计
        journals = article.get("container-title", [])
        for journal in journals:
            stats["by_journal"][journal] = stats["by_journal"].get(journal, 0) + 1
        
        # 作者统计
        for author in article.get("author", []):
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            if name:
                stats["top_authors"][name] = stats["top_authors"].get(name, 0) + 1
            
            # 机构统计
            for aff in author.get("affiliation", []):
                aff_name = aff.get("name", "Unknown")
                stats["top_affiliations"][aff_name] = stats["top_affiliations"].get(aff_name, 0) + 1
    
    # 排序
    stats["by_subject"] = dict(sorted(stats["by_subject"].items(), key=lambda x: x[1], reverse=True)[:20])
    stats["by_publisher"] = dict(sorted(stats["by_publisher"].items(), key=lambda x: x[1], reverse=True)[:10])
    stats["by_type"] = dict(sorted(stats["by_type"].items(), key=lambda x: x[1], reverse=True))
    stats["by_journal"] = dict(sorted(stats["by_journal"].items(), key=lambda x: x[1], reverse=True)[:10])
    stats["top_authors"] = dict(sorted(stats["top_authors"].items(), key=lambda x: x[1], reverse=True)[:10])
    stats["top_affiliations"] = dict(sorted(stats["top_affiliations"].items(), key=lambda x: x[1], reverse=True)[:10])
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="从 CrossRef 抓取指定日期的文章")
    parser.add_argument("--date", type=str, default=None, help="日期 (YYYY-MM-DD)，默认为今天")
    parser.add_argument("--rows", type=int, default=100, help="每页数量 (最大100)")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    parser.add_argument("--mailto", type=str, default="workbuddy@example.com", help="邮箱地址")
    parser.add_argument("--max-total", type=int, default=1000, help="最大获取数量")
    
    args = parser.parse_args()
    
    # 默认使用今天
    if args.date is None:
        args.date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"开始抓取 {args.date} 的学术文章...")
    
    articles = fetch_all_works(args.date, args.rows, args.mailto, args.max_total)
    
    if not articles:
        print("未获取到任何文章")
        return
    
    stats = analyze_articles(articles)
    
    result = {
        "date": args.date,
        "total_fetched": len(articles),
        "statistics": stats,
        "articles": articles[:50]  # 只保留前50篇完整数据
    }
    
    # 输出到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {args.output}")
    else:
        print(f"\n=== {args.date} 学术日报统计 ===")
        print(f"文章总数: {stats['total']}")
        print(f"\n学科分布 (Top 10):")
        for subject, count in list(stats["by_subject"].items())[:10]:
            print(f"  {subject}: {count}")
        print(f"\n出版商 (Top 5):")
        for publisher, count in list(stats["by_publisher"].items())[:5]:
            print(f"  {publisher}: {count}")
        print(f"\n文章类型:")
        for t, count in stats["by_type"].items():
            print(f"  {t}: {count}")

if __name__ == "__main__":
    main()
