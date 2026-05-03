# User Debate Renderer

This document describes the reusable Remotion workflow for turning a debate transcript JSON plus an audio file into a rendered MP4.

The renderer is implemented in:

- `pipeline/video/remotion/render-user-debate.cjs`
- `pipeline/video/remotion/src/UserDebate/DebateVideo.tsx`
- `pipeline/video/remotion/src/UserDebate/index.tsx`

## What it does

The renderer takes a debate transcript JSON file and an audio file, then produces a 1920x1080, 30fps MP4 using Remotion.

The video includes:

- a title and subtitle
- a live clock and total duration display
- one of three reusable layouts: `dual`, `podcast`, or `mindmap`
- the current caption segment on screen
- speaker highlighting based on transcript timing
- turn progress and whole-debate progress bars
- the original debate audio embedded in the rendered MP4

## One-command usage

From the repository root:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json"
```

That is the direct renderer command.

If you are already inside `pipeline/video/remotion`, you can also run:

```powershell
node render-user-debate.cjs --json "G:\path\to\debate.json"
```

## Real example

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json"
```

Preview-only render:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --max-seconds 60
```

Custom output path:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --out "G:\Videos\my-debate.mp4"
```

Podcast layout:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --layout podcast
```

Mindmap layout with an explicit video plan:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --layout mindmap --plan "G:\path\to\debate.video-plan.json"
```

Higher CPU parallelism:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --concurrency 75%
```

Try GPU-backed Chromium rendering:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --gl angle
```

Keep the temporary bundle and staged audio for debugging:

```powershell
node pipeline\video\remotion\render-user-debate.cjs --json "G:\path\to\debate.json" --keep-bundle --keep-staged-audio
```

## Command-line options

`--json "<path>"`

- Required.
- Path to the transcript JSON.

`--audio "<path>"`

- Optional.
- Explicit path to the audio file to use.
- Use this if you do not want the renderer to auto-detect the audio.

`--out "<path>"`

- Optional.
- Full output path for the rendered MP4.
- If omitted, the MP4 is written to `output/video/<derived-name>.mp4`.

`--title "<text>"`

- Optional.
- Overrides the automatically derived video title.

`--subtitle "<text>"`

- Optional.
- Overrides the automatically derived subtitle.

`--max-seconds <number>`

- Optional.
- Renders only the first N seconds.
- Useful for testing visuals and audio sync before doing a long export.

`--output-name "<text>"`

- Optional.
- Overrides the derived output base name.
- This affects the staged audio filename, output filename, and manifest filename.

`--layout <dual|podcast|mindmap>`

- Optional.
- Chooses the reusable visual layout.
- Defaults to `dual`.
- If you do not explicitly set `--out` or `--output-name`, non-default layouts automatically append their name to the output stem so you can compare renders more easily.

`--plan "<path>"`

- Optional.
- Path to a richer `video-plan.json` file.
- This is mainly useful for the `mindmap` layout and future documentary-style expansions.
- If omitted, the renderer looks for:
  - an embedded `videoPlan` object inside the transcript JSON
  - an embedded `video_plan` object inside the transcript JSON
  - a sibling `<stem>.video-plan.json`
  - a sibling `<stem>.plan.json`
  - a sibling `video-plan.json`
- If no plan is found, the renderer falls back to timeline-derived structure built from `turns` and `segments`.

`--help`

- Shows the built-in CLI help text.

`--concurrency <value>`

- Optional.
- Controls how many render workers Remotion should use.
- Accepts either:
  - a number, for example `12`
  - a percentage of CPU threads, for example `75%`
- If omitted, Remotion chooses automatically.

`--gl <renderer>`

- Optional.
- Controls Chromium's OpenGL backend during rendering.
- Accepted values:
  - `swangle`
  - `angle`
  - `egl`
  - `swiftshader`
  - `vulkan`
  - `angle-egl`
- This is primarily useful for WebGL, Skia, shader-heavy, blur-heavy, or transform-heavy compositions.
- For this debate template, gains may be limited because the scene is mostly text and layout.

`--keep-bundle`

- Optional.
- Keeps the temporary Remotion bundle directory after the render finishes.
- Useful when you want to inspect the generated bundle while debugging.
- By default, the CLI removes that temporary bundle after the render.

`--keep-staged-audio`

- Optional.
- Keeps the staged audio file in `packages/example/public/user-debate/input/` after the render finishes.
- Useful if you want to inspect or reuse the staged static asset manually.
- By default, the CLI removes the staged audio after the render.

## Input requirements

The renderer expects a debate-style JSON with `turns`, timing information, and ideally `segments`.

Minimum practical raw JSON shape:

```json
{
  "duration": 120.5,
  "turns": [
    {
      "turn": 1,
      "speaker": "host",
      "start": 0,
      "end": 12.5,
      "content": "Welcome to the debate."
    },
    {
      "turn": 2,
      "speaker": "positive",
      "start": 13.0,
      "end": 35.2,
      "content": "Affirmative opening statement."
    }
  ],
  "segments": [
    {
      "turn": 1,
      "speaker": "host",
      "start": 0,
      "end": 4.8,
      "text": "Welcome to the debate.",
      "accepted": true
    }
  ]
}
```

### Required raw fields

For reliable rendering, the raw JSON should contain:

- `turns`
- `turns[].speaker`
- `turns[].start`
- `turns[].end`
- `turns[].content`

### Recommended raw fields

- `duration`
- `turns[].turn`
- `turns[].duration`
- `segments`
- `segments[].turn`
- `segments[].speaker`
- `segments[].start`
- `segments[].end`
- `segments[].text`
- `segments[].accepted`

### If `segments` are missing

The CLI will fall back to generating renderable segments from the `turns` array.

That means:

- the video can still render
- captions will be less granular
- each turn becomes one large caption block

## Audio resolution behavior

The renderer uses exactly one audio file for the output MP4.

Resolution order:

1. `--audio`
2. the JSON `audio` field
3. a sibling audio file with the same stem as the JSON, for example:
   `debate.json` -> `debate.wav`

Supported auto-detected sibling extensions:

- `.wav`
- `.mp3`
- `.m4a`
- `.aac`
- `.flac`

If no audio file can be found, the render fails with an explicit error.

## How audio gets into the video

The renderer does not merely keep audio as metadata. It is actually loaded and rendered into the final MP4.

Flow:

1. The CLI resolves the source audio path.
2. The audio file is staged into `packages/example/public/user-debate/input/`.
3. The composition receives that staged file path as `audioFile`.
4. The Remotion composition loads it using `staticFile(...)`.
5. The final MP4 contains an AAC audio stream.

Staging is done using:

- a hard link when possible
- a file copy if hard-linking is not possible

This is useful for large WAV files because hard-linking avoids duplicating the whole file on disk when the filesystem allows it.

## Layouts

`dual`

- Best current default for long debates.
- Renders a left/right debate layout with active-speaker highlighting.
- Works fully from the existing transcript JSON plus audio.

`podcast`

- Renders large speaker orbs, live waveform bars, and subtitle focus.
- Works from the existing transcript JSON plus audio.
- The waveform styling is transcript-driven so it stays stable even on very long debate WAV files.

`mindmap`

- Renders rolling argument cards for the left and right side, plus a central topic/evidence area.
- Works now from timeline-derived fallback structure.
- Becomes substantially better when you provide a `video-plan.json` with claims, evidence, chapters, and shots.

## Video Plan File

The richer `video-plan.json` is not required for basic rendering, but it is the recommended extension point for smarter layouts.

Starter example:

- `packages/example/video-plan.example.json`

Primary use cases:

- explicit speaker metadata such as side, display name, and avatar label
- stable chapter boundaries
- semantic claims and rebuttals for the mindmap layout
- evidence cards tied to specific claims
- future documentary/editorial shot planning

Recommended top-level structure:

```json
{
  "cast": [],
  "chapters": [],
  "claims": [],
  "evidence": [],
  "assets": [],
  "shots": []
}
```

### `cast[]`

Use this to define speaker presentation.

```json
{
  "id": "positive",
  "displayName": "正方",
  "role": "debater",
  "side": "left",
  "avatarLabel": "正方",
  "accent": "#26E0C8"
}
```

### `chapters[]`

Use this to control phase labels such as opening, clash, and closing.

```json
{
  "id": "opening",
  "label": "开场立论",
  "start": 0,
  "end": 1200
}
```

### `claims[]`

This is the key addition for information-dense layouts.

```json
{
  "id": "claim-positive-1",
  "speaker": "positive",
  "turn": 2,
  "start": 170.34,
  "end": 377.07,
  "summary": "女性身体自主权是更高位阶的现实权利。",
  "type": "claim",
  "topic": "权利位阶",
  "evidenceIds": ["evidence-positive-1"],
  "targets": []
}
```

### `evidence[]`

These power evidence ribbons or support cards.

```json
{
  "id": "evidence-positive-1",
  "claimId": "claim-positive-1",
  "start": 237.8,
  "end": 287.2,
  "label": "高危妊娠例子",
  "summary": "正方用高风险妊娠举例，强调载体的安全与意愿是生命延续的前提。",
  "kind": "example"
}
```

### `assets[]`

The current debate renderer does not yet fully cut to documentary assets, but the schema already supports attaching future image/video/chart/document IDs to evidence and shots.

### `shots[]`

These are optional editorial hints for richer layouts and future documentary-style work.

```json
{
  "id": "shot-claim-map",
  "start": 377.67,
  "end": 608.85,
  "layout": "mindmap",
  "focusSpeaker": "negative",
  "captionSource": "claim",
  "showClaimIds": ["claim-positive-1", "claim-negative-1"],
  "showEvidenceIds": ["evidence-negative-1"],
  "note": "攻防段可切到论点图谱"
}
```

## Outputs

By default, the renderer creates:

- `packages/example/out/<name>.mp4`
- `packages/example/out/<name>.input.json`

The `.input.json` file is a render manifest that records:

- the source JSON path
- the resolved source audio path
- the selected layout
- the resolved video-plan path, if any
- the video-plan source mode
- the staged audio path
- whether staging used a hard link or copy

## Temp files and cleanup

This renderer now cleans up its own one-shot temporary artifacts after a normal run.

Removed by default after rendering:

- the temporary Remotion bundle directory created under `%TEMP%`
- the staged audio file created in `packages/example/public/user-debate/input/`

Usually cleaned by Remotion itself on normal exit:

- frame working directories such as `%TEMP%\react-motion-render*`
- temporary Chromium profiles such as `%TEMP%\puppeteer_dev_chrome_profile-*`

Retained by design:

- the browser download cache in `node_modules/.remotion`
- your output MP4 and `.input.json` manifest

Notes:

- If the process is interrupted or crashes, some temp directories may still remain.
- `%TEMP%` and `%TMP%` still determine where Remotion creates temporary working directories while the render is running.
- Use `--keep-bundle` or `--keep-staged-audio` if you want to retain those intermediate files for debugging.
- the final `inputProps` used for rendering

This is helpful for:

- debugging
- reproducibility
- checking exactly which title, subtitle, duration, and audio file were used

## Derived title, subtitle, and output name

If you do not pass overrides:

### Title

The title is derived from the JSON filename.

Behavior:

- if the filename contains Chinese text, the longest Chinese segment is preferred
- otherwise, the filename stem is cleaned up into a readable title

### Subtitle

The subtitle is derived from:

- unique speakers in the turn list
- number of turns
- total duration

Example:

```text
主持 / 正方 / 反方 · 22 turns · 2h 6m 35s
```

### Output name

The output base name is derived from:

- `--output-name` if provided
- otherwise the JSON filename stem
- otherwise sanitized to remove invalid filename characters

## Visual behavior

The Remotion scene is now a transcript-driven debate renderer with multiple reusable templates.

It currently renders:

- full-HD landscape video: 1920x1080
- frame rate: 30fps
- layout switching via `--layout`
- support for `host`, `positive`, and `negative`
- fallback colors and labels for unknown speakers
- timeline-derived fallback structure when no video plan exists
- optional semantic structure when a `video-plan.json` is supplied

Known built-in speaker themes:

- `host`
- `positive`
- `negative`

Any other speaker id still renders. It just gets a fallback color theme and a title-cased label.

## Render duration behavior

The composition duration is dynamic.

It is calculated from:

- `renderDurationInSeconds` if provided via `--max-seconds`
- otherwise the normalized timeline duration

The render duration is clamped so it never exceeds the full debate duration.

## Performance tuning

### What Remotion already does

Remotion already renders frames in parallel.

If you do not specify `--concurrency`, Remotion chooses a default automatically based on the host CPU.

### `--concurrency`

Use this when you want to test whether the default worker count is too conservative for your machine.

Examples:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --concurrency 12
```

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --concurrency 75%
```

Practical guidance:

- start with `75%`
- if the machine stays responsive and the render speeds up, try `12` or `14`
- if the machine thrashes, back off

### `--gl`

Use `--gl angle` if the composition uses effects that benefit from GPU-backed Chromium rendering.

Example:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --gl angle
```

For the current debate renderer:

- this may help a little
- it is not expected to be a dramatic win
- it is much more useful for Three.js, Skia, shaders, blur, and heavy visual effects

### Hardware accelerated encoding

Important:

- the current renderer script does not use hardware accelerated encoding
- this Remotion version only exposes `hardwareAcceleration` for H.264 / H.265 / ProRes on macOS
- on Windows, this debate renderer currently falls back to software H.264 encoding through Remotion

So on this machine, the most realistic built-in performance lever is `--concurrency`, not Remotion hardware encoding.

## Internal normalization

Before rendering, the CLI normalizes the source JSON.

This includes:

- coercing numeric timing fields into numbers
- cleaning transcript text
- sorting turns and segments by start time
- deriving missing turn durations from `end - start`
- deriving fallback segments from turns when needed
- deriving total duration from the transcript if `duration` is missing

This makes the workflow more tolerant of slightly inconsistent upstream transcript exports.

## Typical workflow

### First-time test

Run a short preview:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --max-seconds 30
```

Check:

- title and subtitle
- speaker order
- caption readability
- audio presence
- output filename

### Full export

After the preview looks correct:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json"
```

### Explicit audio override

If your JSON points to the wrong audio or has no `audio` field:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --audio "G:\path\to\debate.wav"
```

## Troubleshooting

### Error: Missing `--json` file

Cause:

- wrong path
- typo in filename

Fix:

- verify the JSON path exists
- wrap Windows paths in quotes

### Error: Could not resolve an audio file

Cause:

- no `--audio` was provided
- the JSON `audio` field points to a missing file
- no same-name sibling audio file exists

Fix:

- pass `--audio` explicitly
- or fix the JSON `audio` field

### Render is too slow

Cause:

- long debate
- large WAV
- full 1080p encode

Fix:

- test with `--max-seconds`
- render to a fast local drive
- avoid unnecessary background load while rendering

### Caption blocks are too large

Cause:

- `segments` are missing or too coarse

Fix:

- generate better sentence-level segments upstream
- keep `segments` in the transcript export

### Output exists but audio seems missing

Check:

- the staged file exists in `packages/example/public/user-debate/input/`
- the `.input.json` manifest points to the expected audio file
- the output MP4 contains an AAC audio stream

The current implementation has already been verified with a real rendered preview that contained an audio stream.

## Current limitations

- only one audio track is rendered
- the scene is currently designed for a single master debate audio file
- there is one reusable visual template, not multiple layout presets
- title/subtitle derivation is filename-driven unless you override them
- there is no chaptering, scene splitting, or per-turn visual style switching yet

## Extending it

If you want to evolve this into a larger transcript-to-video system, the next sensible additions are:

- multiple visual themes
- portrait and square output formats
- per-turn scene types
- chapter cards or section breaks
- automatic highlights
- background image or b-roll support
- richer host/positive/negative layout logic
- schema validation for upstream export quality checks

## Code map

Main CLI:

- `packages/example/render-user-debate.cjs`

Composition registration:

- `packages/example/src/UserDebate/index.tsx`

Main visual component and prop schema:

- `packages/example/src/UserDebate/DebateVideo.tsx`

Remotion entrypoint:

- `packages/example/src/UserDebate/entry.tsx`

## Short version

If you only remember one thing, use this:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json"
```

If you want to test first:

```powershell
bun run render-user-debate -- --json "G:\path\to\debate.json" --max-seconds 30
```
