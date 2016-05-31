# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections
import itertools

from networkx import MultiDiGraph
import six


class Path(object):

    def __init__(self, parent, node, matcher):
        self.parent = parent
        self.node = node
        self.matcher = matcher

    def as_list(self):
        path_components = []
        cur = self
        while cur is not None:
            path_components.append(cur)
            cur = cur.parent
        path_components.reverse()
        return path_components

    def __getitem__(self, *args, **kwargs):
        # This is slow since it's O(length); still useful for debugging.
        return self.as_list().__getitem__(*args, **kwargs)

    def __repr__(self):
        return 'Path(parent={parent}, node={node}, matcher={matcher})'.format(
            parent=getattr(self.parent, 'node', None),
            node=self.node,
            matcher=self.matcher
        )

    @property
    def matchers(self):
        matchers = []
        cur = self
        while cur is not None:
            matchers.append(self.matcher)
            cur = cur.parent
        matchers.reverse()
        return matchers

    @property
    def nodes(self):
        cur = self
        nodes = []
        while cur is not None:
            nodes.append(cur.node)
            cur = cur.parent
        nodes.reverse()
        return nodes

    def matching_string_iter(self):
        iterators = []
        cur = self
        while cur.parent is not None:
            iterators.append(cur.matcher.matching_string_iter())
            cur = cur.parent
        iterators.reverse()
        for substrings in itertools.product(*iterators):
            yield ''.join(substrings)


class RegularLanguageMachine(MultiDiGraph):
    def __init__(self, regex=None):
        super(RegularLanguageMachine, self).__init__()
        self.regex = regex
        self.add_node('enter')
        self.add_node('exit')
        # TODO: parse the regex.
        self._node_factory = itertools.count()

    def add_edge(self, u, v, matcher=None):
        if not matcher:
            raise ValueError('Matcher required!')

        return super(RegularLanguageMachine, self).add_edge(
            u, v, matcher=matcher, label=str(matcher))

    def node_factory(self):
        return next(self._node_factory)

    def match_iter(self, string, index=0, node='enter'):
        """
        Iterator on matches of string starting at the given index and node.
        """
        if node == 'exit' and index == len(string):
            yield ()
        for _, next_node, edgedict in self.out_edges([node], data=True):
            matcher = edgedict['matcher']
            match_info = matcher(string, index)
            if match_info:
                new_index = index + match_info.consumed_chars
                for path in self.match_iter(string, new_index, next_node):
                    yield (match_info, ) + path

    def match(self, string, index=0, node='enter'):
        for match_path in self.match_iter(string, index, node):
            return match_path
        return None

    def reverse_match_iter(self):
        """
        Returns a (possibly infinite) generator of paths which lead to "exit",
        and have an initial segment of path.
        """
        paths = [Path(None, 'enter', None)]
        while paths:
            new_paths = []
            for path in paths:
                node = path.node
                for _, next_node, edgedict in self.out_edges_iter([node],
                                                                  data=True):
                    new_path = Path(parent=path,
                                    node=next_node,
                                    matcher=edgedict['matcher'])
                    if new_path.node == 'exit':
                        yield new_path
                    else:
                        new_paths.append(new_path)
            paths = new_paths

    def reverse_string_iter(self):
        for path in self.reverse_match_iter():
            for string in path.matching_string_iter():
                yield string

    def add_literals(self, literals, node='enter'):
        for literal in literals:
            node = string_literal(self, node, literal)
        self.add_edge(node, 'exit', matcher=Epsilon)

    def _draw(self):
        """
        Hack to draw the graph and open it in preview. Sorta OS X only-ish.
        """
        from networkx.drawing.nx_agraph import write_dot
        import os

        write_dot(self, '/tmp/foo_%s.dot' % id(self))
        os.system(
            'dot -Tpng /tmp/foo_{0}.dot -o /tmp/foo_{0}.png'.format(id(self)))
        os.system('open /tmp/foo_{0}.png'.format(id(self)))


MatchInfo = collections.namedtuple(
    'MatchInfo',
    ['consumed_chars', 'matcher', 'string', 'index']
)


@six.python_2_unicode_compatible
class LiteralMatcher(object):
    def __init__(self, literal):
        self.literal = literal

    def __call__(self, string, index):
        """
        Match the string at the given index.

        :param str:
        :param index:
        :return: MatchInfo saying if the string matched, and how
        many characters are consumed; otherwise None.
        """

        # This is technically not maximally efficient, since it introduces
        # quadratic time, but in practice is probably faster than checking
        # character-by-character except for very long strings.
        if string[index:index + len(self.literal)] == self.literal:
            return MatchInfo(
                matcher=self,
                consumed_chars=len(self.literal),
                string=string,
                index=index
            )
        else:
            return None

    def __repr__(self):
        return 'LiteralMatcher(%r)' % self.literal

    def __str__(self):
        return '[%s]' % self.literal

    def matching_string_iter(self):
        """
        Iterator of matching strings for this node.
        """
        yield self.literal


@six.python_2_unicode_compatible
class _Epsilon(LiteralMatcher):
    def __init__(self):
        return super(_Epsilon, self).__init__('')

    def __repr__(self):
        return 'Epsilon()'

    def __str__(self):
        return 'ε'


Epsilon = _Epsilon()


def string_literal(machine, in_node, literal):
    node = machine.node_factory()
    machine.add_edge(in_node, node, matcher=LiteralMatcher(literal))
    return node


def star(node):
    raise NotImplementedError
