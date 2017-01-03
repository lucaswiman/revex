from __future__ import division
import re
from collections import Counter

import revex
from revex.random_generation import NaiveRandomRegularLanguageGenerator

NaiveRandomRegularLanguageGenerator


def assert_dist_approximately_equal(counts, expected_dist, threshold=0.05):
    total = sum(counts.values())
    actual_dist = {event: count / total for event, count in counts.items()}
    for event in set(actual_dist) | set(expected_dist):
        expected = expected_dist.get(event, 0.0)
        actual = actual_dist.get(event, 0.0)
        assert abs(expected - actual) < threshold, event


def test():
    dfa = revex.build_dfa(r'(a|bb|ccc)*', alphabet='abc')
    gen = NaiveRandomRegularLanguageGenerator(dfa)

    neg_dfa = (~revex.compile(r'(a|bb|ccc)*')).as_dfa(alphabet='abc')
    neg_gen = NaiveRandomRegularLanguageGenerator(neg_dfa)

    regex = re.compile(r'^(a|bb|ccc)*$')

    # These assertions are mostly probabilistic, so the numbers are chosen so
    # as to make the tests quite likely to pass.
    assert {gen.random_string(0) for _ in range(10)} == {''}
    assert {gen.random_string(1) for _ in range(10)} == {'a'}

    negs_1 = Counter(neg_gen.random_string(1) for _ in range(1000))
    assert_dist_approximately_equal(negs_1, {'b': 0.5, 'c': 0.5})

    pos_2 = Counter(gen.random_string(2) for _ in range(1000))
    negs_2 = Counter(neg_gen.random_string(2) for _ in range(1000))
    assert_dist_approximately_equal(pos_2, {'aa': 0.5, 'bb': 0.5})
    assert_dist_approximately_equal(
        negs_2,
        {
            'ab': 1/7,
            'ba': 1/7,
            'cc': 1/7,
            'ca': 1/7,
            'cb': 1/7,
            'bc': 1/7,
            'ac': 1/7,
        })

    pos_6 = Counter(gen.random_string(6) for _ in range(10000))
    possibilities = [
        'aaaaaa',
        'cccccc',
        'bbbbbb',
        'cccaaa',
        'aaaccc',
        'abbccc',
        'acccbb',
        'bbaccc',
        'bbccca',
        'cccabb',
        'cccbba',
        'bbaaaa',
        'abbaaa',
        'aabbaa',
        'aaabba',
        'aaaabb',
        'aabbbb',
        'bbaabb',
        'bbbbaa',
    ]
    assert_dist_approximately_equal(
        pos_6,
        {possibility: 1/len(possibilities) for possibility in possibilities}
    )
    for length in range(1, 15):
        for _ in range(100):
            pos = gen.random_string(length)
            neg = neg_gen.random_string(length)
            assert regex.match(pos), pos
            assert not regex.match(neg), neg


def test_empty_nonmatch():
    dfa = revex.build_dfa(r'a', alphabet='a')
    gen = NaiveRandomRegularLanguageGenerator(dfa)
    assert gen.random_string(0) is None
    assert gen.random_string(1) == 'a'
    assert gen.random_string(2) == None
