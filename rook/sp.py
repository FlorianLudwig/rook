"""some helper functions for dealing with subprocesses"""

import sys
import os
import logging
from subprocess import Popen


LOG = logging.getLogger(__name__)


def exe(*args, **kwargs):
    cmd = args[0] + ' ' + ' '.join(repr(arg) for arg in args[1:])
    LOG.info(cmd)
    sys.stdout.flush()
    sys.stderr.flush()
    exit_code = Popen(args, env=os.environ).wait()
    if exit_code != 0:
        LOG.error('FAILED')
        LOG.error(' cmd: ' + cmd)
        LOG.error(' cwd: ' + os.path.abspath('.'))
        LOG.error(' exit code: ' + str(exit_code))
        if kwargs.get('exit_on_error', True):
            sys.exit(exit_code)

