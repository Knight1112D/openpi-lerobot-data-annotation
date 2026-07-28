# Annotation Examples and Field Guide

[Chinese guide](README.zh-CN.md)

The JSON files in this directory contain annotation fields only. Documentation is kept in the README files so it is not mixed into annotation data.

## Files

- `annotations.example.json`: a generic single-episode example;
- `ethernet_cable_episode.example.json`: an Ethernet task with multiple stages and one operator takeover.

## Fields and training flow

### `task_prompt`

The complete task goal `g`. It is written to task metadata and used as the global condition for the high-level planner and low-level policy.

### `success`

An episode-level label: `1` means success and `0` means failure. JSON `true`/`false` are also accepted, but `1`/`0` are recommended. This label is used for episode statistics, recap/value supervision, and failure analysis; it is not a frame-level reward.

### `metadata`

Each completed episode has an episode-level metadata object:

```json
"metadata": {
  "overall_speed": "2000 steps",
  "overall_quality": 4
}
```

- `overall_speed`: computed from the episode length in timesteps and rounded to a 500-step bucket; lengths from 1750 through 2250 become `"2000 steps"`;
- `overall_quality`: human quality score from 1 (lowest) to 5 (highest).

The validator compares `overall_speed` with the actual input episode length, so it should not be guessed manually.

### `segments[].time_seconds`

Enter the timestamp shown by the video player in seconds. The first segment must start at `0.0`; the tool converts seconds to the nearest frame using the dataset `fps`. Add segments at semantic changes such as an established grasp, completed insertion, an object entering the box, or completed recovery. Do not label every fixed interval.

`frame_index` is still accepted for existing annotations. If both `time_seconds` and `frame_index` are present, they must describe the same frame.

### `segments[].response`

The current executable subtask `l_t` for the segment. It is the language target for the current stage.

Example:

```text
Insert the Ethernet cable into the adapter.
```

### `segments[].memory_update`

Write only the new useful memory fact for the current stage. During propagation, the tool concatenates the previous complete memory and this update into the materialized `memory` field.

The update can be represented as:

```text
m_{t+1} = Planner(o_t, g, l_0...l_t, success_history, m_t)
```

The next segment uses the previous materialized `memory` as historical memory `m_t`, so no separate `m_t` field is needed in the JSON. The first segment's `memory_update` describes the initial state.

If a new state invalidates an old fact, use the optional full `memory` field for that segment to replace the accumulated text.

### `segments[].mistake`

Set `mistake` to `1` when the robot made a mistake during the action segment, such as failing to grasp an object or executing the wrong subtask; otherwise set it to `0`. It is propagated to every frame until the next action segment and is separate from `interventions`, which record operator takeovers.

### `interventions`

Record continuous operator-takeover intervals using the seconds shown by the video player:

- `start_time_seconds`: the first timestamp where the operator effectively changes robot behavior;
- `end_time_seconds`: the last correction timestamp before autonomous execution resumes, or the final episode timestamp if recovery never occurs;
- `intervention_reason`: a short English reason;
- use `[]` when there was no takeover;
- use multiple non-overlapping objects for multiple intervals.

This is not a single-frame label and has no numeric intervention amount. The propagation script creates `is_intervention` and `intervention_start` automatically.

## Annotating one episode at a time

Complete one episode and then continue with the next episode in the same JSON file. Use `--allow-missing` for intermediate validation while other episodes still have `success: null`. Remove it for final validation after every episode is complete.

```bash
bash scripts/run.sh validate \
  --dataset-root /path/to/input_dataset \
  --annotations /path/to/annotations.json \
  --allow-missing
```
