import logging
import re
import typing
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Union, Generic

import networkx as nx


logger = logging.getLogger(__name__)


class RevexError(Exception):
    pass


class EmptyLanguageError(RevexError):
    pass


class InfiniteLanguageError(RevexError):
    pass


NodeType = typing.TypeVar('NodeType')

String = str

# All printable ASCII characters. http://www.catonmat.net/blog/my-favorite-regex/
DEFAULT_ALPHABET = list(
    filter(re.compile(r'[ -~]').match, map(chr, range(0, 128))))  # type: Sequence[str]


class DFA(Generic[NodeType], nx.MultiDiGraph):

    def __init__(self, start, start_accepting, alphabet=DEFAULT_ALPHABET):
        # type: (NodeType, bool, Sequence[String]) -> None
        super().__init__()
        self.start = start  # type: NodeType
        self.add_state(start, start_accepting)

        # Index of (state, char): next state transitions. In the literature, this
        # is usually denoted 𝛿.
        self.delta = defaultdict(dict)  # type: defaultdict[NodeType, Dict[String, NodeType]]

        self.alphabet = alphabet  # type: Sequence[String]

    @property
    def as_multidigraph(self):  # type: () -> nx.MultiDiGraph
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
    def is_empty(self):   # type: () -> bool
        return len(self._acceptable_subgraph.nodes) == 0

    @property
    def _acceptable_subgraph(self):  # type:  () -> nx.MultiDiGraph
        graph = self.as_multidigraph
        reachable_states = nx.descendants(graph, self.start) | {self.start}
        graph = graph.subgraph(reachable_states).copy()
        reachable_accepting_states = reachable_states & {
            node for node in graph.nodes if graph.nodes[node]['accepting']
        }

        # Add a "sink" node with an in-edge from every accepting state. This is
        # is solely done because the networkx API makes it easier to find the
        # ancestor of a node than a set of nodes.
        sink = object()
        graph.add_node(sink)
        for state in reachable_accepting_states:
            graph.add_edge(state, sink)

        acceptable_sates = nx.ancestors(graph, sink)
        return graph.subgraph(acceptable_sates).copy()

    @property
    def has_finite_language(self):  # type: () -> bool
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
    def longest_string(self):  # type: () -> String
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
        if len(acceptable_subgraph.nodes) == 0:
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

        chars = []
        for state1, state2 in zip(longest_path, longest_path[1:]):
            edges = self.succ[state1][state2]
            chars.append(next(iter(edges.values()))['transition'])
        return type(self.alphabet[0])().join(chars)

    @property
    def live_subgraph(self):  # type: () -> nx.MultiDiGraph
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
            node for node in graph.nodes if graph.nodes[node]['accepting']
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

    def add_state(self, state, accepting):  # type: (NodeType, bool) -> None
        self.add_node(
            state,
            label=str(state),
            accepting=accepting,
            shape='doublecircle' if accepting else 'box',
            color='green' if accepting else 'black',
        )

    def add_transition(self, from_state, to_state, char):
        # type: (NodeType, NodeType, String) -> None
        if not (self.has_node(from_state) and self.has_node(to_state)):
            raise ValueError('States must be added prior to transitions.')
        if self.delta[from_state].get(char) == to_state:
            # Transition already present.
            return
        elif self.delta[from_state].get(char) is not None:
            raise ValueError('Already have a transition.')
        self.delta[from_state][char] = to_state
        self.add_edge(
            from_state, to_state,
            transition=char,
            label=' %s ' % char,
        )

    def match(self, string):  # type: (String) -> bool
        node = self.start
        for i in range(len(string)):
            node = self.delta[node][string[i:i + 1]]
        return self.nodes[node]['accepting']

    def _draw(self, full=False):  # pragma: no cover
        # type: (bool) -> None
        """
        Hack to draw the graph and open it in preview or display in an ipython
        notebook (if running).
        """
        import os, sys, tempfile, shutil
        if full:
            graph = self.as_multidigraph
        else:
            graph = self.live_subgraph

        invisible_start_node = object()
        graph.add_node(invisible_start_node, label='', color='white')
        graph.add_edge(invisible_start_node, self.start, label=' start')

        if 'ipykernel' in sys.modules:
            import IPython.display
            directory = tempfile.mkdtemp()
            dotpath = os.path.join(directory, 'out.dot')
            pngpath = os.path.join(directory, 'out.png')
            try:
                nx.drawing.nx_agraph.write_dot(graph, dotpath)
                os.system(
                    'dot -Tpng {dotpath} -o {pngpath}'.format(**locals()))
                with open(pngpath, 'rb') as f:
                    IPython.display.display(IPython.display.Image(data=f.read()))
            finally:
                shutil.rmtree(directory)
        elif sys.platform == 'darwin':
            nx.drawing.nx_agraph.write_dot(graph, '/tmp/foo_%s.dot' % id(graph))
            os.system(
                'dot -Tpng /tmp/foo_{0}.dot -o /tmp/foo_{0}.png'.format(id(graph)))
            os.system('open /tmp/foo_{0}.png'.format(id(graph)))
        else:
            raise NotImplementedError(
                'See https://github.com/lucaswiman/revex/issues/19. '
                'Patches welcome!')

    def find_invalid_nodes(self):  # type: () -> Sequence[NodeType]
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
        # type: (DFA) -> Optional[Dict[typing.Any, typing.Any]]
        """
        Returns a mapping of states between self and other exhibiting an
        isomorphism, or None if no isomorphism exists.

        There is a unique isomorphism between DFA's with no "invalid" nodes
        (i.e. every node has a transition for each character in the alphabet).
        """
        if set(self.alphabet) != set(other.alphabet):
            return None  # Two DFAs on different alphabets cannot be isomorphic.
        elif len(self.nodes) != len(other.nodes):
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
                    return None
        assert len(isomorphism) == len(self.nodes)
        return isomorphism


def get_equivalent_states(dfa):
    # type: (DFA[NodeType]) -> Set[tuple[NodeType, NodeType]]
    """
    Return equivalent states in the DFA, as constructed using Hopcroft's
    algorithm. See https://en.wikipedia.org/wiki/DFA_minimization

    See also http://www8.cs.umu.se/kurser/TDBC92/VT06/final/1.pdf and
    https://cse.sc.edu/~fenner/csce551/minimization.pdf for more background.

    TODO: this algorithm does twice as much work as needed by not ordering
    the states.
    """
    states = list(dfa.nodes())
    F = {state for state in states if dfa.nodes[state]['accepting']}

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

    def delta(state, char):  # type: (NodeType, String) -> NodeType
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


T = typing.TypeVar('T')


def minimize_dfa(dfa):  # type: (DFA[T]) -> DFA[frozenset[T]]
    """
    Constructs a minimized DFA by combining equivalent states.
    """
    equivalent_states = get_equivalent_states(dfa)
    equivalency_classes = []  # type: List[frozenset[T]]
    old_states = set(dfa.nodes())  # type: Set[T]
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
    }  # type: Dict[T, frozenset[T]]

    def is_accepting(new_state):  # type: (frozenset[T]) -> bool
        return dfa.nodes[next(iter(new_state))]['accepting']

    start = old_state_to_new_state[dfa.start]
    new_dfa = DFA(start, is_accepting(start), alphabet=dfa.alphabet)  # type: DFA[frozenset[T]]
    for equivalency_class in equivalency_classes:
        if equivalency_class != start:
            new_dfa.add_state(equivalency_class, is_accepting(equivalency_class))

    for from_state, trans in dfa.delta.items():
        for char, to_state in trans.items():
            new_dfa.add_transition(
                old_state_to_new_state[from_state],
                old_state_to_new_state[to_state],
                char,
            )

    return new_dfa


def construct_integer_dfa(dfa):  # type: (DFA) -> DFA[int]
    """
    Constructs a DFA whose states are all integers from 0 to (number of states),
    with 0 the start state.
    This is more efficient for some algorithms, since arrays/lists can be used
    instead of hash tables.
    """
    nodes = [dfa.start] + [node for node in dfa.nodes if node != dfa.start]
    node_to_index = {node: index for index, node in enumerate(nodes)}
    int_dfa = DFA(
        start=node_to_index[dfa.start],
        start_accepting=dfa.nodes[dfa.start]['accepting'],
        alphabet=dfa.alphabet,
    )
    for node, attr in dfa.nodes.items():
        int_dfa.add_state(
            node_to_index[node],
            accepting=attr['accepting'],
        )
    for from_node, trans in dfa.delta.items():
        for char, to_node in trans.items():
            int_dfa.add_transition(
                node_to_index[from_node],
                node_to_index[to_node],
                char,
            )
    return int_dfa
