# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging
import operator
import re
from collections import defaultdict
from functools import reduce

import six
from networkx import MultiDiGraph, ancestors, is_directed_acyclic_graph, \
    descendants

# All printable ASCII characters. http://www.catonmat.net/blog/my-favorite-regex/
DEFAULT_ALPHABET = ''.join(filter(re.compile(r'[ -~]').match, map(chr, range(0, 128))))


logger = logging.getLogger(__name__)


class DFA(MultiDiGraph):
    def __init__(self, start, start_accepting, alphabet=DEFAULT_ALPHABET):
        super(DFA, self).__init__()
        self.start = start
        self.add_state(start, start_accepting)

        # Index of (state, char): next char transitions. In the literature, this
        # is usually denoted 𝛿.
        self.delta = defaultdict(dict)

        self.alphabet = alphabet

    @property
    def as_multidigraph(self):
        """
        Constructs a MultiDiGraph that is a copy of self.

        This is a bit of a hack, but allows some useful methods like .subgraph()
        to work correctly.
        """
        graph = MultiDiGraph()
        graph.add_nodes_from(self.node)
        for node in self.node:
            if 'accepting' in self.node[node]:
                color='green' if self.node[node]['accepting'] else 'black'
            else:
                color = 'black'  # TODO: whatevs
            graph.add_node(
                node,
                color=color)


        graph.add_edges_from(self.edges(data=True))
        # for from_node, to_node,  in self.edges_iter():
        #     graph.add_edge(from_node, to_node)
        return graph

    @property
    def is_empty(self):
        from .derivative import EMPTY
        empty_machine = EMPTY.as_dfa(self.alphabet)
        return bool(minimize_dfa(self).construct_isomorphism(empty_machine))

    @property
    def has_finite_language(self):
        """
        Returns True iff this DFA recognizes a finite (possibly empty) language.

        Based on decision procedure described here:
        http://math.uaa.alaska.edu/~afkjm/cs351/handouts/non-regular.pdf

        - Remove nodes which cannot reach an accepting state
        - Language is infinite iff the remaining graph is acyclic.
        """
        graph = construct_integer_dfa(self)
        accepting_states = {
            node for node in graph.node if graph.node[node]['accepting']
        }
        if not accepting_states:
            # The language is empty, since there are no accepting states.
            return True

        # Add a "sink" node with an in-edge from every accepting state. This is
        # is solely done because the networkx API makes it easier to find the
        # ancestor of a node than a set of nodes.
        sink = object()
        graph.add_node(sink)
        for state in accepting_states:
            graph.add_edge(state, sink)

        live_states = {graph.start} | (ancestors(graph, sink) & descendants(graph, graph.start))
        return is_directed_acyclic_graph(graph.as_multidigraph.subgraph(live_states))

    def get_live_graph(self):
        graph_copy = copy.deepcopy(self)
        accepting_states = {
            node for node in graph_copy.node if graph_copy.node[node]['accepting']
        }

        # Add a "sink" node with an in-edge from every accepting state. This is
        # is solely done because the networkx API makes it easier to find the
        # ancestor of a node than a set of nodes.
        sink = object()
        graph_copy.add_node(sink)
        for state in accepting_states:
            graph_copy.add_edge(state, sink)

        live_states = {graph_copy.start} | (ancestors(graph_copy, sink) & descendants(graph_copy, graph_copy.start))
        live_graph = graph_copy.as_multidigraph.subgraph(live_states)
        for node in live_graph.node:
            edges = live_graph.out_edges(nbunch=[node], data=True)

        # TODO(jeff): collapse edges into character ranges
        return live_graph


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
        from networkx.drawing.nx_agraph import write_dot
        import os
        if full:
            graph = self
        else:
            graph = self.get_live_graph()

        write_dot(graph, '/tmp/foo_%s.dot' % id(graph))
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
    Return equivalent states in the DFA, as constructed using the Hopcroft's
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


def construct_integer_dfa(dfa):
    """
    Constructs a DFA whose states are all integers from 0 to (number of states),
    with 0 the start state.

    This is more efficient for some algorithms, since arrays/lists can be used
    instead of hash tables.
    """
    nodes = [dfa.start] + [node for node in dfa.node if node != dfa.start]
    node_to_index = {node: index for index, node in enumerate(nodes)}
    int_dfa = DFA(
        start=node_to_index[dfa.start],
        start_accepting=dfa.node[dfa.start]['accepting'],
        alphabet=dfa.alphabet,
    )
    for node, attr in six.iteritems(dfa.node):
        int_dfa.add_state(
            node_to_index[node],
            accepting=attr['accepting'],
        )
    for from_node, trans in six.iteritems(dfa.delta):
        for char, to_node in six.iteritems(trans):
            int_dfa.add_transition(
                node_to_index[from_node],
                node_to_index[to_node],
                char,
            )
    return int_dfa
