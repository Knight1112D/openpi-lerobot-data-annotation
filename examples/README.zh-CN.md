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

### `metadata`

每个完成的 episode 都要有一组 episode-level metadata：

```json
"metadata": {
  "overall_speed": "2000 steps",
  "overall_quality": 4
}
```

- `overall_speed`：根据真实 episode 长度按 500 steps 分桶自动生成；人工标注时可以省略或填写 `null`，按照文中的区间，1750 到 2250 steps 都是 `"2000 steps"`；
- `overall_quality`：人工质量分数，范围 1–5，5 代表最高质量。

校验器会根据输入数据集的实际长度计算 `overall_speed`，传播后的输出会写入计算结果。

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

填写当前阶段对应的 memory。传播时脚本只把当前段的值写入当前段帧，不会把所有历史内容拼接成全局 `memory`；当前段没有 memory 时保持为空。

高层更新关系可以表示为：

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

下一段可以使用上一段的当前 `memory` 作为历史记忆 `m_t`，因此 JSON 不需要单独的 `m_t` 字段。第一段的 `memory_update` 填写初始状态。

如果新状态使旧事实失效，可以在该段使用可选的完整 `memory` 字段覆盖前面拼接的内容。

### `segments[].mistake`

如果当前 action segment 中机器人犯了错误（例如抓取失败或执行了错误子任务），填写 `1`；没有错误填写 `0`。传播后该标签会覆盖当前 segment 的所有帧，并且它和人工接管区间是两个独立标签。

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
