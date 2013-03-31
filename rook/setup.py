"""Helper function for pavement"""
import os
import sys
import tempfile
import socket
import subprocess
from multiprocessing import Process


def rpip_server(sock_path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(sock_path)
    sock.listen(1)
    done = set()

    while True:
        connection, client_address = sock.accept()
        print >>sys.stderr, 'connection from', client_address

        data = ''
        while 1:
            new_data = connection.recv(1024)
            if new_data:
                data += new_data
            else:
                break

        print 'received commands:'
        print data

        reps = set()
        for line in data.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                continue
            reps.add(line)

        print reps
        for rep in reps:
            if rep not in done:
                subprocess.call(['pip', 'install', rep])
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
    return proc


def requirements_txt():
    """
    Install the required packages.
    Installs the requirements set in requirements.txt.
    """
    if os.path.exists('requirements.txt'):
        RPIP_SOCK = os.environ.get('RPIP_SOCK')
        proc = None
        if RPIP_SOCK is None:
            proc = start_rpip_server()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(os.environ['RPIP_SOCK'])
        print 'Installing requirements: ' + os.path.abspath('requirements.txt')
        sock.send(open('requirements.txt'))
        sock.shutdown(socket.SHUT_WR)

        if proc:
            proc.join()