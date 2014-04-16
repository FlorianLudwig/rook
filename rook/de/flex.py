import os
import select
import subprocess as sp
import time
import fcntl
import sys
import json
import logging
import jinja2
import tempfile
import re

logger = logging.getLogger('rook.de.flex')
logger.setLevel(logging.DEBUG)
sh = logging.StreamHandler()
logger.addHandler(sh)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_PATH, 'templates')
TESTRUNNER_TPL = os.path.join(TEMPLATE_PATH, 'FlexUnitRunner.mxml')
CONFIG_PATH = os.path.abspath(os.path.expanduser('~/.config/rook/flex'))
ROOK_PATH = os.path.abspath(os.path.expanduser('~/.rook/flex'))
CONFIG = {}

if not os.path.exists(CONFIG_PATH):
    logger.info('creating config dir {}'.format(CONFIG_PATH))
    os.makedirs(CONFIG_PATH)


def check_install(path):
    """
    test, if the mxml-compiler can be found in the given flex-sdk direcotry
    """
    for executable in (os.path.join(path, 'bin', 'fcsh'),
                       os.path.join(path, 'bin', 'mxmlc'),
                       os.path.join(path, 'bin', 'compc')):
        if not os.path.exists(executable):
            raise AttributeError('Could not find or access ' + executable)

        if not os.access(executable, os.X_OK):
            raise AttributeError('Executable on  %s not set' % executable)
    proc = sp.Popen([os.path.join(path, 'bin', 'mxmlc'), '-version'], stdout=sp.PIPE)
    version = proc.communicate()[0]
    version = version.replace('Version', '').strip()
    return version


def load_config():
    """
    load config from file (~/.config/rook/flex/install)
    """
    global CONFIG
    if os.path.exists(CONFIG_PATH + '/install'):
        CONFIG = json.load(open(CONFIG_PATH + '/install'))


def save_config():
    """
    save config from file (~/.config/rook/flex/install)
    """
    json.dump(CONFIG, open(CONFIG_PATH + '/install', 'w'))

load_config()


class ErrorParser(object):
    """Parser for Adobe Flex Compiler"""
    def __init__(self):
        self.stderr = ''

    def parse(self, stderr, stdout):
        if self.stderr != '':
            raise Exception('unknown error during build:', self.stderr +
                            '\nstdout:\n' + stdout)
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
                err_type, message = data.split(':', 1)
            else:
                raise AttributeError('Cant parse error, ' + data)
            error['type'] = err_type.strip().lower()
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
            logger.error('flex compile shell not found, check your flex path')

        if not os.access(fcsh, os.X_OK):
            logger.error('Permission denied')

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
        """
        call fcsh and execute build
        """
        if clear:
            self.fcsh.stdin.write(cmd + '\n')
            stdout, stderr = self.read()

            t_id = None
            if len(stdout.split('fcsh: Assigned ')) > 1:
                    t_id = stdout.split('fcsh: Assigned ')[1].split(' ')[0]
            else:
                try:
                    t_id = stdout.split('fcsh: ')[1].split(' ')[0]
                except IndexError:
                    logger.warn('fcsh: Assigned " not found in:\n' + stdout)
            if t_id:
                self.fcsh.stdin.write('clear %s\n' % t_id)
                self.read()
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
                    print self.log
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

    def __nonzero__(self):
        # we want to write code like:
        # if sdk.swc(...):
        #     ...
        # so a CompileShellJob evaluates to True if it successed and False
        # if there were any compile errors
        return bool(self.last_error)


class SDK(object):
    """Represents a SDK in a specific version"""
    def __init__(self, version='current', source_path=None, fcsh=False):
        self.log = []
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

    def swc(self, name, src='src', requires=None, external=None, libs=None,
            output=None, config=None, args=None, config_append=None, log=True):
        lib_dir = os.environ['VIRTUAL_ENV'] + '/lib/swc/'
        if not args:
            args = []
        args.append('-include-sources')
        if isinstance(src, basestring):
            src = [src]
        args.extend(src)
        if not output:
            output = lib_dir + name + '.swc'
        cmd, args = self.create_args(
            'compc', src=src, requires=requires, external=external, libs=libs,
            output=output, args=args, config=config,
            config_append=config_append)
        t = time.time()
        run = self.run(cmd, args)
        if log:
            self.log.append({
                'type': 'compile ' + output,
                'time': time.time() - t
            })
        return run

    def swf(self, name, target, src='src', requires=None, libs=None,
            external=None, output=None, args=None,
            config=None, config_append=None,
            log=True):
        if not output:
            output = 'bin/' + name + '.swf'
        cmd, args = self.create_args(
            'mxmlc', src=src, requires=requires, external=external, libs=libs,
            output=output, target=target, args=args, config=config,
            config_append=config_append)
        t = time.time()
        run = self.run(cmd, args)
        if log:
            self.log.append({
                'type': 'compile ' + output,
                'time': time.time() - t
            })
        return run

    def print_stats(self):
        print '-'*20
        for stat in self.log:
            print '%7.2fs needed to %s.' % (stat['time'], stat['type'])
        print '-'*20
        print '%7.2fs needed for all tasks.' % \
              sum([s['time'] for s in self.log])

    def lib_path(self, name):
        """
        get file path from library name (take a look in local lib or libs first
        and if it is not there in the global dir)
        """
        if os.path.exists(name):
            return name
        lib_dir = os.environ['VIRTUAL_ENV'] + '/lib/swc/'
        f = self.source_path + '/lib/' + name + '.swc'
        if os.path.exists(f):
            return f
        f = self.source_path + '/libs/' + name + '.swc'
        if os.path.exists(f):
            return f
        f = lib_dir+name+'.swc'
        if os.path.exists(f):
            return f
        raise Exception('lib %s.swc not found' % name)

    def create_args(self, cmd='mxmlc', src='src', requires=None, external=None,
                    output=None, target=None, args=None, config=None,
                    config_append=None, libs=None):
        """create parameter for ActionScript 3 compiler"""
        lib_dir = os.environ['VIRTUAL_ENV'] + '/lib/swc/'
        if not os.path.exists(lib_dir):
            os.makedirs(lib_dir)
        if args is None:
            args = []
        if external:
            for ext in external:
                args.extend([
                    '-external-library-path+=%s' % self.lib_path(ext)])
        if requires:
            for req in requires:
                args.extend([
                    '-compiler.include-libraries+=%s' % self.lib_path(req)])
        if libs:
            for lib in libs:
                args.extend(['-library-path+=%s' % self.lib_path(lib)])
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
                args.insert(0, '-load-config+=%s' % cfg)
        args.append('-source-path')
        if isinstance(src, basestring):
            src = [src]
        args.extend(src)
        args.extend(['-output', output])
        return cmd, args


    def doc(self, src='src', libs=None, args=None, ext_src=None, log=True):
        if ext_src:
            # required external sources that should not appear in the
            # documentation we just build a swc for that
            tmp_dir = tempfile.mkdtemp('test_build')
            doc_swc = os.path.join(tmp_dir, 'Documentation')
            self.swc('Documentation', src=ext_src, libs=libs, 
                     output=doc_swc, log=True)
            libs.append(doc_swc)
        cmd, args = self.create_args_doc(src=src, libs=libs, args=args)
        t = time.time()
        run = self.run(cmd, args)
        if log:
            self.log.append({
                'type': 'asdoc',
                'time': time.time() - t
            })
        return run


    def create_args_doc(self, cmd='asdoc', src='src', libs=None, args=None):
        """
        generate ActionScript documentation with asdoc
        """
        if args is None:
            args = []
        if not src:
            raise AttributeError('src not set')
        elif isinstance(src, basestring):
            src = [src]
        args.append('-source-path')
        if isinstance(src, basestring):
            src = [src]
        args.extend(src)
        args.append('-doc-sources')
        args.extend(src)
        
        if libs:
            for lib in libs:
                args.extend(['-library-path+=%s' % self.lib_path(lib)])
        return cmd, args


    def run(self, cmd='mxmlc', args=None):
        if args is None:
            args = []
        print args
        logger.info('compiling: ' +
                    ' '.join([self.path + '/bin/' + cmd] + list(args)))
        if self.fcsh:
            return self.fcsh.build(cmd + ' ' + ' '.join(args), False)
        else:
            proc = sp.Popen([self.path + '/bin/' + cmd] + list(args))
            return proc.wait() == 0

    def test(self, command=None, test_dir='test/', src='src/', requires=None,
             external=None, config=None, args=None, log=True, libs=None,
             headless=True):
        t = time.time()
        tests = []
        # generate test runner file
        for root, sub, files in os.walk(test_dir):
            for file_name in files:
                filename = os.path.join(root, file_name)
                content = open(filename, 'r').read()
                test_file = {}
                # get package name
                m = re.search('package[ ]+(?P<pkg_name>[0-9a-zA-Z\._]*)', content)
                test_file['pkg_name'] = m.group('pkg_name')
                # get class name
                m = re.search('class[ ]+(?P<cls_name>[0-9a-zA-Z\._]*)', content)
                test_file['cls_name'] = m.group('cls_name')
                tests.append(test_file)

        tmp_dir = tempfile.mkdtemp('test_build')
        content = jinja2.Template(file(TESTRUNNER_TPL, 'r').read()).render(tests=tests)
        flex_unit_runner = os.path.join(tmp_dir, 'FlexUnitRunner.mxml')
        file(flex_unit_runner, 'w').write(content.encode('utf-8'))

        # compile test runner
        out = os.path.join(tmp_dir, 'out')
        os.makedirs(out)
        if isinstance(src, basestring):
            src = [src]
        if isinstance(test_dir, basestring):
            test_dir = [test_dir]
        if not args:
            args = []
        if headless:
            args += ['-headless-server=true']
        self.swf(
            name='FlexUnitRunner',
            output=os.path.join(out, 'FlexUnitRunner.swf'),
            target=flex_unit_runner,
            src=test_dir+src,
            external=external,
            requires=requires,
            args=args,
            config=config,
            libs=libs,
            log=False)
        if log:
            self.log.append({
                'type': 'testing in folder {}'.format(test_dir),
                'time': time.time() - t
            })
        if not command:
            command = '/opt/flashplayerdebugger'
        pass
