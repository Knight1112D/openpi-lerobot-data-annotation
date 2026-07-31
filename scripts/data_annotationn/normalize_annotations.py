#!/usr/bin/env python3
"""把旧标注 JSON 转换为标准、可长期保存的唯一键格式。"""

from __future__ import annotations

import argparse
from pathlib import Path

from annotation_io import read_annotation_bundle, write_annotation_bundle


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="规范化标注 JSON，合并重复 segments 键并输出标准格式"
    )
    parser.add_argument("--input", type=Path, required=True, help="旧标注 JSON 文件")
    parser.add_argument("--output", type=Path, required=True, help="标准化后的 JSON 文件")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已有输出文件")
    return parser.parse_args()


def main() -> None:
    """读取旧文件并写出只有唯一 JSON 键的标准文件。"""
    args = parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"输出文件已存在：{args.output}，如需覆盖请显式传 --overwrite")
    bundle = read_annotation_bundle(args.input)
    episodes = bundle.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("标注文件必须包含非空 episodes 列表")
    write_annotation_bundle(args.output, bundle)
    segment_counts = sorted({len(item.get("segments", [])) for item in episodes})
    print(f"已规范化：{args.output}，episodes={len(episodes)}，segment_counts={segment_counts}")


if __name__ == "__main__":
    main()
