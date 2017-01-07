# -*- coding: utf-8 -*-
from __future__ import absolute_import, division

import random
from bisect import bisect_left
from itertools import count

from six.moves import range

from revex.dfa import construct_integer_dfa


class InvalidDistributionError(Exception):
    pass


class DiscreteRandomVariable(list):
    def __init__(self, counts):
        total = sum(counts, 0.0)
        if total <= 0:
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
        return bisect_left(self, random.random())


class NaiveRandomRegularLanguageGenerator(object):
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
    def __init__(self, dfa):
        invalid_nodes = dfa.find_invalid_nodes()
        if invalid_nodes:  # pragma: no cover
            raise ValueError('Must use a valid DFA.')
        self.dfa = construct_integer_dfa(dfa)
        self.alphabet = list(self.dfa.alphabet)

        self.nodes = range(0, len(self.dfa.node))

        # Denoted by l_{p,n} in section 2 of the Bernardi & Giménez paper,
        # path_counts[state][n] is the number of paths of length n from
        # state to _some_ final/accepting state. Since these numbers can
        # be exponentially large in `n`, we use floating point numbers for efficiency.
        self.path_counts = [
            # Initialize the array with the number of zero-length paths from the
            # state to an accepting state. (i.e. 1 if the state is accepting.)
            [1.0 if self.dfa.node[state]['accepting'] else 0.0]
            for state in self.nodes
        ]
        self.n = 0
        self.node_length_to_character_dist = {}

    def _precompute_l(self, n):
        while self.n < n:
            for state in self.nodes:
                self.path_counts[state].append(
                    sum(self.path_counts[self.dfa.delta[state][char]][self.n]
                        for char in self.dfa.alphabet)
                )
            self.n += 1

    def get_dist_for_node_and_length(self, node, length):
        if (node, length) not in self.node_length_to_character_dist:
            try:
                dist = DiscreteRandomVariable([
                    self.path_counts[self.dfa.delta[node][char]][length - 1]
                    for char in self.alphabet
                ])
            except InvalidDistributionError:
                # There are no paths of the given length.
                dist = None
            self.node_length_to_character_dist[(node, length)] = dist
        return self.node_length_to_character_dist[(node, length)]

    def random_string(self, length):
        """
        Return a string matched by the DFA of the given length, chosen uniformly
        at random among all strings of that length.

        Returns `None` if no such string exists.
        """
        self._precompute_l(length)
        state = self.dfa.start
        chars = []
        if length == 0 and not self.dfa.node[state]['accepting']:
            return None
        for i in range(length):
            dist = self.get_dist_for_node_and_length(state, length - i)
            if dist is None:
                return None
            char = self.alphabet[dist.draw()]
            chars.append(char)
            state = self.dfa.delta[state][char]
        return type(self.alphabet[0])().join(chars)

    def valid_lengths_iter(self):
        for length in count():
            self._precompute_l(length)
            if self.path_counts[self.dfa.start][length] > 0:
                yield length
