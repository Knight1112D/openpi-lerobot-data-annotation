#!/usr/bin/env python3
"""数据标注项目入口，调用 data_annotationn skill 的标准脚本。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = PROJECT_ROOT / "scripts" / "data_annotationn"


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """添加项目中各命令共用的路径参数。"""
    parser.add_argument(
        "--dataset-root",
        type=Path,
        required=True,
        help="LeRobot v2.1 输入数据集目录",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="人工填写的稀疏标注 JSON 文件",
    )


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(description="OpenPI LeRobot 数据标注工作流")
    subparsers = parser.add_subparsers(dest="command", required=True)

    template = subparsers.add_parser("template", help="生成 VSCode 可编辑的标注模板")
    template.add_argument("--dataset-root", type=Path, required=True)
    template.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate", help="验证稀疏标注")
    add_common_arguments(validate)
    validate.add_argument("--allow-missing", action="store_true")

    propagate = subparsers.add_parser("propagate", help="复制数据集并传播逐帧标签")
    propagate.add_argument("--input", type=Path, required=True)
    propagate.add_argument("--annotations", type=Path, required=True)
    propagate.add_argument("--output", type=Path, required=True)
    propagate.add_argument("--overwrite", action="store_true")
    propagate.add_argument("--allow-missing", action="store_true")

    output_validate = subparsers.add_parser("validate-output", help="验证物化后的数据集")
    add_common_arguments(output_validate)
    return parser


def run_skill_script(script_name: str, arguments: list[str]) -> None:
    """在当前项目环境中运行技能提供的标准脚本。"""
    script_path = SKILL_SCRIPTS / script_name
    if not script_path.is_file():
        raise FileNotFoundError(f"找不到技能脚本：{script_path}")
    subprocess.run([sys.executable, str(script_path), *arguments], check=True)


def main() -> None:
    """执行模板、验证或传播命令。"""
    args = build_parser().parse_args()
    if args.command == "template":
        run_skill_script(
            "make_annotation_template.py",
            ["--dataset-root", str(args.dataset_root), "--output", str(args.output)],
        )
    elif args.command == "validate":
        command = [
            "--dataset-root",
            str(args.dataset_root),
            "--annotations",
            str(args.annotations),
        ]
        if args.allow_missing:
            command.append("--allow-missing")
        run_skill_script("validate_annotation_bundle.py", command)
    elif args.command == "propagate":
        command = [
            "--input",
            str(args.input),
            "--annotations",
            str(args.annotations),
            "--output",
            str(args.output),
        ]
        if args.overwrite:
            command.append("--overwrite")
        if args.allow_missing:
            command.append("--allow-missing")
        run_skill_script("propagate_annotations.py", command)
    elif args.command == "validate-output":
        run_skill_script(
            "validate_annotation_bundle.py",
            [
                "--dataset-root",
                str(args.dataset_root),
                "--annotations",
                str(args.annotations),
                "--check-materialized",
            ],
        )


if __name__ == "__main__":
    main()
