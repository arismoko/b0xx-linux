# b0xx-linux

`b0xx-linux` is a Linux port of [agirardeau/b0xx-ahk](https://github.com/agirardeau/b0xx-ahk): it captures keyboard input and exposes a virtual controller for Dolphin so you can play Melee with a B0XX-style layout.

It uses `python-evdev` for keyboard input capture and Linux `uinput` for virtual gamepad output.

## Status

This project currently targets Linux only. The controller output is modeled around signed `evdev` stick axes centered at `0`, which matches Dolphin's `evdev` backend.

## Requirements

- Linux
- Python 3.9+
- `uv` (recommended)
- A kernel with the `uinput` module available
- Dolphin emulator

## Setup

1. Install `uv` if you do not already have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Sync the project environment:

```bash
uv sync
```

3. Load the `uinput` module:

```bash
sudo modprobe uinput
```

4. List available keyboards to find yours:

```bash
sudo .venv/bin/python b0xx.py --list
```

5. Start the emulator with an explicit keyboard:

```bash
sudo .venv/bin/python b0xx.py --keyboard /dev/input/eventX
```

Or let it auto-detect:

```bash
sudo .venv/bin/python b0xx.py
```

6. In Dolphin, set Player 1 to `Standard Controller`, open the controller config, select `B0XX Virtual Controller` as the device, and map inputs to match [`dolphin-profile.ini`](./dolphin-profile.ini).

If you prefer not to use `uv`, installing `evdev` manually with `python3 -m pip install evdev` also works.

## Running Without Root

Add your user to the `input` group and give `uinput` group write access:

```bash
sudo usermod -aG input "$USER"
sudo sh -c 'echo KERNEL=="uinput", GROUP="input", MODE="0660" > /etc/udev/rules.d/99-uinput.rules'
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Log out and back in after changing groups.

## Configuration

Edit [`hotkeys.ini`](./hotkeys.ini) to change bindings. Keys use Linux `evdev` names such as `KEY_A`, `KEY_SPACE`, and `KEY_LEFTSHIFT`.

The default [`hotkeys.ini`](./hotkeys.ini) currently ships with these bindings:

| # | Button | `evdev` key | Typical US keycap |
|---|--------|-------------|-------------------|
| 1 | Analog Up | `KEY_RIGHTBRACE` | `]` |
| 2 | Analog Down | `KEY_3` | `3` |
| 3 | Analog Left | `KEY_2` | `2` |
| 4 | Analog Right | `KEY_4` | `4` |
| 5 | ModX | `KEY_V` | `V` |
| 6 | ModY | `KEY_B` | `B` |
| 7 | A | `KEY_M` | `M` |
| 8 | B | `KEY_O` | `O` |
| 9 | L | `KEY_Q` | `Q` |
| 10 | R | `KEY_9` | `9` |
| 11 | X | `KEY_P` | `P` |
| 12 | Y | `KEY_0` | `0` |
| 13 | Z | `KEY_LEFTBRACE` | `[` |
| 14 | C-Up | `KEY_K` | `K` |
| 15 | C-Down | `KEY_SPACE` | `Space` |
| 16 | C-Left | `KEY_N` | `N` |
| 17 | C-Right | `KEY_COMMA` | `,` |
| 18 | Light Shield | `KEY_MINUS` | `-` |
| 19 | Mid Shield | `KEY_EQUAL` | `=` |
| 20 | Start | `KEY_7` | `7` |
| 21 | D-Up | `KEY_UP` | `Up Arrow` |
| 22 | D-Down | `KEY_DOWN` | `Down Arrow` |
| 23 | D-Left | `KEY_LEFT` | `Left Arrow` |
| 24 | D-Right | `KEY_RIGHT` | `Right Arrow` |

The keycap column assumes a US keyboard layout. `evdev` codes are the source of truth.

## Command-Line Options

- `--keyboard`, `-k`: path to a keyboard device such as `/dev/input/event3`
- `--config`, `-c`: path to `hotkeys.ini`
- `--list`, `-l`: list available keyboards
- `--grab`, `-g`: grab the keyboard exclusively so keys do not reach other applications

## Dolphin Profile

A Dolphin controller profile is included in [`dolphin-profile.ini`](./dolphin-profile.ini). Copy it to:

```text
~/.config/dolphin-emu/Config/Profiles/GCPad/
```

Then load it from Dolphin's controller configuration UI.

## Testing

Run the test suite with:

```bash
uv run pytest -q
```

## Acknowledgements

This project is derived from the Windows AutoHotkey project [`agirardeau/b0xx-ahk`](https://github.com/agirardeau/b0xx-ahk), which is published under the MIT license.

## License

MIT
