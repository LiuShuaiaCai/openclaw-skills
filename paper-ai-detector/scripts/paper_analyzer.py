"""
论文 AI 检测脚本
提供命令行接口进行论文分析
"""

import sys
import json
import argparse
from pathlib import Path

def analyze_paper(content: str, analysis_type: str = "full") -> dict:
    """
    分析论文内容

    Args:
        content: 论文文本内容
        analysis_type: 分析类型 (full/quick/ai_detection/innovation/literature/grammar)
    """
    # 基础文本分析
    word_count = len(content.split())
    char_count = len(content)

    result = {
        "meta": {
            "word_count": word_count,
            "char_count": char_count,
            "analysis_type": analysis_type
        }
    }

    if analysis_type in ["full", "quick"]:
        result["structure"] = analyze_structure(content)
        result["quick_summary"] = generate_summary(content)

    if analysis_type in ["full", "ai_detection"]:
        result["ai_detection"] = detect_ai_writing(content)

    if analysis_type in ["full", "innovation"]:
        result["innovation"] = assess_innovation(content)

    return result


def analyze_structure(content: str) -> dict:
    """分析论文结构"""
    sections = {
        "abstract": "摘要",
        "introduction": "引言|背景",
        "method": "方法|实验|材料",
        "result": "结果|实验结果",
        "discussion": "讨论",
        "conclusion": "结论",
        "reference": "参考文献"
    }

    found_sections = {}
    for key, keywords in sections.items():
        for kw in keywords.split("|"):
            if kw.lower() in content.lower():
                found_sections[key] = True
                break

    return {
        "detected_sections": list(found_sections.keys()),
        "completeness_score": len(found_sections) / len(sections)
    }


def detect_ai_writing(text: str) -> dict:
    """
    检测 AI 写作特征
    简化版：基于规则的检测
    """
    ai_indicators = [
        "crucially", "significantly", "remarkably", "exponentially",
        "intrinsically", "fundamentally", "paradigm", "innovative"
    ]

    text_lower = text.lower()
    words = text_lower.split()

    # 计算指示词出现频率
    indicator_count = sum(1 for w in words if any(ind in w for ind in ai_indicators))
    indicator_rate = indicator_count / len(words) * 100 if words else 0

    # 简单评分
    if indicator_rate > 2:
        probability = 70
        risk = "MEDIUM"
    elif indicator_rate > 1:
        probability = 50
        risk = "LOW"
    else:
        probability = 30
        risk = "LOW"

    return {
        "ai_probability": probability,
        "risk_level": risk,
        "indicator_words_found": indicator_count,
        "indicator_rate": round(indicator_rate, 2)
    }


def assess_innovation(text: str) -> dict:
    """
    评估论文创新性
    简化版：基于关键词分析
    """
    innovation_keywords = [
        "novel", "new", "first", "breakthrough", "state-of-the-art",
        "improve", "advance", "extend", "outperform"
    ]

    text_lower = text.lower()
    words = text_lower.split()

    score = sum(1 for w in words if any(ind in w for ind in innovation_keywords))
    normalized_score = min(10, score / max(1, len(words) / 100))

    return {
        "innovation_score": round(normalized_score, 1),
        "level": "高" if normalized_score >= 7 else "中" if normalized_score >= 4 else "低",
        "keywords_found": score
    }


def generate_summary(content: str) -> str:
    """生成简短摘要"""
    sentences = content.split("。")
    if len(sentences) > 0:
        return sentences[0][:200] + "..."
    return content[:200] + "..."


def main():
    parser = argparse.ArgumentParser(description="论文 AI 检测工具")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径或文本")
    parser.add_argument("--type", "-t", default="full",
                        choices=["full", "quick", "ai_detection", "innovation"],
                        help="分析类型")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")

    args = parser.parse_args()

    # 读取输入
    input_path = Path(args.input)
    if input_path.exists():
        content = input_path.read_text(encoding="utf-8")
    else:
        content = args.input

    # 执行分析
    result = analyze_paper(content, args.type)

    # 输出结果
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"结果已保存至: {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
