import sys
import logging
from collections import namedtuple

# COORDINATE TUPLE USED FOR CONFIGS
Resolution = namedtuple('Resolution', 'x y')
# CONFIG KEYS FOR SERVER
RESET_REQ_HEADER = 'reset'
RESET_REQ_STR = 'reset signal - %s'
RESET_REP_STR = 'reset signal recieved from %s'
ZMQ_TOPIC_DELIM_CHAR = '\x00'
# CONFIG KEYS FOR LOGGING
LOG_BASE_NAME = __package__
LOG_LEVEL = 'INFO'
LOG_LEVEL_ROOT = logging.WARN
LOG_FORMAT = '[%(levelname)-8s] %(message)s'  # '%(asctime)s:%(levelname)s:%(message)s'
# GENERAL APP CONFIG
APP_INTERACTIVE = False
if hasattr(sys, 'ps1'):
    APP_INTERACTIVE = True
elif sys.flags.interactive:
    APP_INTERACTIVE = True
APP_SERVER = 'localhost'
APP_PORT = 12323
APP_COMM_OFFSET = 1
APP_TIMEOUT = 5.0
APP_RATE = 5.0
APP_BUFFER = 5
APP_CLIENT = 'pyqt'
APP_RUN_DEFAULT = '12'
APP_EXP_DEFAULT = 'xppb0114'
APP_BIND_ATTEMPT = 32
APP_RECV_LIMIT = 25
APP_IMG_INTERPOLATION = 'none'
APP_LOCAL = False
APP_XRANGE = None
APP_YRANGE = None
APP_ZRANGE = None
APP_ASPECT = None
APP_BKG_COLOR = None
APP_TEXT_COLOR = None
APP_PALETTE = None
APP_GRID = False
APP_AUTO_ZRANGE = False
APP_LOG = False
APP_RESERVED_TOPIC = 'psmon-internal'
APP_TOPIC_LIST = APP_RESERVED_TOPIC + '-topics'
# PYQT DEFAULT APPEARANCE CONFIG
PYQT_SMALL_WIN = Resolution(640, 480)
PYQT_LARGE_WIN = Resolution(3840, 2880)
PYQT_BORDERS = {'color': (150, 150, 150), 'width': 1.0}
PYQT_AXIS_FMT = {'color': '#969696', 'font-size': '10pt', 'font-family': 'Sans'}
PYQT_PLOT_PEN = None
PYQT_PLOT_SYMBOL = 'o'
PYQT_COLOR_PALETTE = 'thermal'
PYQT_AUTO_COLOR_MAX = 9
PYQT_HIST_ALPHA = 80
PTQT_HIST_LINE_COLOR = 'w'
PYQT_MARK_SIZE = 10
PYQT_MARK_SIZE_SMALL = 5
PYQT_MARK_FALLBACK = 'o'
PYQT_MARK_FALLBACK_SIZE = 5
PYQT_USE_ALT_IMG_ORIGIN = True
PYQT_MOUSE_EVT_RATELIMIT = 30
PYQT_GRID_LINE_ALPHA = None
PYQT_LEGEND_FORMAT = "<div style='margin-left:10px;'>%s</div>"
# MPL DEFAULT APPEARANCE CONFIG
MPL_SMALL_WIN = Resolution(8, 6)
MPL_LARGE_WIN = Resolution(32, 24)
MPL_COLOR_PALETTE = 'hot'
MPL_AXES_BKG_COLOR = 'w'
MPL_HISTO_STYLE = 'steps-mid'
MPL_HIST_ALPHA = 1.0
