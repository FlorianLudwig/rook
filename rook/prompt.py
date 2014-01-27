import socket
import os
import pwd
import sys

import cli

# USAGE
# PS1="\$(rprompt \$?)"

# TODO add terminal title:
# PS1="\[\033]0;Hello \u@\h: \w\007\]bash\\$ "


def main():
    last_return_code = int(sys.argv[1])
    bg = cli.white_bg if last_return_code == 0 else cli.red_bg
    fg = cli.black if last_return_code == 0 else lambda x: x

    width = cli.terminal_size()[0]
    uid = os.getuid()
    user_name = pwd.getpwuid(uid)[0]
    root = uid == 0
    if root:
        user = bg(cli.red(user_name)).encode('utf-8')
    else:
        user = bg(fg(user_name)).encode('utf-8')
    path = os.path.abspath('.').decode('utf-8')

    text = u'@%s %s' % (socket.gethostname(), path)

    if len(text) < width:
        text += ' ' * (width - len(text) - len(user_name))

    title = path
    sys.stdout.write('\033]0;' + title.encode('utf-8') + '\007')
    print user + bg(fg(text)).encode('utf-8')
    if root:
        sys.stdout.write('# ')
    else:
        sys.stdout.write('$ ')


if __name__ == '__main__':
    main()
