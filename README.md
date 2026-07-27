# OpenPI LeRobot Data Annotation

一个面向 LeRobot v2.1 数据集的人工语义标注工具。它把人工填写的稀疏关键帧标签，转换成可供 OpenPI/OpenTau 训练或分析使用的逐帧字段。

This project provides a human-in-the-loop annotation workflow for LeRobot v2.1 datasets. It converts sparse keyframe labels into frame-level fields for OpenPI/OpenTau training and analysis.

## 你将得到什么 / What this project does

- 生成可在 VSCode 中编辑的 JSON 标注模板；
- 按 episode 标注总任务、当前子任务、MEM 和人工接管；
- 严格检查帧号、英文文本、成功标签和接管区间；
- 不修改原始数据，复制出一个新的带语义字段的数据集；
- 将 `response`、`memory`、`episode_success` 和干预字段写入每一帧。

- Generate a VSCode-editable JSON annotation template.
- Annotate task goals, current subtasks, MEM state, and operator takeovers episode by episode.
- Validate frame indices, English text, success labels, and intervention intervals.
- Preserve the raw dataset and create a new annotated copy.
- Materialize `response`, `memory`, `episode_success`, and intervention fields on every frame.

## 1. 安装环境 / Install

要求：Linux/macOS shell、Python 3.10+、[uv](https://docs.astral.sh/uv/)。环境会创建在项目自己的 `.venv` 中。

Requirements: a Linux/macOS shell, Python 3.10+, and [uv](https://docs.astral.sh/uv/). The virtual environment is created inside this project at `.venv`.

```bash
cd /path/to/data_annotation_project
bash scripts/bootstrap.sh
```

检查入口是否可用：

```bash
bash scripts/run.sh --help
```

Check the command entrypoint:

```bash
bash scripts/run.sh --help
```

## 2. 准备输入数据 / Prepare the input dataset

输入必须是 LeRobot v2.1 数据集，至少包含：

The input must be a LeRobot v2.1 dataset containing at least:

```text
input_dataset/
├── meta/info.json
├── meta/episodes.jsonl
├── meta/tasks.jsonl
├── meta/episodes_stats.jsonl
├── data/chunk-*/episode_*.parquet
└── videos/...
```

`meta/info.json` 中的 `codebase_version` 必须是 `v2.1`。项目不会自动寻找或默认使用任何数据集路径。

The `codebase_version` in `meta/info.json` must be `v2.1`. No dataset path is discovered or assumed automatically.

## 3. 生成标注模板 / Generate a template

必须显式传入输入数据集和模板输出文件：

Both the dataset root and output annotation path are required:

```bash
bash scripts/run.sh template \
  --dataset-root /path/to/input_dataset \
  --output /path/to/annotations.json
```

生成的文件会包含所有 episode。你可以一次只填写一个 episode，其他未完成项保持 `success: null`。

The generated file contains all episodes. You may complete one episode at a time and leave unfinished episodes as `success: null`.

## 4. 填写 JSON / Fill the JSON

推荐使用 VSCode 打开 `annotations.json`。JSON 中只保留真实标注字段，字段解释请看 [`examples/README.md`](examples/README.md)。网线任务示例请看 [`examples/ethernet_cable_episode.example.json`](examples/ethernet_cable_episode.example.json)。

Open `annotations.json` in VSCode. The JSON files contain only annotation fields; see [`examples/README.md`](examples/README.md) for the field guide and [`examples/ethernet_cable_episode.example.json`](examples/ethernet_cable_episode.example.json) for the Ethernet example.

一个最小的 episode 结构如下：

A minimal episode structure looks like this:

```json
{
  "episode_index": 0,
  "task_prompt": "Place the red block into the tray.",
  "success": 1,
  "segments": [
    {
      "frame_index": 0,
      "response": "Reach for the red block with the gripper.",
      "memory": "The red block is on the table and has not been grasped yet."
    },
    {
      "frame_index": 120,
      "response": "Place the red block into the tray.",
      "memory": "The gripper holds the red block above the tray."
    }
  ],
  "interventions": []
}
```

### 字段含义 / Field meanings

| 字段 / Field | 填写内容 / What to write | 训练流程对应 / Training role |
|---|---|---|
| `task_prompt` | 完整任务目标，英文 / Full task goal in English | 总任务 `g`，写入任务元数据，并作为 VLM/VLA 条件 / Global goal `g`, task metadata and model condition |
| `success` | `1` 成功，`0` 失败；也接受 `true/false` / `1` success, `0` failure; `true/false` accepted | episode 标签，不是逐帧 reward / Episode label, not a frame reward |
| `frame_index` | 语义状态真正变化的第一帧 / First frame after semantic change | 定义标签区间起点 / Defines the interval start |
| `response` | 当前可执行子任务，英文 / Current executable subtask in English | 当前子任务 `l_t`，传给 low-level VLA / Current subtask `l_t` for the low-level VLA |
| `memory` | 完整压缩记忆，英文 / Complete compressed memory in English | 当前记忆 `m_{t+1}`，下一阶段作为历史 `m_t` / Current memory `m_{t+1}`, next stage history `m_t` |
| `interventions` | 接管区间和英文原因 / Takeover interval and English reason | DAgGER/KI/行为来源分析，可选使用 / Optional DAgGER/KI and behavior-source metadata |

### MEM 的填写逻辑 / MEM logic

`memory` 不要只填写“新增的一句话”。应填写当前阶段完整的、对未来决策有用的状态。

Do not write only a one-line memory delta. Write the complete future-useful state for the current stage.

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

JSON 中不需要单独添加 `m_t` 字段：上一段的 `memory` 就是下一段的历史 `m_t`。第一段可以把 `memory` 写成初始状态。

The JSON does not need a separate `m_t` field: the previous segment's `memory` becomes the next segment's historical `m_t`. The first segment may describe the initial state.

### segments 可以有多少段？ / How many segments?

可以有任意多段，但只在语义状态改变时增加。例如抓取成立、另一个物体被抓住、插入完成、物体进入盒子、错误恢复完成。不要每隔固定 30 帧重复填写。

Use as many segments as needed, but add one only when the semantic state changes: a grasp becomes established, another object is grasped, insertion completes, the object enters the box, or recovery completes. Do not repeat labels every 30 frames.

第一段必须从 `frame_index: 0` 开始，后续帧号严格递增。

The first segment must start at `frame_index: 0`, and later frame indices must be strictly increasing.

### interventions 怎么填写？ / How to annotate interventions

接管是闭区间 `[start_frame, end_frame]`，不是单独一帧：

An intervention is an inclusive interval `[start_frame, end_frame]`, not a single frame:

```json
"interventions": [
  {
    "start_frame": 760,
    "end_frame": 820,
    "intervention_reason": "The cable missed the adapter opening, so the operator corrected the alignment."
  }
]
```

- `start_frame`：操作者第一次有效改变机器人行为的帧；
- `end_frame`：错误修正完成、恢复自主执行前的最后一帧；
- 没有接管时使用空数组 `[]`；
- 不需要填写数值形式的“干预量”；
- 多次不重叠接管就写多个对象。

- `start_frame`: first frame where the operator effectively changes robot behavior;
- `end_frame`: last correction frame before autonomous execution resumes;
- use `[]` when there is no takeover;
- no numeric intervention amount is required;
- write multiple objects for multiple non-overlapping intervals.

## 5. 部分验证：按 episode 工作 / Partial validation: work episode by episode

如果只完成了部分 episode，使用 `--allow-missing`：

If only some episodes are complete, use `--allow-missing`:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --allow-missing
```

此模式会跳过 `success: null` 的未完成 episode，只检查已经填写完成的 episode。注意：如果某个 episode 已经填写了 `success`，但 `response` 或 `memory` 还是空字符串，验证器会报错，需要补齐。

This mode skips unfinished episodes whose `success` is `null` and validates completed episodes. If an episode has a non-null `success` but empty `response` or `memory`, validation fails and the episode must be completed.

## 6. 全量验证 / Final validation

全部 episode 都填写完成后，不要使用 `--allow-missing`：

After every episode is complete, validate without `--allow-missing`:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json
```

验证器会检查：

The validator checks:

- LeRobot v2.1 版本；
- episode 是否存在且没有重复；
- `success` 是否为 `0/1` 或 `true/false`；
- 关键帧是否从 `0` 开始并严格递增；
- 所有文本是否为非空英文 ASCII；
- intervention 是否越界或重叠。

- LeRobot v2.1 version;
- episode existence and uniqueness;
- `success` as `0/1` or `true/false`;
- keyframes starting at `0` and increasing strictly;
- non-empty English ASCII text;
- intervention bounds and overlap.

## 7. 传播并生成新数据集 / Propagate into a new dataset

验证通过后，指定一个新的输出目录。不要把输出目录设为输入目录：

After validation passes, choose a new output directory. Never use the input directory as the output:

```bash
bash scripts/run.sh propagate \
  --input /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --output /path/to/annotated_dataset
```

传播脚本会：

The propagation script will:

- 复制 `meta/`、`data/` 和 `videos/`；
- 根据关键帧区间向后传播 `response` 和 `memory`；
- 写入 `episode_success`、`is_intervention`、`intervention_start`、`intervention_reason`；
- 更新 `tasks.jsonl`、`episodes.jsonl` 和 `info.json`；
- 保留原始 action、状态、时间戳、帧索引和视频。

- Copy `meta/`, `data/`, and `videos/`;
- Propagate `response` and `memory` forward from keyframes;
- Write `episode_success`, `is_intervention`, `intervention_start`, and `intervention_reason`;
- Update `tasks.jsonl`, `episodes.jsonl`, and `info.json`;
- Preserve original actions, states, timestamps, frame indices, and videos.

## 8. 验证物化结果 / Validate the materialized dataset

```bash
bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotated_dataset \
  --annotations /path/to/annotations.json
```

它会检查 parquet 中的物化字段是否存在，并检查每个关键帧区间的 `response` 和 `memory` 是否正确传播。

It checks that materialized parquet fields exist and that `response` and `memory` match the annotated keyframe intervals.

## 9. 物化字段与下游使用 / Materialized fields and downstream use

| 物化字段 / Materialized field | 来源 / Source | 用途 / Use |
|---|---|---|
| `response` | `segments[].response` | 当前 subtask 条件 / Current subtask condition |
| `memory` | `segments[].memory` | MEM 语言上下文 / MEM language context |
| `episode_success` | `success` | episode 成功监督 / Episode success supervision |
| `is_intervention` | `interventions` 区间 / intervention intervals | 行为来源分析 / Behavior-source analysis |
| `intervention_start` | 每个区间的起点 / interval starts | 接管触发点统计 / Takeover trigger statistics |
| `intervention_reason` | `intervention_reason` | 错误分析 / Error analysis |

`episode_success` 不要当成逐帧 reward；`is_intervention` 也不要未经训练配置确认就混入 action loss。

Do not treat `episode_success` as a frame-level reward. Do not mix `is_intervention` into action loss unless the training configuration explicitly requires it.

## 常见错误 / Common mistakes

- 把中文写进 `task_prompt`、`response`、`memory` 或 `intervention_reason`；
- 用 `TRUE`/`FALSE` 字符串代替 JSON 的 `true`/`false`；
- 把 `memory` 写成只有“新增内容”的 delta；
- 把每一帧都写成一个 segment；
- 把 intervention 只写成开始帧；
- 直接覆盖输入数据集；
- 未完成标注就不带 `--allow-missing` 做全量验证。

- Put Chinese text in `task_prompt`, `response`, `memory`, or `intervention_reason`;
- Use `TRUE`/`FALSE` strings instead of JSON `true`/`false`;
- Write only a memory delta instead of the complete memory;
- Create one segment for every frame;
- Mark only the intervention start frame;
- Overwrite the input dataset;
- Run final validation without `--allow-missing` before annotation is complete.

## 示例和源码 / Examples and source

- [`examples/README.md`](examples/README.md)：字段和训练流程解释 / field and training-flow guide
- [`examples/annotations.example.json`](examples/annotations.example.json)：通用 JSON 示例 / generic JSON example
- [`examples/ethernet_cable_episode.example.json`](examples/ethernet_cable_episode.example.json)：网线任务示例 / Ethernet task example
- `scripts/data_annotation.py`：项目入口 / project entrypoint
- `scripts/data_annotationn/`：模板、验证和传播实现 / template, validation, and propagation implementation
