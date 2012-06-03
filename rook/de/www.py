from rw.www import RequestHandler, get

class Main(RequestHandler):
    @get('/')
    def index(self):
        self.finish('hello world')