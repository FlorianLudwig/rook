# -*- coding: utf-8 -*-
import os
import sys
from distutils.command.sdist import sdist
from setuptools import setup, find_packages

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
VERSION_SUFFIX = ''


def get_version_suffix():
    from git import Repo
    from datetime import datetime
    repo = Repo()
    committed_date = repo.head.commit.committed_date
    return '.git' + datetime.fromtimestamp(committed_date).strftime('%Y%m%d%H%M%S')


class sdist_git(sdist):
    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        # make sure we include the git version in the release
        setup_py = open(base_dir + '/setup.py').read()
        setup_py = setup_py.replace("\nVERSION_SUFFIX = ''\n", "\nVERSION_SUFFIX = {}\n".format(repr(VERSION_SUFFIX)))
        f = open(base_dir + '/setup.py', 'w')
        f.write(setup_py)
        f.close()


if '--dev' in sys.argv:
    VERSION_SUFFIX = get_version_suffix()
    sys.argv.remove('--dev')

setup(
    name="rook",
    version="0.0.1" + VERSION_SUFFIX,
    packages=find_packages(),
    install_requires=['pyinotify', 'paver', 'GitPython==0.3.2.RC1', 'rueckenwind>=0.3.0.git0'],
    package_data={'rook': ['build/playerglobal.10.1.swc', 'de/templates/error.html', 'de/templates/index.html']},
    entry_points= {
        'console_scripts': [
            'rookd = rook.de:main',
            'rmake = rook.build:main',
            'rcheck = rook.repo_check:main',
            'rdeploy = rook.deploy:main',
            'rpip = rook.pip:main',
            'rprompt = rook.prompt:main'
        ],
    },
    cmdclass={'sdist': sdist_git}
)
