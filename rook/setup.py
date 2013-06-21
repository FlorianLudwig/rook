"""Helper function for pavement"""
import os
import sys
import time
import tempfile
import socket
import subprocess
import atexit
import string
import random
from multiprocessing import Process, Pipe


## logging



def fake():
    print 'i am fake!'

class RPIPServer(object):
    def start(self):
        print 'Starting RPIP Server'
        cmd_pipe, child_conn = Pipe()
        self.secret = ''.join(random.choice(string.ascii_letters) for i in xrange(32))
        self.proc = Process(target=self.run, args=(child_conn,))
        self.proc.start()
        print 'RPIPServ process spawned'
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

        ## actual server
        sock.listen(1)
        done = set()

        while True:
            print 'waiting for next connection'
            sys.stdout.flush()
            connection, client_address = sock.accept()

            data = ''
            while 1:
                new_data = connection.recv(1024)
                if new_data:
                    data += new_data
                    sys.stdout.flush()
                else:
                    break

            if not '|' in data:
                print 'format not correct ' + repr(data)
                sys.stdout.flush()
                continue

            secret, data = data.split('|', 1)
            if secret != self.secret:
                print 'wrong secret, ignoring ' + repr(data)
                sys.stdout.flush()
                continue

            if data == 'CMD:QUIT':
                print 'shutting down rpip server'
                sys.stdout.flush()
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
                    cmd = 'pip install --exists-action=i ' + rep
                    print 'running command: ' + cmd
                    sys.stdout.flush()
                    exit = subprocess.call(cmd, shell=True)
                    if exit != 0:
                        print >> sys.stderr, cmd + ' FAILED'
                        sys.stderr.flush()
                        ret = str(exit)
                        break
            # all ok, sending return code 0
            connection.send(ret)
            done.update(reps)
            connection.close()

    def _cleanup(self):
        if os.path.exists(self.sock_path):
            os.unlink(self.sock_path)

    def stop(self):
        print 'stopping RPIP Server'
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

        print 'Installing requirements: ' + os.path.abspath('requirements.txt')
        code = int(send_msg(open('requirements.txt').read()))
        print 'return code: ' + str(code)
        sys.stdout.flush()

        if serv:
            serv.stop()

        if code != 0:
            sys.exit(code)
