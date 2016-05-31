# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections
import itertools

from networkx import MultiDiGraph
from parsimonious import Grammar, NodeVisitor
import six


ENTER = 'enter'
EXIT = 'exit'


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
        self.add_node(ENTER)
        self.add_node(EXIT)
        self._node_factory = itertools.count()
        if self.regex is not None:
            RegexVisitor(self).parse(self.regex)

    def add_edge(self, u, v, matcher=None):
        if not matcher:
            raise ValueError('Matcher required!')

        return super(RegularLanguageMachine, self).add_edge(
            u, v, matcher=matcher, label=str(matcher))

    def node_factory(self):
        return next(self._node_factory)

    def match_iter(self, string, index=0, node=ENTER):
        """
        Iterator on matches of string starting at the given index and node.
        """
        if node == EXIT and index == len(string):
            yield ()
        for _, next_node, edgedict in self.out_edges([node], data=True):
            matcher = edgedict['matcher']
            match_info = matcher(string, index)
            if match_info:
                new_index = index + match_info.consumed_chars
                for path in self.match_iter(string, new_index, next_node):
                    yield (match_info, ) + path

    def match(self, string, index=0, node=ENTER):
        for match_path in self.match_iter(string, index, node):
            return match_path
        return None

    def reverse_match_iter(self):
        """
        Returns a (possibly infinite) generator of paths which lead to "exit",
        and have an initial segment of path.
        """
        paths = [Path(None, ENTER, None)]
        while paths:
            new_paths = []
            for path in paths:
                node = path.node
                for _, next_node, edgedict in self.out_edges_iter([node],
                                                                  data=True):
                    new_path = Path(parent=path,
                                    node=next_node,
                                    matcher=edgedict['matcher'])
                    if new_path.node == EXIT:
                        yield new_path
                    else:
                        new_paths.append(new_path)
            paths = new_paths

    def reverse_string_iter(self):
        for path in self.reverse_match_iter():
            for string in path.matching_string_iter():
                yield string

    def add_literals(self, literals, node=ENTER):
        for literal in literals:
            node = string_literal(self, node, literal)
        self.add_edge(node, EXIT, matcher=Epsilon)

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
        return '%s' % self.literal

    def matching_string_iter(self):
        """
        Iterator of matching strings for this node.
        """
        yield self.literal


@six.python_2_unicode_compatible
class MultiCharMatcher(object):
    def __init__(self, chars):
        self.chars = frozenset(chars)

    def __call__(self, string, index):
        if string[index] in self.chars:
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __repr__(self):
        return 'MultiCharMatcher(%r)' % ''.join(self.chars)

    def __str__(self):
        s = ','.join(self.chars)
        if len(self.chars) == 1:
            s = '[%s]' % s
        return s

    def matching_string_iter(self):
        return iter(self.chars)


@six.python_2_unicode_compatible
class CharRangeMatcher(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        if self.start > self.end:
            raise ValueError('Invalid character range %s' % self)

    def __call__(self, string, index):
        if self.start <= string[index] <= self.end:
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __repr__(self):
        return 'CharRangeMatcher(%r, %r)' % (self.start, self.end)

    def __str__(self):
        return '[%s-%s]' % (self.start, self.end)

    def matching_string_iter(self):
        return (
            six.unichr(i) for i in range(ord(self.start), ord(self.end) + 1))



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


REGEX = Grammar(r'''
    re = union / concatenation
    sub_re = union / concatenation
    union = (concatenation "|")+ concatenation
    concatenation = (star / plus / literal)+
    star = literal "*"
    plus = literal "+"
    literal = group / any / chars / positive_set / negative_set
    group = "(" sub_re ")"
    escaped_metachar = "\\" ~"[.$^\\*+\[\]()|]"
    any = "."
    chars = char+
    char = escaped_metachar / non_metachar
    non_metachar = ~"[^.$^\\*+\[\]()|]"
    positive_set = "[" set_items "]"
    negative_set = "[^" set_items "]"
    set_char = ~"[^\\]]|\\]"
    set_items = "-"? (range / ~"[^\\]]")+
    range = set_char "-" set_char
''')

class RegexVisitor(NodeVisitor):
    grammar = REGEX

    def __init__(self, machine):
        self.machine = machine

    def visit_re(self, node, children):
        # Hook up the root to the enter / exit nodes of the machine.
        [[enter, exit]] = children
        self.machine.add_edge(ENTER, enter, Epsilon)
        self.machine.add_edge(exit, EXIT, Epsilon)
        return (ENTER, EXIT)

    def visit_concatenation(self, node, children):
        # ``children`` is a list of (enter, exit) nodes which need to be hooked
        # together (concatenated).
        [node_pairs] = children
        for (enter1, exit1), (enter2, exit2) in zip(node_pairs, node_pairs[1:]):
            self.machine.add_edge(exit1, enter2, matcher=Epsilon)
        enter = node_pairs[0][0]
        exit = node_pairs[-1][1]
        return (enter, exit)

    def visit_group(self, node, children):
        lparen, [(enter, exit)], rparen = children
        return (enter, exit)

    def add_disjunction(self, node_pairs):
        enter, exit = self.machine.node_factory(), self.machine.node_factory()
        for disjunct_enter, disjunct_exit in node_pairs:
            self.machine.add_edge(enter, disjunct_enter, matcher=Epsilon)
            self.machine.add_edge(disjunct_exit, exit, matcher=Epsilon)
        return (enter, exit)

    def visit_union(self, node, children):
        node_pairs = []
        # This is sort of ugly; parsimonious returns children as a list
        # of all its left disjuncts (including the | character) and the final one
        # (sans pipe character).
        disjuncts, rightmost_pair = children
        for (node_pair, superfluous_pipe) in disjuncts:
            node_pairs.append(node_pair)
        node_pairs.append(rightmost_pair)
        return self.add_disjunction(node_pairs)

    def visit_star(self, node, children):
        (enter, exit), star = children
        node = self.machine.node_factory()
        self.machine.add_edge(node, enter, matcher=Epsilon)
        self.machine.add_edge(exit, node, matcher=Epsilon)
        return (node, node)

    def visit_plus(self, node, children):
        (enter, exit), plus = children
        # Add the looping behavior as in *.
        self.visit_star(node, ((enter, exit), '*'))
        # But keep the entry node the same to guarantee at least one traversal
        # through.
        return (enter, exit)

    def visit_literal(self, node, children):
        # Why doesn't parsimonious do this for you?
        [child] = children
        return child

    def visit_chars(self, node, children):
        node1, node2 = self.machine.node_factory(), self.machine.node_factory()
        text = ''.join(children)
        self.machine.add_edge(node1, node2, matcher=LiteralMatcher(text))
        return (node1, node2)

    def visit_escaped_metachar(self, node, children):
        slash, char = children
        return char

    def visit_char(self, node, children):
        child, = children
        return child

    def visit_range(self, node, children):
        # Since a range may be inverted or not, we need to add nodes to the
        # machine for it up the stack.
        start, dash, end = children
        if len(start) == 2:
            assert start[0] == '\\', 'Bug! %s' % start
            start = start[1]
        if len(end) == 2:
            assert end[0] == '\\', 'Bug! %s' % end
            end = end[1]
        return CharRangeMatcher(start, end)

    def visit_set_items(self, node, children):
        [maybe_dash, itemsets] = children
        if maybe_dash[0]:
            itemsets.append(maybe_dash)
        return [item for item, in itemsets]

    def visit_positive_set(self, node, children):
        [lbrac, items, rbrac] = children
        raw_chars = ''.join(s for s in items if not isinstance(s, CharRangeMatcher))
        node_pairs = []
        if raw_chars:
            enter, exit = self.machine.node_factory(), self.machine.node_factory()
            self.machine.add_edge(enter, exit, matcher=MultiCharMatcher(raw_chars))
            node_pairs.append((enter, exit))
        for range_matcher in (s for s in items if isinstance(s, CharRangeMatcher)):
            enter, exit = self.machine.node_factory(), self.machine.node_factory()
            self.machine.add_edge(enter, exit, matcher=range_matcher)
            node_pairs.append((enter, exit))
        return self.add_disjunction(node_pairs)

    def generic_visit(self, node, children):
        return children or node.text
