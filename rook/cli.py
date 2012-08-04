def color(t, c):
    return chr(0x1b) + "["+str(c) + "m" + t + chr(0x1b) + "[0m"


def red(t):
    return color(t, 31)

def cyan(t):
    return color(t, 36)


def green(t):
    return color(t, 32)


def bold(t):
    return color(t, 1)
