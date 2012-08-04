import os

def is_repo(dir):
    return os.path.isdir(dir + '/.git')


def get_top_folder(dir):
    if is_repo(dir):
        return dir
    elif dir == '/':
        return ''
    else:
        return get_top_folder(os.path.dirname(dir))
