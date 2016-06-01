# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections
import itertools

from networkx import MultiDiGraph
from parsimonious import Grammar, NodeVisitor
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


_node_factory = itertools.count()

class RegularLanguageMachine(MultiDiGraph):
    def __init__(self, regex=None, node_factory=_node_factory, enter=None, exit=None):
        super(RegularLanguageMachine, self).__init__()
        self._node_factory = node_factory
        self.regex = regex
        if self.regex is not None:
            machine = RegexVisitor().parse(self.regex)
            self.enter = machine.enter
            self.exit = machine.exit
            self.add_edges_from(machine.edges(data=True, keys=True))
        else:
            self.enter = self.node_factory() if enter is None else enter
            self.exit = self.node_factory() if exit is None else exit
        self.add_node(self.enter)
        self.add_node(self.exit)

    def add_edge(self, u, v, key=None, attr_dict=None, **kwargs):
        # Note that the order of key and attr_dict are important, since networkx
        # uses them as positional arguments in add_edges_from().
        attr_dict = attr_dict or {}
        attr_dict.update(kwargs)
        matcher = attr_dict.get('matcher')
        if not attr_dict.get('matcher'):
            raise ValueError('Matcher required!')
        attr_dict['label'] = str(matcher)
        return super(RegularLanguageMachine, self).add_edge(
            u, v,
            key=key,
            attr_dict=attr_dict)

    def __lshift__(self, other):
        """
        Returns a new version of self and other consisting of the union of
        the edges / nodes and the entrance & nodes of self.
        """
        machine = RegularLanguageMachine(
            node_factory=self._node_factory,
            enter=self.enter,
            exit=self.exit,
        )
        machine.add_edges_from(self.edges(data=True, keys=True))
        machine.add_edges_from(other.edges(data=True, keys=True))
        return machine

    def node_factory(self):
        return next(self._node_factory)

    def match_iter(self, string, index=0, node=None):
        """
        Iterator on matches of string starting at the given index and node.
        """
        node = self.enter if node is None else node
        if node == self.exit and index == len(string):
            yield ()
        for _, next_node, edgedict in self.out_edges([node], data=True):
            matcher = edgedict['matcher']
            match_info = matcher(string, index)
            if match_info:
                new_index = index + match_info.consumed_chars
                for path in self.match_iter(string, new_index, next_node):
                    yield (match_info, ) + path

    def match(self, string, index=0, node=None):
        node = self.enter if node is None else node
        for match_path in self.match_iter(string, index, node):
            return match_path
        return None

    def reverse_match_iter(self):
        """
        Returns a (possibly infinite) generator of paths which lead to "exit",
        and have an initial segment of path.
        """
        paths = [Path(None, self.enter, None)]
        while paths:
            new_paths = []
            for path in paths:
                node = path.node
                for _, next_node, edgedict in self.out_edges_iter([node],
                                                                  data=True):
                    new_path = Path(parent=path,
                                    node=next_node,
                                    matcher=edgedict['matcher'])
                    if new_path.node == self.exit:
                        yield new_path
                    else:
                        new_paths.append(new_path)
            paths = new_paths

    def reverse_string_iter(self):
        for path in self.reverse_match_iter():
            for string in path.matching_string_iter():
                yield string

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

    def __init__(self):
        self.node_factory = itertools.count()

    def visit_re(self, node, children):
        # Hook up the root to the enter / exit nodes of the machine.
        [machine] = children
        return machine

    def visit_concatenation(self, node, children):
        # ``children`` is a list of (enter, exit) nodes which need to be hooked
        # together (concatenated).
        sub_machines = [machine for [machine] in children]
        machine = RegularLanguageMachine(node_factory=self.node_factory)
        last = machine.enter
        for sub_machine in sub_machines:
            machine = machine << sub_machine
            machine.add_edge(last, sub_machine.enter, matcher=Epsilon)
            last = sub_machine.exit
        machine.add_edge(last, machine.exit, matcher=Epsilon)
        return machine

    def visit_group(self, node, children):
        lparen, [machine], rparen = children
        return machine

    def add_disjunction(self, disjuncts):
        machine = RegularLanguageMachine(node_factory=self.node_factory)
        for disjunct in disjuncts:
            machine = machine << disjunct
            machine.add_edge(machine.enter, disjunct.enter, matcher=Epsilon)
            machine.add_edge(disjunct.exit, machine.exit, matcher=Epsilon)
        return machine

    def visit_union(self, node, children):
        disjuncts = []
        # This is sort of ugly; parsimonious returns children as a list
        # of all its left disjuncts (including the | character) and the final one
        # (sans pipe character).
        disjuncts_and_pipes, last_disjunct = children
        for (disjunct, superfluous_pipe) in disjuncts_and_pipes:
            disjuncts.append(disjunct)
        disjuncts.append(last_disjunct)
        return self.add_disjunction(disjuncts)

    def visit_star(self, node, children):
        machine, star_char = children
        star = RegularLanguageMachine(node_factory=self.node_factory) << machine
        star_node = star.node_factory()
        star.add_edge(star.enter, star_node, matcher=Epsilon)
        star.add_edge(star_node, star.exit, matcher=Epsilon)
        star.add_edge(star_node, machine.enter, matcher=Epsilon)
        star.add_edge(machine.exit, star_node, matcher=Epsilon)
        return star

    def visit_plus(self, node, children):
        machine, plus_char = children
        plus = RegularLanguageMachine(node_factory=self.node_factory) << machine
        plus_node = plus.node_factory()
        plus.add_edge(plus.enter, machine.enter, matcher=Epsilon)
        plus.add_edge(machine.exit, plus_node, matcher=Epsilon)
        plus.add_edge(plus_node, machine.enter, matcher=Epsilon)
        plus.add_edge(plus_node, plus.exit, matcher=Epsilon)
        return plus

    def visit_literal(self, node, children):
        # Why doesn't parsimonious do this for you?
        [child] = children
        return child

    def visit_chars(self, node, children):
        text = ''.join(children)
        machine = RegularLanguageMachine(node_factory=self.node_factory)
        machine.add_edge(machine.enter, machine.exit, matcher=LiteralMatcher(text))
        return machine

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
        if maybe_dash:
            itemsets.append(maybe_dash)
        return [item for item, in itemsets]

    def visit_positive_set(self, node, children):
        [lbrac, items, rbrac] = children
        raw_chars = ''.join(s for s in items if not isinstance(s, CharRangeMatcher))
        machines = []
        if raw_chars:
            machine = RegularLanguageMachine(node_factory=self.node_factory)
            machine.add_edge(machine.enter, machine.exit,
                             matcher=MultiCharMatcher(raw_chars))
            machines.append(machine)
        for range_matcher in (s for s in items if isinstance(s, CharRangeMatcher)):
            machine = RegularLanguageMachine(node_factory=self.node_factory)
            machine.add_edge(machine.enter, machine.exit, matcher=range_matcher)
            machines.append(machine)
        return self.add_disjunction(machines)

    def generic_visit(self, node, children):
        return children or node.text
