import os
import select
import subprocess as sp
import time
import fcntl
import sys
import json


CONFIG_PATH = os.path.abspath(os.path.expanduser('~/.config/rook/flex'))
CONFIG = {}

if not os.path.exists(CONFIG_PATH):
    print 'creating config dir', CONFIG_PATH
    os.makedirs(CONFIG_PATH)


def check_install(path):
    for executable in (path + '/bin/fcsh', path + '/bin/mxmlc', path + '/bin/compc'):
        if not os.path.exists(executable):
            raise AttributeError('Could not find or access ' + executable)

        if not os.access(executable, os.X_OK):
            raise AttributeError('Executable on  %s not set' % executable)
    proc = sp.Popen([path + '/bin/mxmlc', '-version'], stdout=sp.PIPE)
    version = proc.communicate()[0]
    version = version.replace('Version', '').strip()
    return version


def load_config():
    global CONFIG
    if os.path.exists(CONFIG_PATH + '/install'):
        CONFIG = json.load(open(CONFIG_PATH + '/install'))


def save_config():
    json.dump(CONFIG, open(CONFIG_PATH + '/install', 'w'))

load_config()


def print_download():
    print
    print 'Needing Flex SDK Version ' + FLEX_VERSION
    print 'Direct Download: http://download.macromedia.com/pub/flex/sdk/flex_sdk_4.6.zip (build 23201)'
    print 'FlexDownloads: http://www.adobe.com/devnet/flex/flex-sdk-download-all.html'
    sys.exit(1)


def fix_permissions():
    print 'try (as root):'
    print 'cd ' + config.FLEX4_PATH
    print 'find . -type d | xargs -I{} chmod o+xr "{}"'
    print 'find . | xargs -I{} chmod o+r "{}"'
    print 'chmod +x bin/*'


class ErrorParser(object):
    """Parser for Adobe Flex Compiler"""
    def __init__(self):
        self.stderr = ''

    def parse(self, stderr, stdout):
        if self.stderr != '':
            raise Exception('unknown error during build:', self.stderr)
        errors = {}
        self.stderr = stderr
        while self.stderr.strip():
            error = {}
            path = self.consume_till(':')

            if '(' in path:
                assert path.count('(') == 1
                path, ln = path.strip(')').split('(')
            else:
                ln = 0
            error['ln'] = ln
            data = self.consume_till('\n\n')
            if ':' in data:
                type, message = data.split(':', 1)
            else:
                raise AttributeError('Cant parse error, ' + data)
                print '*' * 80
                print 'Kein : gefunden'
                print repr(data)
            error['type'] = type.strip().lower()
            error['message'] = message.strip()
            if self.stderr:
                self.consume_till('\n\n')
            errors.setdefault(path, []).append(error)
        return errors

    def consume_till(self, search):
        assert search in self.stderr, '%s not in %s' % (repr(search), repr(self.stderr))
        re, self.stderr = self.stderr.split(search, 1)
        return re

error_parser = ErrorParser()


class CompileShell(object):
    """Wrapper around fcsh - the Adobe Flex SDK Compiler Shell"""
    def __init__(self, source_path, flexsdk_path):
        self.targets = {}
        self.log = ''
        fcsh = '%s/bin/fcsh' % flexsdk_path
        cmd = 'cd %s; LANG=C %s' % (source_path, fcsh)
        if not os.path.exists(fcsh):
            print 'flex install not correct.'
            print 'check config.py - FLEX4_PATH'
            print 'Maybe permissions wrong?'
            fix_permissions()
            print_download()

        if not os.access(fcsh, os.X_OK):
            print 'Permission denied'
            fix_permissions()
            print_download()
        self.fcsh = sp.Popen(cmd, shell=True,
                             stdin=sp.PIPE, stderr=sp.PIPE, stdout=sp.PIPE)

        for fd in (self.fcsh.stdout.fileno(), self.fcsh.stderr.fileno()):
            # get flags
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            # set nonblocking
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.read()

    def read(self):
        stdout = ''
        stderr = ''
        combined = ''
        while not stdout.endswith('(fcsh) '):
            ready = select.select([self.fcsh.stdout, self.fcsh.stderr], [], [])
            # wait for a 50ms to not read byte by byte
            time.sleep(0.05)
            if self.fcsh.stdout in ready[0]:
                data = self.fcsh.stdout.read()
                stdout += data
                combined += data
            if self.fcsh.stderr in ready[0]:
                data = self.fcsh.stderr.read()
                stderr += data
                combined += data

        self.log += combined
        return stdout, stderr

    def build(self, cmd, clear):
        print 'build', cmd
        if clear:
            self.fcsh.stdin.write(cmd + '\n')
            stdout, stderr = self.read()

            t_id = None
            if len(stdout.split('fcsh: Assigned ')) > 1:
                    t_id = stdout.split('fcsh: Assigned ')[1].split(' ')[0]
            else:
                try:
                    t_id = stdout.split('fcsh: ')[1].split(' ')[0]
                except:
                    print 'WARNING!!!!!!!!!! fcsh: Assigned " not found in:\n' + stdout
            if t_id:
                self.fcsh.stdin.write('clear %s\n' % t_id)
                self.read(self)
            return stdout, stderr
        else:
            if not cmd in self.targets:
                self.fcsh.stdin.write(cmd + '\n')
                stdout, stderr = self.read()
                print '----------'
                print self.log
                print
                print
                if len(stdout.split('fcsh: Assigned ')) > 1:
                    t_id = stdout.split('fcsh: Assigned ')[1].split(' ')[0]
                else:
                    try:
                        t_id = stdout.split('fcsh: ')[1].split(' ')[0]
                    except:
                        raise Exception('"fcsh: Assigned " not found in:\n' + stdout)
                self.targets[cmd] = t_id

                # GC
                #if len(self.targets) > 10:
                #    for t in self.targets.keys()[10:]:
                #        self.fcsh.stdin.write('clear %s\n' % self.targets[t])
                #        print 'removing %s from cache' % t
                #        del self.targets[t]
                return CompileShellJob(self, cmd, t_id,
                                       error_parser.parse(stderr, stdout))

            else:
                self.fcsh.stdin.write('compile %s\n' % self.targets[cmd])
                stdout, stderr = self.read()
                if '-d' in sys.argv:
                    print 'fcsh:'
                    print self.logg
                    print
                return error_parser.parse(stderr, stdout)


class CompileShellJob(object):
    def __init__(self, shell, cmd, job_id, last_error):
        self.shell = shell
        self.cmd = cmd
        self.job_id = job_id
        self.last_error = last_error

    def __del__(self):
        self.shell.fcsh.stdin.write('clear %s\n' % self.job_id)
        self.shell.read()
        del self.shell.targets[self.cmd]


class SDK(object):
    """Represents a SDK in a specific version"""
    def __init__(self, version, source_path=None, fcsh=False):
        if source_path is None:
            source_path = '.'
        source_path = os.path.abspath(source_path)
        if not version in CONFIG:
            msg = 'Version "%s" not configured. Avialable: %s'
            msg = msg % (version, ', '.join(repr(v) for v in CONFIG))
            raise AttributeError(msg)
        self.path = CONFIG[version]
        self.source_path = source_path
        check_install(self.path)
        self.fcsh = CompileShell(source_path, self.path) if fcsh else False

    def swc(self, name, src='src', requires=[], external=None, output=None, 
            config=None, args=None, config_append=None):
        lib_dir = os.environ['VIRTUAL_ENV'] + '/lib/swc/'
        if not args:
            args = []
        args += ['-include-sources', src]
        if not output:
            output = lib_dir + name + '.swc'
        self.run('compc', src=src, requires=requires, external=external,
                 output=output, args=args, config=config, 
                 config_append=config_append)

    def swf(self, name, target, src='src', requires=[], external=None, 
            output=None, args=None, config=None, config_append=None):
        if not output:
            output = 'bin/' + name + '.swf'
        self.run('mxmlc', src=src, requires=requires, external=external, 
                 output=output, target=target, args=args, config=config,
                 config_append=config_append)

    def run(self, cmd, src='src', requires=[], external=None,
            output=None, target=None, args=None, config=None,
            config_append=None):
        lib_dir = os.environ['VIRTUAL_ENV'] + '/lib/swc/'
        if not os.path.exists(lib_dir):
            os.makedirs(lib_dir)
        if args is None:
            args = []
        if external:
            for ext in external:
                f = self.source_path+'/lib/'+ext+'.swc'
                if not os.path.exists(f):
                    f = lib_dir+ext+'.swc'
                    if not os.path.exists(f):
                        raise Exception('lib %s.swc not found' % ext)
                args.extend(['-external-library-path+=%s' % f])
        for req in requires:
            args.extend(['-compiler.include-libraries+=%s%s.swc' % (lib_dir, req)])
        if target:
            args.insert(0, target)
        # override default config from flex framework
        if config:
            if not os.path.exists(config):
                raise AttributeError('file not found "' + config + '"')
            args.extend(['-load-config=%s' % config])
        # append parameter to config
        if config_append:
            if isinstance(config_append, (str, unicode)):
                config_append = [config_append]
            for cfg in config_append:
                if not os.path.exists(cfg):
                    raise AttributeError('file not found "' + cfg + '"')
                args.extend(['-load-config+=%s' % cfg])
        args.extend(['-source-path', src,
                     '-output', output,
                     '-optimize'])
        print 'compiling', ' '.join([self.path + '/bin/' + cmd] + list(args))
        if self.fcsh:
            print self.fcsh.build(cmd + ' ' + ' '.join(args), False)
        else:
            proc = sp.Popen([self.path + '/bin/' + cmd] + list(args))
            proc.wait()


