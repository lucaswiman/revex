from networkx import MultiDiGraph


# Characters common to ASCII, UTF-8 encoded text and LATIN-1 encoded text.
from revex.derivative import EMPTY

DEFAULT_ALPHABET = ''.join(map(chr, range(0, 128)))


class DFA(MultiDiGraph):
    def __init__(self, start, start_accepting, alphabet=DEFAULT_ALPHABET):
        super(DFA, self).__init__()
        self.start = start
        self.add_state(start, start_accepting)
        self.transitions = {}  # maintain an index on edges for efficiency
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
        self.transitions[(from_state, char)] = to_state
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
                node = self.transitions[(node, char)]
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
                    if derivative is EMPTY:
                        continue
                    if not self.has_node(derivative):
                        next_nodes.add(derivative)
                        self.add_state(derivative, derivative.accepting)
                    self.add_transition(node, derivative, char)
            nodes = next_nodes
