import sys
import logging

from psmon import app, config, util

# Suppress mpi setup output
with util.redirect_stdout():
    import pyqtgraph as pg
    from pyqtgraph.Qt import QtCore, QtGui
    import psmon.plotpyqt as psplot
    from psmon.plotpyqt import PyQtClientTypeError


LOG = logging.getLogger(__name__)


def set_color_opt(option, value):
    if value is not None:
        try:
            pg.setConfigOption(option, pg.functions.colorTuple(pg.functions.Color(value)))
        except Exception:
            LOG.warning('Inavlid %s color for pyqtgraph: %s', option, value)


def main(client_info, plot_info):
    # initialize all the socket connections
    zmqsub = app.ZMQSubscriber(client_info)

    # grab an initial datagram from the server
    try:
        init_data = zmqsub.data_recv()
    except AttributeError as err:
        LOG.critical('Server returned an unparsable datagram: %s', err)
        return 1

    # Check that the datagram is valid
    if not init_data.valid:
        LOG.critical('Server returned an invalid datagram of datatype: %s', type(init_data))
        return 1

    # attempt to decode its type and go from there
    try:
        data_type = psplot.type_getter(type(init_data))
    except TypeError:
        LOG.exception('Server returned an unknown datatype: %s', type(init_data))
        return 1

    # start the QtApp
    qtapp = QtGui.QApplication([])
    # set widget background/foreground color if specified
    set_color_opt('background', plot_info.bkg_col)
    set_color_opt('foreground', plot_info.fore_col)
    # get geometry of current screen at set max window geo
    qtdesk = qtapp.desktop()
    screen_geo = qtdesk.availableGeometry()
    config.PYQT_LARGE_WIN = config.Resolution(
        min(screen_geo.width(), config.PYQT_LARGE_WIN.x),
        min(screen_geo.height(), config.PYQT_LARGE_WIN.y),
    )

    # start the plotting rendering routine
    try:
        plot = data_type(init_data, zmqsub.get_socket_gen(), plot_info, rate=1.0/client_info.rate)
        plot.animate()
    except PyQtClientTypeError as err:
        LOG.critical('Server returned datagram with an unsupported type: %s', err)
        return 1

    # define signal sender function
    #reset_req = app.ZMQRequester(zmqsub.comm_socket)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()

    return 0
