# rainbow-cli-4-windows

A stylized Python terminal interface built around a rotating 3D scene, fast keyboard navigation, and an integrated task manager. The project is designed to feel more like a compact command-center than a plain script: animated background, modern panel layout, live system data, and process controls in a single ANSI-powered CLI.

## Highlights

- Keyboard-driven interface with a clean panel-based layout
- System configuration view for quick machine details
- Built-in task manager with scrolling, process details, kill action, and file-location reveal
- Lightweight implementation using the Python standard library only


## Requirements

- Python `3.10+` recommended
- Windows terminal with ANSI truecolor support
- Best experience in Windows Terminal or another modern terminal emulator

## Quick Start

Clone or open the project, then run:

```powershell
python .\rainbow-cli-4-windows.py
```

The terminal is cleared before launch so the interface starts cleanly.


## Controls

```text
A                  Open PC configuration
T                  Open task manager
Up / Down          Move task selection
J / K              Alternative task navigation
D                  Show selected process details
X                  End selected process
O                  Open selected process file location
H                  Open help
M                  Return to the main menu
Q                  Quit the application
```

## Usage Guide

### Launch the interface

Start the app with:

```powershell
python .\rainbow-cli-4-windows.py
```

You will land in the main interface with the animated display in the top section and the control panel below it.

### Check system information

Press `A` to open the configuration panel. This view shows:

- Machine name
- Windows version
- CPU
- Architecture
- RAM
- Disk capacity
- GPU

### Manage running processes

Press `T` to open the task manager.

From there you can:

- Scroll through the full process list with `Up` / `Down` or `J` / `K`
- Press `D` to inspect the selected process
- Press `X` to terminate the selected process
- Press `O` to reveal the executable in File Explorer

The selected process is highlighted with an `ACTIVE` marker so it remains easy to track while scrolling.

### Return or exit

- Press `M` to return to the main menu
- Press `H` to open the built-in help panel
- Press `Q` to quit

On exit, the application clears the terminal for a cleaner close.

## Useful Options

Adjust animation speed:

```powershell
python .\rainbow-cli-4-windows.py --fps 24
```

Set a custom render size:

```powershell
python .\rainbow-cli-4-windows.py --width 120 --height 40
```

## Project Structure

```text
rainbow-cli-4-windows.py  Main terminal application
README.md         Project documentation
```

## Technical Notes

- The rendering layer uses ANSI escape sequences for color and screen control
- Keyboard input currently uses Windows-specific APIs
- Process inspection and actions rely on Windows tools such as PowerShell, `taskkill`, and Explorer

Because of that, the current implementation is Windows-focused even though the rendering concept itself is portable.

## Roadmap Ideas

- Cross-platform input and process support
- Optional low-motion mode
- Additional information panels
- Theme presets
- Search and filter inside task manager



