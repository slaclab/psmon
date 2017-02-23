class Plot(object):
    """
    A data container representing a Plot object for the psmon client
    """
    def __init__(self, ts, title, xlabel, ylabel):
        self.ts = ts
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel

    @property
    def valid(self):
        """
        This attribute is True if this Plot object is valid

        Conditions:
         - Always True for Plot class objects - subclasses can override
        """
        return True


class MultiPlot(object):
    """
    A data container of arbitary subtypes of the Plot class - can contain an
    arbitrary number of Plot objects

    Optional arguments
    - ncols: indicates to the client the number of columns to be used for 
            displaying the plots
    - use_windows: tells the client to render the individual plots in separate
            windows if that feature is supported by the client
    """

    def __init__(self, ts, title, data_con=None, ncols=None, use_windows=False):
        self.ts = ts
        self.title = title
        self.ncols = ncols
        self.use_windows = use_windows
        if data_con is None:
            self.data_con = []
        else:
            self.data_con = data_con

    def add(self, data):
        """
        Add an additional Plot to MultiPlot objects plot list
        """
        self.data_con.append(data)

    def get(self, index):
        """
        Returns a reference to the Plot object cooresponding to the index
        """
        return self.data_con[index]

    @property
    def size(self):
        """
        Returns the number of Plot objects contained in the Multiplot object
        """
        return len(self.data_con)

    @property
    def valid(self):
        """
        This attribute is True if this MultiPlot object is valid

        Conditions:
         - The Multiplot object must contain at least one Plot object
         - All the objects contained in the Multiplot object must be valid
        """
        try:
            for data in self.data_con:
                if not data.valid:
                    return False
        except AttributeError:
            return False
        return len(self.data_con) != 0


class Image(Plot):
    """
    A data container for image data for the psmon client
    """

    def __init__(self, ts, title, image, xlabel=None, ylabel=None, aspect_ratio=None, aspect_lock=True, pos=None, scale=None):
        super(Image, self).__init__(ts, title, xlabel, ylabel)
        self.image = image
        self.aspect_ratio = aspect_ratio
        self.aspect_lock = aspect_lock
        self.pos = pos
        self.scale = scale

    @property
    def valid(self):
        """
        This attribute is True if this Image object is valid

        Conditions:
         - The 'image' attribute of must not be None 
        """
        return self.image is not None


class Hist(Plot):
    """
    A data container for 1-d histogram data for the psmon client
    """

    def __init__(self, ts, title, bins, values, xlabel=None, ylabel=None, leg_label=None, leg_offset=None, formats='-', fills=True):
        super(Hist, self).__init__(ts, title, xlabel, ylabel)
        self.bins = bins
        self.values = values
        self.leg_label = leg_label
        self.leg_offset = leg_offset
        self.formats = formats
        self.fills = fills

    @property
    def valid(self):
        """
        This attribute is True if this Hist object is valid

        Conditions:
         - The 'bins' and 'values' attributes must not be None
        """
        return self.bins is not None and self.values is not None


class XYPlot(Plot):
    """
    A data container for xy scatter plot data for the psmon client
    """

    def __init__(self, ts, title, xdata, ydata, xlabel=None, ylabel=None, leg_label=None, leg_offset=None, formats='-'):
        super(XYPlot, self).__init__(ts, title, xlabel, ylabel)
        self.xdata = xdata
        self.ydata = ydata
        self.leg_label = leg_label
        self.leg_offset = leg_offset
        self.formats = formats

    @property
    def valid(self):
        """
        This attribute is True if this XYPlot object is valid

        Conditions:
         - The 'xdata' and 'ydata' attributes must not be None
        """
        return self.xdata is not None and self.ydata is not None
