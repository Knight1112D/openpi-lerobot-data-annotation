#!/usr/bin/env python3
"""为 LeRobot v2.1 数据集生成可在 VSCode 编辑的人工标注模板。

Generate a VSCode-editable human annotation template for a LeRobot v2.1 dataset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_v3_tasks(path: Path) -> dict[int, str]:
    """读取 LeRobot v3.0 tasks.parquet / Read LeRobot v3.0 tasks.parquet."""
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("读取 LeRobot v3.0 需要项目环境中的 pyarrow") from exc
    table = parquet.read_table(path)
    columns = table.to_pydict()
    task_indices = columns.get("task_index", [])
    task_texts = columns.get("task", columns.get("__index_level_0__", []))
    return {int(index): str(task) for index, task in zip(task_indices, task_texts)}


def load_episode_rows(dataset_root: Path, info: dict) -> tuple[list[dict], dict[int, str]]:
    """读取 v2.1/v3.0 episode 信息 / Read v2.1 or v3.0 episode metadata."""
    meta = dataset_root / "meta"
    episodes_path = meta / "episodes.jsonl"
    tasks_path = meta / "tasks.jsonl"
    if episodes_path.exists():
        tasks = {int(row["task_index"]): row["task"] for row in read_jsonl(tasks_path)}
        return read_jsonl(episodes_path), tasks

    if info.get("codebase_version") != "v3.0":
        raise ValueError(
            "数据集缺少 meta/episodes.jsonl；当前只支持 LeRobot v2.1 或 v3.0"
        )
    data_root = dataset_root / "data"
    data_files = sorted(
        set(data_root.glob("chunk-*/episode_*.parquet"))
        | set(data_root.glob("chunk-*/file-*.parquet"))
    )
    if not data_files:
        raise ValueError("找不到 LeRobot v3.0 data/chunk-*/file-*.parquet")
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RuntimeError("读取 LeRobot v3.0 需要项目环境中的 pyarrow") from exc
    tasks = load_v3_tasks(meta / "tasks.parquet")
    rows = []
    for path in data_files:
        table = parquet.read_table(path, columns=["episode_index", "task_index"])
        episode_indices = sorted(set(int(value) for value in table["episode_index"].to_pylist()))
        if len(episode_indices) != 1:
            raise ValueError(f"{path} 必须只包含一个 episode")
        task_indices = sorted(set(int(value) for value in table["task_index"].to_pylist()))
        rows.append(
            {
                "episode_index": episode_indices[0],
                "length": table.num_rows,
                "tasks": task_indices,
            }
        )
    return rows, tasks


def parse_args() -> argparse.Namespace:
    """解析命令行参数 / Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="生成 LeRobot episode 标注模板 / Generate a LeRobot episode template"
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    """读取 JSONL 文件 / Read a JSONL file."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    """读取 episode 元数据并写出人工标注模板。

    Read episode metadata and write the human annotation template.
    """
    args = parse_args()
    info_path = args.dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("codebase_version") not in {"v2.1", "v3.0"}:
        raise ValueError(
            f"只支持 LeRobot v2.1/v3.0，当前版本为 {info.get('codebase_version')!r}"
        )
    episode_rows, tasks = load_episode_rows(args.dataset_root, info)
    episodes = []
    for row in episode_rows:
        task_list = row.get("tasks") or []
        task_prompt = task_list[0] if task_list and isinstance(task_list[0], str) else None
        if not task_prompt:
            task_index = int(task_list[0]) if task_list else 0
            task_prompt = tasks.get(task_index, "REPLACE_WITH_TASK_PROMPT")
        episodes.append(
            {
                "episode_index": int(row["episode_index"]),
                "task_prompt": task_prompt,
                "success": None,
                "metadata": {
                    "overall_speed": None,
                    "overall_quality": None,
                },
                "segments": [
                    {
                        "time_seconds": 0.0,
                        "response": "",
                        "memory_update": "",
                        "mistake": None,
                    }
                ],
                "interventions": [],
            }
        )
    result = {
        "schema_version": "data_annotation.v1",
        "dataset": {
            "format": f"lerobot_{info.get('codebase_version')}",
            "source_root": "REPLACE_WITH_INPUT_DATASET_ROOT",
            "fps": info.get("fps"),
        },
        "episodes": episodes,
    }
    if args.output.exists() and args.output.is_dir():
        raise IsADirectoryError(
            f"模板输出必须是 JSON 文件，不是目录：{args.output}；"
            "请传入例如 /path/to/annotations.json / output must be a JSON file"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {len(episodes)} 条 episode 模板：{args.output}")


if __name__ == "__main__":
    main()
