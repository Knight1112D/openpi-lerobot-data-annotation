# 标注示例说明 / Annotation Examples Guide

这里的 JSON 文件只保留实际标注字段；说明统一放在本 README 中，避免把注释字段混入训练数据。

The JSON files contain only annotation fields. Explanations are kept in this README so documentation fields are not mixed into training data.

## 文件说明 / Files

- `annotations.example.json`：通用的单 episode 示例。
- `ethernet_cable_episode.example.json`：网线任务的单 episode 示例，展示多个子任务阶段和一次人工接管。

## 字段与训练流程 / Fields and training flow

### `task_prompt`

完整任务目标 `g`，例如“把网线插入适配器并放入盒子”。它会写入 LeRobot 的任务元数据，并作为 high-level VLM 和 low-level VLA 的全局任务条件。

The full task goal `g`. It is written to LeRobot task metadata and used as the global condition for both the high-level VLM and low-level VLA.

### `success`

episode 级标签：`1` 表示成功，`0` 表示失败。也接受 JSON 的 `true`/`false`，但推荐使用 `1`/`0`。它用于 episode 成功统计、recap/value 监督或失败分析，不是逐帧 reward。

An episode-level label: `1` means success and `0` means failure. JSON `true`/`false` are also accepted, but `1`/`0` are recommended. It is used for episode statistics, recap/value supervision, and failure analysis, not as a per-frame reward.

### `segments[].frame_index`

语义阶段发生变化后的第一帧。第一段必须从 `0` 开始，后续帧号严格递增。可以有很多段，但只在抓取成立、插入完成、物体进入盒子等语义状态改变时增加，不要每隔固定帧数重复。

The first frame after a semantic stage changes. The first segment must start at `0`, and later frame indices must be strictly increasing. Add as many segments as needed, but only at semantic changes such as a grasp being established, insertion being completed, or an object entering the box.

### `segments[].response`

当前子任务 `l_t`，是 high-level VLM 在当前阶段输出的可执行语言目标，并作为 low-level VLA 的当前 subtask 条件。例如：

```text
Insert the Ethernet cable into the adapter.
```

The current executable subtask `l_t`, produced by the high-level VLM and passed to the low-level VLA as the current language condition.

### `segments[].memory`

填写当前阶段的完整压缩记忆 `m_{t+1}`，不要只填写新增 delta。它应保留未来决策需要的对象状态、已完成步骤、未完成目标和必要的错误恢复状态。

高层更新关系可以理解为：

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

下一阶段使用上一段的 `memory` 作为历史记忆 `m_t`，所以 JSON 不需要额外增加 `m_t` 字段。第一段的历史记忆可以视为空或初始状态。

Write the complete compressed memory `m_{t+1}` for the current stage, not only a new-information delta. Keep object state, completed steps, unfinished goals, and relevant recovery state that may affect future decisions.

The next stage uses the previous segment's `memory` as historical memory `m_t`, so no separate `m_t` field is needed in the JSON. For the first segment, historical memory can be empty or an initial state.

### `interventions`

记录操作者实际改变机器人行为的连续区间，区间是闭区间 `[start_frame, end_frame]`：

- `start_frame`：第一帧有效修正，不是操作者刚碰到控制器的帧；
- `end_frame`：错误修正完成、恢复自主执行的最后一帧；如果没有恢复，就取 episode 最后一帧；
- `intervention_reason`：简短英文原因；
- 没有接管时填写空数组 `[]`。

这不是单帧标记，也没有数值形式的“干预量”。传播脚本会自动生成 `is_intervention` 和 `intervention_start`。默认将这些字段作为行为来源分析、DAgGER/KI 条件或统计信息，不要未经确认混入 action loss。

Record continuous intervals where the operator actually changes robot behavior. The interval is inclusive `[start_frame, end_frame]`:

- `start_frame`: first effective correction, not the frame when the operator merely touches the controller;
- `end_frame`: last correction before autonomous execution resumes, or the last episode frame if recovery never occurs;
- `intervention_reason`: a short English reason;
- use an empty array `[]` when there is no takeover.

This is not a single-frame label and has no numeric intervention amount. The propagation script creates `is_intervention` and `intervention_start` automatically. By default, use these fields for behavior-source analysis, DAgGER/KI conditioning, or statistics rather than mixing them into action loss.

## 逐个 episode 标注 / Annotating one episode at a time

可以先填写一个 episode，再继续填写同一个 JSON 中的下一个 episode。未完成全部 episode 时使用：

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --allow-missing
```

全部完成后，去掉 `--allow-missing` 做正式验证，再执行传播。

You can complete one episode and then continue with the next episode in the same JSON file. Use `--allow-missing` for intermediate validation, remove it for final validation, and propagate only after all episodes are complete.
