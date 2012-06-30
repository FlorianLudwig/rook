from rw import www

class Repolist(www.Widget):
    def render(self):
        self.finsh(template='<b>repository list</b>')


