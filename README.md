# psmon
psmon is a remote and local data visualization tool used at LCLS for online
analysis/monitoring developed originally to work with LCLS psana analysis
framework. ZeroMQ is used as the data trasport layer and it provides two
different rendering clients based on matplotlib and pyqtgraph.

# Requirements
* Python 2.7 or 3.5+
* ipython
* pyzmq
* numpy
* matplotlib
* pyqtgraph

If you wish to use the pyqtgraph based rendering client for plots/images then
one of PyQt4, PyQt5, or PySide will need to be available in your python
environment.
