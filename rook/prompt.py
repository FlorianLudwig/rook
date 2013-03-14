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
    text = '%s@%s:%s' % (user, socket.gethostname(), os.path.abspath('.'))

    if len(text) < width:
        text += ' ' * (width - len(text))

    if last_return_code == 0:
        print cli.white_bg(cli.black(text))
        sys.stdout.write('$ ')
    else:
        print cli.red_bg(text)
        sys.stdout.write('$ ')


if __name__ == '__main__':
    main()