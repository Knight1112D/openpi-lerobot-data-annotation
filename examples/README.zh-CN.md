# 标注示例和字段说明

[English guide](README.md)

本目录中的 JSON 只包含实际标注字段，说明放在 README 中，不把说明字段混入标注数据。

## 文件

- `annotations.example.json`：通用的单 episode 示例；
- `ethernet_cable_episode.example.json`：包含多个阶段和一次人工接管的网线任务示例。

## 字段和训练流程

### `task_prompt`

完整任务目标 `g`。它会写入任务元数据，并作为 high-level planner 和 low-level policy 的全局条件。

### `success`

episode 级标签：`1` 表示成功，`0` 表示失败。也接受 JSON 的 `true`/`false`，但推荐使用 `1`/`0`。它用于 episode 统计、recap/value 监督和失败分析，不是逐帧 reward。

### `segments[].time_seconds`

填写视频播放器显示的秒数。第一段必须从 `0.0` 开始，脚本会根据数据集 `fps` 自动转换成最近的 `frame_index`。应在抓取成立、插入完成、物体进入盒子或错误恢复完成等语义变化时增加段，不要按固定间隔重复。

已有标注仍可使用 `frame_index`。如果同时填写 `time_seconds` 和 `frame_index`，两者必须对应同一帧。

### `segments[].response`

当前阶段的可执行子任务 `l_t`，即当前阶段的语言目标。

示例：

```text
Insert the Ethernet cable into the adapter.
```

### `segments[].memory_update`

只填写当前阶段新增的有效记忆事实。传播时脚本会把前面已经拼接好的完整记忆和当前更新拼接成最终的 `memory` 字段。

高层更新关系可以表示为：

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

下一段使用上一段生成的完整 `memory` 作为历史记忆 `m_t`，因此 JSON 不需要单独的 `m_t` 字段。第一段的 `memory_update` 填写初始状态。

如果新状态使旧事实失效，可以在该段使用可选的完整 `memory` 字段覆盖前面拼接的内容。

### `interventions`

使用视频播放器显示的秒数记录人工接管区间：

- `start_time_seconds`：操作者第一次有效改变机器人行为的时间；
- `end_time_seconds`：恢复自主执行前的最后时间；如果没有恢复，就填写 episode 最后时间；
- `intervention_reason`：简短英文原因；
- 没有接管时填写 `[]`；
- 多次接管填写多个不重叠对象。

它不是单帧标签，也没有数值形式的干预量。传播脚本会自动生成 `is_intervention` 和 `intervention_start`。

## 逐个 episode 标注

可以在同一个 JSON 中逐个完成 episode。其他 episode 仍然是 `success: null` 时，阶段性验证加 `--allow-missing`；全部完成后去掉该参数。

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --allow-missing
```
