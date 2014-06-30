import sys
import functools
import socket
import errno

from tornado import ioloop
from tornado import iostream

NULL_BYTE = '\u0000'


def policy_ready(sock, fd, events):
    while True:
        try:
            connection, address = sock.accept()
        except socket.error, e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
            return
        connection.setblocking(0)
        stream = iostream.IOStream(connection, io_loop=ioloop.IOLoop.instance())
        PolicyConnection(connection, stream, address)


class PolicyConnection(object):
    request_string = '<policy-file-request/>'
    start_of_test_run_ack = "<startOfTestRunAck/>"
    end_of_test_run = "<endOfTestRun/>"
    end_of_test_run_ack = "<endOfTestRunAck/>"
    socket_policy = '<?xml version="1.0"?>' \
        '<cross-domain-policy xmlns="http://localhost"' \
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' \
        'xsi:schemaLocation="http://www.adobe.com/xml/schemas ' \
        'PolicyFileSocket.xsd">"' \
        '<allow-access-from domain="*" to-ports="{}" />' \
        '</cross-domain-policy>'

    def __init__(self, connection, stream, address):
        self.stream = stream
        self.stream.read_bytes(len(self.request_string), self.read)

    def read(self, data):
        if data == self.request_string:
            print 'send policy'
            #self.stream.read_bytes(1, self.read) # there might be another dot comming.
            self.stream.write(self.socket_policy)
            print 'send start test run'
            
            self.stream.write(self.start_of_test_run_ack)

        else:
            print data
        self.stream.read_bytes(262144, self.read)


def main():
    p_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    p_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    p_sock.setblocking(0)
    p_sock.bind(("", 1024))
    p_sock.listen(1)

    #priv.drop_privileges()

    io_loop = ioloop.IOLoop.instance()

    p_callback = functools.partial(policy_ready, p_sock)

    io_loop.add_handler(p_sock.fileno(), p_callback, io_loop.READ)
    print 'serving socketpolicyd'
    io_loop.start()

if __name__ == '__main__':
    main()