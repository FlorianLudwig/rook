#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""checks git status in one ore mor repsotories

If executes without REGEX argument
 - within a repository it shows status of the current repository
 - of outside of a repo it shows the status of all within your $VIRTUAL_ENV/src folder

when a REGEX argument is given all repositories that match from your $VIRTUAL_ENV/src
folder are used.


"""

from sets import Set
from git import Repo, InvalidGitRepositoryError
import os, time
import argparse
import re


def is_git_repo(dir):
    if os.path.isdir(dir + '/.git'):
        return True
    else:
        return False


def get_top_folder(dir):
    if is_git_repo(dir):
        return dir
    elif dir == '/':
        return ''
    else:
        return get_top_folder(os.path.dirname(dir))


def check_dirs(dir, args):
    dirs = get_dirs_with_fullpath(dir)
    for full_dir in dirs:
        git_status(full_dir, args)


def git_status(dir, args):
    dir = os.path.realpath(dir)
    try:
        repo = Repo(dir)
    except InvalidGitRepositoryError:
        return

    for remote in repo.remotes:
        remote.fetch()

    if args.pull:
        for remote in repo.remotes:
            remote.pull()

    if args.push:
        for remote in repo.remotes:
            remote.push()

    name = dir.split('/')[-1]
    if repo.is_dirty():
        name += '*'
    title = bold(name)

    title += ' ' + green(repo.active_branch.name) + ' ' + ' '.join(branch.name for branch in repo.branches if branch != repo.active_branch)
    print title

    commits_origin = Set(repo.iter_commits('origin/master'))
    commits_local = Set(repo.iter_commits())

    push_commits = list(commits_local.difference(commits_origin))
    pull_commits = list(commits_origin.difference(commits_local))

    push_commits = sorted(push_commits)
    pull_commits = sorted(pull_commits)

    if len(push_commits) > 0:
        print red("Commits to push (" + str(len(push_commits)) + "):")
        print_commits(push_commits)
    if len(pull_commits) > 0:
        print red("Commits to pull (" + str(len(pull_commits)) + "):")
        print_commits(pull_commits)

    if len(push_commits) > 0 or len(pull_commits) > 0:
        print


def print_commits(commits):
    for i, commit in enumerate(commits):
        if i > 3:
            break
        msg = commit.message.strip()
        if '\n' in msg:
            msg = msg.split("\n")[0] + u'…'
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime(commit.committed_date))
        print ' %s %s: %s' % (date, commit.author.email, msg)


def get_dirs_with_fullpath(dir):
    return [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]


def color(t, c):
    return chr(0x1b)+"["+str(c)+"m"+t+chr(0x1b)+"[0m"


def red(t):
    return color(t, 31)


def green(t):
    return color(t, 32)


def bold(t):
    return color(t, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-p', '--pull', action="store_true", help='Pull commits')
    parser.add_argument('-P', '--push', action="store_true", help='Push commits')
    parser.add_argument('regex', metavar='REGEX', nargs='?',
                        help='RegEx to search in your virtualenv')
    args = parser.parse_args()

    env_dir = os.environ['VIRTUAL_ENV'] + '/src/'
    self_dir = os.path.realpath('.')

    top_dir = get_top_folder(self_dir)

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

