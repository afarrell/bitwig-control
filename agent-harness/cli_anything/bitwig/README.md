# cli-anything-bitwig

CLI harness for controlling **Bitwig Studio** from the command line via OSC.

Communicates with a running Bitwig instance through the
[DrivenByMoss](https://github.com/git-moss/DrivenByMoss) OSC protocol.
Designed for AI agent consumption (with `--json` output) and interactive
human use (with REPL mode).

## Prerequisites

1. **Bitwig Studio** (5.0+) — must be running
2. **DrivenByMoss extension** installed in Bitwig:
   - Download from [DrivenByMoss releases](https://github.com/git-moss/DrivenByMoss/releases)
   - Copy `.bwextension` file to `~/Bitwig Studio/Extensions/`
3. **OSC controller configured** in Bitwig:
   - Settings > Controllers > Add controller > Open Sound Control
   - Set **Receive Port** to `8000` (where Bitwig listens)
   - Set **Send Host** to `127.0.0.1`
   - Set **Send Port** to `9000` (where the CLI listens)

## Installation

```bash
cd agent-harness
pip install -e .
```

Verify:
```bash
which cli-anything-bitwig
cli-anything-bitwig --help
```

## Usage

### Interactive REPL (default)

```bash
cli-anything-bitwig
```

Starts the REPL, auto-connects to Bitwig, and presents a prompt.

### One-shot commands

```bash
# Transport
cli-anything-bitwig transport play
cli-anything-bitwig transport stop
cli-anything-bitwig transport tempo 128
cli-anything-bitwig transport status

# Tracks
cli-anything-bitwig track list
cli-anything-bitwig track volume 1 0.8
cli-anything-bitwig track mute 2
cli-anything-bitwig track solo 3

# Clips
cli-anything-bitwig clip launch 1 1
cli-anything-bitwig clip grid

# Scenes
cli-anything-bitwig scene launch 1

# Devices
cli-anything-bitwig device status
cli-anything-bitwig device param 1 0.5

# Mixer
cli-anything-bitwig mixer status

# Project
cli-anything-bitwig project save
cli-anything-bitwig undo
cli-anything-bitwig redo
```

### JSON mode (for agents)

```bash
cli-anything-bitwig --json transport status
cli-anything-bitwig --json track list
cli-anything-bitwig --json mixer status
```

### Custom connection

```bash
cli-anything-bitwig --host 192.168.1.100 --send-port 8000 --receive-port 9000 transport play
```

## Architecture

```
Python CLI  ──OSC UDP──>  Bitwig Studio
  (python-osc)            (DrivenByMoss extension)
              <──OSC UDP──
              state updates
```

The CLI sends OSC commands (e.g., `/play`, `/track/1/volume 0.8`) and receives
state updates (track names, volumes, transport state) via a background UDP server.
A thread-safe state cache stores the latest Bitwig state for fast queries.

### Track banks

DrivenByMoss exposes tracks in banks of 8. Use `track bank +` / `track bank -`
to scroll through projects with more than 8 tracks. Clip slots and scenes also
use 8-wide banks.

## Running Tests

```bash
cd agent-harness
pip install -e ".[dev]"

# Unit tests (no Bitwig needed)
pytest cli_anything/bitwig/tests/test_core.py -v

# E2E tests (requires running Bitwig with DrivenByMoss)
pytest cli_anything/bitwig/tests/test_full_e2e.py -v -s

# All tests with installed CLI
CLI_ANYTHING_FORCE_INSTALLED=1 pytest cli_anything/bitwig/tests/ -v -s
```
