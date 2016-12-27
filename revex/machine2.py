from networkx import MultiDiGraph


# Characters common to ASCII, UTF-8 encoded text and LATIN-1 encoded text.
from revex.derivative import EMPTY

DEFAULT_ALPHABET = ''.join(map(chr, range(0, 128)))


class DFA(MultiDiGraph):
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
        super(DFA, self).__init__()
        self.start = regex
        self.add_node(
            regex,
            attr_dict={
                'label': str(regex),
                'accepting': regex.accepting,
            },
            color='green' if regex.accepting else 'black',
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
                    else:
                        accepting = derivative.accepting
                        self.add_node(
                            derivative,
                            attr_dict={
                                'accepting': accepting,
                                'label': str(derivative),
                            },
                            color='green' if accepting else 'black',
                        )
                    self.add_edge(
                        node, derivative,
                        attr_dict={
                            'label': char,
                        }
                    )
            nodes = next_nodes

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
