#!/usr/bin/env python3
"""A rainbow 3D terminal UI with keyboard-driven panels."""

from __future__ import annotations

import argparse
import json
import math
import msvcrt
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import time


SHADES = " .,-~:;=!*#$@"
RESET = "\x1b[0m"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CLEAR = "\x1b[2J"
HOME = "\x1b[H"
TASK_REFRESH_SECONDS = 1.5
SURFACE_BG = (8, 10, 18)
PANEL_BG = (13, 16, 28)
PANEL_BG_ALT = (18, 22, 36)
TEXT_MAIN = (235, 241, 255)
TEXT_MUTED = (150, 166, 196)
ACCENT = (255, 176, 92)
ACCENT_2 = (96, 213, 255)
SUCCESS = (123, 233, 161)
WARNING = (255, 138, 138)
ACTIVE_PREFIX = "__ACTIVE__ "
JOJO_REFERENCES = [
    "It was me, Dio!",
    "Good grief...",
    "That's a nice watch, but I'll break it so you can never see the time on it again. By that, I mean I'll break your face.",
    "I've returned from hell, Dio!",
    "You were two steps too late.",
    "The goddess of victory is already riding on my saddle",
    "Watch JOJO to change your life.",
    "Dio is straight!",
    "Why is heart-attack taking so long?",
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def fg_rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m"


def bg_rgb(r: int, g: int, b: int) -> str:
    return f"\x1b[48;2;{r};{g};{b}m"


def style(text: str, fg: tuple[int, int, int] | None = None, bg: tuple[int, int, int] | None = None, bold: bool = False) -> str:
    parts: list[str] = []
    if bold:
        parts.append("\x1b[1m")
    if fg:
        parts.append(fg_rgb(*fg))
    if bg:
        parts.append(bg_rgb(*bg))
    parts.append(text)
    parts.append(RESET)
    return "".join(parts)


def visible_len(text: str) -> int:
    length = 0
    in_escape = False
    for char in text:
        if char == "\x1b":
            in_escape = True
            continue
        if in_escape:
            if char == "m":
                in_escape = False
            continue
        length += 1
    return length


def pad_styled(text: str, width: int) -> str:
    return text + (" " * max(0, width - visible_len(text)))


def chip(label: str, fg: tuple[int, int, int], bg: tuple[int, int, int], *, bold: bool = True) -> str:
    return style(f" {label} ", fg=fg, bg=bg, bold=bold)


def is_task_row(line: str) -> bool:
    return line.startswith(ACTIVE_PREFIX) or line.startswith("  ")


def get_rotating_subtitle(now: float | None = None) -> str:
    timestamp = time.time() if now is None else now
    index = int(timestamp // 30) % len(JOJO_REFERENCES)
    return JOJO_REFERENCES[index]


def rainbow_rgb(angle: float, light: float) -> tuple[int, int, int]:
    light = clamp((light + 1.0) / 2.0, 0.22, 1.0)
    red = int((math.sin(angle) * 0.5 + 0.5) * 255 * light)
    green = int((math.sin(angle + 2.094) * 0.5 + 0.5) * 255 * light)
    blue = int((math.sin(angle + 4.188) * 0.5 + 0.5) * 255 * light)
    return red, green, blue


def build_c8_points() -> list[tuple[float, float, float, str]]:
    glyphs = [
        "  CCCC     8888  ",
        " CC   CC  88  88 ",
        "CC        88  88 ",
        "CC         8888  ",
        "CC        88  88 ",
        " CC   CC  88  88 ",
        "  CCCC     8888  ",
    ]
    points: list[tuple[float, float, float, str]] = []
    height = len(glyphs)
    width = max(len(row) for row in glyphs)
    for row_index, row in enumerate(glyphs):
        for col_index, char in enumerate(row):
            if char == " ":
                continue
            x = (col_index - width / 2) * 0.22
            y = (height / 2 - row_index) * 0.42
            layer = 0.14 if char == "8" else -0.14
            points.append((x, y, layer, char))
            points.append((x, y, -layer, char))
    return points


C8_POINTS = build_c8_points()


def render_c8(width: int, height: int, ax: float, az: float, hue_shift: float, scale: float) -> str:
    zbuffer = [-1e9] * (width * height)
    chars = [" "] * (width * height)
    colors = [""] * (width * height)

    cosx = math.cos(ax)
    sinx = math.sin(ax)
    cosz = math.cos(az)
    sinz = math.sin(az)

    cosy = math.cos(ax * 0.6)
    siny = math.sin(ax * 0.6)

    for index, (x, y, z, char) in enumerate(C8_POINTS):
        x1 = x * cosy + z * siny
        z1 = -x * siny + z * cosy

        y2 = y * cosx - z1 * sinx
        z2 = y * sinx + z1 * cosx

        x3 = x1 * cosz - y2 * sinz
        y3 = x1 * sinz + y2 * cosz

        depth = z2 + 4.8
        inv_depth = 1.0 / depth

        xp = int(width / 2 + scale * inv_depth * x3 * 2.1)
        yp = int(height / 2 - scale * inv_depth * y3 * 1.1)

        if 0 <= xp < width and 0 <= yp < height:
            idx = xp + yp * width
            if inv_depth > zbuffer[idx]:
                zbuffer[idx] = inv_depth
                chars[idx] = char
                luminance = clamp(0.55 + z2 * 0.45, 0.0, 1.0)
                r, g, b = rainbow_rgb(index * 0.16 + hue_shift, luminance)
                colors[idx] = fg_rgb(r, g, b)

    lines: list[str] = []
    for row in range(height):
        start = row * width
        line: list[str] = []
        current_color = None
        for col in range(width):
            idx = start + col
            color = colors[idx]
            char = chars[idx]
            if char == " ":
                if current_color is not None:
                    line.append(RESET)
                    current_color = None
                line.append(" ")
                continue
            if color != current_color:
                line.append(color)
                current_color = color
            line.append(char)
        if current_color is not None:
            line.append(RESET)
        lines.append("".join(line))
    return "\n".join(lines)


def read_key() -> str | None:
    if not msvcrt.kbhit():
        return None
    key = msvcrt.getwch()
    if key in ("\x00", "\xe0"):
        special = msvcrt.getwch()
        if special == "H":
            return "up"
        if special == "P":
            return "down"
        return None
    return key.lower()


def get_memory_info() -> tuple[str, str]:
    if os.name != "nt":
        return "unknown", "unknown"
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)"],
            text=True,
            timeout=3,
        ).strip()
        total_gb = f"{output} GB"
    except Exception:
        total_gb = "unknown"
    try:
        vm = shutil.disk_usage(os.path.abspath(os.sep))
        disk = f"{vm.total // (1024 ** 3)} GB total"
    except OSError:
        disk = "unknown"
    return total_gb, disk


def get_gpu_name() -> str:
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name)"],
            text=True,
            timeout=3,
        ).strip()
        return output or "unknown"
    except Exception:
        return "unknown"


def get_cpu_name() -> str:
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"],
            text=True,
            timeout=3,
        ).strip()
        return output or "unknown"
    except Exception:
        return "unknown"


def get_pc_configuration() -> list[str]:
    total_ram, disk_total = get_memory_info()
    return [
        f"Machine: {platform.node() or 'unknown'}",
        f"OS: {platform.system()} {platform.release()} ({platform.version()})",
        f"CPU: {get_cpu_name()}",
        f"Architecture: {' '.join(platform.architecture())}",
        f"RAM: {total_ram}",
        f"Disk: {disk_total}",
        f"GPU: {get_gpu_name()}",
    ]


def get_task_snapshot_data() -> list[dict[str, object]]:
    if os.name != "nt":
        return []

    command = (
        "Get-Process | "
        "Sort-Object CPU -Descending | "
        "Select-Object "
        "@{Name='Name';Expression={$_.ProcessName}},"
        "@{Name='Pid';Expression={$_.Id}},"
        "@{Name='Cpu';Expression={if ($_.CPU -ne $null) { [math]::Round($_.CPU, 1) } else { 0 }}},"
        "@{Name='MemoryMb';Expression={[math]::Round($_.WS / 1MB, 1)}} | "
        "ConvertTo-Json -Compress"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            timeout=3,
        )
    except Exception:
        return []

    text = output.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def get_process_details(pid: int) -> list[str]:
    if os.name != "nt":
        return ["Process details are only implemented for Windows terminals."]
    command = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($null -eq $p) { '' } else { "
        "@{"
        "Name=$p.Name;"
        "Pid=$p.ProcessId;"
        "Path=$p.ExecutablePath;"
        "CommandLine=$p.CommandLine;"
        "ParentPid=$p.ParentProcessId;"
        "} | ConvertTo-Json -Compress }"
    )
    try:
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            timeout=3,
        ).strip()
    except Exception:
        return ["Could not load process details."]
    if not output:
        return ["The selected process is no longer running."]
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return ["Could not parse process details."]
    return [
        f"Name: {data.get('Name') or 'unknown'}",
        f"PID: {data.get('Pid') or pid}",
        f"Parent PID: {data.get('ParentPid') or 'unknown'}",
        f"Path: {data.get('Path') or 'unavailable'}",
        f"Command: {data.get('CommandLine') or 'unavailable'}",
    ]


def terminate_process(pid: int) -> str:
    try:
        subprocess.check_call(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=4,
        )
        return f"Terminated process {pid}."
    except Exception:
        return f"Could not terminate process {pid}."


def open_process_location(pid: int) -> str:
    if os.name != "nt":
        return "Open file location is only available on Windows."
    command = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($null -eq $p -or [string]::IsNullOrWhiteSpace($p.ExecutablePath)) { '' } else { $p.ExecutablePath }"
    )
    try:
        path = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            timeout=3,
        ).strip()
    except Exception:
        return "Could not resolve the process path."
    if not path:
        return "No executable path is available for this process."
    try:
        subprocess.Popen(["explorer.exe", "/select,", path])
        return f"Opened file location for PID {pid}."
    except Exception:
        return "Explorer could not open that process location."


def build_task_panel(
    task_data: list[dict[str, object]],
    selected_index: int,
    message: str,
    width: int,
    max_rows: int,
) -> tuple[str, list[str]]:
    if not task_data:
        return "Task Manager", ["No process data available right now."]

    visible_rows = max(4, max_rows)
    start_index = 0
    if selected_index >= visible_rows:
        start_index = selected_index - visible_rows + 1
    end_index = min(len(task_data), start_index + visible_rows)

    rows = [
        f"Processes {start_index + 1}-{end_index} of {len(task_data)}",
        "Up/Down or J/K scroll. D details. X end. O open location.",
        "",
    ]
    max_name = max(12, min(22, width // 4))
    for index in range(start_index, end_index):
        item = task_data[index]
        name = str(item.get("Name") or "unknown")[:max_name].ljust(max_name)
        pid = str(item.get("Pid") or "?").rjust(6)
        cpu = str(item.get("Cpu") or 0).rjust(7)
        mem = str(item.get("MemoryMb") or 0).rjust(7)
        line = f"{name} PID {pid}  CPU {cpu}  RAM {mem} MB"
        if index == selected_index:
            rows.append(f"{ACTIVE_PREFIX}{line}")
        else:
            rows.append(f"  {line}")
    if message:
        rows.extend(["", f"Status: {message}"])
    return "Task Manager", rows


def panel_content(
    panel: str,
    start_time: float,
    fps: float,
    frame: int,
    task_data: list[dict[str, object]],
    selected_index: int,
    task_message: str,
    detail_lines: list[str] | None,
    task_visible_rows: int,
) -> tuple[str, list[str]]:
    if panel == "config":
        return "PC Configuration", get_pc_configuration()
    if panel == "tasks":
        return build_task_panel(task_data, selected_index, task_message, 100, task_visible_rows)
    if panel == "task_details":
        return "Process Details", detail_lines or ["No process selected."]
    if panel == "help":
        return (
            "Help / Keybinds",
            [
                "A  Show PC configuration",
                "T  Show task manager",
                "Up/Down or J/K  Select process in task manager",
                "D  Process details",
                "X  End selected process",
                "O  Open selected file location",
                "H  Show this help screen",
                "M  Return to main menu",
                "Q  Quit the app",
            ],
        )
    return (
        "CLI",
        [
            "A  PC configuration",
            "T  Task manager",
            "D  Task details in task manager",
            "X  End selected task",
            "O  Open selected task file location",
            "H  Help and keybinds",
            "Q  Quit",
            "",
            "I should really make an option to disable the 3D animation :P",
            "Use the menu keys at any time.",
        ],
    )


def panel_lines(
    width: int,
    panel: str,
    start_time: float,
    fps: float,
    frame: int,
    task_data: list[dict[str, object]],
    selected_index: int,
    task_message: str,
    detail_lines: list[str] | None,
    panel_height: int,
) -> list[str]:
    task_visible_rows = max(3, panel_height - 10)
    title, content = panel_content(
        panel,
        start_time,
        fps,
        frame,
        task_data,
        selected_index,
        task_message,
        detail_lines,
        task_visible_rows,
    )
    panel_width = min(max(64, width - 6), width)
    inner_width = max(32, panel_width - 4)
    wrapped: list[str] = []
    for line in content:
        if not line:
            wrapped.append("")
            continue
        if panel == "tasks" and is_task_row(line):
            wrapped.append(line[:inner_width])
            continue
        wrapped.extend(textwrap.wrap(line, inner_width) or [""])
    import random

    jojo_reference = random.choice([
        "It was me, Dio!",
        "Good grief...",
        "That's a nice watch, but I'll break it so you can never see the time on it again. By that, I mean I'll break your face.",
        "I’ve returned from hell, Dio!",
        "You were two steps too late.",
        "The goddess of victory is already riding on my saddle",
        "Watch JOJO to change your life.",
        "Dio is straight!",
        "Why is heart-attack taking so long?"
    ])

    title_chip = chip(title.upper(), (7, 10, 18), ACCENT)
    subtitle_chip = chip(get_rotating_subtitle(), TEXT_MAIN, PANEL_BG_ALT, bold=False)
    header_text = pad_styled(f"{title_chip}  {subtitle_chip}", inner_width)

    actions = [
        chip("A Config", (7, 10, 18), ACCENT),
        chip("T Tasks", (7, 10, 18), ACCENT),
        chip("D Details", (7, 10, 18), ACCENT),
        chip("X End", WARNING, PANEL_BG_ALT),
        chip("O Open", ACCENT_2, PANEL_BG_ALT),
        chip("H Help", TEXT_MAIN, PANEL_BG_ALT),
        chip("M Menu", TEXT_MAIN, PANEL_BG_ALT),
        chip("Q Quit", TEXT_MAIN, PANEL_BG_ALT),
    ]

    action_rows: list[str] = []
    current = ""
    for item in actions:
        spacer = "" if not current else " "
        if visible_len(current + spacer + item) > inner_width:
            action_rows.append(pad_styled(current, inner_width))
            current = item
        else:
            current = current + spacer + item
    if current:
        action_rows.append(pad_styled(current, inner_width))

    rows = [
        style(" " + (" " * inner_width) + " ", bg=PANEL_BG),
        style(" ", bg=PANEL_BG) + style(header_text, fg=TEXT_MAIN, bg=PANEL_BG, bold=True) + style(" ", bg=PANEL_BG),
        style(" ", bg=PANEL_BG) + style((" " * inner_width), fg=TEXT_MUTED, bg=PANEL_BG) + style(" ", bg=PANEL_BG),
    ]

    content_budget = max(1, panel_height - 6 - len(action_rows))
    visible_content = wrapped[:content_budget]
    while len(visible_content) < content_budget:
        visible_content.append("")

    for line in visible_content:
        tone = TEXT_MUTED if line.startswith("Status:") else TEXT_MAIN
        if line.startswith(ACTIVE_PREFIX):
            row = chip("ACTIVE", (7, 10, 18), SUCCESS) + " " + style(line[len(ACTIVE_PREFIX):], fg=TEXT_MAIN, bg=PANEL_BG_ALT, bold=True)
            row = pad_styled(row, inner_width)
            rows.append(style(" ", bg=PANEL_BG) + style(row, bg=PANEL_BG_ALT) + style(" ", bg=PANEL_BG))
            continue
        if line.startswith("Name:") or line.startswith("PID:") or line.startswith("Parent PID:") or line.startswith("Path:") or line.startswith("Command:"):
            key, _, value = line.partition(": ")
            rendered = style(f"{key}:", fg=ACCENT_2, bg=PANEL_BG, bold=True) + style(f" {value}", fg=TEXT_MAIN, bg=PANEL_BG)
            rows.append(style(" ", bg=PANEL_BG) + pad_styled(rendered, inner_width) + style(" ", bg=PANEL_BG))
            continue
        rows.append(style(" ", bg=PANEL_BG) + style(line.ljust(inner_width), fg=tone, bg=PANEL_BG) + style(" ", bg=PANEL_BG))

    rows.append(style(" " + (" " * inner_width) + " ", bg=PANEL_BG))
    for action_row in action_rows:
        rows.append(style(" ", bg=PANEL_BG) + style(action_row, bg=PANEL_BG) + style(" ", bg=PANEL_BG))
    rows.append(style(" " + (" " * inner_width) + " ", bg=PANEL_BG))
    left_padding = max(0, (width - panel_width) // 2)
    return [(" " * left_padding) + row for row in rows]


def compose_screen(
    width: int,
    scene_height: int,
    frame_text: str,
    panel_rows: list[str],
) -> str:
    scene_lines = frame_text.splitlines()
    merged = []
    for row in range(scene_height):
        merged.append(scene_lines[row] if row < len(scene_lines) else " " * width)

    separator = (
        style(" ", bg=SURFACE_BG)
        + style(" " * 2, bg=SURFACE_BG)
        + style("LIVE", fg=(7, 10, 18), bg=ACCENT, bold=True)
        + style("  --version 1.0", fg=TEXT_MUTED, bg=SURFACE_BG)
        + style(" " * max(0, width - 20), bg=SURFACE_BG)
    )
    merged.append(separator)

    for row in panel_rows:
        merged.append(row)
    return "\n".join(merged)


def run_ui(fps: float, width: int | None, height: int | None) -> int:
    start_time = time.time()
    panel = "menu"
    frame = 0
    task_data: list[dict[str, object]] = []
    selected_index = 0
    task_message = ""
    detail_lines: list[str] | None = None
    last_task_refresh = 0.0
    panel_height = 16

    os.system("cls")
    sys.stdout.write(HIDE_CURSOR + CLEAR)
    sys.stdout.flush()

    try:
        while True:
            term_size = shutil.get_terminal_size((100, 34))
            render_width = width or max(60, term_size.columns)
            total_height = height or max(20, term_size.lines - 1)

            key = read_key()
            now = time.time()
            if panel in {"tasks", "task_details"} and (not task_data or now - last_task_refresh >= TASK_REFRESH_SECONDS):
                task_data = get_task_snapshot_data()
                last_task_refresh = now
                if task_data:
                    selected_index = min(selected_index, len(task_data) - 1)
                else:
                    selected_index = 0

            if key == "q":
                break
            if key == "a":
                panel = "config"
            elif key == "t":
                panel = "tasks"
                detail_lines = None
            elif key == "h":
                panel = "help"
            elif key == "m":
                panel = "menu"
            elif key in {"up", "k"} and panel in {"tasks", "task_details"} and task_data:
                selected_index = max(0, selected_index - 1)
                task_message = f"Selected PID {task_data[selected_index].get('Pid')}."
                if panel == "task_details":
                    detail_lines = get_process_details(int(task_data[selected_index]["Pid"]))
            elif key in {"down", "j"} and panel in {"tasks", "task_details"} and task_data:
                selected_index = min(len(task_data) - 1, selected_index + 1)
                task_message = f"Selected PID {task_data[selected_index].get('Pid')}."
                if panel == "task_details":
                    detail_lines = get_process_details(int(task_data[selected_index]["Pid"]))
            elif key == "d" and panel in {"tasks", "task_details"} and task_data:
                pid = int(task_data[selected_index]["Pid"])
                detail_lines = get_process_details(pid)
                panel = "task_details"
            elif key == "x" and panel in {"tasks", "task_details"} and task_data:
                pid = int(task_data[selected_index]["Pid"])
                task_message = terminate_process(pid)
                task_data = get_task_snapshot_data()
                last_task_refresh = now
                if task_data:
                    selected_index = min(selected_index, len(task_data) - 1)
                else:
                    selected_index = 0
                    panel = "tasks"
                    detail_lines = None
            elif key == "o" and panel in {"tasks", "task_details"} and task_data:
                pid = int(task_data[selected_index]["Pid"])
                task_message = open_process_location(pid)

            panel_rows = panel_lines(
                render_width,
                panel,
                start_time,
                fps,
                frame,
                task_data,
                selected_index,
                task_message,
                detail_lines,
                panel_height,
            )
            reserved_lines = panel_height + 2
            scene_height = max(10, total_height - reserved_lines)
            scale = min(render_width, scene_height) * 1.8

            frame_text = render_c8(
                render_width,
                scene_height,
                frame * 0.07,
                frame * 0.033,
                frame * 0.12,
                scale,
            )
            screen = compose_screen(render_width, scene_height, frame_text, panel_rows)

            sys.stdout.write(HOME)
            sys.stdout.write(screen)
            sys.stdout.flush()

            frame += 1
            time.sleep(1.0 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + CLEAR + HOME)
        sys.stdout.flush()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="A cli with menu keybinds."
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=24.0,
        help="Animation speed in frames per second.",
    )
    parser.add_argument("--width", type=int, default=None, help="Render width in characters.")
    parser.add_argument("--height", type=int, default=None, help="Render height in characters.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run_ui(max(1.0, args.fps), args.width, args.height)


if __name__ == "__main__":
    raise SystemExit(main())
