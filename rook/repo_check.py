#!/usr/bin/env python2

from sets import Set
from git import Repo, InvalidGitRepositoryError
import os, sys, time


def git_status(dir):
    dirs = get_dirs_with_fullpath(dir)
    for full_dir in dirs:
        try:
            repo = Repo(full_dir)
        except InvalidGitRepositoryError:
            print "Ignore", full_dir
            continue
        assert len(repo.remotes) == 1, repo.remotes
        
        repo.remotes[0].fetch()

        print "Dir:", full_dir.split('/')[-1]


        print "Is dirty:", repo.is_dirty()

#        if len(repo.untracked_files) > 0:
#            print "Untracked files:"
#            for file in repo.untracked_files:
#                print file, ";",

        commits_origin = Set(repo.iter_commits('origin/master'))
        commits_local = Set(repo.iter_commits())

        push_commits = commits_local.difference(commits_origin)
        if len(push_commits) > 0:
            print "Commits to push (" + str(len(push_commits)) + "):"            
            print_commits(push_commits)
        pull_commits = commits_origin.difference(commits_local)
        if len(pull_commits) > 0:
            print "Commits to pull (" + str(len(pull_commits)) + "):"
            print_commits(pull_commits)

    #        for commit in list(repo.iter_commits('origin/master')):
    #                       print commit 

    #               print "since", repo.commits_since()


def print_commits(commits):
    for commit in commits:
        print commit.hexsha, time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(commit.committed_date)), commit.author.name, commit.author.email
        print commit.message


def get_dirs_with_fullpath(dir):
    return [os.path.join(dir, f) for f in os.listdir(dir) if os.path.isdir(os.path.join(dir, f))]

if __name__ == '__main__':
    git_status(sys.argv[1])
