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
