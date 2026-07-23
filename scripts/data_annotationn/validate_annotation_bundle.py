#!/usr/bin/env python3
"""验证稀疏人工标注和已经物化的 LeRobot v2.1 数据集。

Validate sparse human annotations and a materialized LeRobot v2.1 dataset.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ENGLISH_TEXT = re.compile(r"^[\x09\x0a\x0d\x20-\x7e]*$")
REQUIRED_MATERIALIZED = {
    "response",
    "memory",
    "episode_success",
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


def load_episode_lengths(dataset_root: Path) -> dict[int, int]:
    """读取 episode 长度 / Read episode lengths."""
    rows = read_jsonl(dataset_root / "meta" / "episodes.jsonl")
    return {int(row["episode_index"]): int(row["length"]) for row in rows}


def validate_sparse(dataset_root: Path, annotation_path: Path, allow_missing: bool) -> dict[int, dict]:
    """验证稀疏标签并返回按 episode 索引的标签。

    Validate sparse labels and return them indexed by episode.
    """
    info = json.loads((dataset_root / "meta" / "info.json").read_text(encoding="utf-8"))
    if info.get("codebase_version") != "v2.1":
        raise ValueError(f"输入数据必须是 LeRobot v2.1，当前版本为 {info.get('codebase_version')!r}")
    bundle = json.loads(annotation_path.read_text(encoding="utf-8"))
    if bundle.get("schema_version") != "data_annotation.v1":
        raise ValueError("annotations.json 的 schema_version 必须是 data_annotation.v1")
    lengths = load_episode_lengths(dataset_root)
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
        success = episode.get("success")
        if success not in (0, 1, False, True):
            raise ValueError(f"episode {index}.success 必须是 0 或 1")
        segments = episode.get("segments")
        if not isinstance(segments, list) or not segments:
            raise ValueError(f"episode {index}.segments 不能为空")
        previous = -1
        for segment_index, segment in enumerate(segments):
            frame = segment.get("frame_index")
            if not isinstance(frame, int) or frame <= previous:
                raise ValueError(f"episode {index} 的关键帧必须严格递增")
            if segment_index == 0 and frame != 0:
                raise ValueError(f"episode {index} 的第一段必须从 frame 0 开始")
            if frame >= lengths[index]:
                raise ValueError(f"episode {index} 的关键帧 {frame} 超出长度 {lengths[index]}")
            require_english(segment.get("response"), f"episode {index}.segments[{segment_index}].response")
            require_english(segment.get("memory"), f"episode {index}.segments[{segment_index}].memory")
            previous = frame
        interventions = episode.get("interventions", [])
        previous_end = -1
        for item in sorted(interventions, key=lambda value: int(value["start_frame"])):
            start = item.get("start_frame")
            end = item.get("end_frame")
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
                raise ValueError(f"episode {index} 的接管区间非法")
            if end >= lengths[index] or start <= previous_end:
                raise ValueError(f"episode {index} 的接管区间越界或重叠")
            require_english(item.get("intervention_reason"), f"episode {index}.interventions.reason")
            previous_end = end
        annotations[index] = episode
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


def main() -> None:
    """执行 bundle 验证 / Validate the annotation bundle."""
    args = parse_args()
    annotations = validate_sparse(args.dataset_root, args.annotations, args.allow_missing)
    if args.check_materialized:
        validate_materialized(args.dataset_root, annotations)
    print(f"验证通过：episodes={len(annotations)} materialized={args.check_materialized}")


if __name__ == "__main__":
    main()
