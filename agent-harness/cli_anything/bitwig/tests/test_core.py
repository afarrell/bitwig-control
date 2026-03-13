"""Unit tests for cli-anything-bitwig core modules.

All tests use synthetic data and mock OSC communication.
No running Bitwig instance required.
"""

import copy
import json
import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from cli_anything.bitwig.utils.osc_backend import BitwigState
from cli_anything.bitwig.core.session import Session


# ── BitwigState tests ──────────────────────────────────────────────────

class TestBitwigState:
    def test_initial_state(self):
        state = BitwigState()
        assert state.get("transport", "playing") is False
        assert state.get("transport", "tempo") == 120.0
        assert state.get("transport", "loop") is False

    def test_set_and_get(self):
        state = BitwigState()
        state.set("transport", "playing", True)
        assert state.get("transport", "playing") is True

    def test_nested_set(self):
        state = BitwigState()
        state.set("tracks", 1, "name", "Bass")
        assert state.get("tracks", 1, "name") == "Bass"

    def test_missing_key_returns_none(self):
        state = BitwigState()
        assert state.get("nonexistent") is None
        assert state.get("transport", "nonexistent") is None
        assert state.get("tracks", 99, "name") is None

    def test_snapshot_is_deep_copy(self):
        state = BitwigState()
        state.set("transport", "tempo", 140.0)
        snap = state.snapshot()
        snap["transport"]["tempo"] = 999
        assert state.get("transport", "tempo") == 140.0

    def test_last_update_tracks_time(self):
        state = BitwigState()
        assert state.last_update == 0.0
        state.set("transport", "playing", True)
        assert state.last_update > 0.0

    def test_thread_safety(self):
        state = BitwigState()
        errors = []

        def writer(tid):
            try:
                for i in range(100):
                    state.set("tracks", tid, "volume", i / 100.0)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(100):
                    state.snapshot()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(1,)),
            threading.Thread(target=writer, args=(2,)),
            threading.Thread(target=reader),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0


# ── Session tests ──────────────────────────────────────────────────────

class TestSession:
    def test_default_config(self):
        sess = Session()
        assert sess.host == "127.0.0.1"
        assert sess.send_port == 8000
        assert sess.receive_port == 9000

    def test_custom_config(self):
        sess = Session(host="192.168.1.10", send_port=9999, receive_port=8888)
        assert sess.host == "192.168.1.10"
        assert sess.send_port == 9999
        assert sess.receive_port == 8888

    def test_not_connected_by_default(self):
        sess = Session()
        assert sess.connected is False

    def test_status_disconnected(self):
        sess = Session()
        st = sess.status()
        assert st["connected"] is False
        assert st["host"] == "127.0.0.1"

    def test_send_raises_when_disconnected(self):
        sess = Session()
        with pytest.raises(RuntimeError, match="Not connected"):
            sess.send("/play", 1)

    def test_bank_offset_initial(self):
        sess = Session()
        assert sess._bank_offset == 0
        assert sess._scene_bank_offset == 0

    def test_config_save_load(self, tmp_path):
        with patch("cli_anything.bitwig.core.session._CONFIG_DIR", tmp_path):
            with patch("cli_anything.bitwig.core.session._CONFIG_FILE", tmp_path / "config.json"):
                sess = Session(host="10.0.0.1", send_port=7777, receive_port=6666)
                sess.save_config()

                loaded = Session.load_config()
                assert loaded.host == "10.0.0.1"
                assert loaded.send_port == 7777
                assert loaded.receive_port == 6666


# ── Transport validation tests ─────────────────────────────────────────

class TestTransportValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess.get_state.return_value = {
            "playing": False,
            "recording": False,
            "tempo": 120.0,
            "position": "1.1.0",
            "time_str": "00:00:00",
            "loop": False,
            "click": False,
            "overdub": False,
            "numerator": 4,
            "denominator": 4,
        }
        return sess

    def test_tempo_valid(self):
        from cli_anything.bitwig.core.transport import set_tempo
        sess = self._mock_session()
        result = set_tempo(sess, 120.0)
        assert result["bpm"] == 120.0
        sess.send.assert_called_once_with("/tempo/raw", 120.0)

    def test_tempo_too_low(self):
        from cli_anything.bitwig.core.transport import set_tempo
        with pytest.raises(ValueError, match="20 and 666"):
            set_tempo(self._mock_session(), 10.0)

    def test_tempo_too_high(self):
        from cli_anything.bitwig.core.transport import set_tempo
        with pytest.raises(ValueError, match="20 and 666"):
            set_tempo(self._mock_session(), 700.0)

    def test_position_negative(self):
        from cli_anything.bitwig.core.transport import set_position
        with pytest.raises(ValueError, match=">= 0"):
            set_position(self._mock_session(), -1.0)

    def test_position_valid(self):
        from cli_anything.bitwig.core.transport import set_position
        sess = self._mock_session()
        result = set_position(sess, 16.0)
        assert result["beats"] == 16.0

    def test_play_sends_osc(self):
        from cli_anything.bitwig.core.transport import play
        sess = self._mock_session()
        result = play(sess)
        assert result["action"] == "play"
        sess.send.assert_called_once_with("/play", 1)

    def test_stop_sends_osc(self):
        from cli_anything.bitwig.core.transport import stop
        sess = self._mock_session()
        stop(sess)
        sess.send.assert_called_once_with("/stop", 1)

    def test_record_sends_osc(self):
        from cli_anything.bitwig.core.transport import record
        sess = self._mock_session()
        record(sess)
        sess.send.assert_called_once_with("/record", 1)

    def test_loop_toggle(self):
        from cli_anything.bitwig.core.transport import toggle_loop
        sess = self._mock_session()
        toggle_loop(sess)
        sess.send.assert_called_once_with("/repeat", 1)

    def test_click_toggle(self):
        from cli_anything.bitwig.core.transport import toggle_click
        sess = self._mock_session()
        toggle_click(sess)
        sess.send.assert_called_once_with("/click", 1)

    def test_tap_tempo(self):
        from cli_anything.bitwig.core.transport import tap_tempo
        sess = self._mock_session()
        tap_tempo(sess)
        sess.send.assert_called_once_with("/tempo/tap", 1)

    def test_status_returns_fields(self):
        from cli_anything.bitwig.core.transport import status
        sess = self._mock_session()
        result = status(sess)
        assert "playing" in result
        assert "tempo" in result
        assert "position" in result
        assert "loop" in result
        assert "time_signature" in result


# ── Track validation tests ─────────────────────────────────────────────

class TestTrackValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess._bank_offset = 0
        sess.get_state.return_value = {
            1: {"name": "Bass", "type": "instrument", "volume": 0.8, "pan": 0.5,
                "mute": False, "solo": False, "recarm": False, "selected": True,
                "exists": True, "volume_str": "-2.0 dB", "pan_str": "C",
                "sends": {}, "clips": {}},
        }
        return sess

    def test_track_out_of_range_low(self):
        from cli_anything.bitwig.core.tracks import set_volume
        with pytest.raises(ValueError, match="1-8"):
            set_volume(self._mock_session(), 0, 0.5)

    def test_track_out_of_range_high(self):
        from cli_anything.bitwig.core.tracks import set_volume
        with pytest.raises(ValueError, match="1-8"):
            set_volume(self._mock_session(), 9, 0.5)

    def test_volume_out_of_range(self):
        from cli_anything.bitwig.core.tracks import set_volume
        with pytest.raises(ValueError, match="0.0-1.0"):
            set_volume(self._mock_session(), 1, 1.5)

    def test_pan_out_of_range(self):
        from cli_anything.bitwig.core.tracks import set_pan
        with pytest.raises(ValueError, match="0.0-1.0"):
            set_pan(self._mock_session(), 1, -0.1)

    def test_send_out_of_range(self):
        from cli_anything.bitwig.core.tracks import set_send
        with pytest.raises(ValueError, match="Send number"):
            set_send(self._mock_session(), 1, 0, 0.5)

    def test_send_value_out_of_range(self):
        from cli_anything.bitwig.core.tracks import set_send
        with pytest.raises(ValueError, match="Send value"):
            set_send(self._mock_session(), 1, 1, 2.0)

    def test_volume_sends_correct_osc(self):
        from cli_anything.bitwig.core.tracks import set_volume
        sess = self._mock_session()
        set_volume(sess, 3, 0.75)
        sess.send.assert_called_once_with("/track/3/volume", 0.75)

    def test_mute_toggle(self):
        from cli_anything.bitwig.core.tracks import toggle_mute
        sess = self._mock_session()
        toggle_mute(sess, 2)
        sess.send.assert_called_once_with("/track/2/mute", 1)

    def test_solo_toggle(self):
        from cli_anything.bitwig.core.tracks import toggle_solo
        sess = self._mock_session()
        toggle_solo(sess, 4)
        sess.send.assert_called_once_with("/track/4/solo", 1)

    def test_arm_toggle(self):
        from cli_anything.bitwig.core.tracks import toggle_arm
        sess = self._mock_session()
        toggle_arm(sess, 1)
        sess.send.assert_called_once_with("/track/1/recarm", 1)

    def test_add_audio_track(self):
        from cli_anything.bitwig.core.tracks import add_audio_track
        sess = self._mock_session()
        result = add_audio_track(sess)
        assert result["type"] == "audio"
        sess.send.assert_called_once_with("/track/add/audio", 1)

    def test_add_instrument_track(self):
        from cli_anything.bitwig.core.tracks import add_instrument_track
        sess = self._mock_session()
        result = add_instrument_track(sess)
        assert result["type"] == "instrument"

    def test_list_tracks(self):
        from cli_anything.bitwig.core.tracks import list_tracks
        sess = self._mock_session()
        result = list_tracks(sess)
        assert result["count"] == 1
        assert result["tracks"][0]["name"] == "Bass"


# ── Clip validation tests ──────────────────────────────────────────────

class TestClipValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess.get_state.return_value = {}
        return sess

    def test_clip_track_out_of_range(self):
        from cli_anything.bitwig.core.clips import launch
        with pytest.raises(ValueError, match="Track must be 1-8"):
            launch(self._mock_session(), 0, 1)

    def test_clip_slot_out_of_range(self):
        from cli_anything.bitwig.core.clips import launch
        with pytest.raises(ValueError, match="Slot must be 1-8"):
            launch(self._mock_session(), 1, 9)

    def test_launch_sends_osc(self):
        from cli_anything.bitwig.core.clips import launch
        sess = self._mock_session()
        launch(sess, 2, 3)
        sess.send.assert_called_once_with("/track/2/clip/3/launch", 1)

    def test_stop_sends_osc(self):
        from cli_anything.bitwig.core.clips import stop
        sess = self._mock_session()
        stop(sess, 1)
        sess.send.assert_called_once_with("/track/1/clip/stop", 1)

    def test_record_sends_osc(self):
        from cli_anything.bitwig.core.clips import record
        sess = self._mock_session()
        record(sess, 4, 2)
        sess.send.assert_called_once_with("/track/4/clip/2/record", 1)


# ── Scene validation tests ────────────────────────────────────────────

class TestSceneValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess._scene_bank_offset = 0
        sess.get_state.return_value = {}
        return sess

    def test_scene_out_of_range(self):
        from cli_anything.bitwig.core.scenes import launch
        with pytest.raises(ValueError, match="Scene must be 1-8"):
            launch(self._mock_session(), 0)

    def test_launch_sends_osc(self):
        from cli_anything.bitwig.core.scenes import launch
        sess = self._mock_session()
        launch(sess, 5)
        sess.send.assert_called_once_with("/scene/5/launch", 1)


# ── Device validation tests ───────────────────────────────────────────

class TestDeviceValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess.get_state.return_value = {
            "name": "EQ-5",
            "bypass": False,
            "page_name": "Main",
            "params": {
                1: {"name": "Freq", "value": 0.5, "value_str": "1.0 kHz", "exists": True},
            },
        }
        return sess

    def test_param_out_of_range(self):
        from cli_anything.bitwig.core.devices import set_param
        with pytest.raises(ValueError, match="1-8"):
            set_param(self._mock_session(), 0, 0.5)

    def test_param_value_out_of_range(self):
        from cli_anything.bitwig.core.devices import set_param
        with pytest.raises(ValueError, match="0.0-1.0"):
            set_param(self._mock_session(), 1, 1.5)

    def test_param_sends_osc(self):
        from cli_anything.bitwig.core.devices import set_param
        sess = self._mock_session()
        set_param(sess, 3, 0.7)
        sess.send.assert_called_once_with("/device/param/3/value", 0.7)

    def test_bypass_sends_osc(self):
        from cli_anything.bitwig.core.devices import toggle_bypass
        sess = self._mock_session()
        toggle_bypass(sess)
        sess.send.assert_called_once_with("/device/bypass", 1)

    def test_navigate_next(self):
        from cli_anything.bitwig.core.devices import navigate
        sess = self._mock_session()
        navigate(sess, 1)
        sess.send.assert_called_once_with("/device/+", 1)

    def test_navigate_prev(self):
        from cli_anything.bitwig.core.devices import navigate
        sess = self._mock_session()
        navigate(sess, -1)
        sess.send.assert_called_once_with("/device/-", 1)

    def test_status_extracts_params(self):
        from cli_anything.bitwig.core.devices import status
        sess = self._mock_session()
        result = status(sess)
        assert result["name"] == "EQ-5"
        assert len(result["parameters"]) == 1
        assert result["parameters"][0]["name"] == "Freq"


# ── Mixer validation tests ────────────────────────────────────────────

class TestMixerValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess._bank_offset = 0
        sess.get_state.side_effect = lambda *keys: {
            ("tracks",): {1: {"name": "Bass", "volume": 0.8, "pan": 0.5,
                              "mute": False, "solo": False, "recarm": False,
                              "exists": True, "vu": 0.3, "volume_str": "-2dB",
                              "pan_str": "C"}},
            ("master",): {"volume": 1.0, "volume_str": "0 dB", "pan": 0.5,
                          "mute": False, "vu": 0.5},
        }.get(keys, {})
        return sess

    def test_master_volume_out_of_range(self):
        from cli_anything.bitwig.core.mixer import set_master_volume
        with pytest.raises(ValueError, match="0.0-1.0"):
            set_master_volume(self._mock_session(), 1.5)

    def test_master_pan_out_of_range(self):
        from cli_anything.bitwig.core.mixer import set_master_pan
        with pytest.raises(ValueError, match="0.0-1.0"):
            set_master_pan(self._mock_session(), -0.1)

    def test_master_volume_sends_osc(self):
        from cli_anything.bitwig.core.mixer import set_master_volume
        sess = self._mock_session()
        set_master_volume(sess, 0.6)
        sess.send.assert_called_once_with("/master/volume", 0.6)


# ── Browser validation tests ──────────────────────────────────────────

class TestBrowserValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess.get_state.return_value = {"active": False}
        return sess

    def test_filter_column_out_of_range(self):
        from cli_anything.bitwig.core.browser import navigate_filter
        with pytest.raises(ValueError, match="1-6"):
            navigate_filter(self._mock_session(), 0, 1)

    def test_open_preset(self):
        from cli_anything.bitwig.core.browser import open_presets
        sess = self._mock_session()
        open_presets(sess)
        sess.send.assert_called_once_with("/browser/preset", 1)

    def test_commit(self):
        from cli_anything.bitwig.core.browser import commit
        sess = self._mock_session()
        commit(sess)
        sess.send.assert_called_once_with("/browser/commit", 1)


# ── Project validation tests ──────────────────────────────────────────

class TestProjectValidation:
    def _mock_session(self):
        sess = MagicMock(spec=Session)
        sess.get_state.side_effect = lambda *keys: {
            ("project",): {"name": "My Song", "engine": True},
            ("layout",): "arrange",
        }.get(keys, None)
        return sess

    def test_layout_invalid(self):
        from cli_anything.bitwig.core.project import set_layout
        with pytest.raises(ValueError, match="arrange"):
            set_layout(self._mock_session(), "invalid")

    def test_layout_valid(self):
        from cli_anything.bitwig.core.project import set_layout
        sess = self._mock_session()
        set_layout(sess, "mix")
        sess.send.assert_called_once_with("/layout/mix", 1)

    def test_save_sends_osc(self):
        from cli_anything.bitwig.core.project import save
        sess = self._mock_session()
        save(sess)
        sess.send.assert_called_once_with("/project/save", 1)

    def test_undo_sends_osc(self):
        from cli_anything.bitwig.core.project import undo
        sess = self._mock_session()
        undo(sess)
        sess.send.assert_called_once_with("/undo", 1)

    def test_redo_sends_osc(self):
        from cli_anything.bitwig.core.project import redo
        sess = self._mock_session()
        redo(sess)
        sess.send.assert_called_once_with("/redo", 1)

    def test_status_returns_fields(self):
        from cli_anything.bitwig.core.project import status
        sess = self._mock_session()
        result = status(sess)
        assert result["name"] == "My Song"
        assert result["layout"] == "arrange"
