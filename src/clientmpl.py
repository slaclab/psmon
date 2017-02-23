import socket
import logging
import threading

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

import psmon.plotmpl as psplot
from psmon.plotmpl import MplClientTypeError
from psmon import app, config


LOG = logging.getLogger(__name__)


def main(client_info, plot_info):
    # initialze all the socket connections
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

    # start the plotting rendering routine
    try:
        plot = data_type(init_data, zmqsub.get_socket_gen(), plot_info, rate=1.0/client_info.rate)
        plot_ani = plot.animate()
    except MplClientTypeError as err:
        LOG.critical('Server returned datagram with an unsupported type: %s', err)
        return 1

    # auto zoom button params
    az_xpos = 0.01
    az_ypos = 0.015
    az_xlen = 0.12
    az_ylen = 0.035
    az_xlen_multi = 0.14
    # add some border to the bottom of the plot for the buttons
    plot.figure.subplots_adjust(bottom=0.12)
    if plot.multi_plot:
        button_cnt = 0
        auto_zoom_buttons = []
        for sub_ax in plot.ax:
            auto_zoom_button = Button(plt.axes([az_xpos + button_cnt * (az_xpos + az_xlen_multi) , az_ypos, az_xlen_multi, az_ylen]),
                                      'Auto Zoom %d' % (button_cnt+1))
            auto_zoom_button.on_clicked(sub_ax.autoscale)
            auto_zoom_buttons.append(auto_zoom_button)
            button_cnt += 1
    else:
        auto_zoom_button = Button(plt.axes([az_xpos, az_ypos, az_xlen, az_ylen]), 'Auto Zoom')
        auto_zoom_button.on_clicked(plot.ax.autoscale)

    # define signal sender function
    reset_req = app.ZMQRequester(zmqsub.comm_socket)

    reset_plots_button = Button(plt.axes([0.87, 0.015, 0.12, 0.035]), 'Reset Plots')
    reset_plots_button.on_clicked(reset_req.send_reset_signal)

    try:
        plt.show()
    except:
        # sort of ugly but this can throw all kinds of errors when closing a window
        pass

    # return process status code
    return 0
