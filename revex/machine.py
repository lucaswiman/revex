# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from networkx import MultiDiGraph

# Characters common to ASCII, UTF-8 encoded text and LATIN-1 encoded text.
DEFAULT_ALPHABET = ''.join(map(chr, range(0, 128)))


class DFA(MultiDiGraph):
    def __init__(self, start, start_accepting, alphabet=DEFAULT_ALPHABET):
        super(DFA, self).__init__()
        self.start = start
        self.add_state(start, start_accepting)

        # Index of (state, char): next char transitions. In the literature, this
        # is usually denoted 𝛿.
        self.delta = defaultdict(dict)

        self.alphabet = alphabet

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
        elif self.delta[from_state].get(char) != None:
            raise ValueError('Already have a transition.')
        self.delta[from_state][char] = to_state
        return self.add_edge(
            from_state, to_state,
            attr_dict={
                'transition': char,
                'label': char,
            }
        )

    def matches(self, string):
        node = self.start
        for char in string:
            try:
                node = self.delta[node][char]
            except KeyError:
                return False
        return self.node[node]['accepting']

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
            next_nodes = set()
            for node in nodes:
                for char in alphabet:
                    derivative = node.derivative(char)
                    if not self.has_node(derivative):
                        next_nodes.add(derivative)
                        self.add_state(derivative, derivative.accepting)
                    self.add_transition(node, derivative, char)
            nodes = next_nodes


def get_equivalent_states(dfa):
    """
    Return equivalent states in the DFA, as constructed using the Myhill-Nerode
    theorem here: https://cse.sc.edu/~fenner/csce551/minimization.pdf

    See also http://www8.cs.umu.se/kurser/TDBC92/VT06/final/1.pdf for more background,
    and https://www.tutorialspoint.com/automata_theory/dfa_minimization.htm for diagrams.

    TODO: this algorithm doesn't does twice as much work as needed by not ordering
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

    return equivalent | {(q ,p) for p, q in equivalent}


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
