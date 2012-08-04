#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""checks git status in one or more repositories

If executes without REGEX argument
 - within a repository it shows status of the current repository
 - outside of a repo it shows the status of all within your $VIRTUAL_ENV/src folder

when a REGEX argument is given all repositories that match from your $VIRTUAL_ENV/src
folder are used.


"""
from __future__ import absolute_import

import os, sys
import time
import argparse
import re
import subprocess as sp
from threading import Semaphore, Thread

from git import Repo, InvalidGitRepositoryError

from . import cli, git

git_threads = []
semaphore = Semaphore(8)


def check_dirs(dir, args):
    dirs = get_dirs_with_fullpath(dir)
    for full_dir in dirs:
        git_status(full_dir, args)


def git_status(dir, args):
    thread = GitStatus(dir, args)
    git_threads.append(thread)
    thread.start()


class GitStatus(Thread):
    def __init__ (self, dir, args):
        Thread.__init__(self)
        self.dir = os.path.realpath(dir)
        self.args = args

    def run(self):
        try:
            result = self._git_status(self.dir, self.args)
            if not result is None:
                print result
        except:
            print cli.red('ERROR processing repo ' + self.dir)
            raise

    def _git_status(self, dir, args):
        result = ""
        try:
            repo = Repo(dir)
        except InvalidGitRepositoryError:
            return
        name = dir.split('/')[-1]
        if repo.is_dirty():
            name += '*'
        elif args.only_dirty:
            # show only dirty
            return

        result += cli.bold(name)

        title = ' ' + cli.green(repo.active_branch.name) + ' ' + \
                ' '.join(branch.name for branch in repo.branches if branch != repo.active_branch)
        result += title
        newline = False

        if args.pull:
            for remote in repo.remotes:
                #remote.pull()
                proc = sp.Popen(['git', 'pull', remote.name], cwd=dir, stdout=sp.PIPE, stderr=sp.STDOUT)
                for line in iter(proc.stdout.readline,''):
                    result += "\n" + line
                newline = True
        elif not args.cache:
            for remote in repo.remotes:
                semaphore.acquire()
                try:
                    remote.fetch()
                finally:
                    semaphore.release()

        if args.push:
            for remote in repo.remotes:
                #remote.push()
                sp.Popen(['git', 'push', remote.name], cwd=dir).wait()
                newline = True

        commits_origin = set(repo.iter_commits('origin/master'))
        commits_local = set(repo.iter_commits())

        push_commits = sorted(commits_local.difference(commits_origin))
        pull_commits = sorted(commits_origin.difference(commits_local))

        result_commits = ''
        if len(push_commits) > 0:
            result_commits += cli.cyan("Commits to push (" + str(len(push_commits)) + "):") + "\n"
            result_commits += self.print_commits(push_commits)

        if len(pull_commits) > 0:
            result_commits += cli.cyan("Commits to pull (" + str(len(pull_commits)) + "):") + "\n"
            result_commits += self.print_commits(pull_commits)

        if len(result_commits) > 0:
            result += "\n"
        result += result_commits

        if newline:
            result += ""

        return result


    def print_commits(self, commits):
        result = ""
        for i, commit in enumerate(commits):
            if i > 3:
                break
            msg = commit.message.strip()
            if '\n' in msg:
                msg = msg.split("\n")[0] + u'…'
            date = time.strftime("%Y-%m-%d %H:%M", time.localtime(commit.committed_date))
            result += ' %s %s: %s' % (date, commit.author.email, msg) + "\n"

        return result



def get_dirs_with_fullpath(dir):
    return sorted([os.path.join(dir, f) for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-p', '--pull', action="store_true", help='Pull commits')
    parser.add_argument('-P', '--push', action="store_true", help='Push commits')
    parser.add_argument('-d', '--only-dirty', action="store_true", help='only dirty repositories')
    parser.add_argument('-C', '--cache', action="store_true", help="Do not hit the network, use local avaiable information only")
    parser.add_argument('regex', metavar='REGEX', nargs='?',
                        help='RegEx to search in your virtualenv')
    args = parser.parse_args()

    env_dir = os.environ['VIRTUAL_ENV'] + '/src/'
    self_dir = os.path.realpath('.')

    top_dir = git.get_top_folder(self_dir)

    if args.regex:
        regex = re.compile(args.regex)
        for f in os.listdir(env_dir):
            if regex.search(f):
                git_status(env_dir + f, args)

    elif len(top_dir) > 0:
            git_status(top_dir, args)
    else:
        check_dirs(env_dir, args)


if __name__ == '__main__':
    main()

