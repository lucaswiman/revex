from itertools import islice

import pytest
import re

from revex.machine import RegularLanguageMachine, Epsilon, LiteralMatcher


def add_literals(machine, literals):
    node = machine.enter
    for literal in literals:
        in_node = node
        node = machine.node_factory()
        machine.add_edge(in_node, node, matcher=LiteralMatcher(literal))
    machine.add_edge(node, machine.exit, matcher=Epsilon)


def test_literal_matches():
    machine = RegularLanguageMachine()
    add_literals(machine, ['abc', ' ', 'do', ' ', 're', ' ', 'me'])
    assert machine.match('abc do re me')
    assert not machine.match('abc do re you')
    assert len(list(machine.match_iter('abc do re me'))) == 1
    add_literals(machine, ['abc do re me'])
    assert len(list(machine.match_iter('abc do re me'))) == 2
    add_literals(machine, ['abc do ', 're me'])
    assert len(list(machine.match_iter('abc do re me'))) == 3
    add_literals(machine, ['abc do'])
    assert len(list(machine.match_iter('abc do'))) == 1
    assert len(list(machine.match_iter('abc do re me'))) == 3


def test_reverse_matching_finite():
    machine = RegularLanguageMachine()
    add_literals(machine, ['a', 'b', 'c'])
    assert len(list(machine.reverse_match_iter())) == 1
    add_literals(machine, ['d', 'e', 'f'])
    assert len(list(machine.reverse_match_iter())) == 2
    assert set(machine.reverse_string_iter()) == {'abc', 'def'}


def test_reverse_star():
    # Test that a hand-constructed machine corresponding to (ab)* works as
    # expected.
    machine = RegularLanguageMachine()
    machine.add_edge(machine.enter, '*', matcher=Epsilon)
    node = machine.node_factory()
    machine.add_edge('*', node, matcher=LiteralMatcher('a'))
    machine.add_edge(node, '*', matcher=LiteralMatcher('b'))
    machine.add_edge('*', machine.exit, matcher=Epsilon)
    assert set(islice(machine.reverse_string_iter(), 0, 4)) == \
           {'', 'ab', 'abab', 'ababab'}
    # Now add edges to make the regex equivalent to (ab|cd)*
    node = machine.node_factory()
    machine.add_edge('*', node, matcher=LiteralMatcher('c'))
    machine.add_edge(node, '*', matcher=LiteralMatcher('d'))
    assert set(islice(machine.reverse_string_iter(), 0, 7)) == \
           {'', 'ab', 'cd', 'abcd', 'cdab', 'abab', 'cdcd'}


@pytest.mark.parametrize('regex', [
    r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
    r'([a][b][c])*',

    # Email regex from http://www.regular-expressions.info/email.html
    r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z][A-Z]+',
])
def test_random_walk_matches_regex(regex):
    actual = re.compile(regex)
    machine = RegularLanguageMachine(regex)
    for _ in range(100):
        rand_string = machine.reverse_random_string()
        assert actual.match(rand_string), '%s should match %s' % (regex, rand_string)
        assert machine.match(rand_string), '%s should match %s' % (regex, rand_string)
