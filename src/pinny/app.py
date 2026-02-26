from __future__ import annotations

import argparse
import curses
import importlib.resources
import json
import locale
import os
import re
import subprocess
import sys
import time
import unicodedata
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_PATH_ENV = "PINNY_DATA_PATH"
LANG_ENV = "PINNY_LANG"

I18N: dict[str, dict[str, str]] = {
    "ko": {
        "invalid_item_format": "{index}번째 항목의 형식이 올바르지 않습니다.",
        "invalid_item_coord": "{index}번째 항목의 위도/경도가 숫자가 아닙니다.",
        "invalid_item_desc": "{index}번째 항목의 설명이 비어 있습니다.",
        "json_root_invalid": "JSON 루트는 배열(list) 또는 locations 배열을 가진 객체여야 합니다.",
        "store_corrupted": "저장 파일이 손상되었습니다. 루트는 배열이어야 합니다.",
        "inline_format": "입력 형식: <latitude> <longitude> <description> (콤마 허용)",
        "inline_missing_desc": "설명을 입력하세요.",
        "seed_load_error": "기본 위치 목록을 불러오지 못했습니다: {detail}",
        "set_fail_no_xcrun": "설정 실패: xcrun 명령을 찾을 수 없습니다.",
        "set_done": "위치 설정 완료: {lat:.6f}, {lon:.6f}",
        "set_unknown_error": "알 수 없는 오류",
        "set_fail": "설정 실패: {detail}",
        "menu_set": "위치지정",
        "menu_add": "추가",
        "menu_delete": "삭제",
        "menu_sort": "정렬",
        "menu_exit": "종료",
        "help_set": "설정 : ↑↓ 이동 후 선택 혹은 번호 입력, Ctrl+O:지도 열기",
        "help_add": "추가 : <latitude> <longitude> <description>",
        "help_delete": "삭제 : ↑↓ 이동 후 Enter, y/n 확인",
        "help_sort": "정렬 : 1:Latitude   2:Longitude   3:Description",
        "help_exit": "종료 : Enter",
        "status_tab_hint": "좌/우 키로 메뉴를 변경하세요.",
        "status_ctrlc_again": "종료하려면 Ctrl+C를 한 번 더 누르세요.",
        "status_no_location_set": "설정할 위치가 없습니다.",
        "status_number_only": "번호를 숫자로 입력하세요.",
        "status_number_range": "번호 범위를 확인하세요.",
        "status_add_format_short": "입력 형식: <latitude> <longitude> <description>",
        "status_add_exists": "이미 존재하는 좌표입니다.",
        "status_add_done": "위치를 추가했습니다.",
        "status_no_location_delete": "삭제할 위치가 없습니다.",
        "status_delete_confirm": "[{no}] {lat:.6f}, {lon:.6f} {desc} 삭제? (y/n)",
        "status_delete_confirm_hint": "삭제 확인: y 또는 n 을 입력하세요.",
        "status_delete_done": "삭제 완료: {lat:.6f}, {lon:.6f} {desc}",
        "status_delete_cancel": "삭제를 취소했습니다.",
        "status_sort_choice": "정렬 번호를 입력하세요. 1:위도 2:경도 3:설명",
        "status_sort_lat_done": "위도 기준 정렬 완료",
        "status_sort_lon_done": "경도 기준 정렬 완료",
        "status_sort_desc_done": "설명 기준 정렬 완료",
        "menu_label": "메뉴(←/→) : ",
        "status_open_map_done": "브라우저에서 열기: {url}",
        "status_open_map_failed": "브라우저를 열지 못했습니다.",
        "status_open_map_error": "브라우저 열기 실패: {detail}",
        "input_label": "Pinny: ",
        "file_not_found": "파일을 찾을 수 없습니다: {path}",
        "add_usage": "add 사용법: pinny add <lat> <lon> <description> 또는 pinny add <list.json> (콤마 허용)",
        "add_from_file_done": "{count}개 추가됨 (중복 제외)",
        "add_single_done": "1개 추가됨",
        "cover_done": "{count}개로 덮어쓰기 완료",
        "download_done": "다운로드 완료: {path}",
        "cli_exists": "이미 존재하는 좌표입니다.",
        "argparse_desc": "xcrun simctl location 명령을 관리하기 쉬운 TUI/CLI 도구",
        "argparse_epilog": (
            "실행 예시:\n"
            "  pinny           보유 목록 표시\n"
            "  pinny 2         2번 위치 즉시 적용\n"
            "  pinny tui       TUI 실행\n"
            "  pinny add ...   위치 추가\n"
            "  pinny cover ... 전체 덮어쓰기\n"
            "  pinny download  locations.json 다운로드"
        ),
        "argparse_add_help": "위치 추가",
        "argparse_add_desc": "위치를 단건 또는 JSON 파일로 추가합니다.",
        "argparse_add_items_help": "<lat> <lon> <description> 또는 JSON 파일 경로",
        "argparse_add_epilog": (
            "JSON 파일 구조 예시:\n"
            "1) 배열 루트\n"
            '[\n  {{"latitude": 37.551169, "longitude": 126.988227, "description": "남산타워"}}\n]\n\n'
            "2) locations 키 사용 + 축약 키 허용\n"
            '{{\n  "locations": [\n    {{"lat": 48.858370, "lon": 2.294481, "desc": "파리 에펠탑"}}\n  ]\n}}'
        ),
        "argparse_cover_help": "JSON 목록으로 전체 덮어쓰기",
        "argparse_cover_desc": "JSON 파일로 전체 목록을 덮어씁니다.",
        "argparse_cover_path_help": "입력 JSON 파일",
        "argparse_download_help": "저장된 전체 목록을 locations.json 파일로 다운로드",
        "argparse_tui_help": "TUI 스타일 인터랙티브 실행",
        "json_error": "JSON 파싱 오류: {error}",
        "apply_usage": "사용법: pinny <번호>",
        "apply_done_with_desc": "{message} ({desc})",
    },
    "en": {
        "invalid_item_format": "Item {index} has an invalid format.",
        "invalid_item_coord": "Item {index} has a non-numeric latitude/longitude.",
        "invalid_item_desc": "Item {index} has an empty description.",
        "json_root_invalid": "JSON root must be a list or an object with a locations list.",
        "store_corrupted": "Saved data is corrupted. Root must be a list.",
        "inline_format": "Input format: <latitude> <longitude> <description> (comma allowed)",
        "inline_missing_desc": "Description is required.",
        "seed_load_error": "Failed to load default locations: {detail}",
        "set_fail_no_xcrun": "Set failed: xcrun command not found.",
        "set_done": "Location set: {lat:.6f}, {lon:.6f}",
        "set_unknown_error": "Unknown error",
        "set_fail": "Set failed: {detail}",
        "menu_set": "Set",
        "menu_add": "Add",
        "menu_delete": "Delete",
        "menu_sort": "Sort",
        "menu_exit": "Exit",
        "help_set": "Set: move with ↑↓ then Enter, type number, or press Ctrl+O for map",
        "help_add": "Add: <latitude> <longitude> <description>",
        "help_delete": "Delete: move with ↑↓ then Enter, confirm with y/n",
        "help_sort": "Sort: 1:Latitude   2:Longitude   3:Description",
        "help_exit": "Exit: Enter",
        "status_tab_hint": "Use left/right arrows to switch menus.",
        "status_ctrlc_again": "Press Ctrl+C once more to exit.",
        "status_no_location_set": "No location to set.",
        "status_number_only": "Enter a numeric index.",
        "status_number_range": "Index is out of range.",
        "status_add_format_short": "Input format: <latitude> <longitude> <description>",
        "status_add_exists": "Location already exists.",
        "status_add_done": "Location added.",
        "status_no_location_delete": "No location to delete.",
        "status_delete_confirm": "Delete [{no}] {lat:.6f}, {lon:.6f} {desc}? (y/n)",
        "status_delete_confirm_hint": "Delete confirmation: press y or n.",
        "status_delete_done": "Deleted: {lat:.6f}, {lon:.6f} {desc}",
        "status_delete_cancel": "Delete cancelled.",
        "status_sort_choice": "Enter sort option. 1:Latitude 2:Longitude 3:Description",
        "status_sort_lat_done": "Sorted by latitude.",
        "status_sort_lon_done": "Sorted by longitude.",
        "status_sort_desc_done": "Sorted by description.",
        "menu_label": "Menu(←/→) : ",
        "status_open_map_done": "Opened in browser: {url}",
        "status_open_map_failed": "Could not open browser.",
        "status_open_map_error": "Browser open failed: {detail}",
        "input_label": "Pinny: ",
        "file_not_found": "File not found: {path}",
        "add_usage": "Usage: pinny add <lat> <lon> <description> or pinny add <list.json> (comma allowed)",
        "add_from_file_done": "{count} added (duplicates skipped)",
        "add_single_done": "1 added",
        "cover_done": "Replaced with {count} items",
        "download_done": "Downloaded: {path}",
        "cli_exists": "Location already exists.",
        "argparse_desc": "TUI/CLI wrapper for xcrun simctl location",
        "argparse_epilog": (
            "Examples:\n"
            "  pinny           Show saved locations\n"
            "  pinny 2         Apply location #2\n"
            "  pinny tui       Run interactive TUI\n"
            "  pinny add ...   Add locations\n"
            "  pinny cover ... Replace all\n"
            "  pinny download  Download locations.json"
        ),
        "argparse_add_help": "Add location",
        "argparse_add_desc": "Add a single location or import from a JSON file.",
        "argparse_add_items_help": "<lat> <lon> <description> or JSON file path",
        "argparse_add_epilog": (
            "JSON file examples:\n"
            "1) list root\n"
            '[\n  {{"latitude": 37.551169, "longitude": 126.988227, "description": "Namsan Tower"}}\n]\n\n'
            "2) object with locations + short keys\n"
            '{{\n  "locations": [\n    {{"lat": 48.858370, "lon": 2.294481, "desc": "Eiffel Tower"}}\n  ]\n}}'
        ),
        "argparse_cover_help": "Replace all locations from JSON list",
        "argparse_cover_desc": "Replace all locations from a JSON file.",
        "argparse_cover_path_help": "Input JSON file",
        "argparse_download_help": "Download all saved locations as locations.json",
        "argparse_tui_help": "Run interactive TUI",
        "json_error": "JSON parse error: {error}",
        "apply_usage": "Usage: pinny <number>",
        "apply_done_with_desc": "{message} ({desc})",
    },
}


def _normalized_language(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    if lowered.startswith("ko"):
        return "ko"
    if lowered.startswith("en"):
        return "en"
    return None


def app_language() -> str:
    forced = _normalized_language(os.environ.get(LANG_ENV))
    if forced:
        return forced

    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        detected = _normalized_language(os.environ.get(key))
        if detected:
            return detected

    locale_name, _ = locale.getlocale()
    detected = _normalized_language(locale_name)
    if detected:
        return detected
    return "ko"


def msg(key: str, **kwargs: Any) -> str:
    language = app_language()
    template = I18N.get(language, I18N["ko"]).get(key, I18N["ko"][key])
    return template.format(**kwargs)


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "description": self.description,
        }

    def dedupe_key(self) -> tuple[float, float]:
        return (round(self.latitude, 6), round(self.longitude, 6))


def default_data_path() -> Path:
    if DATA_PATH_ENV in os.environ and os.environ[DATA_PATH_ENV].strip():
        return Path(os.environ[DATA_PATH_ENV]).expanduser()
    return Path.home() / ".pinny" / "locations.json"


def _parse_location_item(item: Any, index: int) -> Location:
    if isinstance(item, dict):
        lat = item.get("latitude", item.get("lat"))
        lon = item.get("longitude", item.get("lon"))
        desc = item.get("description", item.get("desc"))
    elif isinstance(item, list) and len(item) >= 3:
        lat, lon, desc = item[0], item[1], item[2]
    else:
        raise ValueError(msg("invalid_item_format", index=index))

    try:
        latitude = float(lat)
        longitude = float(lon)
    except (TypeError, ValueError) as exc:
        raise ValueError(msg("invalid_item_coord", index=index)) from exc

    description = str(desc).strip() if desc is not None else ""
    if not description:
        raise ValueError(msg("invalid_item_desc", index=index))

    return Location(latitude=latitude, longitude=longitude, description=description)


def load_json_locations(file_path: Path) -> list[Location]:
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = data.get("locations")

    if not isinstance(data, list):
        raise ValueError(msg("json_root_invalid"))

    return [_parse_location_item(item, idx + 1) for idx, item in enumerate(data)]


def load_locations(path: Path | None = None) -> list[Location]:
    data_path = path or default_data_path()
    if not data_path.exists():
        return []

    with data_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError(msg("store_corrupted"))

    return [_parse_location_item(item, idx + 1) for idx, item in enumerate(raw)]


def load_default_locations() -> list[Location]:
    try:
        data_text = (
            importlib.resources.files("pinny")
            .joinpath("default_locations.json")
            .read_text(encoding="utf-8")
        )
        raw = json.loads(data_text)
    except Exception as exc:
        raise ValueError(msg("seed_load_error", detail=str(exc))) from exc

    if not isinstance(raw, list):
        raise ValueError(msg("json_root_invalid"))
    return [_parse_location_item(item, idx + 1) for idx, item in enumerate(raw)]


def load_or_seed_locations(path: Path | None = None) -> list[Location]:
    data_path = path or default_data_path()
    locations = load_locations(data_path)
    if locations:
        return locations

    defaults = load_default_locations()
    if defaults:
        save_locations(defaults, data_path)
    return defaults


def save_locations(locations: list[Location], path: Path | None = None) -> None:
    data_path = path or default_data_path()
    data_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [location.to_dict() for location in locations]
    with data_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def merge_unique(existing: list[Location], new_items: list[Location]) -> tuple[list[Location], int]:
    merged = list(existing)
    seen = {location.dedupe_key() for location in existing}
    added_count = 0

    for item in new_items:
        key = item.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        added_count += 1

    return merged, added_count


def parse_inline_location(raw: str) -> Location:
    text = raw.strip()
    match = re.match(
        r"^([+-]?\d+(?:\.\d+)?)\s*,?\s*([+-]?\d+(?:\.\d+)?)\s+(.+)$",
        text,
    )
    if not match:
        raise ValueError(msg("inline_format"))

    latitude = float(match.group(1))
    longitude = float(match.group(2))
    description = match.group(3).strip()
    if not description:
        raise ValueError(msg("inline_missing_desc"))

    return Location(latitude, longitude, description)


def run_simctl_set_location(location: Location) -> tuple[bool, str]:
    cmd = [
        "xcrun",
        "simctl",
        "location",
        "booted",
        "set",
        f"{location.latitude:.6f},{location.longitude:.6f}",
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return False, msg("set_fail_no_xcrun")

    if proc.returncode == 0:
        return (
            True,
            msg("set_done", lat=location.latitude, lon=location.longitude),
        )

    stderr = proc.stderr.strip()
    stdout = proc.stdout.strip()
    detail = stderr or stdout or msg("set_unknown_error")
    short_detail = detail.splitlines()[-1]
    return False, msg("set_fail", detail=short_detail)


def format_locations_table(locations: list[Location]) -> list[str]:
    no_width = max(2, len(str(len(locations))))
    lines = [
        f"{'No':>{no_width}}  {'Latitude':>10}  {'Longitude':>11}  Description",
        "-" * 70,
    ]
    for idx, item in enumerate(locations, start=1):
        lines.append(
            f"{idx:>{no_width}}  {item.latitude:>10.6f}  {item.longitude:>11.6f}  {item.description}"
        )
    lines.append("-" * 70)
    return lines


class PinnyTUI:
    MENU_SET = 0
    MENU_ADD = 1
    MENU_DELETE = 2
    MENU_SORT = 3
    MENU_EXIT = 4

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.locations = load_or_seed_locations(data_path)
        self.menus = [
            msg("menu_set"),
            msg("menu_add"),
            msg("menu_delete"),
            msg("menu_sort"),
            msg("menu_exit"),
        ]
        self.menu_help = [
            msg("help_set"),
            msg("help_add"),
            msg("help_delete"),
            msg("help_sort"),
            msg("help_exit"),
        ]
        self.menu_index = 0
        self.selected_row = 0
        self.scroll_offset = 0
        self.pending_delete_index: int | None = None
        self.input_buffer = ""
        self.input_cursor = 0
        self.status = msg("status_tab_hint")
        self.last_ctrl_c_at = 0.0

    def run(self, stdscr: curses.window) -> None:
        curses.noecho()
        curses.raw()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.timeout(250)

        while True:
            self._render(stdscr)
            try:
                key = stdscr.get_wch()
            except curses.error:
                continue

            if key == "\x03":
                now = time.monotonic()
                if now - self.last_ctrl_c_at < 1.2:
                    return
                self.last_ctrl_c_at = now
                self.status = msg("status_ctrlc_again")
                continue

            if key == "\x0f" and self.menu_index == self.MENU_SET:
                self._action_open_in_maps()
                continue

            if self._handle_delete_confirmation(key):
                continue

            if key in ("\n", "\r", curses.KEY_ENTER):
                if self._run_current_menu_action():
                    return
                continue

            if key in ("\b", "\x7f", curses.KEY_BACKSPACE):
                if self.input_cursor > 0:
                    self.input_buffer = (
                        self.input_buffer[: self.input_cursor - 1]
                        + self.input_buffer[self.input_cursor :]
                    )
                    self.input_cursor -= 1
                continue

            if key == curses.KEY_UP:
                self._move_selection(-1)
                continue

            if key == curses.KEY_DOWN:
                self._move_selection(1)
                continue

            if key == curses.KEY_LEFT:
                if self._use_left_right_for_cursor():
                    self.input_cursor = max(0, self.input_cursor - 1)
                else:
                    self._move_menu(-1)
                continue

            if key == curses.KEY_RIGHT:
                if self._use_left_right_for_cursor():
                    self.input_cursor = min(len(self.input_buffer), self.input_cursor + 1)
                else:
                    self._move_menu(1)
                continue

            if key == curses.KEY_HOME:
                self.input_cursor = 0
                continue

            if key == curses.KEY_END:
                self.input_cursor = len(self.input_buffer)
                continue

            if key == curses.KEY_DC:
                if self.input_cursor < len(self.input_buffer):
                    self.input_buffer = (
                        self.input_buffer[: self.input_cursor]
                        + self.input_buffer[self.input_cursor + 1 :]
                    )
                continue

            self._append_input_if_valid(key)

    def _move_selection(self, delta: int) -> None:
        if not self.locations:
            self.selected_row = 0
            return
        if self.pending_delete_index is not None:
            self.pending_delete_index = None
            self.status = msg("status_delete_cancel")
        self.selected_row = max(0, min(len(self.locations) - 1, self.selected_row + delta))

    def _move_menu(self, delta: int) -> None:
        self.menu_index = (self.menu_index + delta) % len(self.menus)
        self.pending_delete_index = None
        self.input_buffer = ""
        self.input_cursor = 0
        self.status = ""

    def _use_left_right_for_cursor(self) -> bool:
        return self.menu_index in {self.MENU_SET, self.MENU_ADD, self.MENU_SORT} and bool(
            self.input_buffer
        )

    def _append_input_if_valid(self, key: int | str) -> None:
        if not isinstance(key, str):
            return

        if not key.isprintable():
            return

        char = key
        if self.menu_index == self.MENU_ADD:
            self.input_buffer = (
                self.input_buffer[: self.input_cursor]
                + char
                + self.input_buffer[self.input_cursor :]
            )
            self.input_cursor += 1
            return

        if self.menu_index in {self.MENU_SET, self.MENU_SORT} and char.isdigit():
            self.input_buffer = (
                self.input_buffer[: self.input_cursor]
                + char
                + self.input_buffer[self.input_cursor :]
            )
            self.input_cursor += 1

    def _handle_delete_confirmation(self, key: int | str) -> bool:
        if self.menu_index != self.MENU_DELETE or self.pending_delete_index is None:
            return False
        if not isinstance(key, str):
            return False

        lowered = key.lower()
        if lowered == "y":
            self._confirm_delete_location()
            return True
        if lowered == "n":
            self.pending_delete_index = None
            self.status = msg("status_delete_cancel")
            return True
        return False

    def _run_current_menu_action(self) -> bool:
        if self.menu_index == self.MENU_SET:
            self._action_set_location()
            return False
        if self.menu_index == self.MENU_ADD:
            self._action_add_location()
            return False
        if self.menu_index == self.MENU_DELETE:
            self._action_delete_location()
            return False
        if self.menu_index == self.MENU_SORT:
            self._action_sort_locations()
            return False
        return True

    def _resolve_target_index(self) -> int | None:
        if not self.locations:
            self.status = msg("status_no_location_set")
            self.input_buffer = ""
            self.input_cursor = 0
            return None

        target_index = self.selected_row
        raw = self.input_buffer.strip()
        if raw:
            try:
                target_no = int(raw)
            except ValueError:
                self.status = msg("status_number_only")
                self.input_buffer = ""
                self.input_cursor = 0
                return None
            target_index = target_no - 1

        if target_index < 0 or target_index >= len(self.locations):
            self.status = msg("status_number_range")
            self.input_buffer = ""
            self.input_cursor = 0
            return None

        self.selected_row = target_index
        return target_index

    def _action_set_location(self) -> None:
        target_index = self._resolve_target_index()
        if target_index is None:
            return

        location = self.locations[target_index]
        _, message = run_simctl_set_location(location)
        self.status = message
        self.input_buffer = ""
        self.input_cursor = 0

    def _action_open_in_maps(self) -> None:
        target_index = self._resolve_target_index()
        if target_index is None:
            return

        location = self.locations[target_index]
        url = f"https://www.google.com/maps/search/?api=1&query={location.latitude:.6f},{location.longitude:.6f}"
        try:
            opened = webbrowser.open(url, new=2)
        except Exception as exc:
            self.status = msg("status_open_map_error", detail=str(exc))
            return

        if opened:
            self.status = msg("status_open_map_done", url=url)
        else:
            self.status = msg("status_open_map_failed")

    def _action_add_location(self) -> None:
        raw = self.input_buffer.strip()
        if not raw:
            self.status = msg("status_add_format_short")
            return

        try:
            location = parse_inline_location(raw)
        except ValueError:
            self.status = msg("inline_format")
            return

        merged, added_count = merge_unique(self.locations, [location])
        self.locations = merged
        if added_count == 0:
            self.status = msg("status_add_exists")
        else:
            save_locations(self.locations, self.data_path)
            self.selected_row = len(self.locations) - 1
            self.status = msg("status_add_done")
        self.input_buffer = ""
        self.input_cursor = 0

    def _action_delete_location(self) -> None:
        if not self.locations:
            self.status = msg("status_no_location_delete")
            return

        if self.pending_delete_index is not None:
            self.status = msg("status_delete_confirm_hint")
            return

        self.pending_delete_index = self.selected_row
        target = self.locations[self.pending_delete_index]
        self.status = msg(
            "status_delete_confirm",
            no=self.pending_delete_index + 1,
            lat=target.latitude,
            lon=target.longitude,
            desc=target.description,
        )
        self.input_buffer = ""
        self.input_cursor = 0

    def _confirm_delete_location(self) -> None:
        if self.pending_delete_index is None:
            self.status = msg("status_delete_confirm_hint")
            return
        if self.pending_delete_index < 0 or self.pending_delete_index >= len(self.locations):
            self.pending_delete_index = None
            self.status = msg("status_number_range")
            return

        removed = self.locations.pop(self.pending_delete_index)
        self.pending_delete_index = None
        save_locations(self.locations, self.data_path)
        if self.selected_row >= len(self.locations):
            self.selected_row = max(0, len(self.locations) - 1)

        self.status = msg(
            "status_delete_done",
            lat=removed.latitude,
            lon=removed.longitude,
            desc=removed.description,
        )
        self.input_buffer = ""
        self.input_cursor = 0

    def _action_sort_locations(self) -> None:
        raw = self.input_buffer.strip()
        if raw not in {"1", "2", "3"}:
            self.status = msg("status_sort_choice")
            return

        if raw == "1":
            self.locations.sort(key=lambda item: item.latitude)
            message = msg("status_sort_lat_done")
        elif raw == "2":
            self.locations.sort(key=lambda item: item.longitude)
            message = msg("status_sort_lon_done")
        else:
            self.locations.sort(key=lambda item: item.description)
            message = msg("status_sort_desc_done")

        save_locations(self.locations, self.data_path)
        self.selected_row = 0
        self.scroll_offset = 0
        self.status = message
        self.input_buffer = ""
        self.input_cursor = 0

    def _render(self, stdscr: curses.window) -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()

        no_width = max(2, len(str(len(self.locations))))
        header = f"{'No':>{no_width}}  {'Latitude':>10}  {'Longitude':>11}  Description"
        self._safe_add(stdscr, 0, 0, header)
        self._safe_add(stdscr, 1, 0, "-" * max(10, min(width - 1, 70)))

        footer_lines = 6
        max_table_rows = max(1, height - (2 + footer_lines))
        table_rows = min(max_table_rows, max(5, len(self.locations)))

        if self.selected_row < self.scroll_offset:
            self.scroll_offset = self.selected_row
        if self.selected_row >= self.scroll_offset + table_rows:
            self.scroll_offset = self.selected_row - table_rows + 1

        visible = self.locations[self.scroll_offset : self.scroll_offset + table_rows]
        table_y = 2

        for local_idx, item in enumerate(visible):
            global_idx = self.scroll_offset + local_idx
            line = (
                f"{global_idx + 1:>{no_width}}  "
                f"{item.latitude:>10.6f}  "
                f"{item.longitude:>11.6f}  "
                f"{item.description}"
            )
            attr = 0
            if self.menu_index in {self.MENU_SET, self.MENU_DELETE} and global_idx == self.selected_row:
                attr = curses.A_REVERSE
            self._safe_add(stdscr, table_y + local_idx, 0, line, attr)

        menu_top = table_y + table_rows
        self._safe_add(stdscr, menu_top, 0, "-" * max(10, min(width - 1, 70)))

        menu_prefix = msg("menu_label")
        self._safe_add(stdscr, menu_top + 1, 0, menu_prefix)
        menu_x = self._display_width(menu_prefix)
        for idx, menu in enumerate(self.menus):
            if idx > 0:
                self._safe_add(stdscr, menu_top + 1, menu_x, " ")
                menu_x += 1
            label = f"[{menu}]"
            attr = curses.A_REVERSE if idx == self.menu_index else 0
            self._safe_add(stdscr, menu_top + 1, menu_x, label, attr)
            menu_x += self._display_width(label)
        self._safe_add(stdscr, menu_top + 2, 0, self.menu_help[self.menu_index])
        self._safe_add(stdscr, menu_top + 3, 0, "-" * max(10, min(width - 1, 70)))
        self._safe_add(stdscr, menu_top + 4, 0, self.status)

        input_prefix = msg("input_label")
        input_y = menu_top + 5
        self._safe_add(stdscr, input_y, 0, f"{input_prefix}{self.input_buffer}")

        cursor_x = self._display_width(input_prefix) + self._display_width(
            self.input_buffer[: self.input_cursor]
        )
        cursor_x = max(0, min(cursor_x, max(0, width - 2)))
        if 0 <= input_y < height:
            try:
                stdscr.move(input_y, cursor_x)
            except curses.error:
                pass

        stdscr.refresh()

    @staticmethod
    def _display_width(text: str) -> int:
        total = 0
        for char in text:
            if unicodedata.combining(char):
                continue
            if unicodedata.east_asian_width(char) in {"F", "W"}:
                total += 2
            else:
                total += 1
        return total

    @staticmethod
    def _safe_add(
        stdscr: curses.window,
        y: int,
        x: int,
        text: str,
        attr: int = 0,
    ) -> None:
        height, width = stdscr.getmaxyx()
        if y < 0 or y >= height or x >= width:
            return
        limit = max(0, width - x - 1)
        if limit == 0:
            return
        try:
            stdscr.addnstr(y, x, text, limit, attr)
        except curses.error:
            return


def run_tui(data_path: Path | None = None) -> int:
    path = data_path or default_data_path()

    def _runner(stdscr: curses.window) -> None:
        app = PinnyTUI(path)
        app.run(stdscr)

    try:
        curses.wrapper(_runner)
    except KeyboardInterrupt:
        return 0
    return 0


def command_add(items: list[str], data_path: Path | None = None) -> int:
    path = data_path or default_data_path()
    existing = load_locations(path)

    if len(items) == 1:
        source_path = Path(items[0]).expanduser()
        if source_path.exists() and source_path.is_file():
            new_locations = load_json_locations(source_path)
            merged, added_count = merge_unique(existing, new_locations)
            save_locations(merged, path)
            print(msg("add_from_file_done", count=added_count))
            return 0

    try:
        location = parse_inline_location(" ".join(items))
    except ValueError:
        print(msg("add_usage"), file=sys.stderr)
        return 2

    merged, added_count = merge_unique(existing, [location])
    save_locations(merged, path)
    if added_count == 0:
        print(msg("cli_exists"))
    else:
        print(msg("add_single_done"))
    return 0


def command_cover(json_path: str, data_path: Path | None = None) -> int:
    source_path = Path(json_path).expanduser()
    if not source_path.exists() or not source_path.is_file():
        print(msg("file_not_found", path=source_path), file=sys.stderr)
        return 2

    locations = load_json_locations(source_path)
    save_locations(locations, data_path)
    print(msg("cover_done", count=len(locations)))
    return 0


def command_download(data_path: Path | None = None, output_path: Path | None = None) -> int:
    locations = load_locations(data_path)
    payload = [location.to_dict() for location in locations]
    target = output_path or (Path.cwd() / "locations.json")
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(msg("download_done", path=target))
    return 0


def command_list(data_path: Path | None = None) -> int:
    locations = load_or_seed_locations(data_path)
    for line in format_locations_table(locations):
        print(line)
    return 0


def command_apply_index(index: int, data_path: Path | None = None) -> int:
    locations = load_or_seed_locations(data_path)
    target_index = index - 1
    if target_index < 0 or target_index >= len(locations):
        print(msg("status_number_range"), file=sys.stderr)
        return 2

    target = locations[target_index]
    ok, message = run_simctl_set_location(target)
    if ok:
        print(msg("apply_done_with_desc", message=message, desc=target.description))
    else:
        print(message)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pinny",
        description=msg("argparse_desc"),
        epilog=msg("argparse_epilog"),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser(
        "add",
        help=msg("argparse_add_help"),
        description=msg("argparse_add_desc"),
        epilog=msg("argparse_add_epilog"),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_parser.add_argument(
        "items",
        nargs="+",
        help=msg("argparse_add_items_help"),
    )

    cover_parser = subparsers.add_parser(
        "cover",
        help=msg("argparse_cover_help"),
        description=msg("argparse_cover_desc"),
        epilog=msg("argparse_add_epilog"),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    cover_parser.add_argument("json_path", help=msg("argparse_cover_path_help"))

    subparsers.add_parser("download", help=msg("argparse_download_help"))
    subparsers.add_parser("tui", help=msg("argparse_tui_help"))

    return parser


def main(argv: list[str] | None = None) -> int:
    raw_argv = argv if argv is not None else sys.argv[1:]

    try:
        if len(raw_argv) == 0:
            return command_list()

        if raw_argv[0].isdigit():
            if len(raw_argv) != 1:
                print(msg("apply_usage"), file=sys.stderr)
                return 2
            return command_apply_index(int(raw_argv[0]))

        parser = build_parser()
        args = parser.parse_args(raw_argv)
        if args.command == "add":
            return command_add(args.items)
        if args.command == "cover":
            return command_cover(args.json_path)
        if args.command == "download":
            return command_download()
        if args.command == "tui":
            return run_tui()
        return command_list()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(msg("json_error", error=exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
