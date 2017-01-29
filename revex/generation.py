# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import random
import itertools
from bisect import bisect_left
from itertools import count

from six.moves import range
from typing import Tuple, Dict, List, Union  # noqa

from revex.dfa import DFA  # noqa
from revex.dfa import construct_integer_dfa
from revex.dfa import EmptyLanguageError
from revex.dfa import InfiniteLanguageError


class InvalidDistributionError(Exception):
    pass


class _Distribution(list):
    pass


class DiscreteRandomVariable(_Distribution):
    def __init__(self, counts):  # type: (List[float]) -> None
        total = sum(counts, 0.0)
        if total == 0:
            raise InvalidDistributionError()
        super(DiscreteRandomVariable, self).__init__(
            count / total for count in counts)
        for i in range(1, len(self)):
            # Build the right endpoints to sample from.
            self[i] += self[i - 1]
        if not self:
            # Usually caused by passing a consumable iterator.
            raise ValueError('Empty distribution!')

    def draw(self, random=random):
        """
        Draw according to the probabilities in `counts`.
        """
        return bisect_left(self, random.random())


class LeastFrequentRoundRobin(_Distribution):
    """
    Draws in a cycle from least frequent to most frequent, ignoring indices
    with zero weighting.
    """
    def __init__(self, counts):  # type: (List[Union[float, int]]) -> None
        super(LeastFrequentRoundRobin, self).__init__(
            i for i, count in enumerate(counts) if counts[i] > 0)
        self.sort(key=counts.__getitem__)  # Sort indices from least to most frequent.
        self.chooser = itertools.cycle(self)

    def draw(self, random=random):
        return next(self.chooser)


class PathCounts(list):

    def __init__(self, dfa):  # type: (DFA) -> None
        """
        Class for maintaining state path counts inside a dfa.

        Denoted by l_{p,n} in section 2 of the Bernardi & Giménez paper,
        path_counts[state][n] is the number of paths of length n from
        state to _some_ final/accepting state.

        `dfa` MUST have consecutive integer states, with 0 as the start state,
        though this is not validated.
        """
        self.dfa = dfa
        # Initialize the array with the number of zero-length paths from the
        # state to an accepting state. (i.e. 1 if the state is accepting.)
        self.states = range(len(self.dfa.node))
        super(PathCounts, self).__init__(
            [1.0 if self.dfa.node[state]['accepting'] else 0.0]
            for state in self.states
        )
        self.longest_path_length = 0

    def __getitem__(self, item):
        if isinstance(item, tuple):
            node, path_length = item
            while path_length > self.longest_path_length:
                # Precomputes all path lengths up to path_length by expanding
                # breadth first search.
                for state in self.states:
                    # Compute the next length of paths by summing the number of
                    # paths of length self.longest_path_length among the out-edges
                    # of the node.
                    path_counts = sum(
                        self[self.dfa.delta[state][char]][self.longest_path_length]
                        for char in self.dfa.alphabet)
                    self[state].append(path_counts)
                self.longest_path_length += 1
            return self[node][path_length]
        return list.__getitem__(self, item)

    def __repr__(self):
        return 'PathCounts(%r)' % self.dfa


class BaseGenerator(object):
    def __init__(self, dfa):  # type: (DFA) -> None
        if dfa.find_invalid_nodes():  # pragma: no cover
            raise ValueError('Must use a valid DFA.')
        self.dfa = construct_integer_dfa(dfa)
        self.alphabet = list(self.dfa.alphabet)

        self.nodes = range(0, len(self.dfa.node))

        # Denoted by l_{p,n} in section 2 of the Bernardi & Giménez paper,
        # path_counts[state][n] is the number of paths of length n from
        # state to _some_ final/accepting state. Since these numbers can
        # be exponentially large in `n`, we use floating point numbers for efficiency.
        self.path_counts = PathCounts(self.dfa)
        self.node_length_to_character_dist = {}  # type: Dict[Tuple[int, int], _Distribution]

    def distribution_type(self):
        raise NotImplementedError

    def get_dist_for_node_and_length(self, node, length):
        if (node, length) not in self.node_length_to_character_dist:
            try:
                dist = self.distribution_type([
                    self.path_counts[self.dfa.delta[node][char], length - 1]
                    for char in self.alphabet
                ])
            except InvalidDistributionError:
                # There are no paths of the given length.
                dist = None
            self.node_length_to_character_dist[(node, length)] = dist
        return self.node_length_to_character_dist[(node, length)]

    def generate_string(self, length):
        """
        Return a string matched by the DFA of the given length, chosen uniformly
        at random among all strings of that length.

        Returns `None` if no such string exists.
        """
        state = self.dfa.start
        chars = []
        if length == 0 and not self.dfa.node[state]['accepting']:
            return None
        elif self.path_counts[state, length] == 0:
            return None  # No paths of the given length.
        for i in range(length):
            dist = self.get_dist_for_node_and_length(state, length - i)
            if dist is None:
                return None
            char = self.alphabet[dist.draw()]
            chars.append(char)
            state = self.dfa.delta[state][char]
        return type(self.alphabet[0])().join(chars)

    def valid_lengths_iter(self):
        try:
            longest_string = self.dfa.longest_string
            iterator = iter(range(len(longest_string) + 1))
        except EmptyLanguageError:
            # No valid lengths.
            iterator = iter(())
        except InfiniteLanguageError:
            iterator = count()

        for length in iterator:
            if self.path_counts[self.dfa.start, length] > 0:
                yield length


class RandomRegularLanguageGenerator(BaseGenerator):
    """
    Based off the "Recursive RGA" algorithm described in Bernardi & Giménez,
    "A Linear Algorithm for the Random Generation of Regular Languages"
    Algorithmica. February 2012, Volume 62, Issue 1, pp 130–145

    Preprint available at: http://people.brandeis.edu/~bernardi/publications/regular-sampling.pdf

    The idea is to precompute the number of of paths from the start state to each
    other state, then use those to get a probability distribution for selecting
    transitions. This is less asymptotically efficient than the "divide & conquer"
    method that was original to that paper, but massively simpler to implement.
    """
    distribution_type = DiscreteRandomVariable


class DeterministicRegularLanguageGenerator(BaseGenerator):
    distribution_type = LeastFrequentRoundRobin

    def matching_strings_iter(self):
        """
        Returns an iterator on all strings matched by the DFA.

        Each string will be included exactly once.
        """
        empty_string = type(self.alphabet[0])()

        def strings(state, stack, remaining_length):
            if remaining_length == 0:
                if self.dfa.node[state]['accepting']:
                    yield ''
                return

            for char_idx in self.get_dist_for_node_and_length(state, remaining_length):
                char = self.alphabet[char_idx]
                stack.append(char)
                if remaining_length == 1:
                    yield empty_string.join(stack)
                else:
                    next_state = self.dfa.delta[state][char]
                    for s in strings(next_state, stack, remaining_length - 1):
                        yield s
                stack.pop()

        for length in self.valid_lengths_iter():
            for s in strings(self.dfa.start, [], length):
                yield s
