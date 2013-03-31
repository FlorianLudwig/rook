"""Helper function for pavement"""
import os
import sys
import time
import tempfile
import socket
import subprocess
import atexit
from multiprocessing import Process


def rpip_server(sock_path):
    def cleanup():
        if os.path.exists(sock_path):
            os.unlink(sock_path)

    atexit.register(cleanup)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(1)
    done = set()

    # TODO: security
    while True:
        connection, client_address = sock.accept()

        data = ''
        while 1:
            new_data = connection.recv(1024)
            if new_data:
                data += new_data
            else:
                break

        reps = set()
        for line in data.split('\n'):
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            reps.add(line)

        for rep in reps:
            if rep not in done:
                cmd = 'pip install ' + rep
                exit = subprocess.call(cmd, shell=True)
                if exit != 0:
                    print >> sys.stderr, cmd + ' FAILED'
                    sys.exit(exit)
        done.update(reps)
        connection.close()


def start_rpip_server():
    tmpdir = tempfile.gettempdir()
    i = 0
    while os.path.exists(tmpdir + '/rpip.' + str(i)):
        i += 1
    rpip_sock = tmpdir + '/rpip.' + str(i)
    os.environ['RPIP_SOCK'] = rpip_sock
    proc = Process(target=rpip_server, args=(rpip_sock,))
    proc.start()
    i = 0
    while i < 500 and not os.path.exists(rpip_sock):
        time.sleep(0.01)
    if not os.path.exists(rpip_sock):
        print >> sys.stderr, 'RPIP SERVER FAILED TO START IN TIME.'
        sys.exit(1)
    return proc


def requirements_txt():
    """
    Install the required packages.
    Installs the requirements set in requirements.txt.
    """
    if os.path.exists('requirements.txt'):
        print 'found requirements.txt'
        RPIP_SOCK = os.environ.get('RPIP_SOCK')
        proc = None
        if RPIP_SOCK is None:
            proc = start_rpip_server()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print 'connecting to rpip server' + os.environ['RPIP_SOCK']
        sock.connect(os.environ['RPIP_SOCK'])
        print 'Installing requirements: ' + os.path.abspath('requirements.txt')
        sock.send(open('requirements.txt').read())
        sock.shutdown(socket.SHUT_WR)

        if proc:
            proc.join()