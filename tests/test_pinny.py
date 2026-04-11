import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pinny.app import (
    Location,
    PinnyTUI,
    app_language,
    command_add,
    command_apply_index,
    command_cover,
    command_download,
    command_list,
    find_booted_device_udids,
    get_host_current_location,
    load_default_locations,
    load_json_locations,
    load_locations,
    main,
    merge_unique,
    msg,
    parse_inline_location,
    run_simctl_set_to_host_location,
    run_simctl_set_location,
    save_locations,
)


class PinnyTests(unittest.TestCase):
    def test_merge_unique_dedupes_by_coordinate(self) -> None:
        base = [Location(37.5532, 126.9837, "서울역")]
        new_items = [
            Location(37.5532001, 126.9837001, "중복"),
            Location(52.515854, 13.407141, "베를린"),
        ]

        merged, added = merge_unique(base, new_items)

        self.assertEqual(added, 1)
        self.assertEqual(len(merged), 2)

    def test_load_json_locations_supports_dict_and_array(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "list.json"
            payload = {
                "locations": [
                    {
                        "latitude": 37.5532,
                        "longitude": 126.9837,
                        "description": "서울역",
                    },
                    [52.515854, 13.407141, "베를린"],
                ]
            }
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            locations = load_json_locations(path)

            self.assertEqual(len(locations), 2)
            self.assertEqual(locations[0].description, "서울역")
            self.assertAlmostEqual(locations[1].longitude, 13.407141)

    def test_parse_inline_location_accepts_comma_separator(self) -> None:
        location = parse_inline_location("37.5532, 126.9837 서울역 주차장 입구")
        self.assertAlmostEqual(location.latitude, 37.5532)
        self.assertAlmostEqual(location.longitude, 126.9837)
        self.assertEqual(location.description, "서울역 주차장 입구")

    def test_language_can_be_forced_with_env(self) -> None:
        with patch.dict(os.environ, {"PINNY_LANG": "en_US.UTF-8"}, clear=False):
            self.assertEqual(app_language(), "en")
        with patch.dict(os.environ, {"PINNY_LANG": "ko_KR.UTF-8"}, clear=False):
            self.assertEqual(app_language(), "ko")

    def test_add_messages_use_format_template(self) -> None:
        with patch.dict(os.environ, {"PINNY_LANG": "ko"}, clear=False):
            self.assertEqual(msg("help_add"), "추가 : <latitude> <longitude> <description>")
            self.assertEqual(
                msg("status_add_format_short"),
                "입력 형식: <latitude> <longitude> <description>",
            )
            self.assertEqual(
                msg("inline_format"),
                "입력 형식: <latitude> <longitude> <description> (콤마 허용)",
            )

        with patch.dict(os.environ, {"PINNY_LANG": "en"}, clear=False):
            self.assertEqual(msg("help_add"), "Add: <latitude> <longitude> <description>")
            self.assertEqual(
                msg("status_add_format_short"),
                "Input format: <latitude> <longitude> <description>",
            )
            self.assertEqual(
                msg("inline_format"),
                "Input format: <latitude> <longitude> <description> (comma allowed)",
            )

    def test_default_locations_loaded(self) -> None:
        defaults = load_default_locations()
        self.assertEqual(len(defaults), 6)
        self.assertTrue(any("남산타워" in item.description for item in defaults))

    def test_tui_seeds_default_locations_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([], data_path)

            app = PinnyTUI(data_path)

            self.assertGreaterEqual(len(app.locations), 6)
            self.assertTrue(any("자유의 여신상" in item.description for item in app.locations))
            self.assertEqual(len(load_locations(data_path)), len(app.locations))

    def test_tui_does_not_seed_when_non_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            custom = Location(35.179554, 129.075642, "부산")
            save_locations([custom], data_path)

            app = PinnyTUI(data_path)

            self.assertEqual(len(app.locations), 1)
            self.assertEqual(app.locations[0].description, "부산")

    def test_open_map_uses_selected_or_typed_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            first = Location(37.551169, 126.988227, "남산타워")
            second = Location(48.85837, 2.294481, "에펠탑")
            save_locations([first, second], data_path)

            app = PinnyTUI(data_path)
            app.menu_index = PinnyTUI.MENU_SET
            app.selected_row = 1
            app.input_buffer = "1"

            with patch("pinny.app.webbrowser.open", return_value=True) as browser_open:
                app._action_open_in_maps()

            browser_open.assert_called_once_with(
                "https://www.google.com/maps/search/?api=1&query=37.551169,126.988227",
                new=2,
            )
            self.assertEqual(app.selected_row, 0)

    def test_command_list_prints_tui_style_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([Location(37.551169, 126.988227, "남산타워")], data_path)

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = command_list(data_path=data_path)

            output = buffer.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("No", output)
            self.assertIn("Latitude", output)
            self.assertIn("남산타워", output)

    def test_find_booted_device_udids_returns_all_booted_devices(self) -> None:
        payload = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
                    {
                        "udid": "booted-1",
                        "state": "Booted",
                    },
                    {
                        "udid": "shutdown-1",
                        "state": "Shutdown",
                    },
                ],
                "com.apple.CoreSimulator.SimRuntime.iOS-17-5": [
                    {
                        "udid": "booted-2",
                        "state": "Booted",
                    }
                ],
            }
        }

        with patch("pinny.app.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = json.dumps(payload)
            run.return_value.stderr = ""

            udids = find_booted_device_udids()

        self.assertEqual(udids, ["booted-1", "booted-2"])

    def test_run_simctl_set_location_applies_to_all_booted_devices(self) -> None:
        location = Location(37.551169, 126.988227, "남산타워")
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool):
            calls.append(cmd)
            result = unittest.mock.Mock()
            if cmd[:4] == ["xcrun", "simctl", "list", "devices"]:
                result.returncode = 0
                result.stdout = json.dumps(
                    {
                        "devices": {
                            "runtime": [
                                {"udid": "booted-1", "state": "Booted"},
                                {"udid": "booted-2", "state": "Booted"},
                            ]
                        }
                    }
                )
                result.stderr = ""
                return result

            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        with patch("pinny.app.subprocess.run", side_effect=fake_run):
            ok, message = run_simctl_set_location(location)

        self.assertTrue(ok)
        self.assertIn("37.551169", message)
        self.assertEqual(
            calls[1:],
            [
                [
                    "xcrun",
                    "simctl",
                    "location",
                    "booted-1",
                    "set",
                    "37.551169,126.988227",
                ],
                [
                    "xcrun",
                    "simctl",
                    "location",
                    "booted-2",
                    "set",
                    "37.551169,126.988227",
                ],
            ],
        )

    def test_get_host_current_location_returns_location(self) -> None:
        helper_json = {"latitude": 37.551169, "longitude": 126.988227}

        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run"
            ) as run:
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                def run_helper(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                    if cmd[0] == "xcrun":
                        Path(cmd[-1]).write_text("binary", encoding="utf-8")
                    if cmd[0] == "open":
                        Path(cmd[-1]).write_text(json.dumps(helper_json), encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, "", "")

                run.side_effect = run_helper

                ok, result = get_host_current_location()

        self.assertTrue(ok)
        self.assertIsInstance(result, Location)
        assert isinstance(result, Location)
        self.assertAlmostEqual(result.latitude, 37.551169)
        self.assertAlmostEqual(result.longitude, 126.988227)
        self.assertEqual(result.description, msg("here_host_description"))
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][0:2], ["xcrun", "swiftc"])
        self.assertEqual(commands[1][0], "codesign")
        self.assertEqual(commands[2][0], "open")

    def test_get_host_current_location_caches_helper_after_first_compile(self) -> None:
        helper_json = {"latitude": 37.551169, "longitude": 126.988227}

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            helper_path = root / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=root / "cache"), patch(
                "pinny.app.subprocess.run"
            ) as run:
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                def run_helper(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                    if cmd[0] == "xcrun":
                        Path(cmd[-1]).write_text("binary", encoding="utf-8")
                    if cmd[0] == "open":
                        Path(cmd[-1]).write_text(json.dumps(helper_json), encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, "", "")

                run.side_effect = run_helper
                first_messages: list[str] = []
                second_messages: list[str] = []

                first_ok, _ = get_host_current_location(progress=first_messages.append)
                second_ok, _ = get_host_current_location(progress=second_messages.append)

        self.assertTrue(first_ok)
        self.assertTrue(second_ok)
        self.assertEqual(first_messages, [msg("here_compile_notice")])
        self.assertEqual(second_messages, [])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual([cmd[0] for cmd in commands], ["xcrun", "codesign", "open", "open"])

    def test_get_host_current_location_handles_permission_denied(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run"
            ) as run:
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                def run_helper(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                    if cmd[0] == "xcrun":
                        Path(cmd[-1]).write_text("binary", encoding="utf-8")
                    if cmd[0] == "open":
                        Path(cmd[-1]).write_text(
                            json.dumps({"error": "permission_denied"}),
                            encoding="utf-8",
                        )
                    return subprocess.CompletedProcess(cmd, 0, "", "")

                run.side_effect = run_helper

                ok, result = get_host_current_location()

        self.assertFalse(ok)
        self.assertEqual(result, msg("here_fail_permission_denied"))
        self.assertIn("시스템 설정", str(result))
        self.assertIn("Location Services", str(result))

    def test_get_host_current_location_handles_user_no_response_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run"
            ) as run:
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                def run_helper(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                    if cmd[0] == "xcrun":
                        Path(cmd[-1]).write_text("binary", encoding="utf-8")
                    if cmd[0] == "open":
                        Path(cmd[-1]).write_text(json.dumps({"error": "timeout"}), encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, "", "")

                run.side_effect = run_helper

                ok, result = get_host_current_location()

        self.assertFalse(ok)
        self.assertEqual(result, msg("here_fail_timeout"))

    def test_get_host_current_location_handles_invalid_response(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run"
            ) as run:
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                def run_helper(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                    if cmd[0] == "xcrun":
                        Path(cmd[-1]).write_text("binary", encoding="utf-8")
                    if cmd[0] == "open":
                        Path(cmd[-1]).write_text("not-json", encoding="utf-8")
                    return subprocess.CompletedProcess(cmd, 0, "", "")

                run.side_effect = run_helper

                ok, result = get_host_current_location()

        self.assertFalse(ok)
        self.assertEqual(result, msg("here_fail_invalid_response"))

    def test_get_host_current_location_handles_xcrun_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run", side_effect=FileNotFoundError
            ):
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                ok, result = get_host_current_location()

        self.assertFalse(ok)
        self.assertEqual(result, msg("here_fail_no_xcrun"))

    def test_get_host_current_location_handles_helper_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            helper_path = Path(td) / "host_location.swift"
            helper_path.write_text("import CoreLocation\n", encoding="utf-8")

            with patch("pinny.app._host_location_helper") as helper, patch(
                "pinny.app.importlib.resources.as_file"
            ) as as_file, patch("pinny.app._host_location_cache_root", return_value=Path(td) / "cache"), patch(
                "pinny.app.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["xcrun"], timeout=30),
            ):
                helper.return_value.is_file.return_value = True
                as_file.return_value.__enter__.return_value = helper_path
                as_file.return_value.__exit__.return_value = False

                ok, result = get_host_current_location()

        self.assertFalse(ok)
        self.assertEqual(result, msg("here_fail_helper_timeout"))

    def test_run_simctl_set_to_host_location_delegates_to_set(self) -> None:
        host_location = Location(37.551169, 126.988227, msg("here_host_description"))

        with patch("pinny.app.get_host_current_location", return_value=(True, host_location)), patch(
            "pinny.app.run_simctl_set_location", return_value=(True, "set ok")
        ) as run_set:
            ok, message = run_simctl_set_to_host_location()

        self.assertTrue(ok)
        run_set.assert_called_once_with(host_location)
        self.assertIn("37.551169", message)

    def test_run_simctl_set_to_host_location_returns_fetch_error(self) -> None:
        with patch(
            "pinny.app.get_host_current_location", return_value=(False, msg("here_fail_timeout"))
        ), patch("pinny.app.run_simctl_set_location") as run_set:
            ok, message = run_simctl_set_to_host_location()

        self.assertFalse(ok)
        run_set.assert_not_called()
        self.assertEqual(message, msg("here_fail_timeout"))

    def test_command_apply_index_uses_number(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            first = Location(37.551169, 126.988227, "남산타워")
            second = Location(48.85837, 2.294481, "에펠탑")
            save_locations([first, second], data_path)

            buffer = io.StringIO()
            with patch("pinny.app.run_simctl_set_location", return_value=(True, "ok")) as run_set:
                with redirect_stdout(buffer):
                    rc = command_apply_index(2, data_path=data_path)

            self.assertEqual(rc, 0)
            run_set.assert_called_once_with(second)
            self.assertIn("ok", buffer.getvalue())
            self.assertIn("에펠탑", buffer.getvalue())

    def test_main_default_and_number_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([Location(37.551169, 126.988227, "남산타워")], data_path)

            with patch.dict(os.environ, {"PINNY_DATA_PATH": str(data_path)}, clear=False):
                list_buffer = io.StringIO()
                with redirect_stdout(list_buffer):
                    rc = main([])
                self.assertEqual(rc, 0)
                self.assertIn("남산타워", list_buffer.getvalue())

                with patch("pinny.app.run_simctl_set_location", return_value=(True, "applied")):
                    apply_buffer = io.StringIO()
                    with redirect_stdout(apply_buffer):
                        rc = main(["1"])
                self.assertEqual(rc, 0)
                self.assertIn("applied", apply_buffer.getvalue())

    def test_command_apply_index_zero_uses_current_mac_location(self) -> None:
        buffer = io.StringIO()
        with patch("pinny.app.run_simctl_set_to_host_location", return_value=(True, "current ok")):
            with redirect_stdout(buffer):
                rc = command_apply_index(0)

        self.assertEqual(rc, 0)
        self.assertIn("current ok", buffer.getvalue())

    def test_command_apply_index_zero_prints_compile_notice_to_stderr(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        def fetch(progress=None):
            if progress is not None:
                progress(msg("here_compile_notice"))
            return False, "failed"

        with patch("pinny.app.get_host_current_location", side_effect=fetch), patch(
            "pinny.app.run_simctl_set_location"
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                rc = command_apply_index(0)

        self.assertEqual(rc, 0)
        self.assertIn("failed", stdout.getvalue())
        self.assertIn(msg("here_compile_notice"), stderr.getvalue())

    def test_main_zero_mode(self) -> None:
        buffer = io.StringIO()
        with patch("pinny.app.run_simctl_set_to_host_location", return_value=(True, "current applied")):
            with redirect_stdout(buffer):
                rc = main(["0"])

        self.assertEqual(rc, 0)
        self.assertIn("current applied", buffer.getvalue())

    def test_delete_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([Location(37.5532, 126.9837, "서울역")], data_path)

            app = PinnyTUI(data_path)
            app.menu_index = PinnyTUI.MENU_DELETE
            app.selected_row = 0

            app._action_delete_location()
            self.assertEqual(app.pending_delete_index, 0)
            self.assertEqual(len(app.locations), 1)

            self.assertTrue(app._handle_delete_confirmation("n"))
            self.assertIsNone(app.pending_delete_index)
            self.assertEqual(len(app.locations), 1)

            app._action_delete_location()
            self.assertTrue(app._handle_delete_confirmation("y"))
            self.assertIsNone(app.pending_delete_index)
            self.assertEqual(len(app.locations), 0)
            self.assertEqual(len(load_locations(data_path)), 0)

    def test_tui_here_action_updates_status_without_modifying_saved_locations(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([Location(37.5532, 126.9837, "서울역")], data_path)

            app = PinnyTUI(data_path)
            app.menu_index = PinnyTUI.MENU_HERE
            app.input_buffer = "123"
            app.input_cursor = 3

            with patch(
                "pinny.app.run_simctl_set_to_host_location", return_value=(True, "host applied")
            ) as here_run:
                app._action_here_location()

            here_run.assert_called_once_with()
            self.assertEqual(app.status, "host applied")
            self.assertEqual(app.input_buffer, "")
            self.assertEqual(app.input_cursor, 0)
            self.assertEqual(len(load_locations(data_path)), 1)
            self.assertEqual(load_locations(data_path)[0].description, "서울역")

    def test_tui_includes_here_menu(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            save_locations([Location(37.5532, 126.9837, "서울역")], data_path)

            app = PinnyTUI(data_path)

            self.assertEqual(app.menus[PinnyTUI.MENU_HERE], msg("menu_here"))
            self.assertEqual(app.menu_help[PinnyTUI.MENU_HERE], msg("help_here"))

    def test_command_add_cover_download_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            add_path = Path(td) / "add.json"
            cover_path = Path(td) / "cover.json"
            download_path = Path(td) / "downloaded_locations.json"

            add_payload = [
                {
                    "latitude": 37.5532,
                    "longitude": 126.9837,
                    "description": "서울역",
                },
                {
                    "latitude": 37.5532,
                    "longitude": 126.9837,
                    "description": "중복",
                },
            ]
            add_path.write_text(json.dumps(add_payload, ensure_ascii=False), encoding="utf-8")

            rc = command_add([str(add_path)], data_path=data_path)
            self.assertEqual(rc, 0)
            self.assertEqual(len(load_locations(data_path)), 1)

            cover_payload = [
                {
                    "lat": -62.222929,
                    "lon": -58.786059,
                    "desc": "남극 세종 과학기지",
                }
            ]
            cover_path.write_text(json.dumps(cover_payload, ensure_ascii=False), encoding="utf-8")

            rc = command_cover(str(cover_path), data_path=data_path)
            self.assertEqual(rc, 0)

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = command_download(data_path=data_path, output_path=download_path)
            self.assertEqual(rc, 0)
            self.assertIn(str(download_path), buffer.getvalue())
            self.assertTrue(download_path.exists())

            downloaded = json.loads(download_path.read_text(encoding="utf-8"))
            self.assertEqual(len(downloaded), 1)
            self.assertEqual(downloaded[0]["description"], "남극 세종 과학기지")


if __name__ == "__main__":
    unittest.main()
