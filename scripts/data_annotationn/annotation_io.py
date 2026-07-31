#!/usr/bin/env python3
"""提供标注 JSON 的统一读写，兼容旧文件中的重复 ``segments`` 键。"""

from __future__ import annotations

import json
from pathlib import Path


def merge_duplicate_segment_keys(pairs: list[tuple[str, object]]) -> dict:
    """按出现顺序合并同一对象里的重复 ``segments`` 数组。"""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key == "segments" and key in result:
            previous = result[key]
            if not isinstance(previous, list) or not isinstance(value, list):
                raise ValueError("重复的 segments 键必须都对应 JSON 数组")
            previous.extend(value)
        else:
            result[key] = value
    return result


def read_annotation_bundle(path: Path) -> dict:
    """读取标注 bundle，并在内存中恢复旧文件丢失的 segment。"""
    bundle = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=merge_duplicate_segment_keys,
    )
    if not isinstance(bundle, dict):
        raise ValueError("标注文件根节点必须是 JSON 对象")
    return bundle


def write_annotation_bundle(path: Path, bundle: dict) -> None:
    """以标准 JSON 写出标注 bundle，保证每个 episode 只有一个 segments 数组。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
