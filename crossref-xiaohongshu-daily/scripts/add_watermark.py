"""
图片美术字水印叠加脚本
- 读取 copywriting.json，提取每张图片对应文案的关键要点
- 用 PIL 以美术字体将关键词渲染到图片上的合适位置
- 自动避开主体内容区域，优先选择边角/顶底空白区
- 输出带水印的图片到 watermarked/ 子目录

用法:
    python add_watermark.py <copywriting.json路径> [输出目录]
    e.g.: python add_watermark.py charts/2026-04-19/copywriting.json charts/2026-04-19

依赖:
    pip install pillow
"""

import json
import os
import sys
import re
import platform
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    print("[ERROR] 请先安装 Pillow: pip install pillow")
    PIL_AVAILABLE = False

# ──────────────────────────────────────────────
# 字体路径配置（跨平台）
# ──────────────────────────────────────────────

def get_font_paths() -> dict:
    """返回可用的字体路径字典，按优先级排列。"""
    system = platform.system()

    if system == 'Windows':
        win_fonts = r"C:\Windows\Fonts"
        return {
            "title": [
                os.path.join(win_fonts, "STXINGKA.TTF"),   # 华文行楷
                os.path.join(win_fonts, "STCAIYUN.TTF"),   # 华文彩云
                os.path.join(win_fonts, "STHUPO.TTF"),     # 华文琥珀
                os.path.join(win_fonts, "FZYTK.TTF"),      # 方正姚体
                os.path.join(win_fonts, "msyhbd.ttc"),     # 微软雅黑 Bold
                os.path.join(win_fonts, "msyh.ttc"),       # 微软雅黑
            ],
            "sub": [
                os.path.join(win_fonts, "msyhbd.ttc"),
                os.path.join(win_fonts, "msyh.ttc"),
                os.path.join(win_fonts, "simsun.ttc"),
            ],
        }
    elif system == 'Darwin':  # macOS
        return {
            "title": [
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Bold.ttf",
            ],
            "sub": [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
            ],
        }
    else:  # Linux
        return {
            "title": [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            ],
            "sub": [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ],
        }


def load_font(font_paths: list, size: int) -> "ImageFont.FreeTypeFont":
    """依次尝试字体列表，返回第一个可用的字体。"""
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # 兜底使用 PIL 默认字体
    return ImageFont.load_default()


# ──────────────────────────────────────────────
# 关键词提取
# ──────────────────────────────────────────────

def extract_keywords(copywriting: dict) -> list:
    """
    从文案中提取 1-2 个最关键的短语作为水印文字。
    优先从标题提取（去掉 emoji），截取核心词组。
    """
    title = copywriting.get("title", "")
    chart_type = copywriting.get("chart_type", "")
    stats_date = copywriting.get("image_title", "")

    # 去掉 emoji 和特殊符号
    clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\-\|&]', '', title).strip()

    keywords = []

    # 主关键词：根据图表类型定制
    type_keywords = {
        "bar_horizontal": "期刊发文榜",
        "bar":            "出版社发文榜",
        "pie":            _pick_pie_keyword(stats_date),
        "heatmap":        "学科×期刊热力图",
    }
    primary = type_keywords.get(chart_type, "学术速报")
    keywords.append(primary)

    # 次要关键词：日期标记
    date_str = datetime.now().strftime("%m/%d")
    keywords.append(f"📅 {date_str}")

    return keywords


def _pick_pie_keyword(img_title: str) -> str:
    if "Country" in img_title:
        return "全球发文国分布"
    elif "JCR" in img_title:
        return "JCR分区分布"
    elif "CAS" in img_title:
        return "中科院分区分布"
    elif "Discipline" in img_title or "Domain" in img_title:
        return "学科分布"
    return "分布占比"


# ──────────────────────────────────────────────
# 位置智能选择
# ──────────────────────────────────────────────

POSITION_PRESETS = {
    # name: (x_ratio, y_ratio, anchor_x, anchor_y)
    # anchor: 'l'=left, 'c'=center, 'r'=right (x); 't'=top, 'm'=middle, 'b'=bottom (y)
    "top_left":     (0.02, 0.02, 'l', 't'),
    "top_right":    (0.98, 0.02, 'r', 't'),
    "bottom_left":  (0.02, 0.96, 'l', 'b'),
    "bottom_right": (0.98, 0.96, 'r', 'b'),
    "top_center":   (0.50, 0.01, 'c', 't'),
    "bottom_center":(0.50, 0.97, 'c', 'b'),
}

CHART_POSITION_MAP = {
    "bar_horizontal": "top_right",      # 水平柱状图右侧通常有空白
    "bar":            "top_right",
    "pie":            "bottom_center",  # 饼图底部图例下方
    "heatmap":        "top_left",       # 热力图左上角通常有空白
}


def compute_position(img_w: int, img_h: int, text_w: int, text_h: int,
                     preset_name: str, margin: int = 18) -> tuple:
    """根据预设位置名计算实际像素坐标（左上角起点）。"""
    xr, yr, ax, ay = POSITION_PRESETS.get(preset_name, POSITION_PRESETS["bottom_right"])
    cx = int(img_w * xr)
    cy = int(img_h * yr)

    if ax == 'l':
        x = cx + margin
    elif ax == 'r':
        x = cx - text_w - margin
    else:
        x = cx - text_w // 2

    if ay == 't':
        y = cy + margin
    elif ay == 'b':
        y = cy - text_h - margin
    else:
        y = cy - text_h // 2

    # 边界保护
    x = max(margin, min(x, img_w - text_w - margin))
    y = max(margin, min(y, img_h - text_h - margin))
    return x, y


# ──────────────────────────────────────────────
# 水印渲染核心
# ──────────────────────────────────────────────

def render_watermark(img: "Image.Image", keywords: list,
                     chart_type: str, font_paths: dict) -> "Image.Image":
    """
    在图片上渲染美术字水印。
    - 主关键词：大字、渐变描边效果
    - 次要关键词（日期）：小字、半透明胶囊背景
    """
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    W, H = img.size
    preset = CHART_POSITION_MAP.get(chart_type, "bottom_right")

    # ── 主关键词（大字美术体）
    if keywords:
        primary_text = keywords[0]
        font_size = max(28, int(H * 0.045))  # 图高 4.5%
        font = load_font(font_paths["title"], font_size)

        # 计算文字尺寸
        bbox = draw.textbbox((0, 0), primary_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        x, y = compute_position(W, H, tw, th, preset, margin=20)

        # 绘制半透明圆角矩形背景（胶囊标签）
        pad_x, pad_y = 16, 10
        rect = [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y]
        _draw_rounded_rect(draw, rect, radius=12,
                           fill=(15, 20, 40, 200))  # 深蓝黑，高不透明度

        # 描边（白色薄边，增加立体感）
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            draw.text((x + dx, y + dy), primary_text, font=font, fill=(255, 255, 255, 180))

        # 主文字（渐变橙色/金色）
        draw.text((x, y), primary_text, font=font,
                  fill=(255, 210, 60, 240))   # 金黄色，醒目

    # ── 次要关键词（小字，右下角固定）
    if len(keywords) > 1:
        sub_text = keywords[1]
        sub_font_size = max(18, int(H * 0.028))
        sub_font = load_font(font_paths["sub"], sub_font_size)

        bbox2 = draw.textbbox((0, 0), sub_text, font=sub_font)
        sw = bbox2[2] - bbox2[0]
        sh = bbox2[3] - bbox2[1]

        # 固定在右下角
        sx = W - sw - 24
        sy = H - sh - 24

        rect2 = [sx - 10, sy - 6, sx + sw + 10, sy + sh + 6]
        _draw_rounded_rect(draw, rect2, radius=8, fill=(255, 255, 255, 160))
        draw.text((sx, sy), sub_text, font=sub_font, fill=(60, 60, 80, 230))

    # 合并图层
    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


def _draw_rounded_rect(draw: "ImageDraw.ImageDraw", rect: list,
                       radius: int, fill: tuple):
    """绘制圆角矩形（PIL 版本兼容实现）。"""
    x0, y0, x1, y1 = rect
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)

    # 主矩形
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)

    # 四个圆角
    draw.ellipse([x0, y0, x0 + 2 * r, y0 + 2 * r], fill=fill)
    draw.ellipse([x1 - 2 * r, y0, x1, y0 + 2 * r], fill=fill)
    draw.ellipse([x0, y1 - 2 * r, x0 + 2 * r, y1], fill=fill)
    draw.ellipse([x1 - 2 * r, y1 - 2 * r, x1, y1], fill=fill)


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────

def run(copywriting_path: str, output_dir: str = None) -> list:
    """
    主入口。
    读取 copywriting.json，为每张图片添加美术字水印。
    返回带水印图片的路径列表（同时更新 copywriting.json 中的 watermarked_path 字段）。
    """
    if not PIL_AVAILABLE:
        print("[ERROR] Pillow 未安装，无法处理图片水印。")
        return []

    with open(copywriting_path, 'r', encoding='utf-8') as f:
        copywriting_list = json.load(f)

    if output_dir is None:
        output_dir = os.path.dirname(copywriting_path)

    wm_dir = os.path.join(output_dir, "watermarked")
    os.makedirs(wm_dir, exist_ok=True)

    font_paths = get_font_paths()
    results = []

    for cw in copywriting_list:
        src_path = cw.get("image_path", "")
        if not src_path or not os.path.exists(src_path):
            print(f"[SKIP] 图片不存在: {src_path}")
            cw["watermarked_path"] = src_path
            results.append(cw)
            continue

        try:
            img = Image.open(src_path)
            keywords = extract_keywords(cw)
            wm_img = render_watermark(img, keywords, cw.get("chart_type", ""), font_paths)

            # 输出路径
            base_name = os.path.splitext(os.path.basename(src_path))[0]
            out_path = os.path.join(wm_dir, base_name + "_wm.png")
            wm_img.save(out_path, "PNG", dpi=(200, 200))
            print(f"[WM] {src_path} -> {out_path}")
            cw["watermarked_path"] = out_path
            results.append(cw)

        except Exception as e:
            print(f"[ERROR] 处理图片失败 {src_path}: {e}")
            cw["watermarked_path"] = src_path
            results.append(cw)

    # 回写 copywriting.json（加入 watermarked_path 字段）
    with open(copywriting_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVE] 已更新 {copywriting_path}（含 watermarked_path）")
    print(f"[DONE] 共处理 {len(results)} 张图片，水印图保存在: {wm_dir}")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python add_watermark.py <copywriting.json路径> [输出目录]")
        sys.exit(1)
    cw_arg = sys.argv[1]
    out_arg = sys.argv[2] if len(sys.argv) > 2 else None
    run(cw_arg, out_arg)
