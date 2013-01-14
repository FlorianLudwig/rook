import os
import sys
import tempfile
import logging

from . import sp


LOG = logging.getLogger(__name__)


def recursive_requirements(repo_path, requirements_file, done=None):
    """recursively collect requirements specified in requirements.txt within git repositories"""
    os.environ['LANG'] = 'C'

    if done is None:
        done = []

    if os.path.exists(repo_path + '/requirements.txt'):
        for requirement in open(repo_path + '/requirements.txt'):
            requirement = requirement.strip()
            # ignore comments and blank lines
            if requirement.startswith('#') or not requirement:
                continue

            # for now we only care about editable checkout
            if requirement.startswith('-e'):
                assert requirement.count('#egg=') == 1, 'specifiy #egg= name'
                assert requirement.startswith('-e git+'), 'only git is supported'
                name = requirement.split('#egg=')[-1]
                url = requirement[7:-len(name)-5]
                if name in done:
                    continue

                sub_repo_path = ensure_checkout(url, name)

                done.append(name)
                recursive_requirements(sub_repo_path, requirements_file, done)
                requirements_file.write(os.path.realpath(sub_repo_path) + '\n')
            else:
                requirements_file.write(requirement + '\n')


def ensure_checkout(url, name):
    """ensure that repository is checked out and up to date"""
    sub_repo_path = os.environ['VIRTUAL_ENV'] + '/src/' + name
    url_path_end = url[url.rfind(':'):]
    branch = 'master'
    if '@' in url_path_end:
        # users wants a specific branch
        branch = url_path_end.split('@')[-1]
        url = url[:-len(branch)-1]

    if not os.path.exists(sub_repo_path):
        sp.exe('git', 'clone', url, sub_repo_path)
        os.chdir(sub_repo_path)
        if branch != 'master':
            sp.exe('git', 'checkout', 'origin/' + branch)
            sp.exe('git', 'checkout', '-b', branch)
            sp.exe('git', 'branch', '--set-upstream', branch, 'origin/' + branch)
    else:
        os.chdir(sub_repo_path)
        sp.exe('git', 'checkout', branch)
        sp.exe('git', 'pull')
    sp.exe('git', 'checkout', branch)
    return sub_repo_path


def main():
    logging.basicConfig(level=logging.INFO)
    done = []
    #requirements_file_add = ''
    #for arg in sys.argv[1:]:
    #    name, path = arg.split('=', 1)
    #    done.append(name)
    #    requirements_file_add += path + '\n'

    if sys.argv[1:]:
        repo_path = ensure_checkout(*sys.argv[1].split('#egg='))
    else:
        repo_path = os.path.abspath('.')

    requirements_file = tempfile.NamedTemporaryFile()
    recursive_requirements(repo_path, requirements_file, done)
    requirements_file.write(repo_path + '\n')
    #requirements_file.write(requirements_file_add)
    requirements_file.flush()
    LOG.info('-- Collected requirements file --')
    LOG.info(open(requirements_file.name).read())
    LOG.info('---------------------------------')
    sp.exe('pip', 'install', '-r', requirements_file.name)

