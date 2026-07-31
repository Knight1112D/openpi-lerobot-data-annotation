#!/usr/bin/env python3
"""验证稀疏人工标注和已经物化的 LeRobot v2.1 数据集。

Validate sparse human annotations and a materialized LeRobot v2.1 dataset.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from annotation_io import read_annotation_bundle

ENGLISH_TEXT = re.compile(r"^[\x09\x0a\x0d\x20-\x7e]*$")
REQUIRED_MATERIALIZED = {
    "response",
    "memory",
    "episode_success",
    "episode_overall_speed",
    "episode_overall_quality",
    "mistake",
    "is_intervention",
    "intervention_start",
    "intervention_reason",
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数 / Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="验证 LeRobot 标注 bundle / Validate a LeRobot annotation bundle"
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument(
        "--allow-missing", action="store_true", help="允许只验证部分 episode / Allow partial episode coverage"
    )
    parser.add_argument(
        "--check-materialized", action="store_true", help="同时检查逐帧物化字段 / Check materialized frame fields"
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    """读取 JSONL 文件 / Read a JSONL file."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_english(value: object, label: str, allow_empty: bool = False) -> None:
    """检查文本是否为英文 ASCII 文本 / Check that text uses English ASCII characters."""
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串")
    if not allow_empty and not value.strip():
        raise ValueError(f"{label} 不能为空")
    if not ENGLISH_TEXT.fullmatch(value):
        raise ValueError(f"{label} 必须使用英文 ASCII 字符：{value!r}")


def normalize_success(value: object, label: str) -> int:
    """规范化 success / Normalize success to integer 0 or 1.

    The canonical representation is integer 0/1. JSON booleans false/true are
    accepted for convenience and are normalized to 0/1; uppercase TRUE/FALSE
    strings are not valid JSON booleans and are rejected.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise ValueError(f"{label} 必须是整数 0/1 或 JSON 布尔值 false/true / must be 0/1 or false/true")


def normalize_quality(value: object, label: str) -> int:
    """规范化 episode 质量分数 / Normalize the episode quality score."""
    if isinstance(value, bool) or not isinstance(value, int) or value not in range(1, 6):
        raise ValueError(f"{label} 必须是 1 到 5 的整数 / must be an integer from 1 to 5")
    return value


def overall_speed_label(length_steps: int) -> str:
    """将 episode 长度按 500 steps 分桶。

    Bin episode length into 500-step labels. The nearest 500-step bucket is
    used, with the paper's example interval 1750 through 2250 mapping to
    ``2000 steps``.
    """
    if not isinstance(length_steps, int) or length_steps <= 0:
        raise ValueError("episode length 必须是正整数 / episode length must be positive")
    # Python's ties-to-even rounding gives both 1750 and 2250 the requested
    # ``2000 steps`` label while keeping the bins at 500-step increments.
    bucket = max(500, int(round(length_steps / 500.0)) * 500)
    return f"{bucket} steps"


def normalize_metadata(episode: dict, index: int, length: int) -> dict:
    """验证 episode-level metadata / Validate episode-level metadata."""
    metadata = episode.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError(f"episode {index}.metadata 必须是对象 / must be an object")
    expected_speed = overall_speed_label(length)
    speed = metadata.get("overall_speed")
    if speed not in (None, expected_speed):
        raise ValueError(
            f"episode {index}.metadata.overall_speed 必须为 {expected_speed!r}，当前为 {speed!r}"
        )
    return {
        "overall_speed": expected_speed,
        "overall_quality": normalize_quality(
            metadata.get("overall_quality"), f"episode {index}.metadata.overall_quality"
        ),
    }


def load_episode_lengths(dataset_root: Path) -> dict[int, int]:
    """读取 episode 长度 / Read episode lengths."""
    rows = read_jsonl(dataset_root / "meta" / "episodes.jsonl")
    return {int(row["episode_index"]): int(row["length"]) for row in rows}


def frame_from_seconds(value: object, fps: object, label: str) -> int:
    """将视频秒数转换为最近帧 / Convert video seconds to the nearest frame."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是非负数字 / must be a non-negative number")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        raise ValueError("数据集 meta/info.json 的 fps 必须是正数 / dataset fps must be positive")
    seconds = float(value)
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"{label} 必须是有限的非负数字 / must be finite and non-negative")
    return int(math.floor(seconds * float(fps) + 0.5))


def resolve_frame(item: dict, fps: object, frame_key: str, seconds_key: str, label: str) -> int:
    """解析 frame_index 或秒数输入 / Resolve a frame index or seconds input."""
    has_frame = frame_key in item
    has_seconds = seconds_key in item
    if not has_frame and not has_seconds:
        raise ValueError(f"{label} 必须填写 {frame_key} 或 {seconds_key}")
    converted = frame_from_seconds(item[seconds_key], fps, f"{label}.{seconds_key}") if has_seconds else None
    if has_frame:
        frame = item[frame_key]
        if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
            raise ValueError(f"{label}.{frame_key} 必须是非负整数 / must be a non-negative integer")
        if converted is not None and frame != converted:
            raise ValueError(f"{label} 的 frame_index 与 time_seconds 不一致 / frame and seconds disagree")
        return frame
    return int(converted)


def materialize_memory_segments(segments: list[dict]) -> list[dict]:
    """把每段 memory_update 解析为当前段的 memory，不累加也不继承历史。"""
    materialized: list[dict] = []
    for index, segment in enumerate(segments):
        has_memory = "memory" in segment
        has_update = "memory_update" in segment
        if has_memory == has_update:
            raise ValueError(
                f"segments[{index}] 必须填写 memory 或 memory_update 其中一个 / provide exactly one"
            )
        if has_update:
            update = segment["memory_update"]
            require_english(update, f"segments[{index}].memory_update", allow_empty=True)
            current = update.strip()
        else:
            require_english(segment["memory"], f"segments[{index}].memory", allow_empty=True)
            current = segment["memory"].strip()
        normalized = dict(segment)
        normalized.pop("memory_update", None)
        normalized["memory"] = current
        materialized.append(normalized)
    return materialized


def validate_sparse(dataset_root: Path, annotation_path: Path, allow_missing: bool) -> dict[int, dict]:
    """验证稀疏标签并返回按 episode 索引的标签。

    Validate sparse labels and return them indexed by episode.
    """
    info = json.loads((dataset_root / "meta" / "info.json").read_text(encoding="utf-8"))
    if info.get("codebase_version") != "v2.1":
        raise ValueError(f"输入数据必须是 LeRobot v2.1，当前版本为 {info.get('codebase_version')!r}")
    bundle = read_annotation_bundle(annotation_path)
    if bundle.get("schema_version") != "data_annotation.v1":
        raise ValueError("annotations.json 的 schema_version 必须是 data_annotation.v1")
    lengths = load_episode_lengths(dataset_root)
    fps = info.get("fps")
    rows = bundle.get("episodes")
    if not isinstance(rows, list) or not rows:
        raise ValueError("annotations.json 必须包含非空 episodes 列表")
    annotations: dict[int, dict] = {}
    for episode in rows:
        index = int(episode["episode_index"])
        if index not in lengths:
            raise ValueError(f"episode {index} 不存在于数据集")
        if index in annotations:
            raise ValueError(f"episode {index} 重复标注")
        require_english(episode.get("task_prompt"), f"episode {index}.task_prompt")
        if allow_missing and episode.get("success") is None:
            # 模板会包含全部 episode；部分标注时跳过仍为 null 的未完成项。
            # The generated template contains every episode; skip unfinished null entries in partial mode.
            continue
        success = normalize_success(episode.get("success"), f"episode {index}.success")
        metadata = normalize_metadata(episode, index, lengths[index])
        segments = episode.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"episode {index}.segments 不能为空")
        normalized_segments: list[dict] = []
        previous = -1
        for segment_index, segment in enumerate(segments):
            normalized_segment = dict(segment)
            frame = resolve_frame(
                normalized_segment,
                fps,
                "frame_index",
                "time_seconds",
                f"episode {index}.segments[{segment_index}]",
            )
            normalized_segment["frame_index"] = frame
            if frame <= previous:
                raise ValueError(f"episode {index} 的关键帧必须严格递增")
            if segment_index == 0 and frame != 0:
                raise ValueError(f"episode {index} 的第一段必须从 frame 0 开始")
            if frame >= lengths[index]:
                raise ValueError(f"episode {index} 的关键帧 {frame} 超出长度 {lengths[index]}")
            require_english(
                normalized_segment.get("response"),
                f"episode {index}.segments[{segment_index}].response",
            )
            normalized_segment["mistake"] = normalize_success(
                normalized_segment.get("mistake"),
                f"episode {index}.segments[{segment_index}].mistake",
            )
            normalized_segments.append(normalized_segment)
            previous = frame
        normalized_segments = materialize_memory_segments(normalized_segments)
        normalized_episode = dict(episode)
        normalized_episode["success"] = success
        normalized_episode["metadata"] = metadata
        normalized_episode["segments"] = normalized_segments
        interventions = episode.get("interventions", [])
        normalized_interventions: list[dict] = []
        previous_end = -1
        for item_index, item in enumerate(interventions):
            normalized_item = dict(item)
            start = resolve_frame(
                normalized_item,
                fps,
                "start_frame",
                "start_time_seconds",
                f"episode {index}.interventions[{item_index}]",
            )
            end = resolve_frame(
                normalized_item,
                fps,
                "end_frame",
                "end_time_seconds",
                f"episode {index}.interventions[{item_index}]",
            )
            if end < start:
                raise ValueError(f"episode {index} 的接管区间非法")
            normalized_item["start_frame"] = start
            normalized_item["end_frame"] = end
            normalized_interventions.append(normalized_item)
        normalized_interventions.sort(key=lambda value: value["start_frame"])
        for item in normalized_interventions:
            start = item["start_frame"]
            end = item["end_frame"]
            if end >= lengths[index] or start <= previous_end:
                raise ValueError(f"episode {index} 的接管区间越界或重叠")
            require_english(item.get("intervention_reason"), f"episode {index}.interventions.reason")
            previous_end = end
        normalized_episode["interventions"] = normalized_interventions
        annotations[index] = normalized_episode
    if not allow_missing and set(annotations) != set(lengths):
        missing = sorted(set(lengths) - set(annotations))
        extra = sorted(set(annotations) - set(lengths))
        raise ValueError(f"标注未覆盖全部 episode，missing={missing[:10]} extra={extra[:10]}")
    return annotations


def validate_materialized(dataset_root: Path, annotations: dict[int, dict]) -> None:
    """检查输出 parquet 中的逐帧字段和传播结果。

    Check materialized frame fields and propagation results in output parquet files.
    """
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("--check-materialized 需要安装 pyarrow，请在项目 uv 环境中运行") from exc
    for episode_index, annotation in annotations.items():
        paths = list((dataset_root / "data").glob(f"chunk-*/episode_{episode_index:06d}.parquet"))
        if len(paths) != 1:
            raise ValueError(f"找不到 episode {episode_index} 的 parquet")
        table = parquet.read_table(paths[0])
        missing = REQUIRED_MATERIALIZED - set(table.column_names)
        if missing:
            raise ValueError(f"episode {episode_index} 缺少物化字段：{sorted(missing)}")
        rows = table.to_pydict()
        expected_success = int(annotation["success"])
        if any(int(value) != expected_success for value in rows["episode_success"]):
            raise ValueError(f"episode {episode_index} 的 episode_success 未统一")
        segments = annotation["segments"]
        for segment_index, segment in enumerate(segments):
            start = segment["frame_index"]
            end = segments[segment_index + 1]["frame_index"] if segment_index + 1 < len(segments) else len(rows["response"])
            if rows["response"][start] != segment["response"] or rows["response"][end - 1] != segment["response"]:
                raise ValueError(f"episode {episode_index} response 未按区间传播")
            if rows["memory"][start] != segment["memory"] or rows["memory"][end - 1] != segment["memory"]:
                raise ValueError(f"episode {episode_index} memory 未按区间传播")
            expected_mistake = bool(segment["mistake"])
            if rows["mistake"][start] != expected_mistake or rows["mistake"][end - 1] != expected_mistake:
                raise ValueError(f"episode {episode_index} mistake 未按区间传播")
        expected_speed = annotation["metadata"]["overall_speed"]
        if any(value != expected_speed for value in rows["episode_overall_speed"]):
            raise ValueError(f"episode {episode_index} 的 overall_speed 未统一")
        expected_quality = annotation["metadata"]["overall_quality"]
        if any(int(value) != expected_quality for value in rows["episode_overall_quality"]):
            raise ValueError(f"episode {episode_index} 的 overall_quality 未统一")


def main() -> None:
    """执行 bundle 验证 / Validate the annotation bundle."""
    args = parse_args()
    annotations = validate_sparse(args.dataset_root, args.annotations, args.allow_missing)
    if args.check_materialized:
        validate_materialized(args.dataset_root, annotations)
    print(f"验证通过：episodes={len(annotations)} materialized={args.check_materialized}")


if __name__ == "__main__":
    main()
