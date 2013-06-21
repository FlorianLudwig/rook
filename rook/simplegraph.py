# TODO: merge with graphviz
import os
import tempfile
import subprocess


class Node(object):
    def __init__(self, title, name=None, shape='ellipse'):
        self.title = title
        self.name = name if not name is None else 'Node%i' % id(self)
        self.style = {'shape': shape}

    def __unicode__(self):
        style = {}
        style.update(self.style)
        style['label'] = self.title
        style = ','.join('{}="{}"'.format(k, v) for k, v in style.items())
        return u'    %s [%s];\n' % (self.name, style)


class Edge(object):
    left = None
    right = None
    style = None

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def to_tuple(self):
        return (self.left, self.right)

    def __eq__(self, o):
        return self.to_tuple() == o.to_tuple()

    def __unicode__(self):
        style = ''
        if self.style:
            style = ' ' + self.style
        return u'    %s -> %s%s\n' % (self.left.name, self.right.name, style)


class Graph(object):
    def __init__(self, name=''):
        self.name = name
        self.edges = set()
        self.nodes = set()

    def __unicode__(self):
        write = 'digraph "%s" {\n' % self.name
        write += '    labelloc="b";\n'
        write += '    peripheries=0;\n'
        write += '    ranksep=0.50;\n'
        write += '    edge  [fontsize=10];\n'
        write += '    node  [fontsize=10];\n'
        #write += '    bgcolor=transparent;\n'
        #write += '    edge [arrowsize=1, color=black];\n'
        #write += '    graph [rankdir=LR]\n'
        write += ''.join(unicode(node) for node in self.nodes)
        write += ''.join(unicode(edge) for edge in self.edges)
        write += '}'
        return write

    def create_edge(self, *args, **kwargs):
        ret = Edge(*args, **kwargs)
        self.edges.add(ret)
        return ret

    def create_node(self, *args, **kwargs):
        ret =  Node(*args, **kwargs)
        self.nodes.add(ret)
        return ret

    def render(self, path, names=None, rewrite=False, areamap=False):
        '''create pngs from dot-files'''
        fd, name = tempfile.mkstemp()
        os.write(fd, unicode(self).encode('utf-8'))
        cmd = ['dot', name, '-Tpng', '-o%s' % path]
        if areamap:
            cmd += ['-Tcmapx', '-o%s.map' % path]
        print cmd
        subprocess.call(cmd)
        os.unlink(name)


if __name__ == '__main__':
    g = Graph()
    root = g.create_node('print')
    g.create_edge(root, g.create_node('Hello'))

    w = g.create_node('World')
    g.create_edge(root, w)
    g.render('hello_world')
