import sys
import math
import logging
try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import rcParams
from matplotlib.axes._base import _process_plot_format

from psmon import config
from psmon.util import is_py_iter, arg_inflate_flat, arg_inflate_tuple, inflate_input, check_data
from psmon.util import window_ratio, ts_to_dt
from psmon.plots import Hist, Image, XYPlot, MultiPlot


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
        raise MplClientTypeError('No plotting client for datatype: %s' % data_type)
    return getattr(sys.modules[mod_name], plot_type_name)


class MplClientTypeError(Exception):
    pass


class PlotClient(object):
    def __init__(self, init, framegen, info, rate, **kwargs):
        if 'figax' in kwargs:
            self.figure, self.ax = kwargs['figax']
        else:
            self.figure, self.ax = plt.subplots(facecolor=info.bkg_col, edgecolor=info.bkg_col)
            # this is needed for older versions of matplotlib where axis objects don't have set_facecolor
            if not hasattr(self.ax, 'set_facecolor'):
                self.ax.set_axis_bgcolor(info.bkg_col or config.MPL_AXES_BKG_COLOR)
            if self.figure.canvas.manager is not None:
                self.figure.canvas.manager.set_window_title(init.title)
        self.info = info
        self.set_title(init.ts)
        self.set_labels(init.xlabel, init.ylabel)
        self.set_ax_col(self.ax)
        self.framegen = framegen
        self.rate_ms = rate * 1000
        self.multi_plot = False
        self.xdate = init.xdate
        self.ydate = init.ydate

    def update_sub(self, data):
        pass

    def update(self, data):
        if data is not None:
            self.set_title(data.ts)
            self.set_labels(data.xlabel, data.ylabel)
        return self.update_sub(data)

    def animate(self):
        return animation.FuncAnimation(self.figure, self.update, self.ani_func, interval=self.rate_ms)

    def ani_func(self):
        yield next(self.framegen)

    def set_title(self, title):
        if title is not None:
            if self.info.fore_col is not None:
                self.ax.set_title(title, loc='right', color=self.info.fore_col)
            else:
                self.ax.set_title(title, loc='right')

    def set_labels(self, xlabel=None, ylabel=None):
        self.set_axis_label(self.ax.set_xlabel, xlabel)
        self.set_axis_label(self.ax.set_ylabel, ylabel)

    def set_axis_label(self, axis_label_func, axis_label_data):
        if isinstance(axis_label_data, Mapping):
            if 'axis_title' in axis_label_data:
                label_str = axis_label_data['axis_title']
                if 'axis_units' in axis_label_data:
                    if 'axis_units_prefix' in axis_label_data:
                        label_str += ' [%s%s]' % (axis_label_data['axis_units'], axis_label_data['axis_units_prefix'])
                    else:
                        label_str += ' [%s]' % axis_label_data['axis_units']
                axis_label_func(label_str)
        elif axis_label_data is not None:
            axis_label_func(axis_label_data)

    def set_xy_ranges(self):
        if self.info.xrange is not None:
            self.ax.set_xlim(self.info.xrange)
        if self.info.yrange is not None:
            self.ax.set_ylim(self.info.yrange)

    def set_log_scale(self):
        if self.info.logx:
            self.ax.set_xscale('log')
        if self.info.logy:
            self.ax.set_yscale('log')

    def set_aspect(self, lock=True, ratio=None):
        if ratio is None:
            ratio = self.info.aspect
        if lock:
            if ratio is not None:
                self.ax.set_aspect(ratio)
        else:
            self.ax.set_aspect('auto')

    def set_ax_col(self, ax):
        if self.info.fore_col is not None:
            for ax_name in ['bottom', 'top', 'right', 'left']:
                ax.spines[ax_name].set_color(self.info.fore_col)
            for ax_name in ['x', 'y']:
                ax.tick_params(axis=ax_name, colors=self.info.fore_col)
            ax.yaxis.label.set_color(self.info.fore_col)
            ax.xaxis.label.set_color(self.info.fore_col)

    def set_grid_lines(self, show=None):
        if show is None:
            show = self.info.grid
        self.ax.grid(show)

    def update_plot_data(self, plots, x_vals, y_vals, new_fmts, old_fmts):
        inflated_args = arg_inflate_tuple(1, check_data(x_vals), check_data(y_vals), new_fmts)
        for index, (plot, data_tup, old_fmt) in enumerate(zip(plots, inflated_args, old_fmts)):
            x_val, y_val, new_fmt = data_tup
            plot.set_data(ts_to_dt(x_val) if self.xdate else x_val, ts_to_dt(y_val) if self.ydate else y_val)
            if new_fmt != old_fmt:
                # parse the format string
                linestyle, marker, color = _process_plot_format(new_fmt)
                linestyle = linestyle or rcParams['lines.linestyle']
                marker = marker or rcParams['lines.marker']
                color = color or rcParams['lines.color']
                plot.set_linestyle(linestyle)
                plot.set_marker(marker)
                plot.set_color(color)
                old_fmts[index] = new_fmt

    def add_legend(self, plots, plot_data, leg_label, leg_offset):
        if leg_label is not None:
            self.legend_labels = inflate_input(leg_label, plot_data)
            for plot, label in zip(plots, self.legend_labels):
                plot.set_label(label)
            self.legend = self.ax.legend(loc=leg_offset)


class MultiPlotClient(object):
    def __init__(self, init, framegen, info, rate):
        # set default column and row values
        ncols = init.size
        nrows = 1
        # if any column organization data is passed try to use it
        if init.ncols is not None:
            if isinstance(init.ncols, int) and 0 < init.ncols <= init.size:
                ncols = init.ncols
                nrows = int(math.ceil(init.size/float(init.ncols)))
            else:
                LOG.warning('Invalid column number specified: %s'
                            ' - Must be a positive integer less than the number of plots: %s',
                            init.ncols, init.size)
        if init.use_windows:
            LOG.warning('Separate windows for subplots is not supported in the matplotlib client')
        ratio_calc = window_ratio(config.MPL_SMALL_WIN, config.MPL_LARGE_WIN)
        self.figure, self.ax = plt.subplots(
            nrows=nrows,
            ncols=ncols,
            facecolor=info.bkg_col,
            edgecolor=info.bkg_col,
            figsize=ratio_calc(ncols, nrows),
            squeeze=False
        )
        # flatten the axes array returned by suplot
        self.ax = self.ax.flatten()
        if self.figure.canvas.manager is not None:
            self.figure.canvas.manager.set_window_title(init.title)
        self.plots = [type_getter(type(data_obj))(data_obj, None, info, rate, figax=(self.figure, subax))
                      for data_obj, subax in zip(init.data_con, self.ax)]
        self.framegen = framegen
        self.rate_ms = rate * 1000
        self.info = info
        self.multi_plot = True

    def update(self, data):
        if data is not None:
            for plot, plot_data in zip(self.plots, data.data_con):
                plot.update(plot_data)

    def animate(self):
        return animation.FuncAnimation(self.figure, self.update, self.ani_func, interval=self.rate_ms)

    def ani_func(self):
        yield next(self.framegen)


class ImageClient(PlotClient):
    def __init__(self, init_im, framegen, info, rate=1, **kwargs):
        super(ImageClient, self).__init__(init_im, framegen, info, rate, **kwargs)
        # if a color palette is specified check to see if it valid
        cmap = plt.get_cmap(config.MPL_COLOR_PALETTE)
        # deal with custom axis ranges if requested
        if init_im.pos is None and init_im.scale is None:
            extent = None
        else:
            x1 = 0 if init_im.pos is None else init_im.pos[0]
            xscale = 1 if init_im.scale is None else init_im.scale[0]
            y1 = 0 if init_im.pos is None else init_im.pos[1]
            yscale = 1 if init_im.scale is None else init_im.scale[1]
            extent = [x1, x1 + xscale * init_im.image.shape[1], y1 + yscale * init_im.image.shape[0], y1]
        if self.info.palette is not None:
            try:
                cmap = plt.get_cmap(self.info.palette)
            except ValueError:
                LOG.warning('Inavlid color palette for matplotlib: %s - Falling back to default: %s',
                            self.info.palette, cmap.name)
        self.im = self.ax.imshow(init_im.image, interpolation=self.info.interpol, cmap=cmap, extent=extent)
        self.im.set_clim(self.info.zrange)
        self.cb = self.figure.colorbar(self.im, ax=self.ax)
        self.set_cb_col()
        self.aspect_lock = init_im.aspect_lock
        self.aspect_ratio = init_im.aspect_ratio
        self.set_aspect(self.aspect_lock, self.aspect_ratio)
        self.set_xy_ranges()
        self.set_log_scale()

    def update_sub(self, data):
        """
        Updates the data in the image - none means their was no update for this interval
        """
        if data is not None:
            if self.aspect_lock != data.aspect_lock or self.aspect_ratio != data.aspect_ratio:
                self.aspect_lock = data.aspect_lock
                self.aspect_ratio = data.aspect_ratio
                self.set_aspect(self.aspect_lock, self.aspect_ratio)
            self.im.set_data(data.image)
        return self.im

    def set_cb_col(self):
        if self.info.fore_col is not None:
            self.cb.outline.set_color(self.info.fore_col)
            self.set_ax_col(self.cb.ax)


class HistClient(PlotClient):
    def __init__(self, init_hist, datagen, info, rate=1, **kwargs):
        super(HistClient, self).__init__(init_hist, datagen, info, rate, **kwargs)
        # convert to datetime if requested
        bins = ts_to_dt(init_hist.bins) if self.xdate else init_hist.bins
        values = ts_to_dt(init_hist.values) if self.ydate else init_hist.values
        # pyqtgraph needs a trailing bin edge that mpl doesn't so check for that
        corrected_bins = self.correct_bins(bins, values)
        plot_args = arg_inflate_flat(
            1,
            corrected_bins,
            values,
            init_hist.formats
        )
        self.hists = self.ax.plot(*plot_args, drawstyle=config.MPL_HISTO_STYLE)
        self.fill(corrected_bins, init_hist.values, init_hist.fills)
        self.formats = inflate_input(init_hist.formats, init_hist.values)
        self.set_aspect()
        self.set_xy_ranges()
        self.set_log_scale()
        self.set_grid_lines()
        self.add_legend(self.hists, init_hist.values, init_hist.leg_label, init_hist.leg_offset)

    def update_sub(self, data):
        if data is not None:
            # pyqtgraph needs a trailing bin edge that mpl doesn't so check for that
            corrected_bins = self.correct_bins(data.bins, data.values)
            self.update_plot_data(self.hists, corrected_bins, data.values, data.formats, self.formats)
            self.fill(corrected_bins, data.values, data.fills)
            self.ax.relim()
            self.ax.autoscale_view()
        return self.hists

    def correct_bins(self, bins, values):
        """
        Checks that number of bins is correct for matplotlib. pyqtgraph needs a
        trailing bin edge that mpl doesn't so check for that and remove if
        needed.

        Takes the 'bins' numpy array (single or list of) and compares to the
        'values' numpy array (single or list of) and trims trailing entry from
        'bins' if its size is greater than that of the mathcing 'values'.

        Returns the corrected 'bins'.
        """
        if is_py_iter(bins) or is_py_iter(values):
            corrected_bins = []
            for bin, value in zip(inflate_input(bins, values), values):
                if bin.size > value.size:
                    corrected_bins.append(bin[1:])
                else:
                    corrected_bins.append(bin)
            return corrected_bins
        elif bins.size > values.size:
            return bins[1:]
        else:
            return bins

    def fill(self, corrected_bins, values, fills):
        """
        Adds fill for each histogram based on the boolean 'fills' parameter passed
        with the datagram.

        Takes correct bins (single or list of), histogram values (single or list of),
        and fill configs (single or list of).
        """
        inflated_args = arg_inflate_tuple(3, check_data(corrected_bins), check_data(values), fills, self.hists)
        for bin, val, fill, hist in inflated_args:
            if fill:
                self.ax.fill_between(bin, 0, val, color=hist.get_color(), alpha=config.MPL_HIST_ALPHA)


class XYPlotClient(PlotClient):
    def __init__(self, init_plot, datagen, info, rate=1, **kwargs):
        super(XYPlotClient, self).__init__(init_plot, datagen, info, rate, **kwargs)
        plot_args = arg_inflate_flat(
            1,
            ts_to_dt(init_plot.xdata) if self.xdate else init_plot.xdata,
            ts_to_dt(init_plot.ydata) if self.ydate else init_plot.ydata,
            init_plot.formats
        )
        self.plots = self.ax.plot(*plot_args)
        self.formats = inflate_input(init_plot.formats, init_plot.ydata)
        self.set_aspect()
        self.set_xy_ranges()
        self.set_log_scale()
        self.set_grid_lines()
        self.add_legend(self.plots, init_plot.ydata, init_plot.leg_label, init_plot.leg_offset)

    def update_sub(self, data):
        if data is not None:
            self.update_plot_data(self.plots, data.xdata, data.ydata, data.formats, self.formats)
            self.ax.relim()
            self.ax.autoscale_view()
        return self.plots
