#!/usr/bin/env python3
"""把关键帧标注传播为逐帧字段并生成新的 LeRobot v2.1 数据集。"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as parquet

from validate_annotation_bundle import validate_sparse


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="传播关键帧标签并生成 LeRobot v2.1 副本")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--allow-missing", action="store_true", help="未标注 episode 使用空上下文")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    """读取 JSONL 文件。"""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """写回 JSONL 文件。"""
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def frame_labels(annotation: dict | None, length: int) -> dict[str, list]:
    """将一个 episode 的稀疏标注展开成逐帧列表。"""
    if annotation is None:
        annotation = {
            "success": 0,
            "segments": [{"frame_index": 0, "response": "", "memory": ""}],
            "interventions": [],
        }
    segments = annotation["segments"]
    responses: list[str] = []
    memories: list[str] = []
    for frame in range(length):
        active = segments[0]
        for segment in segments:
            if segment["frame_index"] <= frame:
                active = segment
            else:
                break
        responses.append(active["response"])
        memories.append(active["memory"])
    is_intervention = [False] * length
    intervention_start = [False] * length
    intervention_reason = [""] * length
    for item in annotation.get("interventions", []):
        start = int(item["start_frame"])
        end = int(item["end_frame"])
        for frame in range(start, end + 1):
            is_intervention[frame] = True
            intervention_reason[frame] = item["intervention_reason"]
        intervention_start[start] = True
    return {
        "response": responses,
        "memory": memories,
        "episode_success": [int(annotation["success"])] * length,
        "is_intervention": is_intervention,
        "intervention_start": intervention_start,
        "intervention_reason": intervention_reason,
    }


def append_or_replace(table: pa.Table, name: str, values: list, arrow_type: pa.DataType) -> pa.Table:
    """追加或替换列，便于重复生成输出副本。"""
    column = pa.array(values, type=arrow_type)
    if name in table.column_names:
        return table.set_column(table.column_names.index(name), name, column)
    return table.append_column(name, column)


def update_tasks(root: Path, annotations: dict[int, dict], episode_rows: list[dict], info: dict) -> dict[str, int]:
    """更新 v2.1 tasks.jsonl，并给每个 episode 分配 task_index。"""
    tasks_path = root / "meta" / "tasks.jsonl"
    old_tasks = read_jsonl(tasks_path) if tasks_path.exists() else []
    task_to_index = {str(row["task"]): int(row["task_index"]) for row in old_tasks}
    next_index = max(task_to_index.values(), default=-1) + 1
    for annotation in annotations.values():
        task = annotation["task_prompt"]
        if task not in task_to_index:
            task_to_index[task] = next_index
            next_index += 1
    tasks = [{"task_index": index, "task": task} for task, index in sorted(task_to_index.items(), key=lambda item: item[1])]
    write_jsonl(tasks_path, tasks)
    info["total_tasks"] = len(tasks)
    for row in episode_rows:
        index = int(row["episode_index"])
        annotation = annotations.get(index)
        if annotation is not None:
            row["tasks"] = [annotation["task_prompt"]]
            row["success"] = int(annotation["success"])
            row["is_dagger"] = bool(annotation.get("interventions"))
            row["intervention_count"] = len(annotation.get("interventions", []))
    return task_to_index


def update_info(root: Path, info: dict) -> None:
    """声明新增字段并保持 LeRobot v2.1 版本。"""
    features = info.setdefault("features", {})
    scalar_fields = {
        "response": "string",
        "memory": "string",
        "episode_success": "int8",
        "is_intervention": "bool",
        "intervention_start": "bool",
        "intervention_reason": "string",
    }
    for name, dtype in scalar_fields.items():
        features[name] = {"dtype": dtype, "shape": [1], "names": None}
    info["codebase_version"] = "v2.1"
    (root / "meta" / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def materialize_episode(path: Path, annotation: dict | None, length: int, task_index: int | None) -> None:
    """向一个 parquet 写入传播后的逐帧标签。"""
    table = parquet.read_table(path)
    if table.num_rows != length:
        raise ValueError(f"{path} 行数 {table.num_rows} 与 episode 长度 {length} 不一致")
    labels = frame_labels(annotation, length)
    table = append_or_replace(table, "response", labels["response"], pa.string())
    table = append_or_replace(table, "memory", labels["memory"], pa.string())
    table = append_or_replace(table, "episode_success", labels["episode_success"], pa.int8())
    table = append_or_replace(table, "is_intervention", labels["is_intervention"], pa.bool_())
    table = append_or_replace(table, "intervention_start", labels["intervention_start"], pa.bool_())
    table = append_or_replace(table, "intervention_reason", labels["intervention_reason"], pa.string())
    if annotation is not None and task_index is not None and "task_index" in table.column_names:
        table = table.set_column(
            table.column_names.index("task_index"),
            "task_index",
            pa.array([task_index] * length, type=table["task_index"].type),
        )
    parquet.write_table(table, path)


def main() -> None:
    """复制数据集、传播标签并更新 LeRobot 元数据。"""
    args = parse_args()
    if args.output.exists():
        if not args.overwrite:
            raise FileExistsError(f"输出目录已存在：{args.output}，如需覆盖请显式传 --overwrite")
        shutil.rmtree(args.output)
    annotations = validate_sparse(args.input, args.annotations, args.allow_missing)
    lengths = {
        int(row["episode_index"]): int(row["length"])
        for row in read_jsonl(args.input / "meta" / "episodes.jsonl")
    }
    shutil.copytree(args.input, args.output)
    info_path = args.output / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    episode_rows = read_jsonl(args.output / "meta" / "episodes.jsonl")
    task_to_index = update_tasks(args.output, annotations, episode_rows, info)
    update_info(args.output, info)
    write_jsonl(args.output / "meta" / "episodes.jsonl", episode_rows)
    for path in sorted((args.output / "data").glob("chunk-*/episode_*.parquet")):
        episode_index = int(path.stem.split("_")[-1])
        annotation = annotations.get(episode_index)
        task_index = task_to_index[annotation["task_prompt"]] if annotation is not None else None
        materialize_episode(path, annotation, lengths[episode_index], task_index)
    print(f"已生成：{args.output}，episodes={len(lengths)}，人工标注={len(annotations)}")


if __name__ == "__main__":
    main()
