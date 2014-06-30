"""Helper function for pavement"""
from __future__ import print_function

import os
import sys
import time
import tempfile
import socket
import subprocess
import atexit
import string
import random
import select
from multiprocessing import Process, Pipe


## logging
_org_print = print
def print(*args):
    _org_print(*args)
    sys.stdout.flush()


class RPIPServer(object):
    def start(self):
        cmd_pipe, child_conn = Pipe()
        self.secret = ''.join(random.choice(string.ascii_letters) for i in xrange(32))
        self.proc = Process(target=self.run, args=(child_conn,))
        self.proc.start()
        print('RPIPServ process spawned')
        sys.stdout.flush()
        self.sock_path = cmd_pipe.recv()
        sys.stdout.flush()
        os.environ['RPIP_SOCK'] = self.sock_path
        # this is not really secret, the environment of child process can be
        # read through /proc/<pid>/environ by processes of the same user
        os.environ['RPIP_SECRET'] = self.secret

    def run(self, cmd_pipe):
#        sys.stdout = open('/tmp/rpip_server.log', 'w')
        ## create socket
        atexit.register(self._cleanup)
        tmpdir = tempfile.gettempdir()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        i = 0
        while True:
            sock_path = tmpdir + '/rpip.' + str(i)
            try:
                sock.bind(sock_path)
                break
            except socket.error:
                i += 1
        cmd_pipe.send(sock_path)
        os.environ['RPIP_SOCK'] = sock_path
        # this is not really secret, the environment of child process can be
        # read through /proc/<pid>/environ by processes of the same user
        os.environ['RPIP_SECRET'] = self.secret

        ## actual server
        sock.listen(1)
        done = set()
        children = []

        while True:
            print('waiting for next connection')
            sys.stdout.flush()
            while 1:
                if select.select([sock], [], [], 0.01)[0]:
                    connection, client_address = sock.accept()
                for child, child_con in children:
                    print ('checking child')
                    child.poll()
                    if child.returncode is not None:
                        connection.send(str(ret))
                        child_con.close()

            data = ''
            while 1:
                new_data = connection.recv(1024)
                if new_data:
                    data += new_data
                    sys.stdout.flush()
                else:
                    break

            if not '|' in data:
                print('format not correct ' + repr(data))
                continue

            secret, data = data.split('|', 1)
            if secret != self.secret:
                print('wrong secret, ignoring ' + repr(data))
                continue

            if data == 'CMD:QUIT':
                print('shutting down rpip server')
                connection.send('0')
                connection.close()
                break

            reps = set()
            for line in data.split('\n'):
                line = line.strip()
                if line.startswith('#') or not line:
                    continue
                reps.add(line)

            ret = '0'
            for rep in reps:
                if rep not in done:
                    done.add(rep)
                    assert rep.startswith('-e '), repr(rep)
                    cmd = ['pip', 'install', '--exists-action', 'i']
                    cmd += rep.split(' ', 1)
                    print(cmd)
                    if 'PIP_EXISTS_ACTION' in os.environ:
                        del os.environ['PIP_EXISTS_ACTION']
                    log = open('/tmp/pip.log', 'w')
                    print ('spawned child -1')
                    proc = subprocess.Popen(cmd, env=os.environ, stdout=log)
                    children.append((proc, connection))
                    print ('spawned child')


    def _cleanup(self):
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)

    def stop(self):
        print('stopping RPIP Server')
        send_msg('CMD:QUIT')
        sys.stdout.flush()
        self.proc.join()
        sys.stdout.flush()


def send_msg(data):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#    print 'connecting to rpip server via ' + os.environ['RPIP_SOCK']
    sys.stdout.flush()
    sock.connect(os.environ['RPIP_SOCK'])
    sock.send(os.environ['RPIP_SECRET'] + '|' + data)
    sock.shutdown(socket.SHUT_WR)
    return sock.recv(1024)


def requirements_txt():
    """
    Install the required packages.
    Installs the requirements set in requirements.txt.
    """
    if os.path.exists('requirements.txt'):
        serv = None
        if not 'RPIP_SOCK' in os.environ:
            serv = RPIPServer()
            serv.start()

        print('Installing requirements: ' + os.path.abspath('requirements.txt'))
        code = int(send_msg(open('requirements.txt').read()))
        print('return code: ' + str(code))
        sys.stdout.flush()

        if serv:
            serv.stop()

        if code != 0:
            sys.exit(code)
