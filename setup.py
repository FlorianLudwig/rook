# -*- coding: utf-8 -*-
from distutils.command.sdist import sdist
from setuptools import setup, find_packages


class sdist_git(sdist):
    user_options = sdist.user_options + [
        ('dev', None, "Add a dev marker")
    ]

    def initialize_options(self):
        sdist.initialize_options(self)
        self.dev = 0

    def run(self):
        if self.dev:
            suffix = ".git{}".format(self.get_last_committed_date())
            self.distribution.metadata.version += suffix
        sdist.run(self)

    def get_last_committed_date(self):
        from git import Repo
        from datetime import datetime
        repo = Repo()
        committed_date = repo.head.commit.committed_date
        return datetime.fromtimestamp(committed_date).strftime('%Y%m%d%H%M%S')

setup(
    name="rook",
    version="0.0.1",
    packages=find_packages(),
    install_requires=['pyinotify', 'paver', 'GitPython'],
    entry_points={
        'console_scripts': [
            'rookd = rook.de:main',
            'rmake = rook.build:main',
            'rcheck = rook.repo_check:main',
            'rdeploy = rook.deploy:main',
            'rpip = rook.pip:main',
            'rprompt = rook.prompt:main'
        ],
    },
)
