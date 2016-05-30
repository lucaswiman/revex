# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import abc
import collections
import itertools
import sys

from networkx import MultiDiGraph
import six


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
        for new_node, edgedict in self[node].items():
            for edge in edgedict.values():
                matcher = edge['matcher']
                match_info = matcher(string, index)
                if match_info:
                    new_index = index + match_info.consumed_chars
                    for path in self.match_iter(string, new_index, new_node):
                        yield (match_info, ) + path

    def match(self, string, index=0, node='enter'):
        for match_path in self.match_iter(string, index, node):
            return match_path
        return None

    def add_literals(self, literals, node='enter'):
        for literal in literals:
            node = string_literal(self, node, literal)
        self.add_edge(node, 'exit', matcher=EpsilonMatcher())

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


class Matcher(object):

    def __call(self, str, index):
        """
        Match the string at the given index.

        :param str:
        :param index:
        :return: MatchInfo saying if the string matched, and how
        many characters are consumed; otherwise None.
        """

    def reverse_match_iter(self):
        """
        :return: iterator on strings that would match this node.
        """


@six.python_2_unicode_compatible
class EpsilonMatcher(Matcher):
    def __call__(self, string, index):
        return MatchInfo(
            matcher=self,
            consumed_chars=0,
            string=string,
            index=index
        )

    def __repr__(self):
        return 'EpsilonMatcher()'

    def __str__(self):
        return 'ε'

    def reverse_match_iter(self):
        yield ''



@six.python_2_unicode_compatible
class LiteralMatcher(Matcher):
    def __init__(self, literal):
        self.literal = literal

    def __call__(self, string, index):
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

    def reverse_match_iter(self):
        # This will only match the given literal, so just yield that.
        yield self.literal


def string_literal(machine, in_node, literal):
    node = machine.node_factory()
    machine.add_edge(in_node, node, matcher=LiteralMatcher(literal))
    return node


def star(node):
    raise NotImplementedError
