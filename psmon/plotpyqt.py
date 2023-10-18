import sys
import math
import logging
import numpy as np
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from psmon import config
from psmon.util import arg_inflate_tuple, window_ratio, merge_dicts, check_data, ts_to_str
from psmon.plots import Hist, Image, XYPlot, MultiPlot
from psmon.format import parse_fmt_xyplot, parse_fmt_hist, parse_fmt_leg


LOG = logging.getLogger(__name__)


TypeMap = {
    Hist: 'HistClient',
    Image: 'ImageClient',
    XYPlot: 'XYPlotClient',
    MultiPlot: 'MultiPlotClient',
}


def type_getter(data_type, mod_name=__name__):
    plot_type_name = TypeMap.get(data_type)
    if plot_type_name is None:
        raise PyQtClientTypeError('No plotting client for datatype: %s' % data_type)
    return getattr(sys.modules[mod_name], plot_type_name)


class PyQtClientTypeError(Exception):
    pass


class PlotClient(object):
    def __init__(self, init, framegen, info, rate, **kwargs):
        # set the title
        self.title = init.title
        self.xdate = init.xdate
        self.ydate = init.ydate
        if 'figwin' in kwargs:
            self.is_win = False
            self.fig_win = kwargs['figwin']
            self.fig_layout = self.fig_win.addLayout()
            self.title_layout = self.fig_layout.addLayout()
            self._set_row_stretch(0)
            self.title_layout.addLabel(init.title, size='11pt', bold=True)
            self.fig_layout.nextRow()
        else:
            self.is_win = True
            self.fig_win = pg.GraphicsLayoutWidget()
            self.fig_win.setWindowTitle(init.title)
            self.fig_win.show()
            self.fig_layout = self.fig_win.ci
        self.plot_kwargs = {}
        # configure x/y axis as dates if requested
        self.set_date_axes()
        # create a sublayout for the plot itself
        self.plot_layout = self.fig_layout.addLayout()
        self._set_row_stretch(1)
        self.plot_view = self.plot_layout.addPlot(**self.plot_kwargs)
        # creat a sublayout under the plot for info/buttons
        self.fig_layout.nextRow()
        self.info_layout = self.fig_layout.addLayout()
        self._set_row_stretch(0)
        self.info_label = self.info_layout.addLabel('', justify='right')
        # set labels
        self.set_title(init.ts)
        self.set_title_axis('bottom', init.xlabel)
        self.set_title_axis('left', init.ylabel)
        # specific to this class
        self.framegen = framegen
        self.rate_ms = rate * 1000
        self.info = info
        self.multi_plot = False
        # set any user specified default axis ranges
        self.set_xy_ranges()
        # set log scales
        self.set_log_scale()
        # show grid lines if requested
        self.set_grid_lines()
        # create cursor event listener
        self.proxy = pg.SignalProxy(
            self.plot_view.scene().sigMouseMoved,
            rateLimit=config.PYQT_MOUSE_EVT_RATELIMIT,
            slot=self.cursor_hover_evt
        )

    def update_sub(self, data):
        pass

    def update(self, data):
        """
        Base update function - meant for basic functionality that should happen for all plot/image updates.

        Calls update_sub(self, data) which should be implement an Plot subclass specific update behavior
        """
        if data is not None:
            self.set_title(data.ts)
            self.set_title_axis('bottom', data.xlabel)
            self.set_title_axis('left', data.ylabel)
            self.set_win_title(data.title)
        return self.update_sub(data)

    def animate(self):
        self.ani_func()

    def ani_func(self):
        # call the data update function
        self.update(next(self.framegen))
        # setup timer for calling next update call
        QtCore.QTimer.singleShot(self.rate_ms, self.ani_func)

    def set_win_title(self, title):
        """
        Updates the window title of the plot or if it is an embedded in a MultiPlot the title layout label.
        """
        if title != self.title:
            if self.is_win:
                self.fig_win.setWindowTitle(title)
            else:
                # first item of the title_layout is the textbox
                self.title_layout.getItem(0, 0).setText(title, size='11pt', bold=True)
            self.title = title

    def set_title(self, title):
        if title is not None:
            self.plot_view.setTitle(title, size='10pt', justify='right')

    def set_title_axis(self, axis_name, axis_label_data):
        """
        Function for setting a label on the axis specified by 'axis_name'. The label data can be either a simple
        string or a dictionary of keywords that is passed on to the pyqtgraph setLabel function. Also allows
        additional keywords are treated as CSS style options by pyqtgraph

        Supported keywords:
        - text
        - units
        - unitPrefix
        Optional keywords (CSS style options):
        - font-size
        - font-family
        - font-style
        - font-weight
        - etc...
        """
        if isinstance(axis_label_data, Mapping):
            arg_list = ['text', 'units', 'unitPrefix']
            axis_args = [axis_label_data.get(value, None) for value in arg_list]
            axis_kwargs = {key: value for key, value in axis_label_data.items() if key not in arg_list}
            if axis_kwargs:
                axis_kwargs = merge_dicts(config.PYQT_AXIS_FMT, axis_kwargs)
            self._set_title_axis(axis_name, *axis_args, **axis_kwargs)
        else:
            self._set_title_axis(axis_name, axis_label_data)

    def _set_title_axis(self, axis_name, axis_title, axis_units=None, axis_unit_prefix=None, **kwargs):
        """
        Implementation function for creating a label for a specific axis - takes an axis_name, axis_title and optional
        axis_units, and axis_unit_prefix keyword args, which match to those for pyqtgraph's set label
        """
        if axis_title is not None:
            self.plot_view.setLabel(axis_name, text=axis_title, units=axis_units, unitPrefix=axis_unit_prefix, **kwargs)

    def set_aspect(self, lock, ratio):
        """
        Set the ascept ratio of the viewbox of the plot/image to the specified ratio.

        If no ratio is passed it uses the client side default.

        Note: this is disabled if explicit x/y ranges are set for view box since the
        two options fight each other.
        """
        if ratio is None:
            ratio = self.info.aspect

        # Since the images are technically transposed this is needed for the ratio to work the same as mpl
        if ratio is not None:
            ratio = 1.0 / ratio

        if self.info.xrange is None and self.info.yrange is None:
            self.plot_view.getViewBox().setAspectLocked(lock=lock, ratio=ratio)

    def set_xy_ranges(self):
        if self.info.xrange is not None:
            self.plot_view.setXRange(*self.info.xrange)
        if self.info.yrange is not None:
            self.plot_view.setYRange(*self.info.yrange)

    def set_log_scale(self):
        if self.info.logx or self.info.logy:
            np.seterr(divide='ignore')
        self.plot_view.setLogMode(self.info.logx, self.info.logy)

    def set_grid_lines(self, show=None, alpha=config.PYQT_GRID_LINE_ALPHA):
        if show is None:
            show = self.info.grid
        self.plot_view.showGrid(x=show, y=show, alpha=alpha)

    def _set_row_stretch(self, val):
        self.fig_layout.layout.setRowStretchFactor(self.fig_layout.currentRow, val)

    def set_date_axis(self, name):
        if 'axisItems' not in self.plot_kwargs:
            self.plot_kwargs['axisItems'] = {}
        self.plot_kwargs['axisItems'][name] = pg.DateAxisItem(orientation=name)

    def set_date_axes(self):
        if self.xdate:
            self.set_date_axis('bottom')
        if self.ydate:
            self.set_date_axis('left')

    def cursor_hover_evt_sub(self, x_pos, y_pos):
        fmt = 'x=%s, y=%s' % ('%s' if self.xdate else '%.5g', '%s' if self.ydate else '%.5g')
        vals = (ts_to_str(x_pos) if self.xdate else x_pos, ts_to_str(y_pos) if self.ydate else y_pos)
        self.info_label.setText(fmt % vals, size='10pt')

    def cursor_hover_evt(self, evt):
        pos = evt[0]
        if self.plot_view.sceneBoundingRect().contains(pos):
            mouse_pos = self.plot_view.getViewBox().mapSceneToView(pos)
            self.cursor_hover_evt_sub(mouse_pos.x(), mouse_pos.y())

    def add_legend(self, leg_label, leg_offset):
        if leg_label is not None:
            if leg_offset is None:
                self.plot_view.addLegend()
            else:
                try:
                    leg_offset_fmt = parse_fmt_leg(leg_offset)
                except ValueError:
                    LOG.warning('Inavlid legend offset for pyqtgraph: %s - Falling back to default offset', leg_offset)
                    leg_offset_fmt = None
                self.plot_view.addLegend(offset=leg_offset_fmt)


class ImageClient(PlotClient):
    def __init__(self, init_im, framegen, info, rate=1, **kwargs):
        super(ImageClient, self).__init__(init_im, framegen, info, rate, **kwargs)
        self.im_pos = init_im.pos
        self.im_scale = init_im.scale
        self.aspect_lock = init_im.aspect_lock
        self.aspect_ratio = init_im.aspect_ratio
        self.set_aspect(self.aspect_lock, self.aspect_ratio)
        self.set_grid_lines(False)
        self.im = pg.ImageItem(image=init_im.image.T, border=config.PYQT_BORDERS)
        if self.im_pos is not None:
            self.im.setPos(*self.im_pos)
        if self.im_scale is not None:
            self.im.scale(*self.im_scale)
        self.cb = pg.HistogramLUTItem(self.im, fillHistogram=True)

        # Setting up the color map to use
        cm = config.PYQT_COLOR_PALETTE
        if self.info.palette is not None:
            if self.info.palette in pg.graphicsItems.GradientEditorItem.Gradients:
                cm = self.info.palette
            else:
                LOG.warning('Inavlid color palette for pyqtgraph: %s - Falling back to default: %s',
                            self.info.palette, cm)
        self.cb.gradient.loadPreset(cm)

        # Set up colorbar ranges if specified
        if self.info.zrange is not None:
            self.cb.setLevels(*self.info.zrange)
            self.cb.setHistogramRange(*self.info.zrange)
        else:
            self.cb.setHistogramRange(*self.cb.getLevels())

        if config.PYQT_USE_ALT_IMG_ORIGIN:
            self.plot_view.invertY()
        self.plot_view.addItem(self.im)
        self.plot_layout.addItem(self.cb)

    def update_sub(self, data):
        """
        Updates the data in the image - none means their was no update for this interval
        """
        if data is not None:
            if self.aspect_lock != data.aspect_lock or self.aspect_ratio != data.aspect_ratio:
                self.aspect_lock = data.aspect_lock
                self.aspect_ratio = data.aspect_ratio
                self.set_aspect(self.aspect_lock, self.aspect_ratio)
            self.im.setImage(data.image.T, autoLevels=self.info.auto_zrange)
            if self.info.auto_zrange:
                self.cb.setLevels(*self.im.getLevels())
                self.cb.setHistogramRange(*self.cb.getLevels())
            if data.pos is not None and data.pos != self.im_pos:
                self.im.setPos(*data.pos)
                self.im_pos = data.pos
            if data.scale is not None and data.scale != self.im_scale:
                self.im.scale(*data.scale)
                self.im_scale = data.scale
        return self.im

    def cursor_hover_evt_sub(self, x_pos, y_pos):
        if 0 <= x_pos < self.im.image.shape[0] and 0 <= y_pos < self.im.image.shape[1]:
            z_val = self.im.image[int(x_pos)][int(y_pos)]
            # for image of float type show decimal places
            if hasattr(z_val, 'dtype') and np.issubdtype(z_val, np.integer):
                label_str = 'x=%d, y=%d, z=%d'
            else:
                label_str = 'x=%d, y=%d, z=%.5g'
            self.info_label.setText(label_str % (x_pos, y_pos, z_val), size='10pt')

    def cursor_hover_hevt_sub(self, z_val):
        img_z, img_n = self.im.getHistogram()
        index = np.searchsorted(img_z, z_val, side="right")-1
        if 0 <= index < img_n.shape[0]:
            z_low = img_z[index]
            if index + 1 < img_n.shape[0]:
                z_high = img_z[index+1]
            else:
                z_high = 2 * img_z[index] - img_z[index-1]
            self.info_label.setText('z=(%.5g, %.5g), n=%d' % (z_low, z_high, img_n[index]), size='10pt')

    def cursor_hover_evt(self, evt):
        pos = evt[0]
        if self.plot_view.sceneBoundingRect().contains(pos):
            mouse_pos = self.plot_view.getViewBox().mapSceneToView(pos)
            self.cursor_hover_evt_sub(mouse_pos.x(), mouse_pos.y())
        elif self.cb.sceneBoundingRect().contains(pos):
            mouse_pos = self.cb.vb.mapSceneToView(pos)
            self.cursor_hover_hevt_sub(mouse_pos.y())


class XYPlotClient(PlotClient):
    def __init__(self, init_plot, framegen, info, rate=1, **kwargs):
        super(XYPlotClient, self).__init__(init_plot, framegen, info, rate, **kwargs)
        self.plots = []
        self.formats = []
        self.add_legend(init_plot.leg_label, init_plot.leg_offset)
        inflated_args = arg_inflate_tuple(
            1,
            check_data(init_plot.xdata),
            check_data(init_plot.ydata),
            init_plot.formats,
            init_plot.leg_label
        )
        for xdata, ydata, format_val, legend in inflated_args:
            cval = len(self.plots)
            self.formats.append((format_val, cval))
            self.plots.append(
                self.plot_view.plot(
                    x=xdata,
                    y=ydata,
                    name=config.PYQT_LEGEND_FORMAT % legend,
                    **parse_fmt_xyplot(format_val, cval)
                )
            )

    def update_sub(self, data):
        """
        Updates the data in the plot - none means their was no update for this interval
        """
        if data is not None:
            inflated_args = arg_inflate_tuple(
                1,
                check_data(data.xdata),
                check_data(data.ydata),
                data.formats
            )
            for index, (plot, data_tup, format_tup) in enumerate(zip(self.plots, inflated_args, self.formats)):
                xdata, ydata, new_format = data_tup
                old_format, cval = format_tup
                if new_format != old_format:
                    self.formats[index] = (new_format, cval)
                    plot.setData(x=xdata, y=ydata, **parse_fmt_xyplot(new_format, cval))
                else:
                    plot.setData(x=xdata, y=ydata)
        return self.plots


class HistClient(PlotClient):
    def __init__(self, init_hist, framegen, info, rate=1, **kwargs):
        super(HistClient, self).__init__(init_hist, framegen, info, rate, **kwargs)
        self.hists = []
        self.formats = []
        self.add_legend(init_hist.leg_label, init_hist.leg_offset)
        inflated_args = arg_inflate_tuple(
            1,
            check_data(init_hist.bins),
            check_data(init_hist.values),
            init_hist.formats, init_hist.fills,
            init_hist.leg_label
        )
        for bins, values, format_val, fill_val, legend in inflated_args:
            cval = len(self.hists)
            fillLevel = 0 if fill_val else None
            self.formats.append((format_val, fill_val, cval))
            self.hists.append(
                self.plot_view.plot(
                    x=bins,
                    y=values,
                    name=config.PYQT_LEGEND_FORMAT % legend,
                    stepMode=True,
                    fillLevel=fillLevel,
                    **parse_fmt_hist(format_val, fill_val, cval)
                )
            )

    def update_sub(self, data):
        """
        Updates the data in the histogram - none means their was no update for this interval
        """
        if data is not None:
            inflated_args = arg_inflate_tuple(
                1,
                check_data(data.bins),
                check_data(data.values),
                data.formats,
                data.fills
            )
            for index, (hist, data_tup, format_tup) in enumerate(zip(self.hists, inflated_args, self.formats)):
                bins, values, new_format, new_fill = data_tup
                old_format, old_fill, cval = format_tup
                if new_format != old_format or new_fill != old_fill:
                    fillLevel = 0 if new_fill else None
                    self.formats[index] = (new_format, new_fill, cval)
                    hist.setData(x=bins, y=values, fillLevel=fillLevel, **parse_fmt_hist(new_format, new_fill, cval))
                else:
                    hist.setData(x=bins, y=values)
        return self.hists


class MultiPlotClient(object):
    def __init__(self, init, framegen, info, rate=1, **kwargs):
        # Set the title
        self.title = init.title
        if init.use_windows:
            self.is_win = None
            self.plots = [type_getter(type(data_obj))(data_obj, None, info, rate) for data_obj in init.data_con]
        else:
            if 'figwin' in kwargs:
                self.is_win = False
                self.outer_win = kwargs['figwin'].addLayout()
                # Add layout element for the title that will span all the multiplots columns
                self.title_layout = self.outer_win.addLayout()
                self.outer_win.layout.setRowStretchFactor(self.outer_win.currentRow, 0)
                self.title_layout.addLabel(init.title, size='11pt', bold=True)
                self.outer_win.nextRow()
                # Create an inner 'fig_win' layout for the multiplots themselves
                self.fig_win = self.outer_win.addLayout()
                self.outer_win.layout.setRowStretchFactor(self.outer_win.currentRow, 1)
            else:
                self.is_win = True
                self.fig_win = pg.GraphicsLayoutWidget()
                self.fig_win.setWindowTitle(init.title)
                self.fig_win.show()
            ratio_calc = window_ratio(config.PYQT_SMALL_WIN, config.PYQT_LARGE_WIN)
            if init.ncols is None:
                self.fig_win.resize(*ratio_calc(init.size, 1))
                self.plots = [type_getter(type(data_obj))(data_obj, None, info, rate, figwin=self.fig_win)
                              for data_obj in init.data_con]
            else:
                self.plots = []
                if not isinstance(init.ncols, int) or not 0 < init.ncols <= init.size:
                    ncols = init.size
                    nrows = 1
                    LOG.warning('Invalid column number specified: %s'
                                ' - Must be a positive integer less than the number of plots: %s',
                                init.ncols,
                                init.size)
                else:
                    ncols = init.ncols
                    nrows = math.ceil(init.size/float(init.ncols))
                self.fig_win.resize(*ratio_calc(ncols, nrows))
                for index, data_obj in enumerate(init.data_con):
                    if index > 0 and index % ncols == 0:
                        self.fig_win.nextRow()
                    self.plots.append(type_getter(type(data_obj))(data_obj, None, info, rate, figwin=self.fig_win))
        self.framegen = framegen
        self.rate_ms = rate * 1000
        self.info = info
        self.multi_plot = True

    def set_win_title(self, title):
        """
        Updates the window title of the MultiPlot or if it is an embedded in another MultiPlot then it
        updates title layout items label.
        """
        if title != self.title and self.is_win is not None:
            if self.is_win:
                self.fig_win.setWindowTitle(title)
            else:
                # first item of the title_layout is the textbox
                self.title_layout.getItem(0, 0).setText(title, size='11pt', bold=True)
            self.title = title

    def update(self, data):
        if data is not None:
            self.set_win_title(data.title)
            for plot, plot_data in zip(self.plots, data.data_con):
                plot.update(plot_data)

    def animate(self):
        self.ani_func()

    def ani_func(self):
        # call the data update function
        self.update(next(self.framegen))
        # setup timer for calling next update call
        QtCore.QTimer.singleShot(self.rate_ms, self.ani_func)
