# Test Plan: cli-anything-bitwig

## Test Inventory

- `test_core.py`: 65 unit tests (synthetic data, no Bitwig needed)
- `test_full_e2e.py`: 17 tests (6 subprocess + 11 requiring running Bitwig)

## Unit Test Plan (`test_core.py`)

### BitwigState
- Thread-safe get/set operations
- Nested key access (get "transport", "playing")
- Snapshot returns deep copy (mutation-safe)
- last_update timestamp tracking
- Missing key returns None

### Session
- Session creation with defaults
- Session creation with custom host/ports
- Config save/load round-trip
- Connection status when disconnected
- Bank offset tracking for track/scene scrolling

### Transport
- Validate tempo range (20-666 BPM, reject out-of-range)
- Validate position (reject negative)
- All transport commands return correct action dicts
- Status returns expected fields

### Tracks
- Validate track number range (1-8, reject 0 and 9)
- Validate volume range (0.0-1.0)
- Validate pan range (0.0-1.0)
- Validate send number range (1-8)
- List tracks from state cache
- Get track info
- All track commands return correct action dicts

### Clips
- Validate track/slot ranges (1-8)
- List clips from cache
- Grid construction from cache
- Launch/stop/record return correct dicts

### Scenes
- Validate scene range (1-8)
- List scenes from cache
- Launch returns correct dict

### Devices
- Validate parameter range (1-8)
- Validate parameter value range (0.0-1.0)
- Status extraction from cache
- Navigate direction mapping

### Mixer
- Validate master volume range (0.0-1.0)
- Validate master pan range (0.0-1.0)
- Status combines tracks + master

### Browser
- All browser commands return correct dicts
- Filter column validation (1-6)
- Status extraction from cache

### Project
- Layout validation (arrange/mix/edit)
- All project commands return correct dicts
- Status extraction from cache

### OSC Message Construction
- Correct OSC addresses generated for each command
- Correct argument types (float, int, string)

## E2E Test Plan (`test_full_e2e.py`)

### Prerequisites
- Bitwig Studio running
- DrivenByMoss configured with OSC on ports 8000/9000

### Connection Tests
- Connect to Bitwig, verify state received
- Disconnect cleanly
- Handle connection timeout (Bitwig not running)

### Transport Round-Trip
- Send play command, verify playing state updates
- Set tempo, verify tempo state changes
- Toggle loop, verify loop state

### Track Manipulation
- List tracks, verify names match Bitwig project
- Set track volume, verify state update
- Toggle mute/solo, verify state

### CLI Subprocess Tests
- `--help` returns 0
- `--json status` returns valid JSON
- `--json transport status` returns transport fields
- `--json track list` returns track array
- `--json mixer status` returns mixer structure

### Realistic Workflow Scenarios

**Live Performance Setup:**
1. Connect to Bitwig
2. List tracks and clips
3. Launch clips in sequence
4. Adjust track volumes
5. Launch scenes
6. Stop all clips

**Mixing Workflow:**
1. Connect
2. Get mixer status
3. Adjust track volumes across bank
4. Set send levels
5. Navigate to device, tweak parameters
6. Save project

---

## Test Results

```
CLI_ANYTHING_FORCE_INSTALLED=1 pytest cli_anything/bitwig/tests/ -v --tb=no

============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-9.0.2
plugins: anyio-4.12.1, cov-7.0.0
collected 82 items

test_core.py::TestBitwigState::test_initial_state PASSED
test_core.py::TestBitwigState::test_set_and_get PASSED
test_core.py::TestBitwigState::test_nested_set PASSED
test_core.py::TestBitwigState::test_missing_key_returns_none PASSED
test_core.py::TestBitwigState::test_snapshot_is_deep_copy PASSED
test_core.py::TestBitwigState::test_last_update_tracks_time PASSED
test_core.py::TestBitwigState::test_thread_safety PASSED
test_core.py::TestSession::test_default_config PASSED
test_core.py::TestSession::test_custom_config PASSED
test_core.py::TestSession::test_not_connected_by_default PASSED
test_core.py::TestSession::test_status_disconnected PASSED
test_core.py::TestSession::test_send_raises_when_disconnected PASSED
test_core.py::TestSession::test_bank_offset_initial PASSED
test_core.py::TestSession::test_config_save_load PASSED
test_core.py::TestTransportValidation::test_tempo_valid PASSED
test_core.py::TestTransportValidation::test_tempo_too_low PASSED
test_core.py::TestTransportValidation::test_tempo_too_high PASSED
test_core.py::TestTransportValidation::test_position_negative PASSED
test_core.py::TestTransportValidation::test_position_valid PASSED
test_core.py::TestTransportValidation::test_play_sends_osc PASSED
test_core.py::TestTransportValidation::test_stop_sends_osc PASSED
test_core.py::TestTransportValidation::test_record_sends_osc PASSED
test_core.py::TestTransportValidation::test_loop_toggle PASSED
test_core.py::TestTransportValidation::test_click_toggle PASSED
test_core.py::TestTransportValidation::test_tap_tempo PASSED
test_core.py::TestTransportValidation::test_status_returns_fields PASSED
test_core.py::TestTrackValidation::test_track_out_of_range_low PASSED
test_core.py::TestTrackValidation::test_track_out_of_range_high PASSED
test_core.py::TestTrackValidation::test_volume_out_of_range PASSED
test_core.py::TestTrackValidation::test_pan_out_of_range PASSED
test_core.py::TestTrackValidation::test_send_out_of_range PASSED
test_core.py::TestTrackValidation::test_send_value_out_of_range PASSED
test_core.py::TestTrackValidation::test_volume_sends_correct_osc PASSED
test_core.py::TestTrackValidation::test_mute_toggle PASSED
test_core.py::TestTrackValidation::test_solo_toggle PASSED
test_core.py::TestTrackValidation::test_arm_toggle PASSED
test_core.py::TestTrackValidation::test_add_audio_track PASSED
test_core.py::TestTrackValidation::test_add_instrument_track PASSED
test_core.py::TestTrackValidation::test_list_tracks PASSED
test_core.py::TestClipValidation::test_clip_track_out_of_range PASSED
test_core.py::TestClipValidation::test_clip_slot_out_of_range PASSED
test_core.py::TestClipValidation::test_launch_sends_osc PASSED
test_core.py::TestClipValidation::test_stop_sends_osc PASSED
test_core.py::TestClipValidation::test_record_sends_osc PASSED
test_core.py::TestSceneValidation::test_scene_out_of_range PASSED
test_core.py::TestSceneValidation::test_launch_sends_osc PASSED
test_core.py::TestDeviceValidation::test_param_out_of_range PASSED
test_core.py::TestDeviceValidation::test_param_value_out_of_range PASSED
test_core.py::TestDeviceValidation::test_param_sends_osc PASSED
test_core.py::TestDeviceValidation::test_bypass_sends_osc PASSED
test_core.py::TestDeviceValidation::test_navigate_next PASSED
test_core.py::TestDeviceValidation::test_navigate_prev PASSED
test_core.py::TestDeviceValidation::test_status_extracts_params PASSED
test_core.py::TestMixerValidation::test_master_volume_out_of_range PASSED
test_core.py::TestMixerValidation::test_master_pan_out_of_range PASSED
test_core.py::TestMixerValidation::test_master_volume_sends_osc PASSED
test_core.py::TestBrowserValidation::test_filter_column_out_of_range PASSED
test_core.py::TestBrowserValidation::test_open_preset PASSED
test_core.py::TestBrowserValidation::test_commit PASSED
test_core.py::TestProjectValidation::test_layout_invalid PASSED
test_core.py::TestProjectValidation::test_layout_valid PASSED
test_core.py::TestProjectValidation::test_save_sends_osc PASSED
test_core.py::TestProjectValidation::test_undo_sends_osc PASSED
test_core.py::TestProjectValidation::test_redo_sends_osc PASSED
test_core.py::TestProjectValidation::test_status_returns_fields PASSED
test_full_e2e.py::TestConnection::test_connect_and_disconnect SKIPPED (Bitwig not running)
test_full_e2e.py::TestConnection::test_double_connect SKIPPED
test_full_e2e.py::TestTransportE2E::test_transport_status SKIPPED
test_full_e2e.py::TestTransportE2E::test_set_tempo SKIPPED
test_full_e2e.py::TestTracksE2E::test_list_tracks SKIPPED
test_full_e2e.py::TestMixerE2E::test_mixer_status SKIPPED
test_full_e2e.py::TestCLISubprocess::test_help PASSED
test_full_e2e.py::TestCLISubprocess::test_transport_help PASSED
test_full_e2e.py::TestCLISubprocess::test_track_help PASSED
test_full_e2e.py::TestCLISubprocess::test_clip_help PASSED
test_full_e2e.py::TestCLISubprocess::test_device_help PASSED
test_full_e2e.py::TestCLISubprocess::test_mixer_help PASSED
test_full_e2e.py::TestCLISubprocessE2E::test_json_connect_and_status SKIPPED
test_full_e2e.py::TestCLISubprocessE2E::test_json_transport_status SKIPPED
test_full_e2e.py::TestCLISubprocessE2E::test_json_track_list SKIPPED
test_full_e2e.py::TestCLISubprocessE2E::test_json_mixer_status SKIPPED
test_full_e2e.py::TestCLISubprocessE2E::test_full_workflow SKIPPED

======================== 71 passed, 11 skipped in 2.90s ========================
```

### Summary

- **Total tests:** 82
- **Passed:** 71 (100% of runnable tests)
- **Skipped:** 11 (require running Bitwig Studio with DrivenByMoss)
- **Failed:** 0
- **Execution time:** 2.90s
- **Subprocess tests:** confirmed using installed command via `[_resolve_cli]`

### Coverage Notes

- All validation logic tested (ranges, types, boundaries)
- All OSC address construction tested (correct paths, arguments)
- State cache operations tested (thread safety, deep copy, nested access)
- Session lifecycle tested (config save/load, connection status)
- CLI subprocess tests confirm installed binary works (`--help` for all groups)
- E2E tests require running Bitwig — to run them, start Bitwig with DrivenByMoss OSC configured
