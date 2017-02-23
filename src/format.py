import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from psmon import config


SOLID_LINE_CHAR = '-'
DOTTED_LINE_CHAR = ':'
LINE_CONT_CHAR = ['-', '.']

COLOR_LIST = [
    'b', # blue
    'g', # green
    'r', # red
    'c', # cyan
    'm', # magenta
    'y', # yellow
    'k', # black
    'w', # white
]

COLOR_RGB_MAP = {
    'b': (0, 0, 255), # blue
    'g': (0, 255, 0), # green
    'r': (255, 0, 0), # red
    'c': (0, 255, 255), # cyan
    'm': (255, 0, 255), # magenta
    'y': (255, 255, 0), # yellow
    'k': (0, 0, 0), # black
    'w': (255, 255, 255), # white
}

MARKER_MAP = {
    '.': ('o', config.PYQT_MARK_SIZE_SMALL),
    'o': ('o', config.PYQT_MARK_SIZE),
    'v': ('t', config.PYQT_MARK_SIZE),
    '^': ('t', config.PYQT_MARK_SIZE),
    '<': ('t', config.PYQT_MARK_SIZE),
    '>': ('t', config.PYQT_MARK_SIZE),
    '1': ('t', config.PYQT_MARK_SIZE),
    '2': ('t', config.PYQT_MARK_SIZE),
    '3': ('t', config.PYQT_MARK_SIZE),
    '4': ('t', config.PYQT_MARK_SIZE),
    's': ('s', config.PYQT_MARK_SIZE),
    '+': ('+', config.PYQT_MARK_SIZE),
    'x': ('x', config.PYQT_MARK_SIZE),
    'd': ('d', config.PYQT_MARK_SIZE),
    'D': ('d', config.PYQT_MARK_SIZE),
    # no matching equivalent in pyqt - use the fallback marker
    ',': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    'p': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    '*': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    'h': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    'H': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    '|': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
    '_': (config.PYQT_MARK_FALLBACK, config.PYQT_MARK_FALLBACK_SIZE),
}

LINE_MAP = {
    ':':  QtCore.Qt.DotLine,
    '-':  QtCore.Qt.SolidLine,
    '--': QtCore.Qt.DashLine,
    '-.': QtCore.Qt.DashDotLine,
}


LEGEND_CENTER_X = -config.PYQT_SMALL_WIN.x/3
LEGEND_CENTER_Y = -config.PYQT_SMALL_WIN.y/4
LEGEND_TUPLE_SCALE = 100
LEGEND_TUPLE_MIN = 0.001


LEGEND_OFFSETS = {
    'best': None,
    'upper right': (-20, 20),
    'upper left': (20, 20),
    'lower left': (20, -20),
    'lower right': (-20, -20),
    'right': (-20, LEGEND_CENTER_Y),
    'center left': (20, LEGEND_CENTER_Y),
    'center right': (-20, LEGEND_CENTER_Y),
    'lower center': (LEGEND_CENTER_X, -20),
    'upper center': (LEGEND_CENTER_X, 20),
    'center': (LEGEND_CENTER_X, LEGEND_CENTER_Y),
}


def parse_fmt_leg(leg_offset):
    try:
        x_pos, y_pos = leg_offset
        if abs(x_pos) > 1 or abs(x_pos) > 1:
            raise ValueError('Illegal legend offset tuple values: %s' % str(leg_offset))
        if x_pos > 0.5:
            result_x = LEGEND_TUPLE_SCALE * (x_pos - 1) - LEGEND_TUPLE_MIN
        else:
            result_x = LEGEND_TUPLE_SCALE * x_pos + LEGEND_TUPLE_MIN
        if y_pos > 0.5:
            result_y = LEGEND_TUPLE_SCALE * (y_pos - 1) - LEGEND_TUPLE_MIN
        else:
            result_y = LEGEND_TUPLE_SCALE * y_pos + LEGEND_TUPLE_MIN
        return result_x, result_y
    except (ValueError, TypeError):
        if leg_offset in LEGEND_OFFSETS:
            return LEGEND_OFFSETS[leg_offset]
        else:
            raise ValueError('Illegal legend offset value: %s' % str(leg_offset))


def parse_fmt_str(fmt_str, color_index):
    color = None
    line_style = None
    marker = None
    marker_size = None
    multi_char_seen = False

    for token in fmt_str:
        if multi_char_seen:
            multi_char_seen = False
            if token in LINE_CONT_CHAR:
                line_style = LINE_MAP.get(SOLID_LINE_CHAR + token)
                continue

        if token == SOLID_LINE_CHAR:
            if line_style is not None:
                raise ValueError('Illegal format string "%s"; two linestyle symbols' % fmt_str)
            line_style = LINE_MAP.get(SOLID_LINE_CHAR)
            multi_char_seen = True
        elif token == DOTTED_LINE_CHAR:
            if line_style is not None:
                raise ValueError('Illegal format string "%s"; two linestyle symbols' % fmt_str)
            line_style = QtCore.Qt.DotLine
        elif token in COLOR_LIST:
            if color is not None:
                raise ValueError('Illegal format string "%s"; two color symbols' % fmt_str)
            color = token
        elif token in MARKER_MAP:
            if marker is not None:
                raise ValueError('Illegal format string "%s"; two marker symbols' % fmt_str)
            marker, marker_size = MARKER_MAP.get(token)
        else:
            raise ValueError('Unrecognized character %s in format string "%s"' % (token, fmt_str))

    return color, line_style, marker, marker_size


def parse_fmt_xyplot(fmt_str, color_index=0):
    line = None
    fmt_dict = {}
    color, line_style, marker, marker_size = parse_fmt_str(fmt_str, color_index)

    # set color by rotating scheme if none is specified
    if color is None:
        color = (color_index, config.PYQT_AUTO_COLOR_MAX)

    # create a pen object for line if one is specified
    if line_style is not None:
        line = pg.mkPen(color, style=line_style)

    fmt_dict['pen'] = line

    # only pass add these entries if they are non-null
    if marker is not None or line is not None:
        fmt_dict['symbol'] = marker
    if color is not None:
        fmt_dict['symbolBrush'] = color
    if marker_size is not None:
        fmt_dict['symbolSize'] = marker_size

    return fmt_dict


def parse_fmt_hist(fmt_str, fill=True, color_index=0):
    line = None
    fmt_dict = {}
    color, line_style, marker, marker_size = parse_fmt_str(fmt_str, color_index)

    # set color by rotating scheme if none is specified
    if color is None:
        color = pg.intColor(color_index, config.PYQT_AUTO_COLOR_MAX, alpha=config.PYQT_HIST_ALPHA)
    else:
        color = COLOR_RGB_MAP.get(color) + (config.PYQT_HIST_ALPHA,)

    # create a pen object for line if one is specified
    if line_style is not None:
        if fill:
            line = pg.mkPen(config.PTQT_HIST_LINE_COLOR, style=line_style)
        else:
            line = pg.mkPen(color, style=line_style)

    # brush entry should always be present in the output
    fmt_dict['fillBrush'] = color

    # only pass add these entries if they are non-null
    if line is not None:
        fmt_dict['pen'] = line

    return fmt_dict
