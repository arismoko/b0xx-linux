#!/usr/bin/env python3
"""
B0XX-Linux: A 1:1 port of b0xx-ahk to Linux.

Uses python-evdev for keyboard capture and uinput for virtual gamepad output.
Requires root or appropriate uinput permissions.

Usage:
    sudo python3 b0xx.py [--keyboard /dev/input/eventX] [--config hotkeys.ini] [--list]
"""

import argparse
import configparser
import signal
import sys
from pathlib import Path

import evdev
from evdev import UInput, AbsInfo, ecodes


# --- B0XX Constants (analog stick coordinates) ---
# All coordinates are in Melee units (-1.0 to 1.0)

COORDS_ORIGIN = (0.0, 0.0)
COORDS_VERTICAL = (0.0, 1.0)
COORDS_VERTICAL_MOD_X = (0.0, 0.5375)
COORDS_VERTICAL_MOD_Y = (0.0, 0.7375)
COORDS_HORIZONTAL = (1.0, 0.0)
COORDS_HORIZONTAL_MOD_X = (0.6625, 0.0)
COORDS_HORIZONTAL_MOD_Y = (0.3375, 0.0)
COORDS_QUADRANT = (0.7, 0.7)
COORDS_QUADRANT_MOD_X = (0.7375, 0.3125)
COORDS_QUADRANT_MOD_Y = (0.3125, 0.7375)

COORDS_AIRDODGE_VERTICAL = COORDS_VERTICAL
COORDS_AIRDODGE_VERTICAL_MOD_X = COORDS_VERTICAL_MOD_X
COORDS_AIRDODGE_VERTICAL_MOD_Y = COORDS_VERTICAL_MOD_Y
COORDS_AIRDODGE_HORIZONTAL = COORDS_HORIZONTAL
COORDS_AIRDODGE_HORIZONTAL_MOD_X = COORDS_HORIZONTAL_MOD_X
COORDS_AIRDODGE_HORIZONTAL_MOD_Y = COORDS_HORIZONTAL_MOD_Y
COORDS_AIRDODGE_QUADRANT = (0.7, 0.6875)
COORDS_AIRDODGE_QUADRANT_12 = (0.7, 0.7)
COORDS_AIRDODGE_QUADRANT_34 = (0.7, 0.6875)
COORDS_AIRDODGE_QUADRANT_MOD_X = (0.6375, 0.375)
COORDS_AIRDODGE_QUADRANT_12_MOD_Y = (0.475, 0.875)
COORDS_AIRDODGE_QUADRANT_34_MOD_Y = (0.5, 0.85)

COORDS_FIREFOX_MOD_X_C_DOWN = (0.7, 0.3625)      # ~27 deg
COORDS_FIREFOX_MOD_X_C_LEFT = (0.7875, 0.4875)   # ~32 deg
COORDS_FIREFOX_MOD_X_C_UP = (0.7, 0.5125)         # ~36 deg
COORDS_FIREFOX_MOD_X_C_RIGHT = (0.6125, 0.525)    # ~41 deg
COORDS_FIREFOX_MOD_Y_C_RIGHT = (0.6375, 0.7625)   # ~50 deg
COORDS_FIREFOX_MOD_Y_C_UP = (0.5125, 0.7)         # ~54 deg
COORDS_FIREFOX_MOD_Y_C_LEFT = (0.4875, 0.7875)    # ~58 deg
COORDS_FIREFOX_MOD_Y_C_DOWN = (0.3625, 0.7)       # ~63 deg

COORDS_EXT_FIREFOX_MOD_X = (0.9125, 0.3875)               # ~23 deg
COORDS_EXT_FIREFOX_MOD_X_C_DOWN = (0.875, 0.45)           # ~27 deg
COORDS_EXT_FIREFOX_MOD_X_C_LEFT = (0.85, 0.525)           # ~32 deg
COORDS_EXT_FIREFOX_MOD_X_C_UP = (0.7375, 0.5375)          # ~36 deg
COORDS_EXT_FIREFOX_MOD_X_C_RIGHT = (0.6375, 0.5375)       # ~40 deg
COORDS_EXT_FIREFOX_MOD_Y_C_RIGHT = (0.5875, 0.7125)       # ~50 deg
COORDS_EXT_FIREFOX_MOD_Y_C_UP = (0.5875, 0.8)             # ~54 deg
COORDS_EXT_FIREFOX_MOD_Y_C_LEFT = (0.525, 0.85)           # ~58 deg
COORDS_EXT_FIREFOX_MOD_Y_C_DOWN = (0.45, 0.875)           # ~63 deg
COORDS_EXT_FIREFOX_MOD_Y = (0.3875, 0.9125)               # ~67 deg

# --- Hotkey name to index mapping ---
HOTKEY_NAMES = {
    1: "Analog Up",
    2: "Analog Down",
    3: "Analog Left",
    4: "Analog Right",
    5: "ModX",
    6: "ModY",
    7: "A",
    8: "B",
    9: "L",
    10: "R",
    11: "X",
    12: "Y",
    13: "Z",
    14: "C-stick Up",
    15: "C-stick Down",
    16: "C-stick Left",
    17: "C-stick Right",
    18: "Light Shield",
    19: "Mid Shield",
    20: "Start",
    21: "D-pad Up",
    22: "D-pad Down",
    23: "D-pad Left",
    24: "D-pad Right",
}

# evdev stick axes are centered around 0. Using a vJoy-style 0..32767 range makes
# the virtual device look "always positive" to consumers that expect signed axes.
STICK_AXIS_MIN = -32768
STICK_AXIS_MAX = 32767
STICK_AXIS_MID = 0

# Keep the analog shoulder on a simple positive-only range.
TRIGGER_AXIS_MIN = 0
TRIGGER_AXIS_MAX = 255
TRIGGER_AXIS_MID = 0


class B0XXState:
    """Holds all the mutable state for the B0XX controller emulation."""

    def __init__(self):
        # Directional buttons
        self.button_up = False
        self.button_down = False
        self.button_left = False
        self.button_right = False

        # Action buttons
        self.button_a = False
        self.button_b = False
        self.button_l = False
        self.button_r = False
        self.button_x = False
        self.button_y = False
        self.button_z = False

        # Shield buttons
        self.button_light_shield = False
        self.button_mid_shield = False

        # Modifier buttons
        self.button_mod_x = False
        self.button_mod_y = False

        # C-stick buttons
        self.button_c_up = False
        self.button_c_down = False
        self.button_c_left = False
        self.button_c_right = False

        # SOCD resolution state
        self.most_recent_vertical = ""
        self.most_recent_horizontal = ""
        self.most_recent_vertical_c = ""
        self.most_recent_horizontal_c = ""

        # Simultaneous horizontal modifier lockout
        self.simultaneous_horizontal_modifier_lockout = False

    # --- Helper functions (1:1 port of AHK functions) ---

    def up(self):
        return self.button_up and self.most_recent_vertical == "U"

    def down(self):
        return self.button_down and self.most_recent_vertical == "D"

    def left(self):
        return self.button_left and self.most_recent_horizontal == "L"

    def right(self):
        return self.button_right and self.most_recent_horizontal == "R"

    def c_up(self):
        return self.button_c_up and self.most_recent_vertical_c == "U" and not self.both_mods()

    def c_down(self):
        return self.button_c_down and self.most_recent_vertical_c == "D" and not self.both_mods()

    def c_left(self):
        return self.button_c_left and self.most_recent_horizontal_c == "L" and not self.both_mods()

    def c_right(self):
        return self.button_c_right and self.most_recent_horizontal_c == "R" and not self.both_mods()

    def mod_x(self):
        return (self.button_mod_x and not self.button_mod_y
                and not (self.simultaneous_horizontal_modifier_lockout and not self.any_vert()))

    def mod_y(self):
        return (self.button_mod_y and not self.button_mod_x
                and not (self.simultaneous_horizontal_modifier_lockout and not self.any_vert()))

    def any_vert(self):
        return self.up() or self.down()

    def any_horiz(self):
        return self.left() or self.right()

    def any_quadrant(self):
        return self.any_vert() and self.any_horiz()

    def any_mod(self):
        return self.mod_x() or self.mod_y()

    def both_mods(self):
        return self.button_mod_x and self.button_mod_y

    def any_shield(self):
        return self.button_l or self.button_r or self.button_light_shield or self.button_mid_shield

    def any_vert_c(self):
        return self.c_up() or self.c_down()

    def any_horiz_c(self):
        return self.c_left() or self.c_right()

    def any_c(self):
        return self.c_up() or self.c_down() or self.c_left() or self.c_right()

    # --- Coordinate calculation (1:1 port) ---

    def get_analog_coords(self):
        if self.any_shield():
            coords = self._get_analog_coords_airdodge()
        elif self.any_mod() and self.any_quadrant() and (self.any_c() or self.button_b):
            coords = self._get_analog_coords_firefox()
        else:
            coords = self._get_analog_coords_no_shield()
        return self._reflect_coords(coords)

    def _reflect_coords(self, coords):
        x, y = coords
        if self.down():
            y = -y
        if self.left():
            x = -x
        return (x, y)

    def _get_analog_coords_airdodge(self):
        if not self.any_vert() and not self.any_horiz():
            return COORDS_ORIGIN
        elif self.any_quadrant():
            if self.mod_x():
                return COORDS_AIRDODGE_QUADRANT_MOD_X
            elif self.mod_y():
                return COORDS_AIRDODGE_QUADRANT_12_MOD_Y if self.up() else COORDS_AIRDODGE_QUADRANT_34_MOD_Y
            else:
                return COORDS_AIRDODGE_QUADRANT_12 if self.up() else COORDS_AIRDODGE_QUADRANT_34
        elif self.any_vert():
            if self.mod_x():
                return COORDS_AIRDODGE_VERTICAL_MOD_X
            elif self.mod_y():
                return COORDS_AIRDODGE_VERTICAL_MOD_Y
            else:
                return COORDS_AIRDODGE_VERTICAL
        else:
            if self.mod_x():
                return COORDS_AIRDODGE_HORIZONTAL_MOD_X
            elif self.mod_y():
                # turnaround side-b nerf
                return COORDS_AIRDODGE_HORIZONTAL if self.button_b else COORDS_AIRDODGE_HORIZONTAL_MOD_Y
            else:
                return COORDS_AIRDODGE_HORIZONTAL

    def _get_analog_coords_no_shield(self):
        if not self.any_vert() and not self.any_horiz():
            return COORDS_ORIGIN
        elif self.any_quadrant():
            if self.mod_x():
                return COORDS_QUADRANT_MOD_X
            elif self.mod_y():
                return COORDS_QUADRANT_MOD_Y
            else:
                return COORDS_QUADRANT
        elif self.any_vert():
            if self.mod_x():
                return COORDS_VERTICAL_MOD_X
            elif self.mod_y():
                return COORDS_VERTICAL_MOD_Y
            else:
                return COORDS_VERTICAL
        else:
            if self.mod_x():
                return COORDS_HORIZONTAL_MOD_X
            elif self.mod_y():
                # turnaround side-b nerf
                return COORDS_HORIZONTAL if self.button_b else COORDS_HORIZONTAL_MOD_Y
            else:
                return COORDS_HORIZONTAL

    def _get_analog_coords_firefox(self):
        if self.mod_x():
            if self.c_up():
                return COORDS_EXT_FIREFOX_MOD_X_C_UP if self.button_b else COORDS_FIREFOX_MOD_X_C_UP
            elif self.c_down():
                return COORDS_EXT_FIREFOX_MOD_X_C_DOWN if self.button_b else COORDS_FIREFOX_MOD_X_C_DOWN
            elif self.c_left():
                return COORDS_EXT_FIREFOX_MOD_X_C_LEFT if self.button_b else COORDS_FIREFOX_MOD_X_C_LEFT
            elif self.c_right():
                return COORDS_EXT_FIREFOX_MOD_X_C_RIGHT if self.button_b else COORDS_FIREFOX_MOD_X_C_RIGHT
            else:
                return COORDS_EXT_FIREFOX_MOD_X
        elif self.mod_y():
            if self.c_up():
                return COORDS_EXT_FIREFOX_MOD_Y_C_UP if self.button_b else COORDS_FIREFOX_MOD_Y_C_UP
            elif self.c_down():
                return COORDS_EXT_FIREFOX_MOD_Y_C_DOWN if self.button_b else COORDS_FIREFOX_MOD_Y_C_DOWN
            elif self.c_left():
                return COORDS_EXT_FIREFOX_MOD_Y_C_LEFT if self.button_b else COORDS_FIREFOX_MOD_Y_C_LEFT
            elif self.c_right():
                return COORDS_EXT_FIREFOX_MOD_Y_C_RIGHT if self.button_b else COORDS_FIREFOX_MOD_Y_C_RIGHT
            else:
                return COORDS_EXT_FIREFOX_MOD_Y
        return COORDS_ORIGIN  # shouldn't reach here

    def get_c_stick_coords(self):
        if not self.any_vert_c() and not self.any_horiz_c():
            coords = (0.0, 0.0)
        elif self.any_vert_c() and self.any_horiz_c():
            coords = (0.525, 0.85)
        elif self.any_vert_c():
            coords = (0.0, 1.0)
        else:
            if self.mod_x() and self.up():
                coords = (0.9, 0.5)
            elif self.mod_x() and self.down():
                coords = (0.9, -0.5)
            else:
                coords = (1.0, 0.0)
        return self._reflect_c_stick_coords(coords)

    def _reflect_c_stick_coords(self, coords):
        x, y = coords
        if self.c_down():
            y = -y
        if self.c_left():
            x = -x
        return (x, y)


def convert_coords(coords):
    """Convert Melee coords (-1..1) to signed evdev stick axis values.

    vJoy used an unsigned 0..32767 range with an offset center. evdev stick axes
    are normally centered at 0, and Dolphin's evdev backend expects that model.
    """
    x = int(coords[0] * STICK_AXIS_MAX)
    y = int(-coords[1] * STICK_AXIS_MAX)
    return (x, y)


def convert_analog_r(value):
    """Convert analog shoulder value (0-255) to a positive-only trigger axis."""
    return max(TRIGGER_AXIS_MIN, min(TRIGGER_AXIS_MAX, int(value)))


class VirtualGamepad:
    """Creates and manages a uinput virtual gamepad device."""

    def __init__(self):
        # Define axes: X, Y (left stick), RX, RY (c-stick), Z (analog shoulder)
        # Sticks are signed and centered at 0; trigger is positive-only.
        abs_caps = [
            (ecodes.ABS_X, AbsInfo(value=STICK_AXIS_MID, min=STICK_AXIS_MIN, max=STICK_AXIS_MAX, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_Y, AbsInfo(value=STICK_AXIS_MID, min=STICK_AXIS_MIN, max=STICK_AXIS_MAX, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_Z, AbsInfo(value=TRIGGER_AXIS_MID, min=TRIGGER_AXIS_MIN, max=TRIGGER_AXIS_MAX, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_RX, AbsInfo(value=STICK_AXIS_MID, min=STICK_AXIS_MIN, max=STICK_AXIS_MAX, fuzz=0, flat=0, resolution=0)),
            (ecodes.ABS_RY, AbsInfo(value=STICK_AXIS_MID, min=STICK_AXIS_MIN, max=STICK_AXIS_MAX, fuzz=0, flat=0, resolution=0)),
        ]

        # 12 buttons (matching vJoy config: buttons 1-12)
        # Map to BTN_TRIGGER, BTN_THUMB, BTN_THUMB2, BTN_TOP, BTN_TOP2, BTN_PINKIE,
        # BTN_BASE, BTN_BASE2, BTN_BASE3, BTN_BASE4, BTN_BASE5, BTN_BASE6
        self.btn_codes = [
            ecodes.BTN_TRIGGER,  # btn 1: L
            ecodes.BTN_THUMB,    # btn 2: Y
            ecodes.BTN_THUMB2,   # btn 3: R
            ecodes.BTN_TOP,      # btn 4: B
            ecodes.BTN_TOP2,     # btn 5: A
            ecodes.BTN_PINKIE,   # btn 6: X
            ecodes.BTN_BASE,     # btn 7: Z
            ecodes.BTN_BASE2,    # btn 8: Start
            ecodes.BTN_BASE3,    # btn 9: D-Up
            ecodes.BTN_BASE4,    # btn 10: D-Left
            ecodes.BTN_BASE5,    # btn 11: D-Down
            ecodes.BTN_BASE6,    # btn 12: D-Right
        ]

        capabilities = {
            ecodes.EV_ABS: abs_caps,
            ecodes.EV_KEY: self.btn_codes,
        }

        self.device = UInput(capabilities, name="B0XX Virtual Controller", vendor=0x1234, product=0xB000)
        print(f"Virtual gamepad created: {self.device.device.path}")

    def set_axis(self, axis_index, value):
        """Set axis by 1-based index (matching vJoy convention).
        1=X, 2=Y, 3=Z, 4=RX, 5=RY"""
        axis_map = {
            1: ecodes.ABS_X,
            2: ecodes.ABS_Y,
            3: ecodes.ABS_Z,
            4: ecodes.ABS_RX,
            5: ecodes.ABS_RY,
        }
        axis = axis_map.get(axis_index)
        if axis is not None:
            self.device.write(ecodes.EV_ABS, axis, int(value))
            self.device.syn()

    def set_btn(self, value, btn_index):
        """Set button state. btn_index is 1-based (matching vJoy convention)."""
        if 1 <= btn_index <= len(self.btn_codes):
            self.device.write(ecodes.EV_KEY, self.btn_codes[btn_index - 1], 1 if value else 0)
            self.device.syn()

    def close(self):
        self.device.close()


class B0XX:
    """Main B0XX controller emulation class."""

    def __init__(self, config_path):
        self.state = B0XXState()
        self.gamepad = VirtualGamepad()
        self.key_map = {}  # evdev keycode -> handler index (1-24)
        self._load_config(config_path)

    def _load_config(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)

        if "Hotkeys" not in config:
            print(f"Error: No [Hotkeys] section in {config_path}")
            sys.exit(1)

        for idx_str, key_name in config["Hotkeys"].items():
            # Skip comments
            idx_str = idx_str.strip()
            if idx_str.startswith("#"):
                continue
            try:
                idx = int(idx_str)
            except ValueError:
                continue

            key_name = key_name.strip()
            # Look up the evdev keycode
            keycode = getattr(ecodes, key_name, None)
            if keycode is None:
                print(f"Warning: Unknown key '{key_name}' for hotkey {idx} ({HOTKEY_NAMES.get(idx, '?')})")
                continue

            self.key_map[keycode] = idx
            print(f"  {HOTKEY_NAMES.get(idx, f'#{idx}'):20s} -> {key_name}")

    def _update_analog_stick(self):
        coords = self.state.get_analog_coords()
        converted = convert_coords(coords)
        self.gamepad.set_axis(1, converted[0])
        self.gamepad.set_axis(2, converted[1])

    def _update_c_stick(self):
        coords = self.state.get_c_stick_coords()
        converted = convert_coords(coords)
        self.gamepad.set_axis(4, converted[0])
        self.gamepad.set_axis(5, converted[1])

    def _set_analog_r(self, value):
        converted = convert_analog_r(value)
        self.gamepad.set_axis(3, converted)

    def handle_key(self, keycode, pressed):
        """Handle a key press/release event."""
        idx = self.key_map.get(keycode)
        if idx is None:
            return

        s = self.state

        if idx == 1:  # Analog Up
            if pressed:
                s.button_up = True
                s.most_recent_vertical = "U"
            else:
                s.button_up = False
            self._update_analog_stick()
            self._update_c_stick()

        elif idx == 2:  # Analog Down
            if pressed:
                s.button_down = True
                s.most_recent_vertical = "D"
            else:
                s.button_down = False
            self._update_analog_stick()
            self._update_c_stick()

        elif idx == 3:  # Analog Left
            if pressed:
                s.button_left = True
                s.most_recent_horizontal = "L"
                if s.button_right:
                    s.simultaneous_horizontal_modifier_lockout = True
            else:
                s.button_left = False
                s.simultaneous_horizontal_modifier_lockout = False
            self._update_analog_stick()

        elif idx == 4:  # Analog Right
            if pressed:
                s.button_right = True
                s.most_recent_horizontal = "R"
                if s.button_left:
                    s.simultaneous_horizontal_modifier_lockout = True
            else:
                s.button_right = False
                s.simultaneous_horizontal_modifier_lockout = False
            self._update_analog_stick()

        elif idx == 5:  # ModX
            if pressed:
                s.button_mod_x = True
                s.simultaneous_horizontal_modifier_lockout = False
            else:
                s.button_mod_x = False
                s.simultaneous_horizontal_modifier_lockout = False
            self._update_analog_stick()
            self._update_c_stick()

        elif idx == 6:  # ModY
            s.button_mod_y = pressed
            self._update_analog_stick()

        elif idx == 7:  # A
            s.button_a = pressed
            self.gamepad.set_btn(pressed, 5)

        elif idx == 8:  # B
            s.button_b = pressed
            self.gamepad.set_btn(pressed, 4)
            self._update_analog_stick()

        elif idx == 9:  # L
            s.button_l = pressed
            self.gamepad.set_btn(pressed, 1)
            self._update_analog_stick()

        elif idx == 10:  # R
            s.button_r = pressed
            self.gamepad.set_btn(pressed, 3)
            self._update_analog_stick()

        elif idx == 11:  # X
            s.button_x = pressed
            self.gamepad.set_btn(pressed, 6)

        elif idx == 12:  # Y
            s.button_y = pressed
            self.gamepad.set_btn(pressed, 2)

        elif idx == 13:  # Z
            s.button_z = pressed
            self.gamepad.set_btn(pressed, 7)
            self._update_analog_stick()

        elif idx == 14:  # C-Up
            if pressed:
                s.button_c_up = True
                if s.both_mods():
                    self.gamepad.set_btn(True, 9)  # D-pad Up
                else:
                    s.most_recent_vertical_c = "U"
                    self._update_c_stick()
                    self._update_analog_stick()
            else:
                s.button_c_up = False
                self.gamepad.set_btn(False, 9)
                self._update_c_stick()
                self._update_analog_stick()

        elif idx == 15:  # C-Down
            if pressed:
                s.button_c_down = True
                if s.both_mods():
                    self.gamepad.set_btn(True, 11)  # D-pad Down
                else:
                    s.most_recent_vertical_c = "D"
                    self._update_c_stick()
                    self._update_analog_stick()
            else:
                s.button_c_down = False
                self.gamepad.set_btn(False, 11)
                self._update_c_stick()
                self._update_analog_stick()

        elif idx == 16:  # C-Left
            if pressed:
                s.button_c_left = True
                if s.both_mods():
                    self.gamepad.set_btn(True, 10)  # D-pad Left
                else:
                    s.most_recent_horizontal_c = "L"
                    self._update_c_stick()
                    self._update_analog_stick()
            else:
                s.button_c_left = False
                self.gamepad.set_btn(False, 10)
                self._update_c_stick()
                self._update_analog_stick()

        elif idx == 17:  # C-Right
            if pressed:
                s.button_c_right = True
                if s.both_mods():
                    self.gamepad.set_btn(True, 12)  # D-pad Right
                else:
                    s.most_recent_horizontal_c = "R"
                    self._update_c_stick()
                    self._update_analog_stick()
            else:
                s.button_c_right = False
                self.gamepad.set_btn(False, 12)
                self._update_c_stick()
                self._update_analog_stick()

        elif idx == 18:  # Light Shield
            s.button_light_shield = pressed
            self._set_analog_r(49 if pressed else 0)

        elif idx == 19:  # Mid Shield
            s.button_mid_shield = pressed
            self._set_analog_r(94 if pressed else 0)

        elif idx == 20:  # Start
            self.gamepad.set_btn(pressed, 8)

        elif idx == 21:  # D-Up
            self.gamepad.set_btn(pressed, 9)

        elif idx == 22:  # D-Down
            self.gamepad.set_btn(pressed, 11)

        elif idx == 23:  # D-Left
            self.gamepad.set_btn(pressed, 10)

        elif idx == 24:  # D-Right
            self.gamepad.set_btn(pressed, 12)

    def close(self):
        self.gamepad.close()


def list_keyboards():
    """List available input devices that have keyboard capabilities."""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboards = []
    for dev in devices:
        caps = dev.capabilities(verbose=True)
        has_keys = False
        for (etype_name, etype_code), events in caps.items():
            if etype_name == "EV_KEY":
                # Check if it has typical keyboard keys
                for (key_name, key_code) in events:
                    if isinstance(key_name, str) and key_name.startswith("KEY_"):
                        has_keys = True
                        break
                    elif isinstance(key_name, list):
                        for kn in key_name:
                            if kn.startswith("KEY_"):
                                has_keys = True
                                break
        if has_keys:
            keyboards.append(dev)
            print(f"  {dev.path:25s}  {dev.name}")
        dev.close()
    return keyboards


def find_keyboard():
    """Auto-detect a keyboard device."""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in devices:
        caps = dev.capabilities()
        if ecodes.EV_KEY in caps:
            keys = caps[ecodes.EV_KEY]
            # A real keyboard will have letter keys
            if ecodes.KEY_A in keys and ecodes.KEY_Z in keys and ecodes.KEY_SPACE in keys:
                print(f"Auto-detected keyboard: {dev.path} ({dev.name})")
                return dev
        dev.close()
    return None


def main():
    parser = argparse.ArgumentParser(description="B0XX controller emulator for Linux")
    parser.add_argument("--keyboard", "-k", help="Path to keyboard device (e.g. /dev/input/event3)")
    parser.add_argument("--config", "-c", default=None, help="Path to hotkeys.ini config file")
    parser.add_argument("--list", "-l", action="store_true", help="List available keyboard devices")
    parser.add_argument("--grab", "-g", action="store_true",
                        help="Grab keyboard exclusively (prevents keys from reaching other apps)")
    args = parser.parse_args()

    if args.list:
        print("Available keyboard devices:")
        list_keyboards()
        return

    # Find config file
    config_path = args.config
    if config_path is None:
        script_dir = Path(__file__).parent
        config_path = script_dir / "hotkeys.ini"
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    # Find keyboard
    if args.keyboard:
        try:
            kbd = evdev.InputDevice(args.keyboard)
        except (FileNotFoundError, PermissionError) as e:
            print(f"Error opening keyboard device: {e}")
            print("Try running with sudo, or add your user to the 'input' group.")
            sys.exit(1)
    else:
        kbd = find_keyboard()
        if kbd is None:
            print("Error: Could not auto-detect a keyboard.")
            print("Use --list to see available devices, then specify with --keyboard.")
            sys.exit(1)

    print(f"\nLoading config from: {config_path}")
    print("Key bindings:")
    b0xx = B0XX(str(config_path))

    if args.grab:
        kbd.grab()
        print("\nKeyboard grabbed exclusively (--grab mode)")

    print(f"\nB0XX Linux started! Listening on {kbd.path} ({kbd.name})")
    print("Press Ctrl+C to exit.\n")

    # Handle clean shutdown
    def shutdown(sig, frame):
        print("\nShutting down...")
        if args.grab:
            try:
                kbd.ungrab()
            except Exception:
                pass
        kbd.close()
        b0xx.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Main event loop
    try:
        for event in kbd.read_loop():
            if event.type == ecodes.EV_KEY:
                key_event = evdev.categorize(event)
                if key_event.keystate == evdev.KeyEvent.key_down:
                    b0xx.handle_key(event.code, True)
                elif key_event.keystate == evdev.KeyEvent.key_up:
                    b0xx.handle_key(event.code, False)
                # Ignore key_hold (repeat) events
    except OSError:
        pass
    finally:
        if args.grab:
            try:
                kbd.ungrab()
            except Exception:
                pass
        kbd.close()
        b0xx.close()


if __name__ == "__main__":
    main()
