# Bitwig Studio: Project-Specific Analysis & SOP

## Architecture Summary

Bitwig Studio is a proprietary DAW (Digital Audio Workstation) with no headless mode
or command-line interface. External control is achieved through the **Controller API**,
which allows Java extensions to observe and manipulate all aspects of a running instance.

```
+-------------------------------------------------------------+
|                   Bitwig Studio GUI                          |
|  +----------+ +----------+ +-----------+ +---------------+  |
|  | Arranger | | Launcher | |   Mixer   | |    Devices    |  |
|  | Timeline | |  (Clips) | | (Tracks)  | | (Plugins/FX) |  |
|  +----+-----+ +----+-----+ +-----+-----+ +------+--------+  |
|       |             |             |              |           |
|  +----+-------------+-------------+--------------+--------+  |
|  |              Controller API (Java)                     |  |
|  |  Transport, TrackBank, ClipLauncher, DeviceBank,       |  |
|  |  SceneBank, Mixer, Browser, Application, Arranger      |  |
|  |  Built-in: TCP, UDP, OSC networking                    |  |
|  +---+-------------------+--------------------------------+  |
+------+-------------------+-----------------------------------+
       |                   |
  +----+-------+    +------+----------+
  | OSC Bridge |    | DrivenByMoss    |
  | (UDP)      |    | Extension       |
  +----+-------+    +-----------------+
       |
  +----+------------------+
  | Python CLI            |
  | (python-osc client)   |
  | cli-anything-bitwig   |
  +------------------------+
```

## CLI Strategy: OSC Remote Control via DrivenByMoss

Unlike file-based harnesses (Audacity/JSON, LibreOffice/ODF), this CLI is a
**live remote control** for a running Bitwig instance. The communication path:

1. **DrivenByMoss extension** runs inside Bitwig, exposing a comprehensive OSC protocol
2. **Python CLI** sends OSC commands over UDP (default port 8000)
3. **Bitwig sends back** state updates via OSC to the CLI's listener (default port 9000)
4. **Local state cache** stores the latest state for fast introspection queries

### Why DrivenByMoss OSC?

- 735+ stars, actively maintained (Jurgen Mossgraber), last updated 2026
- Most complete external control protocol available for Bitwig
- ~200+ OSC addresses covering all major DAW operations
- Full bidirectional: commands and state feedback
- No custom extension needed — DrivenByMoss is widely used

### Hard Dependency

**Bitwig Studio must be running** with DrivenByMoss configured as a controller.
The CLI is useless without a live Bitwig instance. This follows the cli-anything
principle: "the software is a required dependency."

## Command Map: GUI Action -> CLI Command

| GUI Action | CLI Command |
|-----------|-------------|
| Transport: Play | `transport play` |
| Transport: Stop | `transport stop` |
| Transport: Record | `transport record` |
| Transport: Loop toggle | `transport loop` |
| Transport: Set tempo | `transport tempo 120` |
| Transport: Tap tempo | `transport tap` |
| Transport: Set position | `transport position 4.0` |
| Transport: Metronome | `transport click` |
| Track: Set volume | `track volume 1 0.8` |
| Track: Set pan | `track pan 1 -0.3` |
| Track: Mute | `track mute 1` |
| Track: Solo | `track solo 1` |
| Track: Rec arm | `track arm 1` |
| Track: Add audio | `track add audio` |
| Track: Add instrument | `track add instrument` |
| Track: Select | `track select 1` |
| Track: Send volume | `track send 1 1 0.5` |
| Clip: Launch | `clip launch 1 1` |
| Clip: Stop | `clip stop 1` |
| Clip: Record | `clip record 1 1` |
| Scene: Launch | `scene launch 1` |
| Device: Set param | `device param 1 0.5` |
| Device: Bypass | `device bypass` |
| Device: Window | `device window` |
| Browser: Open presets | `browser preset` |
| Browser: Commit | `browser commit` |
| Edit: Undo | `undo` |
| Edit: Redo | `redo` |
| Project: Save | `project save` |
| Layout: Switch | `layout arrange` |
| Mixer: Status | `mixer status` |

## OSC Protocol Reference (DrivenByMoss)

### Send to Bitwig (Commands)

**Transport:**
- `/play`, `/stop`, `/record`, `/restart` — toggle/trigger
- `/repeat` — loop toggle
- `/click` — metronome toggle
- `/tempo/raw {bpm}` — set tempo (0-666)
- `/tempo/tap` — tap tempo
- `/position/{+,-}` — nudge position

**Tracks (1-indexed, bank of 8):**
- `/track/{1-8}/volume {0-1}` — set volume
- `/track/{1-8}/pan {0-1}` — set pan (0.5 = center)
- `/track/{1-8}/mute {0|1}` — mute toggle
- `/track/{1-8}/solo {0|1}` — solo toggle
- `/track/{1-8}/recarm {0|1}` — rec arm toggle
- `/track/{1-8}/select` — select track
- `/track/{1-8}/send/{1-8}/volume {0-1}` — send level
- `/track/bank/{+,-}` — scroll track bank

**Clips:**
- `/track/{1-8}/clip/{1-8}/launch` — launch clip
- `/track/{1-8}/clip/{1-8}/record` — record into clip
- `/track/{1-8}/clip/stop` — stop clips on track
- `/scene/{1-8}/launch` — launch scene

**Devices:**
- `/device/param/{1-8}/value {0-1}` — set parameter
- `/device/bypass` — toggle bypass
- `/device/window` — show/hide plugin window
- `/device/{+,-}` — navigate devices
- `/device/page/{+,-}` — navigate parameter pages

**Browser:**
- `/browser/preset` — open preset browser
- `/browser/device` — open device browser
- `/browser/commit` — confirm selection
- `/browser/cancel` — cancel
- `/browser/result/{+,-}` — navigate results
- `/browser/filter/{1-6}/{+,-}` — navigate filter columns

**Global:**
- `/undo` — undo
- `/redo` — redo
- `/project/save` — save project
- `/track/add/audio` — add audio track
- `/track/add/instrument` — add instrument track
- `/layout/{arrange,mix,edit}` — switch layout

### Receive from Bitwig (State Updates)

All of the above + track names, colors, types, VU meters, clip names/colors/states,
device parameter names/values, scene names/colors, transport state (position, tempo,
playing, recording), and browser state.

## Rendering / Export

Bitwig has no headless export. The CLI controls the live instance only.
For bounce/export, the user must use Bitwig's GUI export dialog.
The CLI can assist by:
- Setting loop range for the bounce region
- Soloing/muting tracks to control what gets exported
- Saving the project before export

## Test Coverage

1. **Unit tests** (`test_core.py`): 50+ tests, synthetic data
   - OSC message construction
   - State cache operations
   - Session lifecycle
   - Command argument validation
   - Bank navigation logic

2. **E2E tests** (`test_full_e2e.py`): 20+ tests, live Bitwig connection
   - OSC send/receive round-trips
   - Transport control verification
   - Track manipulation
   - CLI subprocess invocation
