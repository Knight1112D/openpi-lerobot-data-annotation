# OpenPI LeRobot 数据标注项目

本目录按照 `skills/data_annotationn` skill 建立，用于对 LeRobot v2.1 数据集进行人工稀疏标注、验证和逐帧物化。所有数据集、标注文件和输出目录都必须通过命令行显式传入；脚本没有业务路径默认值。原始数据不会被覆盖，物化结果由 `--output` 指定。

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

用 VSCode 打开 `--output` 指定的文件，按照 skill 规范填写英文的 `task_prompt`、`response`、`memory`、`success` 和可选的 `interventions`。人工只填写语义发生变化的关键帧，第一段必须从 `frame_index: 0` 开始。

填写完成后验证：

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json
```

验证通过后生成新数据集副本：

```bash
bash scripts/run.sh propagate \
  --input /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --output /path/to/annotated_dataset
```

最后检查逐帧字段：

```bash
bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotated_dataset \
  --annotations /path/to/annotations.json
```

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

人工标注和物化数据集建议放在项目目录之外，并通过参数传入；`.gitignore` 会忽略本地生成的 `annotations/*.json` 和 `outputs/`。
