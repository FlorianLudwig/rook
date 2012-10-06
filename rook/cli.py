import os, sys
import fcntl
import termios
import struct


def color(t, c):
    return u'\x1b[' + unicode(c) + u'm' + unicode(t) + u'\x1b[0m'

def red(t):
    return color(t, 31)

def cyan(t):
    return color(t, 36)

def green(t):
    return color(t, 32)

def yellow(t):
    return color(t, '1;33')

def bold(t):
    return color(t, 1)

def orange(t):
    return color(t, 33)

def _ioctl_GWINSZ(fd):
    try:
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '0000'))
    except:
        return None
    return cr


def terminal_size():
    env = os.environ

    cr = _ioctl_GWINSZ(sys.stdout.fileno()) or _ioctl_GWINSZ(sys.stderr.fileno())
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = _ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass

    if not cr:
        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])
