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
    width = cli.terminal_size()[0]
    user = pwd.getpwuid(os.getuid())[0]
    if user == 'root':
        user = cli.red(user)
    path = os.path.abspath('.').decode('utf-8')
    text = u'%s@%s %s' % (user, socket.gethostname(), path)

    if len(text) < width:
        text += ' ' * (width - len(text))

    if last_return_code == 0:
        print cli.white_bg(cli.black(text)).encode('utf-8')
    else:
        print cli.red_bg(text)
    sys.stdout.write('$ ')


if __name__ == '__main__':
    main()