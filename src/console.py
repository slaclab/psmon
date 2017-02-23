#!/usr/bin/env python
import sys
import zmq
import logging
import IPython
import argparse

from psmon import app, config, log_level_parse


LOG = logging.getLogger(config.LOG_BASE_NAME)


def _get_banner(host, port):
    banner_base = '\n{sep}\n*  {wel:<{width}s}  *\n*  {info:<{width}s}  *\n*  {help:<{width}s}  *\n{sep}\n'
    welcome_line = 'Welcome to the psmon server request client'
    info_line = 'Connected to host \'{host:s}\' on port \'{port:d}\''.format(host=host, port=port)
    help_line = 'Available commands: \'request\', \'reset\''
    width = max(len(welcome_line), len(info_line), len(help_line))
    separator = '*' * ( width + 6 )

    return banner_base.format(wel=welcome_line, info=info_line, help=help_line, sep=separator, width=width) 

def _parse_cmdline():
    parser = argparse.ArgumentParser(
        description='Psmon console client for communicating with servers'
    )

    parser.add_argument(
        '-s',
        '--server',
        metavar='SERVER',
        default=config.APP_SERVER,
        help='the host name of the server (default: %s)'%config.APP_SERVER
    )

    parser.add_argument(
        '-p',
        '--port',
        metavar='PORT',
        type=int,
        default=config.APP_PORT+config.APP_COMM_OFFSET,
        help='the tcp port of the server (default: %d)'%(config.APP_PORT+config.APP_COMM_OFFSET)
    )

    parser.add_argument(
        '--log',
        metavar='LOG',
        default=config.LOG_LEVEL,
        help='the logging level of the client (default %s)'%config.LOG_LEVEL
    )

    return parser.parse_args()


def main():
    _args = _parse_cmdline()

    # set levels for loggers that we care about
    LOG.setLevel(log_level_parse(_args.log))

    # start zmq requester
    LOG.debug('Starting request client for host \'%s\' on port \'%d\'', _args.server, _args.port)

    try:
        _zmqcontext = zmq.Context()
        _comm_socket = _zmqcontext.socket(zmq.REQ)
        _comm_socket.connect('tcp://%s:%d' % (_args.server, _args.port))
        _requester = app.ZMQRequester(_comm_socket)
        host = _args.server
        port = _args.port
        request = _requester.send_request
        reset = _requester.send_reset_signal
        LOG.debug('Request client started successfully')

        # Embed an ipython interactive session
        IPython.embed(banner1=_get_banner(_args.server, _args.port))
    except zmq.ZMQError as err:
        LOG.error('Failed to connect to server: %s', err)
    except KeyboardInterrupt:
        print('\nExitting client!')


if __name__ == '__main__':
    sys.exit(main())
