import os
import re
import sys
import zmq
import atexit
import socket
import shutil
import logging
import tempfile
import threading
from collections import namedtuple
from psmon import config
# Queue module changed to queue in py3
if sys.version_info < (3,):
    import Queue as queue
else:
    import queue


LOG = logging.getLogger(__name__)


class PublishError(Exception):
    """
    Class for exceptions related to ZMQ message publishing errors.
    """
    pass


class Info(object):
    """
    Basic info object that implements basic repr and str functions.
    """
    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.__dict__)


class ClientInfo(Info):
    """
    The ClientInfo class is a container for psplot client configuration.
    """
    def __init__(self, data_socket_url, comm_socket_url, buffer, rate, recvlimit, topic, renderer, daemon):
        super(ClientInfo, self).__init__()
        self.data_socket_url = data_socket_url
        self.comm_socket_url = comm_socket_url
        self.buffer = buffer
        self.rate = rate
        self.recvlimit = recvlimit
        self.topic = topic
        self.renderer = renderer
        self.daemon = daemon


class PlotInfo(Info):
    """
    The PlotInfo class is a container for the plotting configuration of the psplot client.
    """
    def __init__(
        self,
        xrange=config.APP_XRANGE,
        yrange=config.APP_YRANGE,
        zrange=config.APP_ZRANGE,
        logx=config.APP_LOG,
        logy=config.APP_LOG,
        aspect=config.APP_ASPECT,
        fore_col=config.APP_TEXT_COLOR,
        bkg_col=config.APP_BKG_COLOR,
        interpol=config.APP_IMG_INTERPOLATION,
        palette=config.APP_PALETTE,
        grid=config.APP_GRID,
        auto_zrange=config.APP_AUTO_ZRANGE
    ):
        super(PlotInfo, self).__init__()
        self.xrange = xrange
        self.yrange = yrange
        self.zrange = zrange
        self.logx = logx
        self.logy = logy
        self.aspect = aspect
        self.fore_col = fore_col
        self.bkg_col = bkg_col
        self.interpol = interpol
        self.palette = palette
        self.grid = grid
        self.auto_zrange = auto_zrange


class MessageHandler(object):
    def __init__(self, name, qlimit, is_pyobj):
        self.name = name
        self.is_pyobj = is_pyobj
        self.__mqueue = queue.Queue(maxsize=qlimit)

    def get(self):
        return self.__mqueue.get_nowait()

    def put(self, msg):
        self.__mqueue.put_nowait(msg)

    @property
    def size(self):
        return self.__mqueue.qsize()

    @property
    def empty(self):
        return self.__mqueue.empty()

    @property
    def full(self):
        return self.__mqueue.full()


class ZMQPublisher(object):
    def __init__(self, comm_offset=config.APP_COMM_OFFSET):
        self.context = zmq.Context()
        self.data_socket = self.context.socket(zmq.XPUB)
        self.comm_socket = self.context.socket(zmq.REP)
        self.proxy_send_socket = self.context.socket(zmq.PUB)
        self.proxy_recv_socket = self.context.socket(zmq.SUB)
        self.proxy_url = "inproc://send-proxy"
        self.proxy_thread = threading.Thread(target=self._send_proxy)
        self.comm_offset = comm_offset
        self.initialized = False
        self.tempdir = None
        self.cache = {
            config.APP_TOPIC_LIST: []
        }
        atexit.register(self._clean_tmpdir)

    @property
    def data_endpoint(self):
        return self.data_socket.getsockopt(zmq.LAST_ENDPOINT)

    @property
    def comm_endpoint(self):
        return self.comm_socket.getsockopt(zmq.LAST_ENDPOINT)

    def initialize(self, port, bufsize, local):
        if self.initialized:
            LOG.debug('Publisher is already initialized - Nothing to do')
            return

        # set the hwm for the socket to the specified buffersize
        if LOG.isEnabledFor(logging.DEBUG):
            LOG.debug('Publisher data socket buffer size set to %d', bufsize)
        self.data_socket.set_hwm(bufsize)

        # set the data socket to verbose mode
        self.data_socket.setsockopt(zmq.XPUB_VERBOSE, True)
        # set the subscription filter on the proxy socket
        self.proxy_recv_socket.setsockopt_string(zmq.SUBSCRIBE, u"")

        # set up the external communication sockets
        if local:
            sock_bound = self._initialize_icp()
        else:
            sock_bound = self._initialize_tcp(port)

        # connect the proxy_sockets if setup of other socks succeeded
        if sock_bound:
            try:
                # if the proxy thread is not already running start it
                if not self.proxy_thread.is_alive():
                    self.proxy_send_socket.bind(self.proxy_url)
                    self.proxy_recv_socket.connect(self.proxy_url)
                    self.proxy_thread.daemon = True
                    # start the proxy receiver thread
                    self.proxy_thread.start()
                self.initialized = True
                LOG.debug('Initialized publisher proxy socket with endpoint: %s' % self.proxy_url)
            except zmq.ZMQError:
                LOG.warning('Unable to bind proxy sockets for publisher - disabling!')

    def send(self, topic, data):
        if self.initialized:
            if topic.startswith(config.APP_RESERVED_TOPIC):
                raise PublishError('Cannot publish data to internally reserved topic: %s' % topic)
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug('Publishing data to topic: %s', topic)
            self.proxy_send_socket.send_string(topic, zmq.SNDMORE)
            self.proxy_send_socket.send_pyobj(data)

    def _send_proxy(self):
        # set up a poller for incoming data from proxy or subscrition messages
        proxy_poller = zmq.Poller()
        proxy_poller.register(self.proxy_recv_socket, zmq.POLLIN)
        proxy_poller.register(self.data_socket, zmq.POLLIN)
        while not self.proxy_recv_socket.closed and not self.data_socket.closed:
            ready_socks = dict(proxy_poller.poll())
            # if proxy socket has inbound data foward it to the data publisher
            if self.proxy_recv_socket in ready_socks:
                topic = self.proxy_recv_socket.recv_string()
                data = self.proxy_recv_socket.recv_pyobj()
                if LOG.isEnabledFor(logging.DEBUG):
                    LOG.debug('Received data on proxy socket for topic: %s' % topic)
                self.data_socket.send_string(topic + config.ZMQ_TOPIC_DELIM_CHAR, zmq.SNDMORE)
                self.data_socket.send_pyobj(data)
                if topic not in self.cache:
                    self.cache[config.APP_TOPIC_LIST].append(topic)
                    self.data_socket.send_string(config.APP_TOPIC_LIST + config.ZMQ_TOPIC_DELIM_CHAR, zmq.SNDMORE)
                    self.data_socket.send_pyobj(self.cache[config.APP_TOPIC_LIST])
                self.cache[topic] = data
            # if the data socket has inbound data check for new subs
            if self.data_socket in ready_socks:
                topic_msg = self.data_socket.recv_string()
                if topic_msg[0] == '\x01':
                    if topic_msg[-1] != '\x00':
                        if LOG.isEnabledFor(logging.WARN):
                            LOG.warn('Received new subscription message for invalid topic - ignoring!')
                    else:
                        topic = topic_msg[1:-1]
                        if LOG.isEnabledFor(logging.DEBUG):
                            LOG.debug('Received subscription message for topic: %s' % topic)
                        try:
                            last_data = self.cache[topic]
                            if LOG.isEnabledFor(logging.DEBUG):
                                LOG.debug('Found cached message to resend for topic: %s' % topic)
                            self.data_socket.send_string(topic + config.ZMQ_TOPIC_DELIM_CHAR, zmq.SNDMORE)
                            self.data_socket.send_pyobj(last_data)
                        except KeyError:
                            if LOG.isEnabledFor(logging.DEBUG):
                                LOG.debug('No cached message found for topic: %s' % topic)

    def _initialize_icp(self):
        try:
            self.tempdir = tempfile.mkdtemp()
            self.data_socket.bind('ipc://%s/data' % self.tempdir)
            self.comm_socket.bind('ipc://%s/comm' % self.tempdir)
            LOG.info('Initialized publisher. Data socket %s, Comm socket: %s',
                     str(self.data_endpoint), self.comm_endpoint)
            return True
        except zmq.ZMQError:
            LOG.warning('Unable to bind local sockets for publisher - disabling!')
            return False

    def _initialize_tcp(self, port):
        offset = 0
        while offset < config.APP_BIND_ATTEMPT:
            port_try = port + offset
            result = self._attempt_bind(port_try)
            offset += result
            if result == 0:
                output_str = 'Initialized publisher%s. Data port: %d, Comm port: %d'
                if offset == 0:
                    LOG.info(output_str, '', port_try, port_try + self.comm_offset)
                else:
                    LOG.warning(output_str, ' (alternate ports)', port_try, port_try + self.comm_offset)
                return True
            elif result == 1:
                LOG.warning('Unable to bind publisher to data port: %d', port_try)
            else:
                LOG.warning('Unable to bind publisher to communication port: %d', (port_try+self.comm_offset))

        # some logging output on the status of the port initialization attempts
        LOG.warning('Unable to initialize publisher after %d attempts - disabling!' % offset)

        return False

    def _attempt_bind(self, port):
        try:
            self._bind(self.data_socket, port)
            try:
                self._bind(self.comm_socket, port + self.comm_offset)
                return 0
            except zmq.ZMQError:
                # make sure to clean up the first bind which succeeded in this case
                self._unbind(self.data_socket, port)
                return 2
        except zmq.ZMQError:
            return 1

    def _bind(self, sock, port):
        sock.bind('tcp://*:%d' % port)

    def _unbind(self, sock, port):
        sock.unbind('tcp://*:%d' % port)

    def _clean_tmpdir(self):
        if self.tempdir is not None and os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)


class ZMQSubscriber(object):
    def __init__(self, client_info, connect=True):
        self.client_info = client_info
        self.context = zmq.Context()
        self.data_socket = self.context.socket(zmq.SUB)
        self.topic_str = self.client_info.topic + config.ZMQ_TOPIC_DELIM_CHAR
        # Handle byte versus unicode strings for the topic
        if isinstance(self.topic_str, bytes):
            self.topic_str = self.topic_str.decode('ascii')
        self.data_socket.setsockopt_string(zmq.SUBSCRIBE, self.topic_str)
        self.data_socket.set_hwm(self.client_info.buffer)
        self.comm_socket = self.context.socket(zmq.REQ)
        self.connected = False
        if connect:
            self.connect()

    def connect(self):
        if not self.connected:
            self.sock_init(self.data_socket, self.client_info.data_socket_url)
            self.sock_init(self.comm_socket, self.client_info.comm_socket_url)
            self.connected = True

    def sock_init(self, sock, con_str):
        sock.connect(con_str)

    def data_recv(self, flags=0):
        self.data_socket.recv(flags)
        return self.data_socket.recv_pyobj(flags)

    def get_socket_gen(self):
        while True:
            count = 0
            data = None
            while count < self.client_info.recvlimit:
                try:
                    data = self.data_recv(flags=zmq.NOBLOCK)
                    count += 1
                except zmq.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        if LOG.isEnabledFor(logging.DEBUG):
                            LOG.debug('Number of queued messages discarded: %d', count)
                        break
                    else:
                        raise

            if count >= self.client_info.recvlimit and LOG.isEnabledFor(logging.WARN):
                LOG.warn('Number of queued messages exceeds the discard limit: %d', self.client_info.recvlimit)

            yield data


class ZMQListener(object):
    MessageHandle = namedtuple('MessageHandle', 'msg type')

    def __init__(self, comm_socket):
        self._reset = config.RESET_REQ_HEADER
        self._signal = re.compile(config.RESET_REQ_STR % '(.*)')
        self._reply = config.RESET_REP_STR
        self.__comm_socket = comm_socket
        self.__reset_flag = threading.Event()
        self.__message_handler = {}
        self.__thread = threading.Thread(target=self.comm_listener)
        self.__thread.daemon = True

    def send_reply(self, header, msg, send_py_obj=False):
        self.__comm_socket.send_string(header, zmq.SNDMORE)
        if send_py_obj:
            self.__comm_socket.send_pyobj(msg)
        else:
            self.__comm_socket.send_string(msg)

    def register_handler(self, name, limit=0, is_pyobj=True):
        if LOG.isEnabledFor(logging.DEBUG):
            LOG.debug('Attempting to register message handler: name=%s, limit=%s, pyobj=%s', (name, limit, is_pyobj))
        if name in self.__message_handler:
            if LOG.isEnabledFor(logging.WARN):
                LOG.warning('Attempted to register message handler which already exists: %s', name)
            raise ValueError('Message handler \'%s\' already registered' % name)
        handler = self.__message_handler[name] = MessageHandler(name, limit, is_pyobj)
        if LOG.isEnabledFor(logging.INFO):
            LOG.info('Sucessfully registered message handler: %s' % name)
        return handler

    def get_handler(self, name):
        return self.__message_handler.get(name)

    def comm_listener(self):
        while not self.__comm_socket.closed:
            header = self.__comm_socket.recv_string()
            if header == self._reset:
                msg = self.__comm_socket.recv_string()
                signal_matcher = self._signal.match(msg)
                if signal_matcher is not None:
                    self.set_flag()
                    self.send_reply(self._reset, self._reply % signal_matcher.group(1))
                    if LOG.isEnabledFor(logging.INFO):
                        LOG.info('Received valid reset request: %s', msg)
                else:
                    self.send_reply(self._reset, "invalid request from client")
                    if LOG.isEnabledFor(logging.WARN):
                        LOG.warning('Invalid request received on comm port: %s', msg)
            else:
                if header in self.__message_handler:
                    if self.__message_handler[header].is_pyobj:
                        msg = self.__comm_socket.recv_pyobj()
                    else:
                        msg = self.__comm_socket.recv_string()
                    try:
                        self.__message_handler[header].put(msg)
                        if LOG.isEnabledFor(logging.DEBUG):
                            LOG.debug('Message for handler \'%s\' processed', header)
                        self.send_reply(header, 'Message for handler processed')
                    except queue.Full:
                        if LOG.isEnabledFor(logging.WARN):
                            LOG.warning('Message handler \'%s\' is full - request dropped', header)
                        self.send_reply(header, 'Message handler full - request dropped')
                else:
                    if LOG.isEnabledFor(logging.DEBUG):
                        LOG.debug('Received message for unregistered handler: %s', header)

    def get_flag(self):
        return self.__reset_flag.is_set()

    def set_flag(self):
        self.__reset_flag.set()

    def clear_flag(self):
        self.__reset_flag.clear()

    def start(self):
        if not self.__thread.is_alive():
            self.__thread.start()


class ZMQRequester(object):
    def __init__(self, comm_socket):
        self._reset = config.RESET_REQ_HEADER
        self._request = config.RESET_REQ_STR % socket.gethostname()
        self._req_reply = config.RESET_REP_STR % socket.gethostname()
        self.__comm_socket = comm_socket
        self.__comm_lock = threading.Lock()
        self.__pending_flag = threading.Event()
        self.__thread = None

    def send_request(self, header, msg, send_py_obj=True, recv_py_obj=False):
        with self.__comm_lock:
            self.__comm_socket.send_string(header, zmq.SNDMORE)
            if send_py_obj:
                self.__comm_socket.send_pyobj(msg)
            else:
                self.__comm_socket.send_string(msg)
            rep_header = self.__comm_socket.recv_string()
            if header != rep_header and LOG.isEnabledFor(logging.WARN):
                LOG.warning('Request header does not match repy header: \'%s\' and \'%s\'', header, rep_header)
            if recv_py_obj:
                rep_msg = self.__comm_socket.recv_pyobj()
            else:
                rep_msg = self.__comm_socket.recv_string()

            return rep_msg

    def reset_signal(self):
        # check to see if there is another pending reset req
        if not self.__pending_flag.is_set():
            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug('Sending reset request to server')
            self.__pending_flag.set()
            reply = self.send_request(self._reset, self._request, False)
            if reply != self._req_reply and LOG.isEnabledFor(logging.ERROR):
                LOG.error('Server returned unexpected reply to reset request: %s', reply)
            self.__pending_flag.clear()

    def send_reset_signal(self, *args):
        self.__thread = threading.Thread(target=self.reset_signal)
        self.__thread.daemon = True
        self.__thread.start()
