#!/usr/bin/env python
import time
import argparse
import numpy as np
from psmon import publish
from psmon.plotting import Histogram, ScatterPlot, LinePlot, StripChart


def base(plot_type, cmd, name, title, *args, **kwargs):
    """base function for creating the plots with selected options"""
    h1 = plot_type('plot1', "Single %s %s"%(plot_type.__name__, title), **kwargs)
    h2 = plot_type('plot2', "Double %s %s"%(plot_type.__name__, title), **kwargs)
    h3 = plot_type('plot3', "Triple %s %s"%(plot_type.__name__, title), **kwargs)

    cmd(h1, '%s1'%name, *args)
    cmd(h2, '%s1'%name, *args)
    cmd(h2, '%s2'%name, *args)
    cmd(h3, '%s1'%name, *args)
    cmd(h3, '%s2'%name, *args)
    cmd(h3, '%s3'%name, *args)

    return h1, h2, h3


def full(plot_type, cmd, name, *args):
    """runs test plots with labels and legends"""
    return base(plot_type, cmd, name, 'Full', *args, xlabel='x val', ylabel='y val', leg_offset='upper right')


def nolabel(plot_type, cmd, name, *args):
    """runs test plots with no labels"""
    return base(plot_type, cmd, name, 'No Labels', *args, leg_offset='upper right')


def nolegendoffset(plot_type, cmd, name, *args):
    """runs test plots with no legend offset"""
    return base(plot_type, cmd, name, 'No Legend Offset', *args, xlabel='x val', ylabel='y val')


def plain(plot_type, cmd, name, *args):
    """runs test plots with no labels or legends"""
    return base(plot_type, cmd, name, 'Plain', *args)


def legendoffstr(plot_type, cmd, name, *args):
    """runs test plots with legends testing offset parameters"""
    return base(plot_type, cmd, name, 'Legend Offset String', *args, xlabel='x val', ylabel='y val', leg_offset='upper right')


def legendofftup(plot_type, cmd, name, *args):
    """runs test plots with legends testing offset parameters"""
    return base(plot_type, cmd, name, 'Legend Offset Tuple', *args, xlabel='x val', ylabel='y val', leg_offset=(0.2, 0.8))


def parse_cli():
    parser = argparse.ArgumentParser(
        description='Psmon plot server application: High-level API plotting examples'
    )

    def_updates = 1000
    def_rate = 2.0
    def_bins = 100
    def_points = 10
    def_funcs = [full, nolabel, nolegendoffset, plain, legendoffstr, legendofftup]

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
        '-b',
        '--bins',
        metavar='NUM_BINS',
        type=int,
        default=def_bins,
        help='the number of bins to use for each plot (default: %d)'%def_bins
    )

    parser.add_argument(
        '-p',
        '--points',
        metavar='NUM_POINTS',
        type=int,
        default=def_points,
        help='the number of points to use for each update (default: %d)'%def_points
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
        description='runs tests using Histogram objects',
        help='uses Histogram objects for tests'
    )
    parser_hist.set_defaults(plot_type=Histogram)
    parser_hist.set_defaults(plot_func=Histogram.make_hist)
    parser_hist.set_defaults(plot_name='hist')

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

    parser_scatter = subparsers.add_parser(
        'scatter',
        description='runs tests using ScatterPlot objects',
        help='uses ScatterPlot objects for tests'
    )
    parser_scatter.set_defaults(plot_type=ScatterPlot)
    parser_scatter.set_defaults(plot_func=ScatterPlot.make_plot)
    parser_scatter.set_defaults(plot_name='scatter')

    scatter_subparsers = parser_scatter.add_subparsers(title='options', dest='option')
    scatter_subparsers.required = True

    for func in def_funcs:
        func_name = func.__name__
        parser_scatter_func = scatter_subparsers.add_parser(
            func_name,
            description=func.__doc__,
            help='runs the %s test set' % func_name,
        )
        parser_scatter_func.set_defaults(func=func)

    parser_line = subparsers.add_parser(
        'line',
        description='runs tests using LinePlot objects',
        help='uses LinePlot objects for tests'
    )
    parser_line.set_defaults(plot_type=LinePlot)
    parser_line.set_defaults(plot_func=LinePlot.make_plot)
    parser_line.set_defaults(plot_name='line')

    line_subparsers = parser_line.add_subparsers(title='options', dest='option')
    line_subparsers.required = True

    for func in def_funcs:
        func_name = func.__name__
        parser_line_func = line_subparsers.add_parser(
            func_name,
            description=func.__doc__,
            help='runs the %s test set' % func_name,
        )
        parser_line_func.set_defaults(func=func)

    parser_strip = subparsers.add_parser(
        'strip',
        description='runs tests using StripChart objects',
        help='uses StripChart objects for tests'
    )
    parser_strip.set_defaults(plot_type=StripChart)
    parser_strip.set_defaults(plot_func=StripChart.make_plot)
    parser_strip.set_defaults(plot_name='strip')

    strip_subparsers = parser_strip.add_subparsers(title='options', dest='option')
    strip_subparsers.required = True

    for func in def_funcs:
        func_name = func.__name__
        parser_strip_func = strip_subparsers.add_parser(
            func_name,
            description=func.__doc__,
            help='runs the %s test set' % func_name,
        )
        parser_strip_func.set_defaults(func=func)

    return parser.parse_args()


def main():
    args = parse_cli()
    max_updates = args.num_updates
    period = 1/args.rate
    status_rate = 100
    bin_n = args.bins
    points_n = args.points
    
    #optional port, buffer-depth arguments.
    publish.local = args.local
    publish.client_opts.daemon = True
    if args.mpl:
      publish.client_opts.renderer = 'mpl'
    elif args.pyqt:
      publish.client_opts.renderer = 'pyqt'

    name = None
    counter = 0
    if args.plot_type == Histogram:
        plot1, plot2, plot3 = args.func(args.plot_type,args.plot_func, args.plot_name, bin_n, 0, bin_n)
    elif args.plot_type == StripChart:
        plot1, plot2, plot3 = args.func(args.plot_type,args.plot_func, args.plot_name, bin_n)
    else:
        plot1, plot2, plot3 = args.func(args.plot_type,args.plot_func, args.plot_name)
    while counter < max_updates or max_updates < 1:
        # add data to val arrays
        pos = bin_n/4.0
        width = bin_n/16.0
        if args.plot_type == Histogram or args.plot_type == StripChart:
            val1 = [np.random.normal(pos, width, points_n)]
            val2 = [np.random.normal(3*pos, width, points_n)]
            val3 = [np.random.normal(2*pos, width, points_n)]
        else:
            val1 = [np.arange(counter*points_n, (counter+1)*points_n), np.random.normal(pos, width, points_n)]
            val2 = [np.arange(counter*points_n, (counter+1)*points_n), np.random.normal(3*pos, width, points_n)]
            val3 = [np.arange(counter*points_n, (counter+1)*points_n), np.random.normal(2*pos, width, points_n)]

        plot1.add('%s1'%args.plot_name, *val1)
        plot2.add('%s1'%args.plot_name, *val1)
        plot2.add('%s2'%args.plot_name, *val2)
        plot3.add('%s1'%args.plot_name, *val1)
        plot3.add('%s2'%args.plot_name, *val2)
        plot3.add('%s3'%args.plot_name, *val3)

        plot1.publish()
        plot2.publish()
        plot3.publish()

        counter += 1

        if counter % status_rate == 0:
            print("Processed %d updates so far" % counter)

        time.sleep(period)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExitting script!')
