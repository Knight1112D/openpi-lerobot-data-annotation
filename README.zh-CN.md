# LeRobot v2.1 人工语义标注工具

[English README](README.md)

本目录按照 `skills/data_annotationn` skill 建立，用于对 LeRobot v2.1 数据集进行人工稀疏标注、验证和逐帧物化；模板生成器同时支持读取 LeRobot v3.0 数据。所有数据集、标注文件和输出目录都必须通过命令行显式传入；脚本没有业务路径默认值。原始数据不会被覆盖，物化结果由 `--output` 指定。

## 字段语义

- `success`：最终填写 `1` 或 `0`；也接受 JSON 的 `true`/`false`，脚本会转换成 `1`/`0`。模板中的 `null` 只表示尚未填写，不能通过最终验证；大写 `TRUE`/`FALSE` 不是合法 JSON 布尔值。
- `metadata.overall_speed`：根据 episode 的实际 timestep 长度按 500 steps 自动计算；人工标注时可以省略或填写 `null`，例如 1750 到 2250 steps（含边界）会自动标记为 `"2000 steps"`。
- `metadata.overall_quality`：人工填写的 episode 质量分数，范围为 1–5，5 代表质量最高。
- `response`：当前关键帧开始执行的子任务 `l_t`，使用可执行英文短句。
- `memory_update`：当前阶段新增的记忆事实；传播时会自动和前面内容拼接成完整 `memory`。
- `segments[].mistake`：当前 action segment 是否发生错误；发生填写 `1`，没有填写 `0`。传播后会成为逐帧 `mistake` 字段。
- `segments`：可以有多个关键帧段；手工填写 `time_seconds`，传播时按 `fps` 自动转换成 `frame_index`。
- 每个 episode 的标准格式只能有一个 `"segments"` 数组。旧标注文件如果把每一段错误地写成重复的 `"segments"` 键，校验和传播脚本会按原顺序合并，避免 JSON 解析时后面的键覆盖前面的段；新生成的标注文件会统一写成单个数组。

如需把旧文件永久修复成标准格式，执行：

```bash
bash scripts/run.sh normalize \
  --input /path/to/legacy_annotations.json \
  --output /path/to/annotations.canonical.json
```

该命令会输出合法 JSON，并保证每个 episode 只有一个 `"segments"` 数组。`validate` 和 `propagate` 也可以直接读取旧格式，但共享数据集和提交 GitHub 时应使用规范化后的文件。
- `interventions`：使用 `start_time_seconds` 和 `end_time_seconds` 标记操作者实际改变机器人行为的连续区间，不是只标记一个时间，也不需要填写数值形式的“干预量”。

可以按 episode 逐个完成同一个 JSON 文件。尚未完成全部 episode 时，验证命令加 `--allow-missing`；全部完成后再进行不带该参数的正式验证和传播。

## 环境

环境固定在本项目主目录的 `.venv`，安装源遵循项目规范：

```bash
cd /path/to/data_annotation_project
bash scripts/bootstrap.sh
```

## 标注流程

先生成模板：

```bash
bash scripts/run.sh template \
  --dataset-root /path/to/input_dataset \
  --output /path/to/annotations.json
```

如果输入是 LeRobot v3.0，模板生成器会从 `meta/tasks.parquet` 和 `data/chunk-*/file-*.parquet` 自动读取任务与 episode 长度；当前 `validate`、`propagate` 和 `validate-output` 物化流程仍要求 v2.1。

用 VSCode 打开 `--output` 指定的文件，填写英文的 `task_prompt`、`response`、`memory_update`、`success`、`metadata.overall_quality`、`segments[].mistake` 和可选的 `interventions`。`metadata.overall_speed` 不需要手工填写，由校验和传播脚本根据数据集长度自动计算。人工只填写语义发生变化的关键帧，第一段必须从 `time_seconds: 0.0` 开始。视频播放器只有秒数时，直接把秒数写入 `time_seconds`，脚本会根据数据集 `fps` 自动转换帧号。

填写完成后验证：

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json
```

全部 episode 标注完成并且正式验证通过后，运行下面的命令生成最终的 LeRobot v2.1 数据集：

```bash
bash scripts/run.sh propagate \
  --input /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --output /path/to/annotated_dataset
```

`--output` 指定的目录就是新的最终数据集。脚本会复制数据集文件，并把 `time_seconds` 转换得到的关键帧标签传播到每一帧；输入数据集不会作为输出目录使用。

最后检查逐帧字段：

```bash
bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotated_dataset \
  --annotations /path/to/annotations.json
```

这一步用于确认最终 LeRobot 数据集中的 parquet 已经包含 `response`、`memory`、`episode_success`、episode metadata 和 mistake/干预字段。

## VLM 辅助标注

VLM/API 只作为最后的可选辅助方式，不是手工标注的前置条件。如果使用 VLM 生成草稿，仍然要人工对照完整视频确认 `time_seconds`、语义变化、英文文本、`success` 和 `interventions`，然后使用上面的 `validate`、`propagate`、`validate-output` 流程生成最终数据集。

## 参数说明

所有数据路径都必须显式提供：

- `template`：`--dataset-root`、`--output`
- `normalize`：`--input`、`--output`
- `validate`：`--dataset-root`、`--annotations`
- `propagate`：`--input`、`--annotations`、`--output`
- `validate-output`：`--dataset-root`、`--annotations`

## Windows + uv 部署

在 PowerShell 中执行下面的命令即可从 GitHub 完整 clone、创建环境并运行项目。先确保已安装 Git；没有 `uv` 时可用 `winget` 安装：

如果使用随项目提供的完整离线部署包，优先阅读项目根目录的 [`INSTALL_WINDOWS.txt`](INSTALL_WINDOWS.txt)，并运行 `scripts\install_windows.ps1`；该包可以携带 Python、uv 和 Windows wheel，不需要 Git 或管理员密码。

```powershell
winget install --id Git.Git -e
winget install --id astral-sh.uv -e
```

重新打开 PowerShell 后：

```powershell
git clone https://github.com/Knight1112D/openpi-lerobot-data-annotation.git
Set-Location openpi-lerobot-data-annotation
uv python install 3.11
uv sync --python 3.11
.\scripts\run.ps1 --help
```

如果 PowerShell 阻止执行本地脚本，在当前窗口临时放开限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Windows 下使用 `scripts\run.ps1`，不使用 Linux/macOS 的 `bash scripts/run.sh`。以下是完整的模板、验证和传播命令示例：

```powershell
$Dataset = "D:\datasets\raw_lerobot_v21"
$Work = "D:\annotation_work"
New-Item -ItemType Directory -Force $Work | Out-Null

.\scripts\run.ps1 template --dataset-root $Dataset --output (Join-Path $Work "annotations.json")
.\scripts\run.ps1 validate --dataset-root $Dataset --annotations (Join-Path $Work "annotations.json")
.\scripts\run.ps1 propagate --input $Dataset --annotations (Join-Path $Work "annotations.json") --output (Join-Path $Work "annotated_dataset")
.\scripts\run.ps1 validate-output --dataset-root (Join-Path $Work "annotated_dataset") --annotations (Join-Path $Work "annotations.json")
```

也可以不使用 `run.ps1`，直接用项目环境运行：

```powershell
uv run python scripts\data_annotation.py --help
```

完整示例：

```bash
bash scripts/run.sh template \
  --dataset-root /path/to/dataset \
  --output annotations/custom.json

bash scripts/run.sh propagate \
  --input /path/to/dataset \
  --annotations annotations/custom.json \
  --output outputs/custom_dataset
```

## 展示文件

[`examples/annotations.example.json`](examples/annotations.example.json) 是仅用于展示字段和传播效果的示例文件，文件名和内容都已明确标注为示例，不对应任何真实数据集，也不能直接作为生产标注提交。实际使用时请通过 `template` 命令针对自己的数据集生成文件。

所有数据集、标注文件和输出目录都通过命令参数传入。完整的人工视频标注步骤请参阅项目根目录的 `README.md`。
