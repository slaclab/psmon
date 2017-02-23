#!/usr/bin/env python
import time
import argparse
import numpy as np
from psmon import publish
from psmon.plots import Hist, XYPlot


def full(ts, plot_type, bins, val1, val2, val3):
    """runs test plots with labels and legends"""
    h1 = plot_type(ts, "Single %s Full"%plot_type.__name__, bins, val1, xlabel='x val', ylabel='y val', leg_label='hist1', leg_offset='upper right')
    h2 = plot_type(ts, "Double %s Full"%plot_type.__name__, bins, [val1, val2], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2'], leg_offset='upper right')
    h3 = plot_type(ts, "Triple %s Full"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2', 'hist3'], leg_offset='upper right')
    return h1, h2, h3


def nolabel(ts, plot_type, bins, val1, val2, val3):
    """runs test plots with no labels"""
    h1 = plot_type(ts, "Single %s No Labels"%plot_type.__name__, bins, val1, leg_label='hist1', leg_offset='upper right')
    h2 = plot_type(ts, "Double %s No Labels"%plot_type.__name__, bins, [val1, val2], leg_label=['hist1', 'hist2'], leg_offset='upper right')
    h3 = plot_type(ts, "Triple %s No Labels"%plot_type.__name__, bins, [val1, val2, val3], leg_label=['hist1', 'hist2', 'hist3'], leg_offset='upper right')
    return h1, h2, h3


def nolegend(ts, plot_type, bins, val1, val2, val3):
    """runs test plots with no legends"""
    h1 = plot_type(ts, "Single %s Full"%plot_type.__name__, bins, val1, xlabel='x val', ylabel='y val')
    h2 = plot_type(ts, "Double %s Full"%plot_type.__name__, bins, [val1, val2], xlabel='x val', ylabel='y val')
    h3 = plot_type(ts, "Triple %s Full"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val')
    return h1, h2, h3


def nolegendoffset(ts, plot_type, bins, val1, val2, val3):
    h1 = plot_type(ts, "Single %s Full"%plot_type.__name__, bins, val1, xlabel='x val', ylabel='y val', leg_label='hist1')
    h2 = plot_type(ts, "Double %s Full"%plot_type.__name__, bins, [val1, val2], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2'])
    h3 = plot_type(ts, "Triple %s Full"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2', 'hist3'])
    return h1, h2, h3


def plain(ts, plot_type, bins, val1, val2, val3):
    """runs test plots with no labels or legends"""
    h1 = plot_type(ts, "Single %s Plain"%plot_type.__name__, bins, val1)
    h2 = plot_type(ts, "Double %s Plain"%plot_type.__name__, bins, [val1, val2])
    h3 = plot_type(ts, "Triple %s Plain"%plot_type.__name__, bins, [val1, val2, val3])
    return h1, h2, h3


def multibin(ts, plot_type, bins, val1, val2, val3):
    """runs test plots where bin parameter is a list"""
    h1 = plot_type(ts, "Double %s Multibin"%plot_type.__name__, [bins], [val1], xlabel='x val', ylabel='y val')
    h2 = plot_type(ts, "Double %s Multibin"%plot_type.__name__, [bins, bins], [val1, val2], xlabel='x val', ylabel='y val')
    h3 = plot_type(ts, "Triple %s Multibin"%plot_type.__name__, [bins, bins, bins], [val1, val2, val3], xlabel='x val', ylabel='y val')
    return h1, h2, h3


def legendoff(ts, plot_type, bins, val1, val2, val3):
    """runs test plots with legends testing offset parameters"""
    h1 = plot_type(ts, "Triple %s Legend Offset String"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2', 'hist3'], leg_offset='upper right')
    h2 = plot_type(ts, "Triple %s Legend Offset Tuple"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2', 'hist3'], leg_offset=(0.2, 0.8))
    h3 = plot_type(ts, "Triple %s No Legend Offset"%plot_type.__name__, bins, [val1, val2, val3], xlabel='x val', ylabel='y val', leg_label=['hist1', 'hist2', 'hist3'], leg_offset=None)
    return h1, h2, h3


def parse_cli():
    parser = argparse.ArgumentParser(
        description='Psmon plot server application: Low-level plot API examples'
    )

    def_updates = 1000
    def_rate = 2.0
    def_funcs = [full, nolabel, nolegend, nolegendoffset, plain, multibin, legendoff]

    parser.add_argument(
        '-n',
        '--num-updates',
        metavar='NUM_UPDATES',
        type=int,
        default=def_updates,
        help='the max number of plot updates to send (default: %d)'%def_updates
    )

    parser.add_argument(
        '-r',
        '--rate',
        metavar='RATE',
        type=float,
        default=def_rate,
        help='the max rate to publish data (default: %.2f Hz)'%def_rate
    )

    parser.add_argument(
        '--local',
        action='store_true',
        default=False,
        help='use the local plot feature of the publish module'
    )

    client_parser = parser.add_mutually_exclusive_group(required=False)

    client_parser.add_argument(
      '--mpl',
      action='store_true',
      help='use matplotlib rendering client'
    )

    client_parser.add_argument(
      '--pyqt',
      action='store_true',
      help='use pyqtgraph rendering client'
    )

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
    subparsers.required = True

    parser_hist = subparsers.add_parser(
        'hist',
        description='runs tests using Hist objects',
        help='uses Hist objects for tests'
    )
    parser_hist.set_defaults(plot_type=Hist)

    hist_subparsers = parser_hist.add_subparsers(title='options', dest='option')
    hist_subparsers.required = True

    for func in def_funcs:
        func_name = func.__name__
        parser_hist_func = hist_subparsers.add_parser(
            func_name,
            description=func.__doc__,
            help='runs the %s test set' % func_name,
        )
        parser_hist_func.set_defaults(func=func)

    parser_xyplot = subparsers.add_parser(
        'xyplot',
        description='runs tests using XYPlot objects',
        help='uses XYPlot objects for tests'
    )
    parser_xyplot.set_defaults(plot_type=XYPlot)

    xyplot_subparsers = parser_xyplot.add_subparsers(title='options', dest='option')
    xyplot_subparsers.required = True

    for func in def_funcs:
        func_name = func.__name__
        parser_xyplot_func = xyplot_subparsers.add_parser(
            func_name,
            description=func.__doc__,
            help='runs the %s test set' % func_name,
        )
        parser_xyplot_func.set_defaults(func=func)

    return parser.parse_args()


def main():
    args = parse_cli()
    max_updates = args.num_updates
    period = 1/args.rate
    status_rate = 100
    bin_n = 100
    points_n = bin_n
    
    #optional port, buffer-depth arguments.
    publish.local = args.local
    publish.client_opts.daemon = True
    if args.mpl:
      publish.client_opts.renderer = 'mpl'
    elif args.pyqt:
      publish.client_opts.renderer = 'pyqt'

    counter = 0
    if args.plot_type == Hist:
        bins = np.arange(bin_n + 1)
    else:
        bins = np.arange(bin_n)
    val1 = np.zeros(bin_n)
    val2 = np.zeros(bin_n)
    val3 = np.zeros(bin_n)
    while counter < max_updates or max_updates < 1:
        # add data to val arrays
        pos = bin_n/4.0
        width = bin_n/16.0
        rnd1 = np.random.normal(pos, width, points_n)
        rnd2 = np.random.normal(3*pos, width, points_n)
        rnd3 = np.random.normal(2*pos, width, points_n)
        if args.plot_type == Hist:
            tmp_val1, _ = np.histogram(rnd1, bins)
            tmp_val2, _ = np.histogram(rnd2, bins)
            tmp_val3, _ = np.histogram(rnd3, bins)
            val1 += tmp_val1
            val2 += tmp_val2
            val3 += tmp_val3
        else:
            val1 = rnd1
            val2 = rnd2
            val3 = rnd3

        plot1, plot2, plot3 = args.func(counter, args.plot_type, bins, val1, val2, val3)

        publish.send('plot1', plot1)
        publish.send('plot2', plot2)
        publish.send('plot3', plot3)

        counter += 1

        if counter % status_rate == 0:
            print("Processed %d updates so far" % counter)

        time.sleep(period)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExitting script!')
