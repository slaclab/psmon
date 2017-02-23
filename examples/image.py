#!/usr/bin/env python
import time
import argparse
import numpy as np
from psmon import publish
from psmon.plots import MultiPlot, Image


def parse_cli():
    parser = argparse.ArgumentParser(
        description='Psmon plot server application: Image example'
    )

    def_updates = 1000
    def_images = 1
    def_columns = 3
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
        '-i',
        '--images',
        metavar='IMAGES',
        type=int,
        default=def_images,
        help='the max number of images to send (default: %d)'%def_images
    )

    parser.add_argument(
        '-c',
        '--columns',
        metavar='COLUMNS',
        type=int,
        default=def_columns,
        help='the max number of columns to use for multi images (default: %d)'%def_columns
    )

    parser.add_argument(
        '--windows',
        action='store_true',
        default=False,
        help='use the separate windows for the multi images'
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
    status_rate = 100
    image_n = args.images
    col_n = args.columns
    windows = args.windows
    pixels_n = 1024
    width = 50
    pos = 25
    topic = 'image'
    title = 'Image Test'
    multi_topic = 'multi-image'
    multi_title = 'Mulit Image Test'

    #optional port, buffer-depth arguments.
    publish.local = args.local
    publish.client_opts.daemon = True
    if args.mpl:
      publish.client_opts.renderer = 'mpl'
    elif args.pyqt:
      publish.client_opts.renderer = 'pyqt'
    publish.plot_opts.zrange = (-250., 250.)

    counter = 0
    while counter < max_updates or max_updates < 1:
        multi_image = MultiPlot(counter, multi_title, ncols=min(col_n, image_n), use_windows=windows)
        for num in range(image_n):
            image_data = Image(counter, '%s %d'%(title, num), np.random.normal((-1)**num * pos * num, width, (pixels_n, pixels_n)))
            multi_image.add(image_data)
        publish.send(multi_topic, multi_image)
        image_data = Image(counter, title, np.random.normal(0, width, (pixels_n, pixels_n)))
        publish.send(topic, image_data)

        counter += 1

        if counter % status_rate == 0:
            print("Processed %d updates so far" % counter)

        time.sleep(period)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExitting script!')
