from __future__ import absolute_import

from rw.www import RequestHandler, get, post
from . import flex


class Main(RequestHandler):
    @get('/')
    def index(self):
        if 'messages' not in self:
            self['messages'] = []
        for version, path in flex.CONFIG.items():
            try:
                real_version = flex.check_install(path)
            except AttributeError, e:
                self['path'] = path
                self['error'] = e.message
                self.finish(template='error.html')
            if version != real_version:
                msg = '%s was configed as version %s but is %s, config updated.'
                msg = msg % (path, version, real_version)
                self['messages'].append(msg)
                del flex.CONFIG[version]
                flex.CONFIG[real_version] = path
                flex.save_config()
        self['flex'] = flex.CONFIG
        print flex.CONFIG
        self.finish(template='index.html')

    @post('/')
    def add_flex(self):
        path = self.get_argument('path')
        try:
            version = flex.check_install(path)
        except AttributeError, e:
            self['path'] = path
            self['error'] = e.message
            self.finish(template='error.html')
        flex.CONFIG[version] = path
        flex.save_config()
        self['messages'] = ['Flex %s at %s added' % (version, path)]
        self.index()


    @get('/repo')
    def repo(self):
        self['list'] = self
        self.finish(template='repo.html')