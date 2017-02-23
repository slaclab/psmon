#!/usr/bin/env python
import time
import argparse
import numpy as np
from psmon import publish
from psmon.helper import StripHelper


def parse_cli():
    parser = argparse.ArgumentParser(
        description='Psmon plot server application: Strip Chart example'
    )

    def_updates = 1000
    def_points = 50
    def_rate = 2.0

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
        '-p',
        '--points',
        metavar='POINTS',
        type=int,
        default=def_points,
        help='the max number of points in the strip chart (default: %d)'%def_points
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

    return parser.parse_args()


def main():
    args = parse_cli()
    max_updates = args.num_updates
    period = 1/args.rate
    points = args.points
    status_rate = 100
    topic = 'stripchart'

    #optional port, buffer-depth arguments.
    publish.local = args.local
    publish.client_opts.daemon = True
    if args.mpl:
      publish.client_opts.renderer = 'mpl'
    elif args.pyqt:
      publish.client_opts.renderer = 'pyqt'

    shelp = StripHelper(topic, points, title="Strip Chart Test")

    counter = 0
    while counter < max_updates or max_updates < 1:
        if publish.get_reset_flag():
            shelp.clear()
            publish.clear_reset_flag()
        shelp.add(np.random.randint(10))
        shelp.publish()

        counter += 1

        if counter % status_rate == 0:
            print("Processed %d updates so far" % counter)

        time.sleep(period)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExitting script!')
