#!/usr/bin/env python3
"""为 LeRobot v2.1 数据集生成可在 VSCode 编辑的人工标注模板。

Generate a VSCode-editable human annotation template for a LeRobot v2.1 dataset.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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
    episodes_path = args.dataset_root / "meta" / "episodes.jsonl"
    tasks_path = args.dataset_root / "meta" / "tasks.jsonl"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("codebase_version") != "v2.1":
        raise ValueError(f"只支持 LeRobot v2.1，当前版本为 {info.get('codebase_version')!r}")
    tasks = {int(row["task_index"]): row["task"] for row in read_jsonl(tasks_path)}
    episodes = []
    for row in read_jsonl(episodes_path):
        task_list = row.get("tasks") or []
        task_prompt = task_list[0] if task_list else tasks.get(0, "")
        episodes.append(
            {
                "episode_index": int(row["episode_index"]),
                "task_prompt": task_prompt,
                "success": None,
                "segments": [
                    {
                        "frame_index": 0,
                        "response": "",
                        "memory": "",
                    }
                ],
                "interventions": [],
            }
        )
    result = {
        "schema_version": "data_annotation.v1",
        "dataset": {
            "format": "lerobot_v2.1",
            "source_root": str(args.dataset_root.resolve()),
            "fps": info.get("fps"),
        },
        "episodes": episodes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {len(episodes)} 条 episode 模板：{args.output}")


if __name__ == "__main__":
    main()
