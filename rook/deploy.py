"""Merge commits into a live branch - currently, staging"""
from __future__ import absolute_import

import os, sys
import time
import argparse
import re
import subprocess as sp
import webbrowser

from git import Repo, InvalidGitRepositoryError

from . import cli, git


def main():
    env_dir = os.environ['VIRTUAL_ENV'] + '/src/'
    src = 'master'
    dst = 'staging'
    log = ''
    real = 'real' in sys.argv
    for folder in os.listdir(env_dir):
        path = env_dir + folder
        try:
            repo = Repo(path)
        except InvalidGitRepositoryError:
            continue
        if not dst in repo.branches:
            continue
        print path
        log += folder + '\n'
        proc = sp.Popen(['git', 'shortlog', dst + '..' + src], cwd=path, stdout=sp.PIPE)
        proc.wait()
        log += proc.stdout.read()
        sp.Popen(['git', 'checkout', dst], cwd=os.path.join(env_dir, folder)).wait()
        if real:
            sp.Popen(['git', 'merge', src], cwd=os.path.join(env_dir, folder)).wait()
            sp.Popen(['git', 'push'], cwd=os.path.join(env_dir, folder)).wait()
    webbrowser.open('https://docs.google.com/a/greyrook.com/document/d/1ilHY9Gjb-zFK_1Teh3DEGiinMfK6MlWnLNRguBfjN68/edit')
    open('/tmp/rdeploy.log', 'w').write(log)
    sp.Popen(['gedit', '/tmp/rdeploy.log'])

    if not real:
        print 'not really doing anything, use'
        print 'rdploy real'
        print 'to actually change something on the server'
    else:
        print '-- compile client --'
        os.chdir(os.path.join(env_dir, 'leijuna-client'))
        # sp.Popen(['./compile-all-for-client.sh']).wait()
        sp.Popen(['rsync', '-av', 'bin', 'root@leijuna.de:/srv/leijuna/deploy/staging/src/leijuna-server/leijuna/static/']).wait()
        sp.Popen(['ssh', 'root@leijuna.de', '/srv/leijuna/deploy/staging/src/update']).wait()


        print 'Done. checking out master again'
        for folder in os.listdir(env_dir):
            path = env_dir + folder
            try:
                repo = Repo(path)
            except InvalidGitRepositoryError:
                continue
            if not dst in repo.branches:
                continue
        sp.Popen(['git', 'checkout', src], cwd=os.path.join(env_dir, folder)).wait()

        print 'ssh into server'
        sp.Popen(['ssh', '-t', 'root@leijuna.de', 'screen', '-r', 'eva']).wait()
    #parser = argparse.ArgumentParser(description=__doc__,
    #                                 formatter_class=argparse.RawTextHelpFormatter)
    #args = parser.parse_args()
