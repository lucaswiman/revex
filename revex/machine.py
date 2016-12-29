# -*- coding: utf-8 -*-

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

        Conventions:
            - If there is no out-edge for a given transition, the regular
              expression does not match.
            - Nodes labeled as "accepting" represent terminals where the regular
              expression matches.
            - As in the construction here: https://drona.csa.iisc.ernet.in/~deepakd/fmcs-06/seminars/presentation.pdf  # noqa
            - Nodes are named by the regular expression that, starting at that
              node, matches that regular expression. In particular, the "start" node
              is labeled with `regex`.
            - Edges' `label` attribute stores the transition character.
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


def minimize_dfa(dfa):
    """
    Return a minimized DFA, as constructed using the Myhill-Nerode theorem
    here: https://cse.sc.edu/~fenner/csce551/minimization.pdf

    See also http://www8.cs.umu.se/kurser/TDBC92/VT06/final/1.pdf for more background,
    and https://www.tutorialspoint.com/automata_theory/dfa_minimization.htm for diagrams.

    """
    raise NotImplementedError  # TODO: test & work out bugs.
    states = list(dfa.nodes())
    F = {state for state in states if dfa.node[state]['accepting']}
    marked = set()
    unmarked = set()

    # Sentinel to hold non-terminating "hold" state. By convention a lack an
    # out-edge means "does not match".
    TERMINAL = object()
    # states.append(TERMINAL)

    def delta(state, char):
        if state is TERMINAL:
            return TERMINAL
        return dfa.delta[state].get(char, TERMINAL)

    for i, p in enumerate(states):
        for q in states[i+1:]:
            if (p in F) != (q in F):
                marked.add((p, q))
            else:
                unmarked.add((p, q))

    update = True
    while update:
        update = False
        for p, q in list(unmarked):
            for a in dfa.alphabet:
                if (delta(p, a), delta(q, a)) in marked:
                    unmarked.remove((p, q))
                    marked.add((p, q))
                    update = True
                    break

    def is_equivalent(p, q, marked=frozenset(marked)):
        return (p, q) in unmarked

    return is_equivalent, unmarked
