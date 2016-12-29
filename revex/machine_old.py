# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import collections
import itertools
import operator
import random

from functools import reduce
from uuid import uuid1

from networkx import MultiDiGraph, relabel_nodes
from parsimonious import Grammar, NodeVisitor
import six
from six.moves import range
from six import unichr as chr


# TODO: properly handle unicode. 9 and 512 were chosen arbitrarily.
UNICODE_CHARS = [chr(i) for i in range(9, 512)]


class Walk(object):

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
        return 'Walk(parent={parent}, node={node}, matcher={matcher})'.format(
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

    def random_string(self):
        strings = []
        cur = self
        while cur.parent is not None:
            strings.append(cur.matcher.random_matching_string())
            cur = cur.parent
        return ''.join(reversed(strings))

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
    def __init__(self, regex=None, node_factory=None, enter=None, exit=None):
        super(RegularLanguageMachine, self).__init__()
        self._node_factory = node_factory or itertools.count()
        self.regex = regex
        if self.regex is not None:
            machine = RegexVisitor().parse(self.regex)
            self.enter = machine.enter
            self.exit = machine.exit
            self.add_edges_from(machine.edges(data=True, keys=True))
            relabel_nodes(self, {self.enter: 'enter', self.exit: 'exit'}, copy=False)
            self.enter = 'enter'
            self.exit = 'exit'
        else:
            self.enter = self.node_factory() if enter is None else enter
            self.exit = self.node_factory() if exit is None else exit
        self.add_node(self.enter)
        self.add_node(self.exit)

    @classmethod
    def from_matcher(cls, matcher, node_factory=None):
        machine = cls(node_factory=node_factory)
        machine.add_edge(machine.enter, machine.exit, matcher=matcher)
        return machine

    def add_edge(self, u, v, key=None, attr_dict=None, **kwargs):
        # Note that the order of key and attr_dict are important, since networkx
        # uses them as positional arguments in add_edges_from().

        # All state machine edges should be distinct. Obnoxiously, this is not
        # the default behavior in MultiDiGraph. See
        # https://github.com/networkx/networkx/issues/2112 and
        # https://github.com/networkx/networkx/issues/1654
        key = uuid1()
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
        machine = self.isomorphic_copy(relabel=False)
        machine.add_edges_from(other.edges(data=True, keys=True))
        return machine

    def __add__(self, other):
        """
        Returns the concatenation of the two machines.
        """
        combined = self.isomorphic_copy(relabel=False)
        if self.successors(self.exit) == [] and other.predecessors(other.enter) == []:
            # In this case, we can optimize the combined machine by using the same
            # vertex for both.
            relabel_nodes(
                combined, {self.exit: other.enter}, copy=False)
            combined.add_edges_from(other.edges(data=True, keys=True))
        else:
            combined.add_edges_from(other.edges(data=True, keys=True))
            combined.add_edge(self.exit, other.enter, matcher=Epsilon)
        combined.exit = other.exit
        return combined

    def __or__(self, other):
        """
        Returns a machine which recognizes the disjunction of the two languages.
        """
        combined = self.isomorphic_copy(relabel=False)
        if combined.predecessors(combined.enter) == [] and other.predecessors(other.enter) == []:
            # In this case, we can optimize the combined machine by using the same
            # vertex for both.
            relabel_nodes(combined, {combined.enter: other.enter}, copy=False)
            combined.enter = other.enter
        if combined.successors(combined.exit) == [] and other.successors(other.exit) == []:
            relabel_nodes(combined, {combined.exit: other.exit}, copy=False)
            combined.exit = other.exit
        combined.add_edges_from(other.edges(data=True, keys=True))
        if combined.enter != other.enter:
            orig_enter = combined.enter
            enter = combined.node_factory()
            combined.add_node(enter)
            combined.enter = enter
            combined.add_edge(combined.enter, other.enter, matcher=Epsilon)
            combined.add_edge(combined.enter, orig_enter, matcher=Epsilon)
        if combined.exit != other.exit:
            orig_exit = combined.exit
            exit = combined.node_factory()
            combined.add_node(exit)
            combined.exit = exit
            combined.add_edge(other.exit, combined.exit, matcher=Epsilon)
            combined.add_edge(orig_exit, combined.exit, matcher=Epsilon)
        return combined

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
        paths = [Walk(None, self.enter, None)]
        while paths:
            new_paths = []
            for path in paths:
                node = path.node
                for _, next_node, edgedict in self.out_edges_iter([node],
                                                                  data=True):
                    new_path = Walk(parent=path,
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

    def random_walk(self, max_iter=10000):
        i = 0
        walk = Walk(None, self.enter, None)
        while i < max_iter:
            i += 1
            _, next_node, edgedict = random.choice(
                self.out_edges([walk.node], data=True))
            walk = Walk(parent=walk,
                        node=next_node,
                        matcher=edgedict['matcher'])
            if walk.node == self.exit:
                return walk
        raise ValueError(
            'Did not find a path out of %r after %r iterations' % (
                self, max_iter))

    def reverse_random_string(self, max_iter=10000):
        """
        Performs a random walk of the machine, until an exit node is reached,
        and returns it.

        This has no backtracking, so it will simply fail if the machine has
        a dead end. It will go for max_iter iterations before raising an error
        to avoid infinite loops.
        """
        # TODO: random the shit out of this.
        walk = self.random_walk(max_iter=max_iter)
        return walk.random_string()

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

    def isomorphic_copy(self, relabel=True, manual_map=None):
        """
        Relabels the nodes of the machine and returns a copy of it.
        """
        if relabel:
            mapping = {node: self.node_factory() for node in self.nodes()}
            if manual_map:
                mapping.update(manual_map)
        else:
            mapping = {node: node for node in self.nodes()}
        new_machine = RegularLanguageMachine(
            node_factory=self._node_factory,
            enter=mapping[self.enter],
            exit=mapping[self.exit],
        )
        new_machine.add_edges_from(
            (mapping.get(n1, n1), mapping.get(n2, n2), k, d.copy())
            for (n1, n2, k, d) in self.edges_iter(keys=True, data=True))

        new_machine.add_nodes_from(mapping[n] for n in self)
        new_machine.node.update(
            {mapping[n]: d.copy() for n, d in self.node.items()})
        new_machine.graph.update(self.graph.copy())

        return new_machine


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

    def random_matching_string(self):
        return self.literal

    def matching_string_iter(self):
        """
        Iterator of matching strings for this node.
        """
        yield self.literal


@six.python_2_unicode_compatible
class MultiCharMatcher(object):
    """
    Matches any of the given characters.
    """
    def __init__(self, chars):
        self.char_array = list(chars)
        self.chars = frozenset(chars)

    def __call__(self, string, index):
        if index < len(string) and string[index] in self.chars:
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

    def random_matching_string(self):
        return random.choice(self.char_array)

    def matching_string_iter(self):
        return iter(self.chars)


@six.python_2_unicode_compatible
class ComplementMatcher(object):
    """
    Matches the complement of the given characters.
    """
    def __init__(self, chars):
        self.char_array = list(chars)
        self.chars = frozenset(chars)
        self.valid_chars = list(set(UNICODE_CHARS) - self.chars)

    def __call__(self, string, index):
        if index < len(string) and string[index] not in self.chars:
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __repr__(self):
        return 'ComplementMatcher(%r)' % ''.join(self.chars)

    def __str__(self):
        return '[^%s]' % ','.join(self.chars)

    def random_matching_string(self):
        return random.choice(self.valid_chars)

    def matching_string_iter(self):
        return iter(self.valid_chars)


@six.python_2_unicode_compatible
class CharRangeMatcher(object):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        if self.start > self.end:
            raise ValueError('Invalid character range %s' % self)

    def __call__(self, string, index):
        if index < len(string) and self.start <= string[index] <= self.end:
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.start, self.end)

    def __str__(self):
        return '[%s-%s]' % (self.start, self.end)

    def random_matching_string(self):
        return chr(random.randint(ord(self.start), ord(self.end)))

    def matching_string_iter(self):
        return (chr(i) for i in range(ord(self.start), ord(self.end) + 1))

    def __invert__(self):
        return ComplementCharRangeMatcher(self.start, self.end)


@six.python_2_unicode_compatible
class ComplementCharRangeMatcher(CharRangeMatcher):
    def __call__(self, string, index):
        if index < len(string) and self.start > string[index] or string[index] > self.end:
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __str__(self):
        return '[^%s-%s]' % (self.start, self.end)

    def random_matching_string(self):
        raise NotImplementedError

    def matching_string_iter(self):
        raise NotImplementedError


@six.python_2_unicode_compatible
class _Dot(object):
    def __call__(self, string, index):
        if index < len(string):
            return MatchInfo(
                matcher=self,
                consumed_chars=1,
                string=string,
                index=index,
            )
        else:
            return None

    def __repr__(self):
        return 'DotMatcher()'

    def __str__(self):
        return '.'

    def random_matching_string(self):
        """
        TODO: properly handle unicode; idk. How does Hypothesis handle this?
        """
        return random.choice(UNICODE_CHARS)

    def matching_string_iter(self):
        return iter(UNICODE_CHARS)


Dot = _Dot()


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
    concatenation = (star / plus / repeat_fixed / repeat_range / optional / literal)+
    star = literal "*"
    plus = literal "+"
    optional = literal "?"
    repeat_fixed = literal "{" ~"\d+" "}"
    repeat_range = literal "{" ~"(\d+)?" "," ~"(\d+)?" "}"
    literal = group / any / chars / negative_set / positive_set
    group = "(" sub_re ")"
    escaped_metachar = "\\" ~"[.$^\\*+\[\]()|{}?]"
    any = "."
    chars = char+
    char = escaped_metachar / non_metachar
    non_metachar = ~"[^.$^\\*+\[\]()|{}?]"
    positive_set = "[" set_items "]"
    negative_set = "[^" set_items "]"
    set_char = ~"[^\\]]|\\\\]"
    set_items = (range / ~"[^\\]]")+
    range = set_char "-" set_char
''')


def repeat(machine, min_repeat, max_repeat):
    """
    Repeats the machine in the given range.

    If max_repeat is None, the right is unbounded (any finite number of repeats).

    Examples:
        (machine)* == machine{0,} == repeat(machine, 0, None)
        (machine)+ == machine{1,} == repeat(machine, 1, None
        (machine){n} == repeat(machine, n, n)
        (machine){n,m} == repeat(machine, n, m}
        (machine){,n} == repeat(machine, 0, n)
        (machine){n,} == repeat(machine, n, None)
    """
    num_machines = max_repeat or min_repeat or 1
    machines = [machine.isomorphic_copy()]
    for _ in six.moves.range(num_machines - 1):
        # Construct a machine whose entry node is the same as the previous exit
        # node.
        machines.append(
            machine.isomorphic_copy(manual_map={machine.enter: machines[-1].exit}))

    repeated = RegularLanguageMachine(
        node_factory=machine._node_factory,
        enter=machines[0].enter,
    )
    # Include all the sub machines in the repeated machine.
    for m in machines:
        repeated.add_edges_from(m.edges(data=True, keys=True))

    # Add "early exit" edges for when we've finished the minimum number of repeats.
    for m in machines[min_repeat:]:
        repeated.add_edge(m.enter, repeated.exit, matcher=Epsilon)

    last_machine = machines[-1]
    repeated.add_edge(last_machine.exit, repeated.exit, matcher=Epsilon)
    # Add an epsilon transition to loop the last machine indefinitely if we have
    # no upper bound.
    if max_repeat is None:
        repeated.add_edge(last_machine.exit, last_machine.enter, matcher=Epsilon)
    return repeated


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
        return reduce(operator.add, [machine for [machine] in children])

    def visit_group(self, node, children):
        lparen, [machine], rparen = children
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
        return reduce(operator.or_, disjuncts)

    def visit_star(self, node, children):
        machine, star_char = children
        return repeat(machine, 0, None)

    def visit_plus(self, node, children):
        machine, plus_char = children
        return repeat(machine, 1, None)

    def visit_literal(self, node, children):
        # Why doesn't parsimonious do this for you?
        [child] = children
        return child

    def visit_chars(self, node, children):
        text = ''.join(children)
        return RegularLanguageMachine.from_matcher(
            LiteralMatcher(text), node_factory=self.node_factory)

    def visit_escaped_metachar(self, node, children):
        slash, char = children
        return char

    def visit_any(self, node, children):
        return RegularLanguageMachine.from_matcher(
            Dot, node_factory=self.node_factory)

    def visit_char(self, node, children):
        child, = children
        return child

    def visit_set_char(self, node, children):
        char = node.text
        if len(char) == 2:
            assert char[0] == '\\', 'Bug! %s' % char
            return char[1]
        return char

    def visit_range(self, node, children):
        # Since a range may be inverted or not, we need to add nodes to the
        # machine for it up the stack.
        start, dash, end = children
        return CharRangeMatcher(start, end)

    def visit_set_items(self, node, children):
        # Dashes can appear either at the beginning or the end of a char-range
        # block and count as a dash.
        return [item for item, in children]

    def visit_positive_set(self, node, children):
        [lbrac, items, rbrac] = children
        raw_chars = ''.join(s for s in items if not isinstance(s, CharRangeMatcher))
        machines = []
        if raw_chars:
            machines.append(RegularLanguageMachine.from_matcher(
                MultiCharMatcher(raw_chars), node_factory=self.node_factory))
        for range_matcher in (s for s in items if isinstance(s, CharRangeMatcher)):
            machines.append(RegularLanguageMachine.from_matcher(
                range_matcher, node_factory=self.node_factory))
        return reduce(operator.or_, machines)

    def visit_negative_set(self, node, children):
        [lbrac, items, rbrac] = children
        raw_chars = ''.join(s for s in items if not isinstance(s, CharRangeMatcher))
        machines = []
        if raw_chars:
            machines.append(RegularLanguageMachine.from_matcher(
                ComplementMatcher(raw_chars), node_factory=self.node_factory))
        for range_matcher in (s for s in items if isinstance(s, CharRangeMatcher)):
            machines.append(RegularLanguageMachine.from_matcher(
                ~range_matcher, node_factory=self.node_factory))
        return reduce(operator.or_, machines)

    def visit_repeat_fixed(self, node, children):
        machine, lbrac, repeat_count, rbrac = children
        repeat_count = int(repeat_count)
        if repeat_count == 0:
            raise ValueError('Invalid repeat %s' % node.text)
        return repeat(machine, repeat_count, repeat_count)

    def visit_repeat_range(self, node, children):
        machine, lbrac, min_repeat, comma, max_repeat, rbrac = children
        min_repeat = int(min_repeat or '0')
        max_repeat = None if not max_repeat else int(max_repeat)
        return repeat(machine, min_repeat, max_repeat)

    def visit_optional(self, node, children):
        machine, question_mark = children
        return repeat(machine, 0, 1)

    def generic_visit(self, node, children):
        return children or node.text