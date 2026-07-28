# LeRobot v2.1 人工语义标注工具

[English README](README.md)

本目录按照 `skills/data_annotationn` skill 建立，用于对 LeRobot v2.1 数据集进行人工稀疏标注、验证和逐帧物化。所有数据集、标注文件和输出目录都必须通过命令行显式传入；脚本没有业务路径默认值。原始数据不会被覆盖，物化结果由 `--output` 指定。

## 字段语义

- `success`：最终填写 `1` 或 `0`；也接受 JSON 的 `true`/`false`，脚本会转换成 `1`/`0`。模板中的 `null` 只表示尚未填写，不能通过最终验证；大写 `TRUE`/`FALSE` 不是合法 JSON 布尔值。
- `metadata.overall_speed`：根据 episode 的实际 timestep 长度按 500 steps 分桶自动计算，例如 1750 到 2250 steps（含边界）标记为 `"2000 steps"`，不能手工写成与真实长度不符的值。
- `metadata.overall_quality`：人工填写的 episode 质量分数，范围为 1–5，5 代表质量最高。
- `response`：当前关键帧开始执行的子任务 `l_t`，使用可执行英文短句。
- `memory_update`：当前阶段新增的记忆事实；传播时会自动和前面内容拼接成完整 `memory`。
- `segments[].mistake`：当前 action segment 是否发生错误；发生填写 `1`，没有填写 `0`。传播后会成为逐帧 `mistake` 字段。
- `segments`：可以有多个关键帧段；手工填写 `time_seconds`，传播时按 `fps` 自动转换成 `frame_index`。
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

用 VSCode 打开 `--output` 指定的文件，填写英文的 `task_prompt`、`response`、`memory_update`、`success`、`metadata.overall_quality`、`segments[].mistake` 和可选的 `interventions`。`metadata.overall_speed` 由模板根据数据集长度生成并由校验器复核。人工只填写语义发生变化的关键帧，第一段必须从 `time_seconds: 0.0` 开始。视频播放器只有秒数时，直接把秒数写入 `time_seconds`，脚本会根据数据集 `fps` 自动转换帧号。

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
- `validate`：`--dataset-root`、`--annotations`
- `propagate`：`--input`、`--annotations`、`--output`
- `validate-output`：`--dataset-root`、`--annotations`

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
