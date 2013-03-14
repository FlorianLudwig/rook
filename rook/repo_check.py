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

import os
import sys
import shutil
import stat
import time
import argparse
import re
import subprocess as sp
from threading import Semaphore, Thread

from git import Repo, Git, InvalidGitRepositoryError
from git.exc import GitCommandError

from . import cli, git

git_threads = []
semaphore = Semaphore(8)

GITHOOK = """# GIT HOOK CREATED BY rcheck

GIT=`dirname $0`

if [ -e $0.real ]; then
  $0.real || exit $?
fi

REPO_HOOK="$GIT/../../.githooks/`basename $0`"
if [ -e "$REPO_HOOK" ]; then
 $REPO_HOOK || exit $?
fi"""
RX = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH \
     | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH


def git_status(dir, args):
    thread = GitStatus(dir, args)
    git_threads.append(thread)
    thread.start()


class GitStatus(Thread):
    def __init__ (self, dir, args):
        Thread.__init__(self)
        self.dir = os.path.realpath(dir)
        self.args = args
        self.result = u''

    def run(self):
        try:
            self.result += self._git_status(self.dir, self.args)
        except GitCommandError, e:
            msg = e.command[0]
            self.result += self.dir +u'\n' + cli.red(msg) + u'\n'
            if 'The remote end hung up unexpectedly' in msg \
             or 'Unable to look up' in msg:
                 self.result += u'Network might be down, try -C\n'
        except:
            print cli.red(u'ERROR processing repo ' + self.dir)
            raise

    def _git_status(self, dir, args):
        # we abuse rcheck to make sure everyone got his git repository
        # setup "properly". Lets sneak in some git hooks.
        githooks = dir + '/.githooks'
        if os.path.exists(githooks):
            # ok there are repository hooks, lets make sure they are used
            for hook in os.listdir(githooks):
                rcheck_hook = dir + '/.git/hooks/' + hook
                if os.path.exists(rcheck_hook):
                    if open(rcheck_hook).readline() != '# GIT HOOK CREATED BY rcheck\n':
                        shutil.move(rcheck_hook, rcheck_hook + '.real')
                    else:
                        continue
                open(rcheck_hook, 'w').write(GITHOOK)
                os.chmod(rcheck_hook, RX)

        result = u''
        try:
            repo = Repo(dir)
        except InvalidGitRepositoryError:
            return u''
        name = dir.split('/')[-1]
        if repo.is_dirty():
            name += cli.red(u'*')
        elif args.only_dirty:
            # show only dirty
            return u''

        result += cli.bold(name)

        is_detached = False
        try:
            active_branch = repo.active_branch
        except TypeError:
            is_detached = True
            active_branch = '[detached]'

        title = u' ' + cli.green(active_branch) + ' ' + \
                u' '.join(branch.name for branch in repo.branches if branch != active_branch)
        result += u' ' + title.strip()

        len_untracked_files = len(repo.untracked_files)
        if len_untracked_files > 0:
            result += cli.orange( u' (' + unicode(len_untracked_files) + u' untracked files)')

        if args.sha1:
            g = Git(dir)
            hexshas = g.log('--pretty=%H', '--all').split('\n')
            if not args.sha1[0] in hexshas:
                return ""
            commit = repo.commit(args.sha1[0])
            result += cli.green("\nFOUND:\n")
            result += self.print_commits([commit])
            return result

        if args.pull:
            for remote in repo.remotes:
                #remote.pull()
                proc = sp.Popen(['git', '-c', 'color.ui=always', 'pull', remote.name], cwd=dir, stdout=sp.PIPE, stderr=sp.STDOUT)
                for line in iter(proc.stdout.readline, ''):
                    if line.strip() == 'Already up-to-date.':
                        result += u' ' + cli.yellow('up-to-data')
                    else:
                        result += u'\n' + line.decode('utf-8').strip()
                if remote != repo.remotes[-1]:
                    result += u'\n'

        elif not args.cache:
            for remote in repo.remotes:
                semaphore.acquire()
                try:
                    remote.fetch()
                finally:
                    semaphore.release()

        if is_detached:
            return result

        if args.push:
            for remote in repo.remotes:
                #remote.push()
                sp.Popen(['git', 'push', remote.name], cwd=dir).wait()

        commits_origin = set(repo.iter_commits("origin/" + repo.active_branch.name))
        commits_local = set(repo.iter_commits(repo.active_branch.name))

        push_commits = sorted(commits_local.difference(commits_origin))
        pull_commits = sorted(commits_origin.difference(commits_local))

        result_commits = u''
        if len(push_commits) > 0:
            result_commits += cli.cyan(u'Commits to push ({0}):'.format(len(push_commits))) + u'\n'
            result_commits += self.print_commits(push_commits)

        if len(pull_commits) > 0:
            result_commits += cli.cyan(u'Commits to pull ({0}):'.format(len(pull_commits))) + u'\n'
            result_commits += self.print_commits(pull_commits)

        if len(result_commits) > 0:
            result += u'\n'
        result += result_commits
        assert(isinstance(result, unicode))

        return result

    def print_commits(self, commits):
        result = u''
        for i, commit in enumerate(commits):
            if i > 3:
                break
            msg = commit.message.strip()
            assert isinstance(msg, unicode)
            if u'\n' in msg:
                msg = msg.split(u'\n')[0] + u'…'
            date = self.format_date(commit.committed_date)
            result += u' %s %s: %s' % (date, commit.author.email, msg)
            if i < 3:
                result += u'\n'

        return result

    def format_date(self, date):
        return time.strftime(u'%Y-%m-%d %H:%M', time.localtime(date))

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-p', '--pull', action="store_true", help='Pull commits')
    parser.add_argument('-P', '--push', action="store_true", help='Push commits')
    parser.add_argument('-d', '--only-dirty', action="store_true", help='only dirty repositories')
    parser.add_argument('-C', '--cache', action="store_true", help="Do not hit the network, use local avaiable information only")
    parser.add_argument('-s', '--sha1', nargs='*', help='Search for sha1')
    parser.add_argument('regex', metavar='REGEX', nargs='*',
                        help='RegEx to search in your virtualenv')
    args = parser.parse_args()

    env_dir = os.environ['VIRTUAL_ENV'] + '/src/'
    self_dir = os.path.realpath('.')

    top_dir = git.get_top_folder(self_dir)

    result = u''
    if len(top_dir) > 0:
        git_status(top_dir, args)
    else:
        regex = [re.compile(r) for r in args.regex]

        for f in sorted(os.listdir(env_dir)):
            if regex and not any(r.search(f) for r in regex):
                continue
            git_status(env_dir + f, args)

    # wait for all threads to be done and print results -- in sorted order
    done = 0.0
    sys.stdout.write('  0%')
    sys.stdout.flush()
    for thread in git_threads:
        thread.join()
        done += 1
        sys.stdout.write('\r{:3.0f}%'.format(done / len(git_threads) * 100))
        sys.stdout.flush()
        if thread.result:
            assert isinstance(result, unicode), 'result: ' + repr(result)
            result += thread.result + u'\n'
    sys.stdout.write(u'\r     \r')
    sys.stdout.flush()

    available_lines = cli.terminal_size()[1]
    if available_lines < result.count('\n'):

        less = sp.Popen(['less', '-R'], stdin=sp.PIPE)
        less.stdin.write(result.encode('utf-8', errors='replace'))
        less.stdin.close()
        less.wait()
    else:
        print result.strip()

if __name__ == '__main__':
    main()

