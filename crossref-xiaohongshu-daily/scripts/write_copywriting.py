# -*- coding: utf-8 -*-
"""
工具脚本：接收命令行传入的 JSON 字符串，写入指定路径
用途：Agent 生成文案后通过此脚本安全写入，避免 Shell 编码问题
用法：python write_copywriting.py <output_path> <json_file_path>
    其中 json_file_path 是一个包含文案数组的临时 JSON 文件
"""
import sys
import json
import os

def main():
    if len(sys.argv) < 3:
        print("Usage: python write_copywriting.py <output_path> <input_json_path>")
        sys.exit(1)

    output_path = sys.argv[1]
    input_path = sys.argv[2]

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Written {len(data)} items to {output_path}")

if __name__ == '__main__':
    main()
