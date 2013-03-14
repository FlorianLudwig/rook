import os, sys
import fcntl
import termios
import struct




def color(t, c, bg=0):
    return u'\x1b[' + unicode(c) + u'm' + unicode(t) + u'\x1b[0m'


def black(t):
    return color(t, u'30')


def red(t):
    return color(t, u'31')


def green(t):
    return color(t, u'32')


def yellow(t):
    return color(t, u'1;33')


def cyan(t):
    return color(t, u'36')


def bold(t):
    return color(t, u'1')


def orange(t):
    return color(t, u'33')


def black_bg(t):
    return color(t, u'40')


def red_bg(t):
    return color(t, u'41')


def green_bg(t):
    return color(t, u'42')


def yellow_bg(t):
    return color(t, u'43')


def blue_bg(t):
    return color(t, u'44')


def purple_bg(t):
    return color(t, u'45')


def cyan_bg(t):
    return color(t, u'46')


def white_bg(t):
    return color(t, u'47')


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
