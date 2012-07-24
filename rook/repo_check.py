#!/usr/bin/env python2

from sets import Set
from git import Repo, InvalidGitRepositoryError
import os, sys, time


def is_git_repo(dir):
    if os.path.isdir(dir + '/.git'):
        return True
    else:
        return False

def check_dirs(dir):
    dirs = get_dirs_with_fullpath(dir)
    for full_dir in dirs:
        git_status(full_dir)

def git_status(dir):
    dir = os.path.realpath(dir)
    try:
        repo = Repo(dir)
    except InvalidGitRepositoryError:
        print "Ignore", dir
        return

    for remote in repo.remotes:
        remote.fetch()

    title = dir.split('/')[-1]
    if repo.is_dirty():
        title += '*'

    title += ' ' + ' '.join(green(branch.name) if branch == repo.active_branch else branch.name
                     for branch in repo.branches) 
    print bold(title)
    print ""

    commits_origin = Set(repo.iter_commits('origin/master'))
    commits_local = Set(repo.iter_commits())

    push_commits = commits_local.difference(commits_origin)
    if len(push_commits) > 0:
        print red("Commits to push (" + str(len(push_commits)) + "):")
        print_commits(push_commits)
    pull_commits = commits_origin.difference(commits_local)
    if len(pull_commits) > 0:
        print red("Commits to pull (" + str(len(pull_commits)) + "):")
        print_commits(pull_commits)


def print_commits(commits):
    for commit in commits:
        print commit.hexsha, time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(commit.committed_date)), commit.author.name, commit.author.email
        print commit.message


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
    dir = '.'
    if len(sys.argv) > 1:
        dir = sys.argv[1]

    if is_git_repo(dir):
        git_status(dir)
    else:
        check_dirs(dir)            

if __name__ == '__main__':
    main()

