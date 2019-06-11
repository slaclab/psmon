#!/usr/bin/env python
import re
import sys
import logging
import argparse
import multiprocessing as mp

from psmon import app, config, log_level_parse


LOG = logging.getLogger(config.LOG_BASE_NAME)


def parse_cmdline():
    parser = argparse.ArgumentParser(
        description='Psmon plot client application'
    )

    parser.add_argument(
        'topics',
        nargs='*',
        help='the topic(s) from the server to which the client should subscribe'
    )

    parser.add_argument(
        '-s',
        '--server',
        metavar='SERVER',
        default=config.APP_SERVER,
        help='the host name of the server (default: %s)' % config.APP_SERVER
    )

    parser.add_argument(
        '-p',
        '--port',
        metavar='PORT',
        type=int,
        default=config.APP_PORT,
        help='the tcp port of the server (default: %d)' % config.APP_PORT
    )

    parser.add_argument(
        '-r',
        '--rate',
        metavar='RATE',
        type=float,
        default=config.APP_RATE,
        help='update rate of the histogram in Hz (default: %.2fHz)' % config.APP_RATE
    )

    parser.add_argument(
        '-b',
        '--buffer',
        metavar='BUFFER',
        type=int,
        default=config.APP_BUFFER,
        help='the size in messages of recieve buffer (default: %d)' % config.APP_BUFFER
    )

    parser.add_argument(
        '-x',
        '--x-range',
        metavar='X_RANGE',
        type=float,
        nargs=2,
        default=config.APP_XRANGE,
        help='the fixed x range for any plots'
    )

    parser.add_argument(
        '-y',
        '--y-range',
        metavar='Y_RANGE',
        type=float,
        nargs=2,
        default=config.APP_YRANGE,
        help='the fixed y range for any plots'
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-z',
        '--z-range',
        metavar='Z_RANGE',
        type=float,
        nargs=2,
        default=config.APP_ZRANGE,
        help='the fixed z range for any plots'
    )

    group.add_argument(
        '--auto-z-range',
        action='store_true',
        default=config.APP_AUTO_ZRANGE,
        help='enable auto scaling of z range'
    )

    parser.add_argument(
        '-a',
        '--aspect',
        metavar='ASPECT',
        type=float,
        default=config.APP_ASPECT,
        help='the aspect ratio for the plot'
    )

    parser.add_argument(
        '-i',
        '--interpolation',
        metavar='INTERPOLATION',
        default=config.APP_IMG_INTERPOLATION,
        help='the interpolation type for images (default: \'%s\')' % config.APP_IMG_INTERPOLATION
    )

    parser.add_argument(
        '--bkg-color',
        metavar='BKG_COLOR',
        default=config.APP_BKG_COLOR,
        help='the background color for plots'
    )

    parser.add_argument(
        '--text-color',
        metavar='TEXT_COLOR',
        default=config.APP_TEXT_COLOR,
        help='the text color for plots'
    )

    parser.add_argument(
        '--palette',
        metavar='PALETTE',
        default=config.APP_PALETTE,
        help='the color palette to use for images'
    )

    parser.add_argument(
        '--logx',
        action='store_true',
        default=config.APP_LOG,
        help='show the x-axis in a logarithmic scale'
    )

    parser.add_argument(
        '--logy',
        action='store_true',
        default=config.APP_LOG,
        help='show the y-axis in a logarithmic scale'
    )

    parser.add_argument(
        '-g',
        '--grid',
        action='store_true',
        default=config.APP_GRID,
        help='show grid lines overlaid on plots'
    )

    parser.add_argument(
        '--client',
        metavar='CLIENT',
        default=config.APP_CLIENT,
        help='the client backend used for rendering (default: %s)' % config.APP_CLIENT
    )

    parser.add_argument(
        '--recv-limit',
        metavar='RECV_LIMIT',
        type=int,
        default=config.APP_RECV_LIMIT,
        help='the maximum number of messages to discard from the recieve buffer per time'
    )

    parser.add_argument(
        '--log',
        metavar='LOG',
        default=config.LOG_LEVEL,
        help='the logging level of the client (default %s)' % config.LOG_LEVEL
    )

    return parser.parse_args()


def plot_client(client_info, plot_info):
    render_mod = __import__('psmon.client%s' % client_info.renderer, fromlist=['main'])
    sys.exit(render_mod.main(client_info, plot_info))


def topic_client(client_info, plot_info):
    # try to find out the server and port number
    name_parse = re.match(r'tcp://(?P<server>\S+):(?P<port>\d+)', client_info.data_socket_url)
    if name_parse:
        server = name_parse.group('server')
        port = name_parse.group('port')
    else:
        server = None
        port = None
    LOG.debug('Attempting to retrieve topic list from server %s at port %s', server, port)
    topic_sub = app.ZMQSubscriber(client_info)
    topics = topic_sub.data_recv()
    LOG.info('Topic list successfully retrieved from %s', server)
    # Now print the topic list
    LOG.info("Available topics on %s: %s", server, topics)


def spawn_process(client_info, plot_info, target=plot_client):
    proc = mp.Process(name='%s-client' % client_info.topic, target=target, args=(client_info, plot_info))
    proc.daemon = client_info.daemon
    proc.start()

    return proc


def main():
    try:
        args = parse_cmdline()

        # set levels for loggers that we care about
        LOG.setLevel(log_level_parse(args.log))

        # create the plot info object from cmd args
        plot_info = app.PlotInfo(
            xrange=args.x_range,
            yrange=args.y_range,
            zrange=args.z_range,
            logx=args.logx,
            logy=args.logy,
            aspect=args.aspect,
            bkg_col=args.bkg_color,
            fore_col=args.text_color,
            interpol=args.interpolation,
            palette=args.palette,
            grid=args.grid,
            auto_zrange=args.auto_z_range
        )

        # creat the tcp socket urls from cli parameters
        data_socket_url = 'tcp://%s:%d' % (args.server, args.port)
        comm_socket_url = 'tcp://%s:%d' % (args.server, args.port+config.APP_COMM_OFFSET)

        if args.topics:
            proc_list = []
            for topic in args.topics:
                client_info = app.ClientInfo(
                    data_socket_url,
                    comm_socket_url,
                    args.buffer,
                    args.rate,
                    args.recv_limit,
                    topic,
                    args.client,
                    True)
                LOG.info('Starting client for topic: %s', topic)
                proc = spawn_process(client_info, plot_info)
                proc_list.append(proc)

            # wait for all the children to exit
            failed_client = False
            for proc in proc_list:
                proc.join()
                if proc.exitcode == 0:
                    LOG.info('%s exited successfully', proc.name)
                else:
                    failed_client = True
                    LOG.error('%s exited with non-zero status code: %d', proc.name, proc.exitcode)

            LOG.info('All clients have exited')

            # return a non-zero status code if any clients died
            if failed_client:
                return 1
        else:
            LOG.info('No topics specified - attempting to retrieve list of topics from the server')
            client_info = app.ClientInfo(
                data_socket_url,
                comm_socket_url,
                args.buffer,
                args.rate,
                args.recv_limit,
                config.APP_TOPIC_LIST,
                args.client,
                True)
            proc = spawn_process(client_info, plot_info, target=topic_client)
            proc.join(config.APP_TIMEOUT)
            # check the return code of the topic process - if it has hung it will be 'None'
            if proc.exitcode != 0:
                LOG.error('Failed to retrieve topic information from %s on port %d - server may be down!',
                          args.server, args.port)
                return 1

    except KeyboardInterrupt:
        print('\nExitting client!')


if __name__ == '__main__':
    sys.exit(main())
