import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pinny.app import (
    Location,
    PinnyTUI,
    app_language,
    command_add,
    command_cover,
    command_download,
    load_default_locations,
    load_json_locations,
    load_locations,
    merge_unique,
    msg,
    parse_inline_location,
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

    def test_command_add_cover_download_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            data_path = Path(td) / "locations.json"
            add_path = Path(td) / "add.json"
            cover_path = Path(td) / "cover.json"

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
                rc = command_download(data_path=data_path)
            self.assertEqual(rc, 0)

            downloaded = json.loads(buffer.getvalue())
            self.assertEqual(len(downloaded), 1)
            self.assertEqual(downloaded[0]["description"], "남극 세종 과학기지")


if __name__ == "__main__":
    unittest.main()
