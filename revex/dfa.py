# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re
import sys
from collections import defaultdict

import six
import networkx as nx
import typing
from typing import Dict
from typing import Sequence
from typing import Tuple


logger = logging.getLogger(__name__)

# All printable ASCII characters. http://www.catonmat.net/blog/my-favorite-regex/
DEFAULT_ALPHABET = ''.join(filter(re.compile(r'[ -~]').match, map(chr, range(0, 128))))


class RevexError(Exception):
    pass


class EmptyLanguageError(RevexError):
    pass


class InfiniteLanguageError(RevexError):
    pass


NodeType = typing.TypeVar('NodeType')

if sys.version_info < (3, ):
    Character = typing.Union[str, unicode]
else:
    Character = typing.Union[str]


class DFA(nx.MultiDiGraph):
    def __init__(self, start, start_accepting, alphabet=DEFAULT_ALPHABET):
        # type: (NodeType, bool, Sequence[Character]) -> None
        super(DFA, self).__init__()
        self.start = start
        self.add_state(start, start_accepting)

        # Index of (state, char): next state transitions. In the literature, this
        # is usually denoted 𝛿.
        self.delta = defaultdict(dict)  # type: defaultdict[NodeType, Dict[Character, NodeType]]

        self.alphabet = alphabet

    @property
    def as_multidigraph(self):
        """
        Constructs a MultiDiGraph that is a copy of self.

        This is a bit of a hack, but allows some useful methods like .subgraph()
        to work correctly.
        """
        graph = nx.MultiDiGraph()
        graph.add_nodes_from(self.nodes(data=True))
        graph.add_edges_from(self.edges(data=True))
        return graph

    @property
    def is_empty(self):
        return len(self._acceptable_subgraph.node) == 0

    @property
    def _acceptable_subgraph(self):
        graph = self.as_multidigraph
        reachable_states = nx.descendants(graph, self.start) | {self.start}
        graph = graph.subgraph(reachable_states)
        reachable_accepting_states = reachable_states & {
            node for node in graph.node if graph.node[node]['accepting']
        }

        # Add a "sink" node with an in-edge from every accepting state. This is
        # is solely done because the networkx API makes it easier to find the
        # ancestor of a node than a set of nodes.
        sink = object()
        graph.add_node(sink)
        for state in reachable_accepting_states:
            graph.add_edge(state, sink)

        acceptable_sates = nx.ancestors(graph, sink)
        return graph.subgraph(acceptable_sates)

    @property
    def has_finite_language(self):
        """
        Returns True iff this DFA recognizes a finite (possibly empty) language.

        Based on decision procedure described here:
        http://math.uaa.alaska.edu/~afkjm/cs351/handouts/non-regular.pdf

        - Remove nodes which cannot reach an accepting state (see
          `_acceptable_subgraph` above).
        - Language is finite iff the remaining graph is acyclic.
        """
        return nx.is_directed_acyclic_graph(self._acceptable_subgraph)

    @property
    def longest_string(self):
        """
        Returns an example of a maximally long string recognized by this DFA.

        If the language is infinite, raises InfiniteLanguageError.
        If the language is empty, raises EmptyLanguageError.

        The algorithm is similar to the one described in these lecture notes
        for deciding whether a language is finite:
        http://math.uaa.alaska.edu/~afkjm/cs351/handouts/non-regular.pdf
        """

        # Compute what we're calling the "acceptable subgraph" by restricting to
        # states which are (1) descendants of a start state, and (2) ancestors of
        # an accepting state. These two properties imply that there is at least
        # one walk between these two states, corresponding to a string present in
        # the language.
        acceptable_subgraph = self._acceptable_subgraph
        if len(acceptable_subgraph.node) == 0:
            # If this graph is _empty_, then the language is empty.
            raise EmptyLanguageError()

        # Otherwise, we try to find the longest path in it. Internally, networkx
        # does this by topologically sorting the graph (which only works if it's
        # a DAG), then using the sorted graph to construct the longest path in
        # linear time.
        try:
            longest_path = nx.algorithms.dag.dag_longest_path(
                acceptable_subgraph)
        except nx.NetworkXUnfeasible:
            # If a topological sort is not possible, this means there is a
            # cycle, and the recognized language is infinite. In this case,
            # nx raises ``nx.NetworkXUnfeasible``.
            raise InfiniteLanguageError()

        # To show that the longest path must originate at the start node,
        # consider 3 cases for the position of s in a longest path P from u to v:
        #
        # (a) At the beginning. Done; this is what we were seeking to prove.
        # (b) On the path, but not at the beginning. In this case, u is
        #     reachable from s (by property (1) above), and s in reachable from
        #     u (since s is on a path from u to v). This means the graph
        #     contains a cycle, which contradicts that we've constructed a
        #     topological sort on it.
        # (c) Disjoint from s. Let P' be a path connecting s to u (which must
        #     exist by property (1)). If this path contains a vertex u'!=u in P,
        #     then P ∪ P' contains a cycle (from u to u' on P and from u' to u
        #     on P'), which is a contradiction. But then P ∪ P' is a path, which
        #     contains at least one more vertex than P (in particular, s), and
        #     so is a longer path, which contradicts the maximality assumption.

        chars = []
        for state1, state2 in zip(longest_path, longest_path[1:]):
            edges = self.succ[state1][state2]
            chars.append(next(six.itervalues(edges))['transition'])
        return ''.join(chars)

    @property
    def live_subgraph(self):
        """
        Returns the graph of "live" states for this graph, i.e. the start state
        together with states that may be involved in positively matching a string
        (reachable from the start node and an ancestor of an accepting node).

        This is intended for display purposes, only showing the paths which
        might lead to an accepting state, or just the start state if no such
        paths exist.
        """
        graph = self.as_multidigraph
        accepting_states = {
            node for node in graph.node if graph.node[node]['accepting']
        }

        # Add a "sink" node with an in-edge from every accepting state. This is
        # is solely done because the networkx API makes it easier to find the
        # ancestor of a node than a set of nodes.
        sink = object()
        graph.add_node(sink)
        for state in accepting_states:
            graph.add_edge(state, sink)

        live_states = {self.start} | (nx.ancestors(graph, sink) & nx.descendants(graph, self.start))
        return graph.subgraph(live_states)

    def add_state(self, state, accepting):
        return self.add_node(
            state,
            attr_dict={
                'label': str(state),
                'accepting': accepting,
            },
            color='green' if accepting else 'black',
        )

    def add_transition(self, from_state, to_state, char):
        if not (self.has_node(from_state) and self.has_node(to_state)):
            raise ValueError('States must be added prior to transitions.')
        if self.delta[from_state].get(char) == to_state:
            # Transition already present.
            return
        elif self.delta[from_state].get(char) is not None:
            raise ValueError('Already have a transition.')
        self.delta[from_state][char] = to_state
        return self.add_edge(
            from_state, to_state,
            attr_dict={
                'transition': char,
                'label': char,
            }
        )

    def match(self, string):
        node = self.start
        for char in string:
            node = self.delta[node][char]
        return self.node[node]['accepting']

    def _draw(self, full=False):  # pragma: no cover
        """
        Hack to draw the graph and open it in preview. Sorta OS X only-ish.
        """
        import os
        if full:
            graph = self
        else:
            graph = self.live_subgraph

        nx.drawing.nx_agraph.write_dot(graph, '/tmp/foo_%s.dot' % id(graph))
        os.system(
            'dot -Tpng /tmp/foo_{0}.dot -o /tmp/foo_{0}.png'.format(id(graph)))
        os.system('open /tmp/foo_{0}.png'.format(id(graph)))

    def find_invalid_nodes(self):
        """
        Returns a list of nodes which do not have a transition for every element
        of the alphabet.

        If this method returns a non-empty list, various methods in this module
        may not work correctly.
        """
        invalid_nodes = []
        alphabet = set(self.alphabet)
        for from_node in self.nodes():
            trans = self.delta[from_node]
            if set(trans) != alphabet:
                invalid_nodes.append(from_node)
        return invalid_nodes

    def construct_isomorphism(self, other):
        """
        Returns a mapping of states between self and other exhibiting an
        isomorphism, or None if no isomorphism exists.

        There is a unique isomorphism between DFA's with no "invalid" nodes
        (i.e. every node has a transition for each character in the alphabet).
        """
        if set(self.alphabet) != set(other.alphabet):
            return None  # Two DFAs on different alphabets cannot be isomorphic.
        elif len(self.node) != len(other.node):
            return None
        isomorphism = {self.start: other.start}
        to_explore = [(self.start, other.start)]
        while to_explore:
            self_node, other_node = to_explore.pop()
            for char, self_next_node in self.delta[self_node].items():
                other_next_node = other.delta[other_node][char]
                if self_next_node not in isomorphism:
                    to_explore.append((self_next_node, other_next_node))
                    isomorphism[self_next_node] = other_next_node
                elif isomorphism[self_next_node] != other_next_node:
                    logger.debug('Found inconsistent mapping %r->%r and %r via %s',
                                 self_node, other_next_node, isomorphism[self_next_node],
                                 char)
                    return None
        assert len(isomorphism) == len(self.node)
        return isomorphism


class RegexDFA(DFA):
    def __init__(self, regex, alphabet=DEFAULT_ALPHABET):
        """
        Builds a DFA from a revex.derivative.RegularExpression object.

        Based of the construction here: https://drona.csa.iisc.ernet.in/~deepakd/fmcs-06/seminars/presentation.pdf  # noqa
        Nodes are named by the regular expression that, starting at that node,
        matches that regular expression. In particular, the "start" node is
        labeled with `regex`.
        """
        super(RegexDFA, self).__init__(
            start=regex,
            start_accepting=regex.accepting,
            alphabet=alphabet,
        )
        nodes = {regex}
        while nodes:
            node = nodes.pop()
            for char in alphabet:
                derivative = node.derivative(char)
                if not self.has_node(derivative):
                    nodes.add(derivative)
                    self.add_state(derivative, derivative.accepting)
                self.add_transition(node, derivative, char)


def get_equivalent_states(dfa):
    """
    Return equivalent states in the DFA, as constructed using Hopcroft's
    algorithm. See https://en.wikipedia.org/wiki/DFA_minimization

    See also http://www8.cs.umu.se/kurser/TDBC92/VT06/final/1.pdf and
    https://cse.sc.edu/~fenner/csce551/minimization.pdf for more background.

    TODO: this algorithm does twice as much work as needed by not ordering
    the states.
    """
    states = list(dfa.nodes())
    F = {state for state in states if dfa.node[state]['accepting']}

    # Two nodes p and q in the DFA are considered _equivalent_ iff for every
    # string S=c0c1c2...ck, starting off at p and q are always accepting or not
    # accepting.

    # Start off assuming that _all_ node pairs are equivalent, then search for
    # disproofs of equivalency.
    equivalent = {
        (p, q) for p in states for q in states

        # First remove pairs whose equivalence is disproved by the empty string
        # (i.e. one is an accepting state and the other is not).
        if (p in F) == (q in F)
    }

    def delta(state, char):
        return dfa.delta[state][char]

    # Now proceed in a backtracking search for all 1-character disproofs of
    # equivalency, 2-character disproofs, and so on. When no new disproofs are
    # found, we are done.
    found_disproof = True
    while found_disproof:
        found_disproof = False
        to_disprove = set(equivalent)
        while to_disprove:
            p, q = to_disprove.pop()
            to_disprove.discard((q, p))
            for a in dfa.alphabet:
                if (delta(p, a), delta(q, a)) not in equivalent:
                    equivalent.remove((p, q))
                    found_disproof = True
                    break

    return equivalent | {(q, p) for p, q in equivalent}


def minimize_dfa(dfa):
    """
    Constructs a minimized DFA by combining equivalent states.
    """
    equivalent_states = get_equivalent_states(dfa)
    equivalency_classes = []
    old_states = set(dfa.nodes())
    while old_states:
        state = old_states.pop()
        new_state = {state}
        for (p, q) in equivalent_states:
            if p == state:
                new_state.add(q)
                old_states.discard(q)
        equivalency_classes.append(frozenset(new_state))
    old_state_to_new_state = {
        state: new_state for new_state in equivalency_classes
        for state in new_state
    }

    def is_accepting(new_state):
        return dfa.node[next(iter(new_state))]['accepting']

    start = old_state_to_new_state[dfa.start]
    new_dfa = DFA(start, is_accepting(start), alphabet=dfa.alphabet)
    for state in equivalency_classes:
        if state != start:
            new_dfa.add_state(state, is_accepting(state))

    for from_state, trans in dfa.delta.items():
        for char, to_state in trans.items():
            new_dfa.add_transition(
                old_state_to_new_state[from_state],
                old_state_to_new_state[to_state],
                char,
            )

    return new_dfa


class IntegerDFA(DFA):
    """
    Constructs a DFA whose states are all integers from 0 to (number of states),
    with 0 the start state.

    This is more efficient for some algorithms, since arrays/lists can be used
    instead of hash tables.
    """
    def __init__(self, dfa):  # type: (DFA) -> None
        nodes = [dfa.start] + [node for node in dfa.node if node != dfa.start]
        node_to_index = {node: index for index, node in enumerate(nodes)}
        super(IntegerDFA, self).__init__(
            start=node_to_index[dfa.start],
            start_accepting=dfa.node[dfa.start]['accepting'],
            alphabet=dfa.alphabet,
        )
        for node, attr in six.iteritems(dfa.node):
            self.add_state(
                node_to_index[node],
                accepting=attr['accepting'],
            )
        for from_node, trans in six.iteritems(dfa.delta):
            for char, to_node in six.iteritems(trans):
                self.add_transition(
                    node_to_index[from_node],
                    node_to_index[to_node],
                    char,
                )
