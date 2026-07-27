# LeRobot v2.1 人工语义标注工具

这是一个以人工视频标注为主的 LeRobot v2.1 数据标注项目。对照完整 episode 视频，在语义状态发生变化的关键帧填写英文任务、子任务、MEM 和人工接管区间；脚本负责验证 JSON，并把稀疏标签传播到新的数据集副本。

This is a manual-first annotation workflow for LeRobot v2.1 datasets. You inspect the complete episode videos, write English task/subtask/MEM labels at semantic keyframes, validate the JSON, and materialize the labels into a new dataset copy.

## 先看结论 / Quick overview

- 人工视频标注是主要使用方式；
- 按完整 episode 视频定位帧号，不对视频设置采样帧数；
- 传播结果写到新的 `--output` 目录；
- 标注文本统一使用英文 ASCII；
- `response` 是当前子任务 `l_t`；
- `memory` 是完整的当前记忆 `m_{t+1}`，不是只写新增 delta；
- `interventions` 是连续接管区间，不是只标记一个帧。

## 1. 目录怎么放 / Where to put the dataset

工作目录可以按以下结构组织，命令中的路径替换为实际路径：

Organize the working directory as follows and replace the command paths with actual paths:

```text
workspace/
├── data_annotation_project/
├── datasets/
│   └── raw_lerobot_v21/
└── annotation_work/
    ├── annotations.json
    └── annotated_dataset/
```

`raw_lerobot_v21/` 必须是 LeRobot v2.1 数据集，至少包含：

`raw_lerobot_v21/` must be a LeRobot v2.1 dataset containing at least:

```text
raw_lerobot_v21/
├── meta/info.json
├── meta/episodes.jsonl
├── meta/tasks.jsonl
├── meta/episodes_stats.jsonl
├── data/chunk-*/episode_*.parquet
└── videos/
    └── chunk-*/<video_key>/episode_*.mp4
```

检查 `meta/info.json`：

Check `meta/info.json`:

- `codebase_version` 必须是 `v2.1`；
- `fps` 是视频和帧号换算的重要信息；
- `videos/` 中的 episode 编号应与 `episodes.jsonl`、parquet 文件一致。

- `codebase_version` must be `v2.1`;
- `fps` is needed when relating video time to frame indices;
- episode numbers should match across `videos/`, `episodes.jsonl`, and parquet files.

每次运行都显式传入数据集、标注文件和输出目录路径。

Pass the dataset, annotation, and output paths explicitly for every command.

## 2. 安装项目环境 / Install the environment

要求 Python 3.10+、`uv` 和 Linux/macOS shell。环境会创建在项目目录自己的 `.venv` 中。

Requirements: Python 3.10+, `uv`, and a Linux/macOS shell. The environment is created in the project's own `.venv` directory.

```bash
cd /path/to/data_annotation_project
bash scripts/bootstrap.sh
bash scripts/run.sh --help
```

## 3. 生成标注模板 / Generate the annotation template

模板生成读取数据集元数据，并生成所有 episode 的标注对象：

Template generation reads dataset metadata and creates an annotation object for every episode:

```bash
bash scripts/run.sh template \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --output /path/to/annotation_work/annotations.json
```

生成的 JSON 会包含所有 episode。你可以一次只完成一个 episode，未完成项先保留 `success: null`。

The generated JSON contains all episodes. Complete one episode at a time and leave unfinished entries as `success: null`.

## 4. 对照视频手工标注 / Annotate manually against the video

这是本项目的主要流程。使用能显示准确帧号的视频播放器或 VSCode 视频插件，对照 episode 的完整视频填写 JSON。

This is the main workflow. Use a frame-accurate video player or VSCode video extension to inspect the complete episode video and fill the JSON.

### 4.1 找到 episode 对应的视频 / Find the episode video

以 `episode_index: 0` 为例：

1. 在 `meta/episodes.jsonl` 找到 episode 0 的长度和任务；
2. 在 `videos/chunk-*/<video_key>/episode_000000.mp4` 找到对应视频；
3. 优先使用主视角视频观察整体任务，必要时对照腕部相机；
4. 记录视频播放器显示的帧号，或根据 `fps` 将时间换算为帧号；
5. 关键帧必须与数据中的 `frame_index` 对齐，不要凭时间大概估计。

For `episode_index: 0`:

1. Find its length and task in `meta/episodes.jsonl`;
2. Open `videos/chunk-*/<video_key>/episode_000000.mp4`;
3. Start with the main camera and use wrist cameras when needed;
4. Record the player frame index, or convert time using `fps`;
5. Align labels with the dataset `frame_index`, not an approximate timestamp.

### 4.2 先填写 episode 级字段 / Fill episode-level fields first

```json
{
  "episode_index": 0,
  "task_prompt": "Pick up the Ethernet cable with the left gripper and pick up the Ethernet adapter with the right gripper. Insert the cable into the adapter and put them into the box.",
  "success": 1,
  "segments": [],
  "interventions": []
}
```

- `episode_index`：必须和数据集中的编号一致；
- `task_prompt`：完整任务目标，使用英文现在时和明确动作；
- `success`：episode 最终成功填 `1`，失败填 `0`；也接受 JSON `true/false`，但推荐 `1/0`；
- `success: null`：只代表还没填完，最终验证不能保留；
- `interventions`：没有人工接管就填空数组 `[]`。

- `episode_index`: must match the dataset episode index;
- `task_prompt`: the complete goal in clear English present-tense actions;
- `success`: `1` for success and `0` for failure; JSON `true/false` are accepted, but `1/0` is recommended;
- `success: null`: means unfinished and cannot remain in final validation;
- `interventions`: use `[]` when there was no operator takeover.

### 4.3 在视频中找关键帧 / Find semantic keyframes

第一段必须从 `frame_index: 0` 开始。播放视频时，只在“语义状态已经改变”的第一帧暂停并新增一个 segment。

The first segment must start at `frame_index: 0`. While playing the video, pause and add a segment only at the first frame where the semantic state has changed.

应该标注的时刻：

Good moments to label:

- 抓取已经成立，而不是夹爪刚开始靠近；
- 第二个物体已经抓住，而不是手正在移动；
- 插入已经完成，而不是刚对准接口；
- 物体已经进入盒子，而不是正在移动到盒子上方；
- 错误已经修正并恢复到新的可执行状态。

- A grasp is established, not when the gripper merely starts approaching;
- The second object is held, not while the hand is still moving;
- Insertion is complete, not when the connector is merely aligned;
- The object is inside the box, not merely above the box;
- An error has been corrected and the robot has entered a new executable state.

不要按固定间隔写 `frame_index: 0, 30, 60...`。一个 episode 可以有很多 segment，也可以只有一个，但每个新增段都必须对应真实语义变化，帧号严格递增。

Do not write labels at fixed intervals such as `0, 30, 60...`. An episode may have many segments or only one; every segment must represent a real semantic change and frame indices must increase strictly.

### 4.4 填写 response：当前子任务 / Fill response: the current subtask

`response` 是当前阶段应该完成的一个可执行子任务 `l_t`，对应 high-level VLM 输出给 low-level VLA 的当前语言目标。

`response` is the executable subtask `l_t` for the current stage, corresponding to the language goal produced by the high-level planner for the low-level policy.

推荐写法：

Recommended style:

```text
Pick up the Ethernet cable with the left gripper.
Pick up the Ethernet adapter with the right gripper.
Insert the Ethernet cable into the adapter.
Place the connected cable and adapter into the box.
```

不要写：

Avoid:

```text
Continue.
Do it.
Looks good.
Move the arm.
```

每段 `response` 只描述当前子任务，不要把完整任务再次复制进去，也不要写结果预测。

Each `response` should describe only the current subtask, not repeat the full task or predict the result.

### 4.5 填写 memory：完整的 m_{t+1} / Fill memory: complete m_{t+1}

`memory` 不是动作日志，也不是只写这一帧新增的 delta。它要写成当前阶段结束后，对未来决策仍有用的完整压缩状态。

`memory` is not an action log and not only a one-line delta. Write the complete compressed state that remains useful for future decisions after the current stage.

高层记忆关系可以理解为：

The high-level memory update can be understood as:

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

JSON 不需要额外填写 `m_t`：上一段的 `memory` 就是下一段的历史 `m_t`。每一段都要让自己的 `memory` 在脱离上一段文字时仍然可读。

The JSON does not need a separate `m_t`: the previous segment's `memory` becomes the next segment's historical `m_t`. Each memory should remain understandable without relying on the previous sentence.

例如：

Example:

```text
Previous memory m_t:
The left gripper holds the Ethernet cable.

New fact:
The right gripper has grasped the Ethernet adapter.

Correct m_{t+1}:
The left gripper holds the Ethernet cable and the right gripper holds the Ethernet adapter. The cable has not been inserted yet.
```

### 4.6 填写 interventions：连续接管区间 / Fill interventions: continuous takeover intervals

人工接管不是只标开始那一帧，而是一个闭区间 `[start_frame, end_frame]`：

An operator takeover is not only the start frame; it is an inclusive interval `[start_frame, end_frame]`:

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
- `end_frame`：错误修正完成、恢复自主执行前的最后一帧；如果没有恢复，就填写 episode 最后一帧；
- `intervention_reason`：简短、具体的英文原因；
- 多次接管写多个不重叠对象；
- 没有接管填写 `[]`；
- 没有“干预量”数值字段。

- `start_frame`: the first frame where the operator effectively changes robot behavior;
- `end_frame`: the last correction frame before autonomous execution resumes, or the final episode frame if it never resumes;
- `intervention_reason`: a short, specific English reason;
- Use multiple non-overlapping objects for multiple takeovers;
- Use `[]` when there was no takeover;
- There is no numeric intervention amount field.

## 5. 部分验证：标完一个 episode 就检查 / Validate after each episode

生成模板后，每完成一个 episode 就可以保存并检查。因为其他 episode 仍然是 `success: null`，阶段性验证需要 `--allow-missing`：

After completing each episode, save and validate it. Since other episodes remain `success: null`, use `--allow-missing` for intermediate validation:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json \
  --allow-missing
```

该模式会跳过 `success: null` 的未完成 episode，但会严格检查已填写的 episode。如果一个 episode 已经填了 `success`，但 `response` 或 `memory` 为空，验证会失败。

This mode skips unfinished `success: null` episodes but strictly validates completed episodes. If an episode has a non-null `success` but an empty `response` or `memory`, validation fails.

## 6. 全部标完后的正式验证 / Final validation

全部 episode 都完成后，去掉 `--allow-missing`：

After all episodes are complete, remove `--allow-missing`:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json
```

验证器会检查：数据集版本、episode 编号、成功标签、英文 ASCII 文本、关键帧单调性、帧号边界、干预区间越界和重叠。

The validator checks the dataset version, episode IDs, success labels, English ASCII text, keyframe ordering, frame bounds, and intervention overlap/bounds.

## 7. 传播到新数据集副本 / Materialize a new dataset copy

正式验证通过后，使用一个全新的输出目录：

After final validation passes, use a new output directory:

```bash
bash scripts/run.sh propagate \
  --input /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json \
  --output /path/to/annotation_work/annotated_lerobot_v21
```

脚本会复制 `meta/`、`data/`、`videos/`，并把关键帧区间传播到每一帧。原始 action、状态、时间戳、帧索引和视频不会被重排或覆盖。

The script copies `meta/`, `data/`, and `videos/`, then propagates keyframe intervals to every frame. Original actions, states, timestamps, frame indices, and videos are not reordered or overwritten.

传播后的字段：

Materialized fields:

| 字段 / Field | 来源 / Source | 含义 / Meaning |
|---|---|---|
| `response` | `segments[].response` | 当前子任务 `l_t` / Current subtask `l_t` |
| `memory` | `segments[].memory` | 当前完整记忆 `m_{t+1}` / Complete current memory `m_{t+1}` |
| `episode_success` | `success` | episode 成功标签 / Episode success label |
| `is_intervention` | 接管区间 / takeover intervals | 当前帧是否接管 / Whether the frame is under takeover |
| `intervention_start` | 区间起点 / interval start | 接管触发点 / Takeover trigger |
| `intervention_reason` | 接管原因 / takeover reason | 错误分析 / Error analysis |

## 8. 传播后验证 / Validate the output

```bash
bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotation_work/annotated_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json
```

它会读取输出 parquet，检查字段是否存在，并检查每个关键帧区间的 `response` 和 `memory` 是否正确传播。

It reads the output parquet files, checks the materialized fields, and verifies `response` and `memory` at each keyframe interval.

## 9. API 是可选的，放在人工流程之后 / Optional API extension comes later

本项目的核心流程不依赖任何 API，人工视频标注可以独立完成。当前仓库不内置 Gemini 或其他 API 客户端，也不提供采样帧数限制的 API 流程。

The core workflow does not depend on any API. Manual video annotation works independently. This repository does not bundle a Gemini or other API client, and it does not define an API workflow that limits the number of sampled frames.

如果将来接入 API，它只能作为预标注或辅助检查：

If an API is added later, it should only provide pre-annotations or review assistance:

1. 输入完整 episode 的观测、总任务和已有历史记忆；
2. 输出与本项目相同格式的 `task_prompt`、`response`、`memory`、`success`、`interventions`；
3. 仍然由人工对照完整视频确认 frame index、语义变化、成功状态和接管区间；
4. API 输出必须先通过本项目的 `validate`，不能直接作为最终训练标签。

1. Feed the complete episode observations, task goal, and historical memory;
2. Produce the same `task_prompt`, `response`, `memory`, `success`, and `interventions` schema;
3. Have a human verify frame indices, semantic changes, success, and takeover intervals against the complete video;
4. Run this project's `validate` before using the output as training labels.

## 常见错误 / Common mistakes

- 把数据集路径写死在脚本或 JSON 中；
- 在采集阶段截断 episode 或限制帧数；
- 把每一帧都写成一个 segment；
- 把 `memory` 写成只有新增内容的 delta；
- 把 intervention 只写成开始帧；
- 在 `task_prompt`、`response`、`memory`、`intervention_reason` 中写中文；
- 使用大写 `TRUE`/`FALSE` 字符串；
- 直接覆盖输入数据集；
- 没有人工复核 API 生成的标签。

- Hard-code dataset paths in scripts or JSON;
- Truncate episodes or limit frames during collection;
- Create one segment for every frame;
- Write only a memory delta;
- Mark only the intervention start frame;
- Write Chinese text in the English annotation fields;
- Use uppercase `TRUE`/`FALSE` strings;
- Overwrite the input dataset;
- Use API-generated labels without human review.

## 示例和详细字段说明 / Examples and field guide

- [`examples/README.md`](examples/README.md)：字段和 MEM 训练流程说明 / field and MEM training guide
- [`examples/annotations.example.json`](examples/annotations.example.json)：干净的通用 JSON 示例 / clean generic JSON example
- [`examples/ethernet_cable_episode.example.json`](examples/ethernet_cable_episode.example.json)：网线任务示例 / Ethernet task example
- `scripts/data_annotation.py`：命令入口 / command entrypoint
- `scripts/data_annotationn/`：模板、验证、传播实现 / template, validation, and propagation implementation
