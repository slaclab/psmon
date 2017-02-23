import time
import numpy as np

from psmon import publish
from psmon.util import make_bins
from psmon.plots import Image, MultiPlot, Hist, XYPlot


class Helper(object):
    def __init__(self, topic, title=None, pubrate=None, publisher=None):
        self.topic = topic
        self.data = None
        self.title = title or self.topic
        self.pubrate = pubrate
        self.publisher = publisher or publish.send
        self.__last_pub = time.time()

    def publish(self):
        current_time = time.time()
        if self.pubrate is None or self.pubrate * (current_time - self.__last_pub) >= 1:
            self.__last_pub = current_time
            self.publisher(self.topic, self.data)


class MultiHelper(Helper):
    def __init__(self, topic, num_data, title=None, pubrate=None, publisher=None):
        super(MultiHelper, self).__init__(topic, title, pubrate, publisher)
        self.data = MultiPlot(None, self.title, [None] * num_data)

    def set_data(self, index, type, *args, **kwargs):
        self.data.data_con[index] = type(*args, **kwargs)


class ImageHelper(Helper):
    def __init__(self, topic, title=None, pubrate=None, publisher=None):
        super(ImageHelper, self).__init__(topic, title, pubrate, publisher)
        self.data = Image(None, self.title, None)

    def set_image(self, image, image_title=None):
        if image_title is not None:
            self.data.ts = image_title
        self.data.image = image


class MultiImageHelper(MultiHelper):
    def __init__(self, topic, num_image, title=None, pubrate=None, publisher=None):
        super(MultiImageHelper, self).__init__(topic, num_image, title, pubrate, publisher)

    def set_image(self, index, image, image_title=None):
        self.set_data(index, Image, image_title, None, image)


class StripHelper(Helper):
    def __init__(self, topic, npoints, title=None, xlabel=None, ylabel=None, format='-', pubrate=None, publisher=None):
        super(StripHelper, self).__init__(topic, title, pubrate, publisher)
        self.index = 0
        self.npoints = npoints
        self.xdata = np.arange(npoints)
        self.ydata = np.zeros(npoints)
        self.data = XYPlot(
            None,
            self.title,
            None,
            None,
            xlabel=xlabel,
            ylabel=ylabel,
            formats=format
        )

    def add(self, point_value, entry_title=None):
        if entry_title is not None:
            self.data.ts = entry_title
        if self.index >= self.npoints:
            self.xdata = np.roll(self.xdata, -1)
            self.ydata = np.roll(self.ydata, -1)
            self.xdata[-1] = self.index
            self.ydata[-1] = point_value
            self.data.xdata = self.xdata
            self.data.ydata = self.ydata
        else:
            self.ydata[self.index] = point_value
            self.data.xdata = self.xdata[:self.index]
            self.data.ydata = self.ydata[:self.index]
        self.index += 1

    def clear(self):
        self.index = 0


class XYPlotHelper(Helper):
    DEFAULT_ARR_SIZE = 100

    def __init__(self, topic, title=None, xlabel=None, ylabel=None, format='-', pubrate=None, publisher=None):
        super(XYPlotHelper, self).__init__(topic, title, pubrate, publisher)
        self.index = 0
        self.xdata = np.zeros(XYPlotHelper.DEFAULT_ARR_SIZE)
        self.ydata = np.zeros(XYPlotHelper.DEFAULT_ARR_SIZE)
        self.data = XYPlot(
            None,
            self.title,
            None,
            None,
            xlabel=xlabel,
            ylabel=ylabel,
            formats=format
        )

    def add(self, xval,  yval, entry_title=None):
        if entry_title is not None:
            self.data.ts = entry_title
        if self.index == self.xdata.size:
            # double the size if we need to reallocate
            self.xdata = np.resize(self.xdata, 2*self.index)
            self.ydata = np.resize(self.ydata, 2*self.index)
        self.xdata[self.index] = xval
        self.ydata[self.index] = yval
        self.index += 1
        self.data.xdata = self.xdata[:self.index]
        self.data.ydata = self.ydata[:self.index]

    def clear(self):
        self.index = 0


class HistHelper(Helper):
    def __init__(self, topic, nbins, bmin, bmax, title=None, xlabel=None, ylabel=None, format='-', pubrate=None, publisher=None):
        super(HistHelper, self).__init__(topic, title, pubrate, publisher)
        self.nbins = int(nbins)
        self.bmin = float(bmin)
        self.bmax = float(bmax)
        self.range = (bmin, bmax)
        self.data = Hist(
            None,
            self.title,
            make_bins(self.nbins, self.bmin, self.bmax),
            np.zeros(self.nbins),
            xlabel=xlabel,
            ylabel=ylabel,
            formats=format
        )

    def add(self, value, entry_title=None):
        if entry_title is not None:
            self.data.ts = entry_title
        self.data.values += np.histogram(value, self.nbins, range=self.range)[0]

    def clear(self):
        self.data.values[:] = 0


class HistOverlayHelper(Helper):
    def __init__(self, topic, title=None, xlabel=None, ylabel=None, pubrate=None, publisher=None):
        super(HistOverlayHelper, self).__init__(topic, title, pubrate, publisher)
        self.nhist = 0
        self.nbins = []
        self.ranges = []
        self.bins = []
        self.values = []
        self.formats = []
        self.data = Hist(
            None,
            self.title,
            self.bins,
            self.values,
            xlabel=xlabel,
            ylabel=ylabel,
            formats=self.formats
        )

    def make_hist(self, nbins, bmin, bmax, format='-'):
        index = self.nhist
        self.nbins.append(nbins)
        self.ranges.append((bmin, bmax))
        self.bins.append(make_bins(nbins, bmin, bmax))
        self.values.append(np.zeros(nbins))
        self.formats.append(format)
        self.nhist += 1
        return index

    def add(self, index, value, entry_title=None):
        if entry_title is not None:
            self.data.ts = entry_title
        self.values[index] += np.histogram(value, self.nbins[index], range=self.ranges[index])[0]

    def clear(self, index=None):
        if index is None:
            for value in self.values:
                value[:] = 0
        else:
            self.values[index][:] = 0
