# b0xx-linux

`b0xx-linux` is a Linux port of [agirardeau/b0xx-ahk](https://github.com/agirardeau/b0xx-ahk): it captures keyboard input and exposes a virtual controller for Dolphin so you can play Melee with a B0XX-style layout.

It uses `python-evdev` for keyboard input capture and Linux `uinput` for virtual gamepad output.

## Status

This project currently targets Linux only. The controller output is modeled around signed `evdev` stick axes centered at `0`, which matches Dolphin's `evdev` backend.

## Requirements

- Linux
- Python 3.9+
- `python-evdev`
- A kernel with the `uinput` module available
- Dolphin emulator

## Setup

1. Install the dependency:

```bash
python3 -m pip install evdev
```

2. Load the `uinput` module:

```bash
sudo modprobe uinput
```

3. List available keyboards to find yours:

```bash
sudo python3 b0xx.py --list
```

4. Start the emulator with an explicit keyboard:

```bash
sudo python3 b0xx.py --keyboard /dev/input/eventX
```

Or let it auto-detect:

```bash
sudo python3 b0xx.py
```

5. In Dolphin, set Player 1 to `Standard Controller`, open the controller config, select `B0XX Virtual Controller` as the device, and map inputs to match [`dolphin-profile.ini`](./dolphin-profile.ini).

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

The numbered entries map to:

| # | Button |
|---|--------|
| 1 | Analog Up |
| 2 | Analog Down |
| 3 | Analog Left |
| 4 | Analog Right |
| 5 | ModX |
| 6 | ModY |
| 7 | A |
| 8 | B |
| 9 | L |
| 10 | R |
| 11 | X |
| 12 | Y |
| 13 | Z |
| 14 | C-Up |
| 15 | C-Down |
| 16 | C-Left |
| 17 | C-Right |
| 18 | Light Shield |
| 19 | Mid Shield |
| 20 | Start |
| 21 | D-Up |
| 22 | D-Down |
| 23 | D-Left |
| 24 | D-Right |

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
./.venv/bin/python -m pytest -q
```

## Acknowledgements

This project is derived from the Windows AutoHotkey project [`agirardeau/b0xx-ahk`](https://github.com/agirardeau/b0xx-ahk), which is published under the MIT license.

## License

MIT
