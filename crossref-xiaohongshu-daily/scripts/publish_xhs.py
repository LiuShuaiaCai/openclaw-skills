# -*- coding: utf-8 -*-
"""
小红书发布脚本（xhs-mcp CLI 直接调用版）
- 读取 copywriting.json
- 逐条调用 xhs-mcp publish CLI 命令发布
- 支持批量发布 / 单条发布 / 仅预览三种模式

用法:
    python publish_xhs.py <copywriting.json路径> [--mode preview|single|batch] [--index 0]

模式说明:
    preview  (默认) 仅打印将要发布的内容
    single   发布指定 index 的一条
    batch    批量发布所有条目（每条间隔30秒）
"""

import json
import os
import re
import subprocess
import sys
import time
import argparse
import unicodedata
from datetime import datetime

# Windows PowerShell/cmd 默认 GBK，emoji 会崩溃
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PUBLISH_INTERVAL = 30

# xhs-mcp 入口路径（Node.js 直接调用，绕过 npx subprocess PATH 问题）
XHS_MCP_PATH = r"E:\node_global\node_modules\xhs-mcp\dist\xhs-mcp.cjs"
NODE_CMD = "node"


def build_payload(cw: dict, manifest_path: str = None) -> dict:
    """将一条 copywriting 转换为发布参数。"""
    title = cw.get("title", "今日学术速报")
    # 标题限20字（含emoji按双字节计）
    width = sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in title)
    if width > 20:
        # 截断到20宽度单位
        truncated = ""
        w = 0
        for c in title:
            cw2 = 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
            if w + cw2 > 20:
                break
            truncated += c
            w += cw2
        title = truncated + "..."

    body = cw.get("body", "")
    question = cw.get("question", "")
    full_text = body
    if question:
        full_text += "\n\n" + question
    # xhs-mcp --content 限制 1000 字符，超长截断
    if len(full_text) > 1000:
        full_text = full_text[:997] + "..."

    raw_tags = cw.get("tags", [])
    topics = ",".join([t.lstrip('#') for t in raw_tags])

    # 图片路径：combined 模式强制用 manifest 所有图，否则用单图
    img_path = cw.get("image_path", "")
    if manifest_path and not img_path:
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            imgs = m.get("images", [])
            paths = [img["path"] for img in imgs if img.get("path")]
            if len(paths) > 1:
                img_path = ",".join(paths)
            elif paths:
                img_path = paths[0]
        except Exception:
            pass

    return {
        "title": title,
        "content": full_text,
        "media": img_path,
        "tags": topics,
    }


def preview_entry(payload: dict, idx: int):
    sep = "─" * 50
    print(f"\n{sep}")
    print(f"  第 {idx + 1} 条预览")
    print(sep)
    print(f"  标题   : {payload['title']}")
    print(f"  图片   : {payload['media']}")
    print(f"  标签   : {payload['tags']}")
    print(f"  正文预览 (前200字):\n")
    safe_body = payload['content'][:200].replace('\n', '\n  ')
    print(f"  {safe_body}")
    print()


def check_login_and_relogin() -> bool:
    """检查登录状态，未登录则自动打开浏览器扫码。返回 True 表示已登录或登录成功。"""
    print("  检查登录状态...")
    try:
        r = subprocess.run(
            [NODE_CMD, XHS_MCP_PATH, "status"],
            capture_output=True, timeout=30,
        )
        raw = r.stdout.decode("utf-8", errors="replace").strip()
        data = json.loads(raw)
        if data.get("loggedIn"):
            print("  已登录，开始发布")
            return True
        print("  未登录（Cookie 过期），自动打开浏览器扫码...")
    except Exception as ex:
        print(f"  状态检查失败: {ex}，尝试直接登录")

    # 未登录 → 自动弹出浏览器扫码
    print("  请在弹出的浏览器中用小红书 App 扫码登录（120秒内）...")
    try:
        r = subprocess.run(
            [NODE_CMD, XHS_MCP_PATH, "login", "--timeout", "120"],
            capture_output=True, timeout=150,
        )
        raw = r.stdout.decode("utf-8", errors="replace").strip()
        data = json.loads(raw)
        if data.get("loggedIn"):
            print("  扫码登录成功！")
            return True
        print(f"  登录失败: {data.get('message', raw[:100])}")
        return False
    except subprocess.TimeoutExpired:
        print("  登录超时（150秒）")
        return False
    except Exception as ex:
        print(f"  登录异常: {ex}")
        return False


def call_publish_cli(payload: dict, retry: int = 3) -> bool:
    """
    调用 xhs-mcp publish CLI 命令发布一条内容。
    自动重试最多 retry 次（针对网络超时和元素未加载错误）。
    返回 True 表示成功，False 表示失败。
    """
    args = [
        NODE_CMD, XHS_MCP_PATH, "publish",
        "--type", "image",
        "--title", payload["title"],
        "--content", payload["content"],
        "--media", payload["media"],
        "--tags", payload["tags"],
    ]

    for attempt in range(1, retry + 1):
        wait = 10 * attempt
        print(f"  尝试 {attempt}/{retry}，等待 {wait}s...")
        time.sleep(wait)
        print(f"  执行: node ... publish ...")
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                timeout=180,
            )
            rc = result.returncode
            try:
                raw = result.stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                raw = result.stderr.decode("utf-8", errors="replace").strip()

            if rc == 0:
                try:
                    data = json.loads(raw)
                    if data.get("success"):
                        print(f"  返回: success=True")
                        return True
                    msg = data.get("message", "")
                    print(f"  返回: {msg[:200]}")
                    if "title" in msg.lower() or "net::" in msg.lower() or "upload" in msg.lower():
                        continue  # 重试
                    return False
                except json.JSONDecodeError:
                    if "error" not in raw.lower():
                        return True
                    print(f"  解析失败，继续: {raw[:100]}")
                    continue
            else:
                print(f"  exitcode={rc}")
                continue
        except subprocess.TimeoutExpired:
            print("  超时（180秒）")
            continue
        except Exception as e:
            print(f"  异常: {e}")
            continue

    print("  [FAIL] 全部尝试失败")
    return False


def run(copywriting_path: str, mode: str = "preview", index: int = 0,
         manifest_path: str = None) -> list:
    """主入口。"""
    with open(copywriting_path, 'r', encoding='utf-8') as f:
        cw_list = json.load(f)

    if not cw_list:
        print("[WARN] copywriting.json 为空，无内容可发布。")
        return []

    # 推断 manifest_path（如果未指定）
    if manifest_path is None:
        date_dir = os.path.dirname(copywriting_path)
        candidate = os.path.join(date_dir, "manifest.json")
        if os.path.exists(candidate):
            manifest_path = candidate

    # combined 模式：只发布第1条，但自动合并所有图
    is_combined = (mode == "combined")
    first = cw_list[0] if cw_list else None
    if is_combined:
        payloads = [build_payload(cw_list[0], manifest_path)]
        # 优先使用 copywriting_combined.json 中的 selected_images
        if first and first.get("selected_images"):
            payloads[0]["media"] = ",".join(first["selected_images"])
            print(f"  [COMBINED] 使用 selected_images，共 {len(first['selected_images'])} 张图")
    else:
        payloads = [build_payload(cw, manifest_path) for cw in cw_list]

    if mode == "preview":
        print(f"\n[PREVIEW] 共 {len(payloads)} 条待发布内容：")
        for i, p in enumerate(payloads):
            preview_entry(p, i)
        print("[PREVIEW] 预览结束。使用 --mode batch 正式发布。")
        return payloads

    if mode == "combined":
        if not check_login_and_relogin():
            print("[FAIL] 登录失败，终止发布")
            return []
        p = payloads[0]
        # 如果 copywriting_combined.json 中有 selected_images，优先使用
        if first and first.get("selected_images"):
            p["media"] = ",".join(first["selected_images"])
            print(f"  [COMBINED] 使用 selected_images，共 {len(first['selected_images'])} 张图")
        elif manifest_path:
            # 否则从 manifest 读取
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    m = json.load(f)
                all_paths = [img["path"] for img in m.get("images", []) if img.get("path")]
                if len(all_paths) > 1:
                    p["media"] = ",".join(all_paths)
                    print(f"  [COMBINED] 已合并 {len(all_paths)} 张图")
            except Exception as ex:
                print(f"  [WARN] 读取manifest失败: {ex}")
        print(f"\n[COMBINED] 整合发布：{len(p['media'].split(',')) if p['media'] else 0}张图合并到1篇笔记")
        preview_entry(p, 0)
        success = call_publish_cli(p)
        print(f"[{'OK' if success else 'FAIL'}] {'发布成功' if success else '发布失败'}")
        return payloads if success else []

    if mode == "single":
        if not check_login_and_relogin():
            print("[FAIL] 登录失败，终止发布")
            return []
        if index >= len(payloads):
            print(f"[ERROR] index={index} 超出范围（共 {len(payloads)} 条）")
            return []
        target = payloads[index]
        print(f"\n[SINGLE] 准备发布第 {index + 1} 条")
        preview_entry(target, index)
        success = call_publish_cli(target)
        print(f"[{'OK' if success else 'FAIL'}] 第 {index + 1} 条 {'发布成功' if success else '发布失败'}")
        return [target] if success else []

    if mode == "batch":
        if not check_login_and_relogin():
            print("[FAIL] 登录失败，终止发布")
            return []
        print(f"\n[BATCH] 开始批量发布，共 {len(payloads)} 条")
        print(f"        每条间隔 {PUBLISH_INTERVAL} 秒...")
        results = []
        for i, p in enumerate(payloads):
            print(f"\n{'='*60}")
            print(f"  发布第 {i + 1}/{len(payloads)} 条")
            print(f"{'='*60}")
            preview_entry(p, i)
            success = call_publish_cli(p)
            print(f"[{'OK' if success else 'FAIL'}] 第 {i + 1} 条 {'发布成功' if success else '发布失败'}")
            results.append(success)
            if i < len(payloads) - 1:
                print(f"\n  等待 {PUBLISH_INTERVAL} 秒...")
                time.sleep(PUBLISH_INTERVAL)

        ok_count = sum(results)
        print(f"\n{'='*60}")
        print(f"  批量发布完成：{ok_count}/{len(payloads)} 成功")
        print(f"{'='*60}")
        return payloads

    print(f"[ERROR] 未知模式: {mode}")
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小红书发布脚本")
    parser.add_argument("copywriting_json", help="copywriting.json 路径")
    parser.add_argument("--mode", choices=["preview", "single", "batch", "combined"],
                        default="preview", help="发布模式（默认 preview）\n"
                        "  preview  - 仅预览\n"
                        "  single   - 发布指定index的一条\n"
                        "  batch    - 批量发布所有条\n"
                        "  combined - 整合模式：8张图合并到1篇发布（每日模式）")
    parser.add_argument("--index", type=int, default=0,
                        help="single 模式下发布第几条（0起）")
    parser.add_argument("--manifest", default=None,
                        help="manifest.json 路径（用于 combined 模式读取所有图片）")
    args = parser.parse_args()
    run(args.copywriting_json, args.mode, args.index, args.manifest)
