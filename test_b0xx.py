"""Tests for b0xx.py — covers B0XXState logic, coordinate math, and handle_key integration."""

import pytest
from unittest.mock import MagicMock, call
from b0xx import (
    B0XXState,
    convert_coords,
    convert_analog_r,
    STICK_AXIS_MAX,
    STICK_AXIS_CENTER_X,
    STICK_AXIS_CENTER_Y,
    TRIGGER_AXIS_MAX,
    TRIGGER_AXIS_MIN,
    COORDS_ORIGIN,
    COORDS_VERTICAL,
    COORDS_VERTICAL_MOD_X,
    COORDS_VERTICAL_MOD_Y,
    COORDS_HORIZONTAL,
    COORDS_HORIZONTAL_MOD_X,
    COORDS_HORIZONTAL_MOD_Y,
    COORDS_QUADRANT,
    COORDS_QUADRANT_MOD_X,
    COORDS_QUADRANT_MOD_Y,
    COORDS_AIRDODGE_QUADRANT_12,
    COORDS_AIRDODGE_QUADRANT_34,
    COORDS_AIRDODGE_QUADRANT_MOD_X,
    COORDS_AIRDODGE_QUADRANT_12_MOD_Y,
    COORDS_AIRDODGE_QUADRANT_34_MOD_Y,
    COORDS_AIRDODGE_HORIZONTAL_MOD_Y,
    COORDS_FIREFOX_MOD_X_C_UP,
    COORDS_FIREFOX_MOD_X_C_DOWN,
    COORDS_FIREFOX_MOD_X_C_LEFT,
    COORDS_FIREFOX_MOD_X_C_RIGHT,
    COORDS_FIREFOX_MOD_Y_C_UP,
    COORDS_FIREFOX_MOD_Y_C_DOWN,
    COORDS_FIREFOX_MOD_Y_C_LEFT,
    COORDS_FIREFOX_MOD_Y_C_RIGHT,
    COORDS_EXT_FIREFOX_MOD_X,
    COORDS_EXT_FIREFOX_MOD_X_C_UP,
    COORDS_EXT_FIREFOX_MOD_X_C_DOWN,
    COORDS_EXT_FIREFOX_MOD_X_C_LEFT,
    COORDS_EXT_FIREFOX_MOD_X_C_RIGHT,
    COORDS_EXT_FIREFOX_MOD_Y,
    COORDS_EXT_FIREFOX_MOD_Y_C_UP,
    COORDS_EXT_FIREFOX_MOD_Y_C_DOWN,
    COORDS_EXT_FIREFOX_MOD_Y_C_LEFT,
    COORDS_EXT_FIREFOX_MOD_Y_C_RIGHT,
    B0XX,
)


@pytest.fixture
def s():
    return B0XXState()


# ============================================================
# convert_coords
# ============================================================

class TestConvertCoords:
    def test_origin(self):
        x, y = convert_coords((0.0, 0.0))
        assert x == STICK_AXIS_CENTER_X
        assert y == STICK_AXIS_CENTER_Y

    def test_full_right(self):
        x, y = convert_coords((1.0, 0.0))
        assert x == int(round(STICK_AXIS_CENTER_X + 10271))
        assert y == STICK_AXIS_CENTER_Y

    def test_full_up(self):
        x, y = convert_coords((0.0, 1.0))
        assert x == STICK_AXIS_CENTER_X
        assert y == int(round(STICK_AXIS_CENTER_Y - 10271))

    def test_full_down(self):
        x, y = convert_coords((0.0, -1.0))
        assert x == STICK_AXIS_CENTER_X
        assert y == int(round(STICK_AXIS_CENTER_Y + 10271))

    def test_full_left(self):
        x, y = convert_coords((-1.0, 0.0))
        assert x == int(round(STICK_AXIS_CENTER_X - 10271))

    def test_symmetry(self):
        xr, yr = convert_coords((0.5, 0.5))
        xl, yl = convert_coords((-0.5, -0.5))
        assert abs((xr - STICK_AXIS_CENTER_X) + (xl - STICK_AXIS_CENTER_X)) <= 1
        assert abs((yr - STICK_AXIS_CENTER_Y) + (yl - STICK_AXIS_CENTER_Y)) <= 1

    def test_matches_upstream_ahk_effective_range(self):
        coords = (0.7375, 0.3125)
        x, y = convert_coords(coords)
        assert x == int(round((coords[0] * 10271) + STICK_AXIS_CENTER_X))
        assert y == int(round((-coords[1] * 10271) + STICK_AXIS_CENTER_Y))

    def test_up_mod_x_matches_upstream_raw_axis(self):
        x, y = convert_coords(COORDS_VERTICAL_MOD_X)
        assert x == STICK_AXIS_CENTER_X
        assert y == int(round(STICK_AXIS_CENTER_Y - (COORDS_VERTICAL_MOD_X[1] * 10271)))


# ============================================================
# convert_analog_r
# ============================================================

class TestConvertAnalogR:
    def test_zero(self):
        assert convert_analog_r(0) == TRIGGER_AXIS_MIN

    def test_49(self):
        assert convert_analog_r(49) == 49

    def test_94(self):
        assert convert_analog_r(94) == 94

    def test_255(self):
        assert convert_analog_r(255) == TRIGGER_AXIS_MAX


# ============================================================
# B0XXState — SOCD resolution helpers
# ============================================================

class TestSOCD:
    def test_up_active_when_most_recent(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.up() is True

    def test_up_inactive_when_not_most_recent(self, s):
        s.button_up = True
        s.most_recent_vertical = "D"
        assert s.up() is False

    def test_down_active(self, s):
        s.button_down = True
        s.most_recent_vertical = "D"
        assert s.down() is True

    def test_left_right_socd(self, s):
        """Hold right, then left: left should be active (last wins)."""
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.right() is True
        s.button_left = True
        s.most_recent_horizontal = "L"
        assert s.left() is True
        # right is still held but not most recent
        assert s.right() is False

    def test_up_down_socd(self, s):
        """Hold up, then down: down should be active (last wins)."""
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_down = True
        s.most_recent_vertical = "D"
        assert s.down() is True
        assert s.up() is False


# ============================================================
# B0XXState — modifier helpers
# ============================================================

class TestModifiers:
    def test_mod_x_active_alone(self, s):
        s.button_mod_x = True
        assert s.mod_x() is True

    def test_mod_y_active_alone(self, s):
        s.button_mod_y = True
        assert s.mod_y() is True

    def test_both_mods_cancels_both(self, s):
        s.button_mod_x = True
        s.button_mod_y = True
        assert s.mod_x() is False
        assert s.mod_y() is False
        assert s.both_mods() is True

    def test_simultaneous_horizontal_lockout(self, s):
        """When lockout is set and no vertical held, mods are disabled."""
        s.button_mod_x = True
        s.simultaneous_horizontal_modifier_lockout = True
        assert s.mod_x() is False

    def test_simultaneous_horizontal_lockout_with_vertical(self, s):
        """Lockout doesn't apply when a vertical is held."""
        s.button_mod_x = True
        s.simultaneous_horizontal_modifier_lockout = True
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.mod_x() is True


# ============================================================
# B0XXState — C-stick helpers
# ============================================================

class TestCStick:
    def test_c_up_active(self, s):
        s.button_c_up = True
        s.most_recent_vertical_c = "U"
        assert s.c_up() is True

    def test_c_down_active(self, s):
        s.button_c_down = True
        s.most_recent_vertical_c = "D"
        assert s.c_down() is True

    def test_c_left_active(self, s):
        s.button_c_left = True
        s.most_recent_horizontal_c = "L"
        assert s.c_left() is True

    def test_c_right_active(self, s):
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        assert s.c_right() is True

    def test_c_disabled_when_both_mods(self, s):
        """C-stick buttons become D-pad when both mods held."""
        s.button_mod_x = True
        s.button_mod_y = True
        s.button_c_up = True
        s.most_recent_vertical_c = "U"
        assert s.c_up() is False

    def test_any_c(self, s):
        assert s.any_c() is False
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        assert s.any_c() is True


# ============================================================
# B0XXState — shield/quadrant/composite helpers
# ============================================================

class TestCompositeHelpers:
    def test_any_shield(self, s):
        assert s.any_shield() is False
        s.button_l = True
        assert s.any_shield() is True

    def test_any_shield_light(self, s):
        s.button_light_shield = True
        assert s.any_shield() is True

    def test_any_shield_mid(self, s):
        s.button_mid_shield = True
        assert s.any_shield() is True

    def test_any_quadrant(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.any_quadrant() is True

    def test_not_quadrant_single_direction(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.any_quadrant() is False


# ============================================================
# B0XXState — analog stick coordinates (no shield)
# ============================================================

class TestAnalogCoordsNoShield:
    def test_neutral(self, s):
        assert s.get_analog_coords() == COORDS_ORIGIN

    def test_up(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.get_analog_coords() == COORDS_VERTICAL

    def test_down(self, s):
        s.button_down = True
        s.most_recent_vertical = "D"
        assert s.get_analog_coords() == (0.0, -1.0)  # reflected

    def test_left(self, s):
        s.button_left = True
        s.most_recent_horizontal = "L"
        assert s.get_analog_coords() == (-1.0, 0.0)  # reflected

    def test_right(self, s):
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.get_analog_coords() == COORDS_HORIZONTAL

    def test_up_right(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.get_analog_coords() == COORDS_QUADRANT

    def test_down_left(self, s):
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_left = True
        s.most_recent_horizontal = "L"
        assert s.get_analog_coords() == (-0.7, -0.7)

    def test_up_mod_x(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_mod_x = True
        assert s.get_analog_coords() == COORDS_VERTICAL_MOD_X

    def test_up_mod_y(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_mod_y = True
        assert s.get_analog_coords() == COORDS_VERTICAL_MOD_Y

    def test_right_mod_x(self, s):
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_x = True
        assert s.get_analog_coords() == COORDS_HORIZONTAL_MOD_X

    def test_right_mod_y(self, s):
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        assert s.get_analog_coords() == COORDS_HORIZONTAL_MOD_Y

    def test_quadrant_mod_x(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_x = True
        assert s.get_analog_coords() == COORDS_QUADRANT_MOD_X

    def test_quadrant_mod_y(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        assert s.get_analog_coords() == COORDS_QUADRANT_MOD_Y

    def test_turnaround_side_b_nerf_horizontal(self, s):
        """ModY + horizontal + B should give full horizontal (nerf)."""
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        s.button_b = True
        assert s.get_analog_coords() == COORDS_HORIZONTAL


# ============================================================
# B0XXState — analog stick coordinates (airdodge / shield held)
# ============================================================

class TestAnalogCoordsAirdodge:
    def _hold_l(self, s):
        s.button_l = True

    def test_neutral_with_shield(self, s):
        self._hold_l(s)
        assert s.get_analog_coords() == COORDS_ORIGIN

    def test_up_with_shield(self, s):
        self._hold_l(s)
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.get_analog_coords() == COORDS_VERTICAL  # same as airdodge vertical

    def test_quadrant_up_no_mod(self, s):
        self._hold_l(s)
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.get_analog_coords() == COORDS_AIRDODGE_QUADRANT_12

    def test_quadrant_down_no_mod(self, s):
        self._hold_l(s)
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_right = True
        s.most_recent_horizontal = "R"
        x, y = s.get_analog_coords()
        assert (x, -y) == COORDS_AIRDODGE_QUADRANT_34  # reflected down

    def test_quadrant_mod_x(self, s):
        self._hold_l(s)
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_x = True
        assert s.get_analog_coords() == COORDS_AIRDODGE_QUADRANT_MOD_X

    def test_quadrant_up_mod_y(self, s):
        self._hold_l(s)
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        assert s.get_analog_coords() == COORDS_AIRDODGE_QUADRANT_12_MOD_Y

    def test_quadrant_down_mod_y(self, s):
        self._hold_l(s)
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        x, y = s.get_analog_coords()
        assert (x, -y) == COORDS_AIRDODGE_QUADRANT_34_MOD_Y

    def test_horizontal_mod_y_side_b_nerf(self, s):
        """ModY + horizontal + B + shield should give full horizontal (nerf)."""
        self._hold_l(s)
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        s.button_b = True
        assert s.get_analog_coords() == COORDS_HORIZONTAL

    def test_horizontal_mod_y_no_b(self, s):
        self._hold_l(s)
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_y = True
        assert s.get_analog_coords() == COORDS_AIRDODGE_HORIZONTAL_MOD_Y


# ============================================================
# B0XXState — firefox angles
# ============================================================

class TestFirefoxAngles:
    def _setup_firefox(self, s, mod, c_dir, with_b=False):
        """Set up state for a firefox angle test.
        mod: 'x' or 'y'
        c_dir: 'up', 'down', 'left', 'right', or None
        """
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        if mod == "x":
            s.button_mod_x = True
        else:
            s.button_mod_y = True
        if c_dir == "up":
            s.button_c_up = True
            s.most_recent_vertical_c = "U"
        elif c_dir == "down":
            s.button_c_down = True
            s.most_recent_vertical_c = "D"
        elif c_dir == "left":
            s.button_c_left = True
            s.most_recent_horizontal_c = "L"
        elif c_dir == "right":
            s.button_c_right = True
            s.most_recent_horizontal_c = "R"
        if with_b:
            s.button_b = True

    def test_mod_x_c_up(self, s):
        self._setup_firefox(s, "x", "up")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_X_C_UP

    def test_mod_x_c_down(self, s):
        self._setup_firefox(s, "x", "down")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_X_C_DOWN

    def test_mod_x_c_left(self, s):
        self._setup_firefox(s, "x", "left")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_X_C_LEFT

    def test_mod_x_c_right(self, s):
        self._setup_firefox(s, "x", "right")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_X_C_RIGHT

    def test_mod_y_c_up(self, s):
        self._setup_firefox(s, "y", "up")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_Y_C_UP

    def test_mod_y_c_down(self, s):
        self._setup_firefox(s, "y", "down")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_Y_C_DOWN

    def test_mod_y_c_left(self, s):
        self._setup_firefox(s, "y", "left")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_Y_C_LEFT

    def test_mod_y_c_right(self, s):
        self._setup_firefox(s, "y", "right")
        assert s.get_analog_coords() == COORDS_FIREFOX_MOD_Y_C_RIGHT

    # Extended firefox (with B)
    def test_ext_mod_x_c_up(self, s):
        self._setup_firefox(s, "x", "up", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_X_C_UP

    def test_ext_mod_x_c_down(self, s):
        self._setup_firefox(s, "x", "down", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_X_C_DOWN

    def test_ext_mod_x_c_left(self, s):
        self._setup_firefox(s, "x", "left", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_X_C_LEFT

    def test_ext_mod_x_c_right(self, s):
        self._setup_firefox(s, "x", "right", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_X_C_RIGHT

    def test_ext_mod_x_no_c(self, s):
        self._setup_firefox(s, "x", None, with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_X

    def test_ext_mod_y_c_up(self, s):
        self._setup_firefox(s, "y", "up", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_Y_C_UP

    def test_ext_mod_y_c_down(self, s):
        self._setup_firefox(s, "y", "down", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_Y_C_DOWN

    def test_ext_mod_y_c_left(self, s):
        self._setup_firefox(s, "y", "left", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_Y_C_LEFT

    def test_ext_mod_y_c_right(self, s):
        self._setup_firefox(s, "y", "right", with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_Y_C_RIGHT

    def test_ext_mod_y_no_c(self, s):
        self._setup_firefox(s, "y", None, with_b=True)
        assert s.get_analog_coords() == COORDS_EXT_FIREFOX_MOD_Y


# ============================================================
# B0XXState — reflection
# ============================================================

class TestReflection:
    def test_down_reflects_y(self, s):
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_right = True
        s.most_recent_horizontal = "R"
        x, y = s.get_analog_coords()
        assert x == COORDS_QUADRANT[0]
        assert y == -COORDS_QUADRANT[1]

    def test_left_reflects_x(self, s):
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_left = True
        s.most_recent_horizontal = "L"
        x, y = s.get_analog_coords()
        assert x == -COORDS_QUADRANT[0]
        assert y == COORDS_QUADRANT[1]

    def test_down_left_reflects_both(self, s):
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_left = True
        s.most_recent_horizontal = "L"
        x, y = s.get_analog_coords()
        assert x == -COORDS_QUADRANT[0]
        assert y == -COORDS_QUADRANT[1]


# ============================================================
# B0XXState — C-stick coordinates
# ============================================================

class TestCStickCoords:
    def test_neutral(self, s):
        assert s.get_c_stick_coords() == (0.0, 0.0)

    def test_c_up(self, s):
        s.button_c_up = True
        s.most_recent_vertical_c = "U"
        assert s.get_c_stick_coords() == (0.0, 1.0)

    def test_c_down(self, s):
        s.button_c_down = True
        s.most_recent_vertical_c = "D"
        assert s.get_c_stick_coords() == (0.0, -1.0)  # reflected

    def test_c_right(self, s):
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        assert s.get_c_stick_coords() == (1.0, 0.0)

    def test_c_left(self, s):
        s.button_c_left = True
        s.most_recent_horizontal_c = "L"
        assert s.get_c_stick_coords() == (-1.0, 0.0)

    def test_c_diagonal(self, s):
        s.button_c_up = True
        s.most_recent_vertical_c = "U"
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        assert s.get_c_stick_coords() == (0.525, 0.85)

    def test_c_right_mod_x_up(self, s):
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        s.button_mod_x = True
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.get_c_stick_coords() == (0.9, 0.5)

    def test_c_right_mod_x_down(self, s):
        s.button_c_right = True
        s.most_recent_horizontal_c = "R"
        s.button_mod_x = True
        s.button_down = True
        s.most_recent_vertical = "D"
        assert s.get_c_stick_coords() == (0.9, -0.5)

    def test_c_left_reflects(self, s):
        s.button_c_left = True
        s.most_recent_horizontal_c = "L"
        s.button_mod_x = True
        s.button_up = True
        s.most_recent_vertical = "U"
        assert s.get_c_stick_coords() == (-0.9, 0.5)

    def test_c_down_diagonal_reflects(self, s):
        s.button_c_down = True
        s.most_recent_vertical_c = "D"
        s.button_c_left = True
        s.most_recent_horizontal_c = "L"
        x, y = s.get_c_stick_coords()
        assert x == -0.525
        assert y == -0.85


# ============================================================
# B0XX.handle_key integration (mocked gamepad)
# ============================================================

class TestHandleKey:
    @pytest.fixture
    def b0xx(self, tmp_path):
        config = tmp_path / "hotkeys.ini"
        config.write_text(
            "[Hotkeys]\n"
            "1=KEY_W\n"       # Analog Up
            "2=KEY_S\n"       # Analog Down
            "3=KEY_A\n"       # Analog Left
            "4=KEY_D\n"       # Analog Right
            "5=KEY_V\n"       # ModX
            "6=KEY_B\n"       # ModY
            "7=KEY_M\n"       # A
            "8=KEY_O\n"       # B
            "9=KEY_Q\n"       # L
            "10=KEY_E\n"      # R
            "11=KEY_P\n"      # X
            "12=KEY_0\n"      # Y
            "13=KEY_L\n"      # Z
            "14=KEY_K\n"      # C-Up
            "15=KEY_J\n"      # C-Down
            "16=KEY_N\n"      # C-Left
            "17=KEY_COMMA\n"  # C-Right
            "18=KEY_MINUS\n"  # Light Shield
            "19=KEY_EQUAL\n"  # Mid Shield
            "20=KEY_7\n"      # Start
            "21=KEY_UP\n"     # D-Up
            "22=KEY_DOWN\n"   # D-Down
            "23=KEY_LEFT\n"   # D-Left
            "24=KEY_RIGHT\n"  # D-Right
        )
        from evdev import ecodes
        b = B0XX.__new__(B0XX)
        b.state = B0XXState()
        b.gamepad = MagicMock()
        b.key_map = {}
        # Manually parse since _load_config prints
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(str(config))
        for idx_str, key_name in cfg["Hotkeys"].items():
            idx = int(idx_str.strip())
            keycode = getattr(ecodes, key_name.strip(), None)
            if keycode is not None:
                b.key_map[keycode] = idx
        return b

    def test_press_a_sets_button(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_M, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 5)
        assert b0xx.state.button_a is True

    def test_release_a_clears_button(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_M, True)
        b0xx.handle_key(ecodes.KEY_M, False)
        b0xx.gamepad.set_btn.assert_called_with(False, 5)
        assert b0xx.state.button_a is False

    def test_press_b_updates_analog(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_O, True)
        assert b0xx.state.button_b is True
        b0xx.gamepad.set_btn.assert_any_call(True, 4)

    def test_up_updates_state_and_sticks(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_W, True)
        assert b0xx.state.button_up is True
        assert b0xx.state.most_recent_vertical == "U"
        # Should have called set_axis for analog stick and c-stick
        assert b0xx.gamepad.set_axis.call_count >= 2

    def test_left_right_lockout(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_D, True)   # right
        assert b0xx.state.simultaneous_horizontal_modifier_lockout is False
        b0xx.handle_key(ecodes.KEY_A, True)   # left while right held
        assert b0xx.state.simultaneous_horizontal_modifier_lockout is True
        b0xx.handle_key(ecodes.KEY_A, False)  # release left
        assert b0xx.state.simultaneous_horizontal_modifier_lockout is False

    def test_mod_x_clears_lockout(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_D, True)
        b0xx.handle_key(ecodes.KEY_A, True)
        assert b0xx.state.simultaneous_horizontal_modifier_lockout is True
        b0xx.handle_key(ecodes.KEY_V, True)  # ModX
        assert b0xx.state.simultaneous_horizontal_modifier_lockout is False

    def test_c_up_with_both_mods_sends_dpad(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_V, True)  # ModX
        b0xx.handle_key(ecodes.KEY_B, True)  # ModY
        b0xx.gamepad.reset_mock()
        b0xx.handle_key(ecodes.KEY_K, True)  # C-Up
        b0xx.gamepad.set_btn.assert_any_call(True, 9)  # D-pad Up

    def test_light_shield_sets_analog_r(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_MINUS, True)
        assert b0xx.state.button_light_shield is True
        b0xx.gamepad.set_axis.assert_called()

    def test_mid_shield_sets_analog_r(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_EQUAL, True)
        assert b0xx.state.button_mid_shield is True

    def test_start_button(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_7, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 8)

    def test_dpad_buttons(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_UP, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 9)
        b0xx.handle_key(ecodes.KEY_DOWN, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 11)
        b0xx.handle_key(ecodes.KEY_LEFT, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 10)
        b0xx.handle_key(ecodes.KEY_RIGHT, True)
        b0xx.gamepad.set_btn.assert_called_with(True, 12)

    def test_unmapped_key_ignored(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_F12, True)
        b0xx.gamepad.set_btn.assert_not_called()
        b0xx.gamepad.set_axis.assert_not_called()

    def test_x_y_z_buttons(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_P, True)   # X
        b0xx.gamepad.set_btn.assert_called_with(True, 6)
        b0xx.handle_key(ecodes.KEY_0, True)   # Y
        b0xx.gamepad.set_btn.assert_called_with(True, 2)
        b0xx.handle_key(ecodes.KEY_L, True)   # Z
        b0xx.gamepad.set_btn.assert_called_with(True, 7)

    def test_l_r_update_analog_stick(self, b0xx):
        from evdev import ecodes
        b0xx.handle_key(ecodes.KEY_Q, True)   # L
        assert b0xx.state.button_l is True
        assert b0xx.gamepad.set_axis.call_count > 0
        b0xx.gamepad.reset_mock()
        b0xx.handle_key(ecodes.KEY_E, True)   # R
        assert b0xx.state.button_r is True
        assert b0xx.gamepad.set_axis.call_count > 0


# ============================================================
# Full sequence tests (simulating gameplay scenarios)
# ============================================================

class TestGameplaySequences:
    def test_wavedash_right(self, s):
        """Simulate wavedash right: hold right + down + L, expect airdodge coords."""
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_l = True
        x, y = s.get_analog_coords()
        assert x == COORDS_AIRDODGE_QUADRANT_34[0]
        assert y == -COORDS_AIRDODGE_QUADRANT_34[1]

    def test_dashback(self, s):
        """Hold right, then quickly tap left: left should take over."""
        s.button_right = True
        s.most_recent_horizontal = "R"
        assert s.right() is True
        s.button_left = True
        s.most_recent_horizontal = "L"
        assert s.left() is True
        assert s.right() is False

    def test_firefox_angle_sequence(self, s):
        """Set up a full firefox angle: up+right+modX+c_up."""
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_x = True
        s.button_c_up = True
        s.most_recent_vertical_c = "U"
        coords = s.get_analog_coords()
        assert coords == COORDS_FIREFOX_MOD_X_C_UP

    def test_shield_drop(self, s):
        """Shield + down + modX = airdodge vertical modX coords (reflected)."""
        s.button_r = True
        s.button_down = True
        s.most_recent_vertical = "D"
        s.button_mod_x = True
        x, y = s.get_analog_coords()
        assert x == 0.0
        assert y == -0.5375  # reflected COORDS_VERTICAL_MOD_X

    def test_all_buttons_release_to_neutral(self, s):
        """Press everything, then release: should return to origin."""
        s.button_up = True
        s.most_recent_vertical = "U"
        s.button_right = True
        s.most_recent_horizontal = "R"
        s.button_mod_x = True
        assert s.get_analog_coords() != COORDS_ORIGIN

        s.button_up = False
        s.button_right = False
        s.button_mod_x = False
        assert s.get_analog_coords() == COORDS_ORIGIN
