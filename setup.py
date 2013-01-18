from setuptools import setup, find_packages

setup(
    name = "rook",
    version = "0.0.1",
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'rookd = rook.de:main',
            'rmake = rook.build:main',
            'rcheck = rook.repo_check:main',
            'rdeploy = rook.deploy:main',
            'rpip = rook.pip:main'
        ],
    },
)
