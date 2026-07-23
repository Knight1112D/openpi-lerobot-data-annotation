# OpenPI LeRobot Data Annotation

## 中文

这是一个独立的 LeRobot v2.1 数据标注项目，支持：

- 生成 VSCode 可编辑的稀疏标注模板；
- 验证英文任务、子任务、MEM 和 DAgGER 接管区间；
- 将关键帧标签传播到每一帧，并生成新的数据集副本。

所有数据路径都必须显式传参，项目没有业务路径默认值。原始数据不会被覆盖。

```bash
bash scripts/bootstrap.sh
bash scripts/run.sh template \
  --dataset-root /path/to/input_dataset \
  --output /path/to/annotations.json

bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json

bash scripts/run.sh propagate \
  --input /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --output /path/to/annotated_dataset

bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotated_dataset \
  --annotations /path/to/annotations.json
```

展示格式请查看 [`examples/annotations.example.json`](examples/annotations.example.json)。该文件仅用于说明格式，不能直接用于生产验证或训练。

### 字段语义

- `success`：最终标注时填写 `1` 或 `0`；也接受 JSON 的 `true`/`false`，脚本会规范化为 `1`/`0`。`null` 只表示模板尚未填写，不能通过最终验证；`TRUE`/`FALSE` 不是合法 JSON 布尔值。
- `response`：当前关键帧开始执行的子任务 `l_t`，使用可执行的英文短句。
- `memory`：当前阶段对应的完整压缩记忆 `m_{t+1}`，不是只记录新增差异的 delta。下一阶段将上一段 `memory` 作为历史记忆 `m_t`，再结合当前观测生成新的完整记忆。
- `segments`：可以有任意多个关键帧段；每段从语义状态真正改变的第一帧开始，`frame_index` 必须严格递增，第一段必须是 `0`。
- `interventions`：记录操作者实际改变机器人行为的连续区间 `[start_frame, end_frame]`。`start_frame` 是第一帧有效修正，`end_frame` 是最后一帧修正；不需要逐帧写记录，也没有“干预量”数值字段，只需填写区间和英文原因。

可以按 episode 逐条完成同一个 JSON 文件。尚未覆盖全部 episode 时，阶段性检查加 `--allow-missing`；全部 episode 完成后，正式验证和传播不要加该参数。

## English

This standalone project supports LeRobot v2.1 annotation workflows:

- Generate VSCode-editable sparse annotation templates.
- Validate English task, subtask, MEM, and DAgGER intervention labels.
- Propagate keyframe labels to every frame and create a new dataset copy.

All dataset, annotation, and output paths are required command-line arguments. No business-path defaults are used, and the raw dataset is never overwritten.

```bash
bash scripts/bootstrap.sh
bash scripts/run.sh template \
  --dataset-root /path/to/input_dataset \
  --output /path/to/annotations.json

bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json

bash scripts/run.sh propagate \
  --input /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --output /path/to/annotated_dataset

bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotated_dataset \
  --annotations /path/to/annotations.json
```

See [`examples/annotations.example.json`](examples/annotations.example.json) for a clearly labeled format demonstration. It must not be used directly for production validation or training.

### Field semantics

- `success`: use `1` or `0` in the final annotation. JSON `true`/`false` are also accepted and normalized to `1`/`0`. `null` means the template is unfinished and will fail final validation; `TRUE`/`FALSE` are not valid JSON booleans.
- `response`: the executable subtask `l_t` that starts at the current keyframe.
- `memory`: the complete compressed memory `m_{t+1}` for the current stage, not only a delta. The previous segment's `memory` becomes historical memory `m_t` for the next planner step.
- `segments`: any number of semantic keyframe segments is allowed. Frame indices must be strictly increasing, and the first segment must start at `0`.
- `interventions`: one continuous operator-takeover interval `[start_frame, end_frame]`. Mark the first effective correction and the last correction; do not create one record per frame, and do not provide a numeric intervention amount.

You may annotate one episode at a time in the same JSON file. While the bundle is incomplete, add `--allow-missing` for intermediate checks; omit it for final validation and propagation after all episodes are complete.
