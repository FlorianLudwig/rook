from rw import www

class Repolist(www.Widget):
    def render(self):
        # get info about accessable repository
        # ssh git@leijuna.de info
        
        # list of checked out repositories
        os.listdir(os.environ['VIRTUAL_ENV'] + '/src/')
        
        self.finsh(template='<b>repository list</b>')


