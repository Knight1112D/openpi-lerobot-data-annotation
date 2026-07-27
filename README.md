# LeRobot v2.1 Manual Annotation

[Chinese README](README.zh-CN.md)

This project provides a manual-first workflow for annotating LeRobot v2.1 robot datasets. You inspect complete episode videos, mark semantic keyframes, write English task/subtask/MEM labels and operator takeover intervals, validate the JSON, and materialize the sparse labels into a new dataset copy.

## What this project provides

- A VSCode-editable annotation template;
- Episode-level task and success labels;
- Keyframe-level subtask and memory labels;
- Operator takeover interval labels;
- Validation for text, frame indices, episode coverage, and interval bounds;
- Propagation of sparse labels into frame-level parquet fields.

The normal workflow is manual video annotation. Every dataset, annotation, and output path is passed explicitly to the command line.

## 1. Install

Requirements: Python 3.10+, `uv`, and a Linux/macOS shell.

The environment is created inside this project's `.venv` directory.

```bash
cd /path/to/data_annotation_project
bash scripts/bootstrap.sh
bash scripts/run.sh --help
```

## 2. Organize the working directory

Use any local directory layout. Replace the paths in the commands with your actual paths.

```text
workspace/
├── data_annotation_project/
├── datasets/
│   └── raw_lerobot_v21/
└── annotation_work/
    ├── annotations.json
    └── annotated_dataset/
```

The input dataset must be LeRobot v2.1 and contain at least:

```text
raw_lerobot_v21/
├── meta/info.json
├── meta/episodes.jsonl
├── meta/tasks.jsonl
├── meta/episodes_stats.jsonl
├── data/chunk-*/episode_*.parquet
└── videos/chunk-*/<video_key>/episode_*.mp4
```

Check that:

- `meta/info.json` has `codebase_version: "v2.1"`;
- `fps` matches the recorded videos;
- episode indices match across metadata, parquet files, and videos.

## 3. Generate a template

```bash
bash scripts/run.sh template \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --output /path/to/annotation_work/annotations.json
```

The template contains one object for every episode. You can complete one episode at a time and leave unfinished episodes as `success: null`.

## 4. Annotate manually against the complete video

Use a frame-accurate video player or a VSCode video extension. The project does not require an API for manual annotation.

### 4.1 Find the episode video

For `episode_index: 0`:

1. Find episode 0 in `meta/episodes.jsonl`;
2. Open `videos/chunk-*/<video_key>/episode_000000.mp4`;
3. Start with the main camera and use wrist cameras when necessary;
4. Record the timestamp shown by the player in seconds;
5. Enter `time_seconds` in the JSON. The tool converts it to the nearest `frame_index` using `meta/info.json` `fps`.

Review the complete episode. Do not use a fixed sampling schedule such as every 30 frames.

### 4.2 Fill episode-level fields

```json
{
  "episode_index": 0,
  "task_prompt": "Pick up the Ethernet cable with the left gripper and insert it into the adapter.",
  "success": 1,
  "segments": [],
  "interventions": []
}
```

- `episode_index`: must match the dataset;
- `task_prompt`: the complete task goal in clear English;
- `success`: `1` for success and `0` for failure; JSON `true`/`false` are accepted, but `1`/`0` are recommended;
- `success: null`: unfinished and invalid for final validation;
- `interventions`: use `[]` when there was no operator takeover.

### 4.3 Mark semantic keyframes

The first segment must start at `time_seconds: 0.0`. Add a segment only at the first time where the semantic state has actually changed.

Use seconds directly:

```json
{
  "time_seconds": 18.0,
  "response": "Insert the Ethernet cable into the adapter.",
  "memory_update": "The right gripper now holds the adapter. The cable has not been inserted yet."
}
```

The converter calculates `frame_index = round(time_seconds * fps)`. You may still provide `frame_index` directly, but if both fields are present they must agree.

Good keyframes include:

- a grasp has become established;
- the second object is held;
- insertion has completed;
- an object has entered the box;
- an error has been corrected and the robot has entered a new executable state.

Do not label preparation frames, hand movement without a state change, or every fixed time interval. Converted frame indices must be strictly increasing.

### 4.4 Fill `response`: current subtask `l_t`

`response` is the current executable subtask for the segment. It is the language target for the current stage.

Recommended examples:

```text
Pick up the Ethernet cable with the left gripper.
Pick up the Ethernet adapter with the right gripper.
Insert the Ethernet cable into the adapter.
Place the connected cable and adapter into the box.
```

Avoid vague text such as `Continue`, `Do it`, `Looks good`, or `Move the arm`.

Each `response` should describe only the current subtask, not repeat the entire task or predict the result.

### 4.5 Fill `memory_update`: write only the new memory fact

For manual annotation, write only the new useful memory fact in `memory_update`. During propagation, the tool concatenates the previous complete memory and the new update into the materialized `memory` field.

The high-level update can be represented as:

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

The JSON does not need a separate `m_t` field. The previous segment's materialized `memory` becomes the next segment's historical `m_t`. The first segment's `memory_update` should describe the initial state.

Each update should describe a new future-useful object state, completed step, unfinished goal, or recovery fact. If a new state invalidates an old fact, use the optional full `memory` field for that segment to replace the accumulated text.

Example:

```text
Previous m_t:
The left gripper holds the Ethernet cable.

New observation:
The right gripper has grasped the Ethernet adapter.

Manual memory_update:
The right gripper now holds the Ethernet adapter. The cable has not been inserted yet.

Materialized m_{t+1}:
The left gripper holds the Ethernet cable. The right gripper now holds the Ethernet adapter. The cable has not been inserted yet.
```

### 4.6 Fill `interventions`

An operator takeover is an interval entered in seconds, not only a start-time flag:

```json
"interventions": [
  {
    "start_time_seconds": 25.333,
    "end_time_seconds": 27.333,
    "intervention_reason": "The cable missed the adapter opening, so the operator corrected the alignment."
  }
]
```

- `start_time_seconds`: the first timestamp where the operator effectively changes robot behavior;
- `end_time_seconds`: the last correction timestamp before autonomous execution resumes, or the final episode timestamp if it never resumes;
- `intervention_reason`: a short, specific English reason;
- use multiple non-overlapping objects for multiple takeovers;
- use `[]` when there was no takeover;
- no numeric intervention amount is required.

## 5. Validate after each episode

While other episodes still contain `success: null`, use `--allow-missing`:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json \
  --allow-missing
```

This skips unfinished episodes and validates completed ones. If an episode has a non-null `success` but an empty `response` or `memory_update`, validation fails.

## 6. Run final validation

After every episode is complete, remove `--allow-missing`:

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json
```

The validator checks the dataset version, episode IDs, success labels, English ASCII text, keyframe ordering, frame bounds, and intervention overlap/bounds.

## 7. Generate the final LeRobot dataset

After every episode has been annotated and the final `validate` command passes, run the following command. Its `--output` directory is the new final LeRobot dataset:

```bash
bash scripts/run.sh propagate \
  --input /path/to/datasets/raw_lerobot_v21 \
  --annotations /path/to/annotation_work/annotations.json \
  --output /path/to/annotation_work/annotated_dataset
```

The script copies `meta/`, `data/`, and `videos/`, then propagates keyframe labels to every frame. This is the command that creates the final annotated dataset; it does not modify the input dataset.

Materialized fields:

| Field | Source | Meaning |
|---|---|---|
| `response` | `segments[].response` | Current subtask `l_t` |
| `memory` | Accumulated `memory_update` values | Complete current memory `m_{t+1}` |
| `episode_success` | `success` | Episode success label |
| `is_intervention` | Intervention intervals | Whether the frame is under takeover |
| `intervention_start` | Interval start | Takeover trigger frame |
| `intervention_reason` | Intervention reason | Error analysis |

## 8. Validate the final dataset

```bash
bash scripts/run.sh validate-output \
  --dataset-root /path/to/annotation_work/annotated_dataset \
  --annotations /path/to/annotation_work/annotations.json
```

Run this after `propagate` to confirm that the final LeRobot dataset contains the materialized parquet fields and that `response` and `memory` match the annotated keyframe intervals.

## 9. Optional VLM-assisted annotation

Manual video annotation is the primary workflow. A VLM or API is optional and is not required for this project.

If a VLM is used to draft labels, it should produce the same JSON schema. A human must still verify `time_seconds`, semantic changes, English text, success, and intervention intervals against the complete video. Save the reviewed JSON, then run the same final `validate`, `propagate`, and `validate-output` commands above.

## Examples

- [`README.zh-CN.md`](README.zh-CN.md): Chinese README;
- [`examples/README.md`](examples/README.md): English field guide;
- [`examples/README.zh-CN.md`](examples/README.zh-CN.md): Chinese field guide;
- [`examples/annotations.example.json`](examples/annotations.example.json): generic JSON example;
- [`examples/ethernet_cable_episode.example.json`](examples/ethernet_cable_episode.example.json): Ethernet task example.
