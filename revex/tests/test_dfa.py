from __future__ import unicode_literals

import re

import pytest
from hypothesis import given, example
from hypothesis import strategies as st

import revex
from revex.derivative import EPSILON, EMPTY
from revex.dfa import DFA, get_equivalent_states, minimize_dfa, \
    InfiniteLanguageError, EmptyLanguageError

example_regex = revex.compile(r'a[abc]*b[abc]*c')
example_dfa = revex.build_dfa(r'a[abc]*b[abc]*c', alphabet='abcd')
example_builtin_regex = re.compile(r'^a[abc]*b[abc]*c$')


@given(st.text(alphabet='abcd'))
@example('abbbbc')
def test_derivative_matches_builtin(s):
    assert example_regex.match(s) == bool(example_builtin_regex.match(s))


@given(st.text(alphabet='abcd'))
@example('abbbbc')
def test_dfa_matches_builtin(s):
    assert example_dfa.match(s) == bool(example_builtin_regex.match(s))


def test_equivalent_state_computation():
    # Construct a DFA where all states are equivalent to each other.
    alphabet = '01'
    dfa = DFA(0, True, alphabet=alphabet)
    dfa.add_state(1, True)
    dfa.add_state(2, True)
    dfa.add_state(3, True)
    dfa.add_transition(0, 1, '0')
    dfa.add_transition(0, 0, '1')
    dfa.add_transition(1, 2, '0')
    dfa.add_transition(1, 1, '1')
    dfa.add_transition(2, 3, '0')
    dfa.add_transition(2, 2, '1')
    dfa.add_transition(3, 0, '0')
    dfa.add_transition(3, 3, '1')
    equivalent = get_equivalent_states(dfa)
    states = [0, 1, 2, 3]
    assert equivalent == {(p, q) for p in states for q in states}

    new_dfa = minimize_dfa(dfa)
    assert len(new_dfa.node) == 1


def test_equivalent_state_example():
    # Construct the DFA in this example:
    # https://www.tutorialspoint.com/automata_theory/dfa_minimization.htm
    alphabet = '01'
    a, b, c, d, e, f = states = 'abcdef'
    dfa = DFA(a, False, alphabet=alphabet)
    dfa.add_state(b, False)
    dfa.add_state(c, True)
    dfa.add_state(d, True)
    dfa.add_state(e, True)
    dfa.add_state(f, False)

    assert set(dfa.find_invalid_nodes()) == set(states)

    dfa.add_transition(a, b, '0')
    dfa.add_transition(a, c, '1')
    assert set(dfa.find_invalid_nodes()) == set(states) - {a}

    dfa.add_transition(b, a, '0')
    dfa.add_transition(b, d, '1')
    assert set(dfa.find_invalid_nodes()) == set(states) - {a, b}

    dfa.add_transition(c, e, '0')
    dfa.add_transition(c, f, '1')
    assert set(dfa.find_invalid_nodes()) == set(states) - {a, b, c}

    dfa.add_transition(d, e, '0')
    dfa.add_transition(d, f, '1')
    assert set(dfa.find_invalid_nodes()) == set(states) - {a, b, c, d}

    dfa.add_transition(e, e, '0')
    dfa.add_transition(e, f, '1')
    assert set(dfa.find_invalid_nodes()) == set(states) - {a, b, c, d, e}

    dfa.add_transition(f, f, '0')
    dfa.add_transition(f, f, '1')
    assert not dfa.find_invalid_nodes()

    expected = {(a, b), (c, d), (c, e), (d, e)}
    expected |= {(x, x) for x in states}
    expected |= {(p, q) for (q, p) in expected}

    equivalent = get_equivalent_states(dfa)
    assert equivalent == expected
    new_dfa = minimize_dfa(dfa)
    assert not new_dfa.find_invalid_nodes()

    expected_dfa = DFA('ab', False, alphabet=alphabet)
    expected_dfa.add_state('cde', True)
    expected_dfa.add_state('f', False)

    expected_dfa.add_transition('ab', 'ab', '0')
    expected_dfa.add_transition('ab', 'cde', '1')
    expected_dfa.add_transition('cde', 'cde', '0')
    expected_dfa.add_transition('cde', 'f', '1')
    expected_dfa.add_transition('f', 'f', '0')
    expected_dfa.add_transition('f', 'f', '1')

    assert not expected_dfa.construct_isomorphism(dfa)
    assert expected_dfa.construct_isomorphism(new_dfa)


def test_has_finite_language():
    assert revex.build_dfa('aa').has_finite_language
    assert not revex.build_dfa('aa*').has_finite_language
    assert revex.build_dfa('a(bc|cd|aaa)').has_finite_language
    assert not revex.build_dfa('a(bc*|cd|aaa)').has_finite_language
    assert not (~EPSILON).as_dfa().has_finite_language
    assert EMPTY.as_dfa().has_finite_language
    assert not (~EMPTY).as_dfa().has_finite_language


def test_is_empty():
    assert not (~EPSILON).as_dfa().is_empty
    assert not EPSILON.as_dfa().is_empty
    assert EMPTY.as_dfa().is_empty
    assert (revex.compile('a*|b*') & revex.compile('c+')).as_dfa('abc').is_empty


def test_longest_string():
    ip = revex.compile(
        r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)')
    assert ip.as_dfa('0123456789.').has_finite_language
    assert len(ip.as_dfa('0123456789.').longest_string) == 15
    assert ip.match(ip.as_dfa('0123456789.').longest_string)

    with pytest.raises(InfiniteLanguageError):
        (revex.compile(r'([ab]{4})*') & revex.compile(r'([ab]{3})*')).as_dfa('ab').longest_string

    assert (revex.compile(r'(ab)*') & revex.compile(r'(ba)*')).as_dfa('ab').has_finite_language
    assert (revex.compile(r'(ab)*') & revex.compile(r'(ba)*')).as_dfa('ab').longest_string == ''

    assert (revex.compile(r'(ab)+') & revex.compile(r'(ba)+')).as_dfa('ab').has_finite_language
    with pytest.raises(EmptyLanguageError):
        (revex.compile(r'(ab)+') & revex.compile(r'(ba)+')).as_dfa('ab').longest_string

    assert EPSILON.as_dfa().longest_string == ''
