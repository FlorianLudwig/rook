#! -*- coding: utf-8 -*-
import os
import time
import shutil


last_notification = None
try:
    from gi.repository import Notify, GLib
except ImportError:
    print 'Couldn\'t  "from gi.repository import Notify, GLib"'
    Notify = None


if Notify is None or not Notify.init("Leijuna Build Deamon"):
    print 'Couldn\'t init gnome notify'
    Notify = None



def show_notification(msg, details='', urgent=False):
    try:
        global last_notification
        clear_notification()
        n = Notify.Notification.new(msg, details, None)
        n.set_hint("transient", GLib.Variant.new_boolean(True))
        n.set_urgency(Notify.Urgency.CRITICAL if urgent else Notify.Urgency.NORMAL)
        n.show()
        last_notification = n
    except:
        print 'Could not display notification', msg


def clear_notification():
    if last_notification:
        last_notification.close()


def _ignore(dirname, basename):
    """returns true for pathes that should get ignored by all parts of the build system

    Like temp files"""
    return basename.startswith('.') or basename.endswith('~') or basename.endswith('.swp') \
           or basename.endswith('.tmp') \
           or os.path.basename(dirname).startswith('.')


class Environment(object):
    def __init__(self, source_dir, build_dir='_build'):
        self.sources = {}
        self.destination = {}
        self.todo = set()
        self.done = set()
        self.source_dir = os.path.normpath(os.path.abspath(source_dir))
        self.build_dir = os.path.normpath(os.path.abspath(build_dir))

    def build(self):
        errors = {}
        if Notify:
            show_notification('Leijuna compiling ...')

        self.before_build(errors)
        start = t = time.time()
        while self.todo:
            error = self.todo.pop()()
        print '%5.2fs needed for executing tasks' % (time.time() - t)
        self.after_build(errors)

        build_time = time.time() - start
        print '-------------------------------'
        print '%5.2fs needed in sum' % build_time
        print

        if Notify:
            if errors:
                msg = u'✖ Leijuna build failed'
                count_err = sum([len(x) for x in errors.values()])
                count_files = len(errors)
                details = '%i ' % count_err
                details += 'error' if count_err == 1 else 'errors'
                details += ' in %i ' % count_files
                details += 'file' if count_files == 1 else 'files'
                details += '. '
            else:
                msg = u'✔ Leijuna build successful. '
                details = ''
            details += 'Needed %.1fs' % build_time
            show_notification(msg, details, bool(errors))
        return errors

    def before_build(self, errors):
        """Extend build process by subclassing and overwriting this"""

    def after_build(self, errors):
        """Extend build process by subclassing and overwriting this"""

    def generate_tasks(self, path=None, basename=None):
        if path is None:
            path = self.source_dir
        if basename is None:
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
        else:
            dirname = path
            path = dirname + '/' + basename

        if _ignore(dirname, basename):
            return

        if  os.path.islink(path):
            SymlinkTask(self, path)
        elif os.path.isdir(path):
            for sub in os.listdir(path):
                if not _ignore(path, sub):
                    self.generate_tasks(path, sub)
        elif '_.' in basename:
            TemplateTask(self, path)
        else:
            CopyTask(self, path)

    def deamon(self):
        import tornado.ioloop
        import rw
        import pyinotify

        rw.DEBUG = True
        rw.setup('flexsdk', port=45473)
        setup()

        class Identity(pyinotify.ProcessEvent):
            def process_default(iself, event):
                #dirname = os.path.dirname(event.pathname)[len(BASE_PATH):].strip('/')
                dirname = os.path.dirname(event.pathname).rstrip('/')
                basename = os.path.basename(event.pathname)
                path = dirname + '/' + basename

                if _ignore(dirname, basename):
                    return
                print '-> changed', dirname, basename

                if event.mask & (pyinotify.IN_MODIFY | pyinotify.IN_MOVED_TO | pyinotify.IN_CLOSE_WRITE):
                    print 'new'
                    if path in self.sources:
                        self.todo.update(self.sources[path])
                    else:
                        print 'genererating new', dirname, basename
                        self.generate_tasks(dirname, basename)
                elif event.mask & pyinotify.IN_DELETE:
                    print 'delete'
                    for task in self.sources[path].copy():
                        task.delete()
                    self.todo.add(DoNothingButRebuild)
                else:
                    print 'ignoring change because of event mask'

        wm = pyinotify.WatchManager()
        # Stats is a subclass of ProcessEvent provided by pyinotify
        # for computing basics statistics.
        notifier = pyinotify.Notifier(wm, default_proc_fun=Identity())

        events = pyinotify.IN_DELETE \
                 | pyinotify.IN_MODIFY \
                 | pyinotify.IN_CREATE \
                 | pyinotify.IN_MOVED_TO \
                 | pyinotify.IN_MOVE_SELF \
                 | pyinotify.IN_CLOSE_WRITE
        wm.add_watch('src', events, rec=True, auto_add=True)

        def process_inotify_events():
            if notifier.check_events(50):
                notifier.read_events()
            notifier.process_events()
            if self.todo:
                self.build()

        check = tornado.ioloop.PeriodicCallback(callback=process_inotify_events, callback_time=150)
        check.start()
        # tornado.autoreload uses a 0.5 second timeout, we want to run after it
        tornado.ioloop.IOLoop.instance().add_timeout(time.time() + 0.51, self.build)
        rw.start()


class Task(object):
    """Base class for tasks. Subclasses must implement __call__"""
    def __init__(self, env, src, dst=None):
        self.env = env
        src = os.path.normpath(os.path.abspath(src))
        self.src = src
        if not dst:
            self.dst = env.build_dir + '/' + src[len(env.source_dir):]
        else:
            self.dst = dst
        self.dst = os.path.normpath(self.dst)
        self.env.sources.setdefault(src, set()).add(self)
        self.env.destination.setdefault(self.dst, set()).add(self)
        self.env.todo.add(self)

    def delete(self):
        self.env.sources[self.src].remove(self)
        self.env.destination[self.dst].remove(self)
        if os.path.exists(self.dst):
            os.unlink(self.dst)


class DoNothingButRebuild(Task):
    def __init__(self):
        pass



class CopyTask(Task):
    def __call__(self):
        dirname = os.path.dirname(self.dst)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        # there is nothing to copy
        # TODO: find better way to start the compiler again without having
        # a CopyTask when the source file changes!
        if self.src != self.dst:
            try:
                shutil.copyfile(self.src, self.dst)
            except Exception, e:
                if os.path.exists(self.src):
                    raise e
                self.delete()


class SymlinkTask(Task):
    def __call__(self):
        dirname = os.path.dirname(self.dst)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if os.path.exists(self.dst):
            os.unlink(self.dst)
        os.symlink(os.path.realpath(self.src), self.dst)


class TemplateTask(Task):
    def __init__(self, env, src):
        dot = src.rfind('.')
        suffix = src[dot:]
        super(TemplateTask, self).__init__(env, src)
        self.dst = self.env.build_dir + src[3:dot-1] + suffix

    def __call__(self):
        # print 'template', self.src, '->', self.dst
        pass # XXX


_setup = False
def setup():
    global _setup
    if _setup:
        return
    import tornado.autoreload
    tornado.autoreload.add_reload_hook(clear_notification)
    _setup = True



def main():
    print 'rmake'
    if os.path.exists('build.py'):
        print __import__('build')

