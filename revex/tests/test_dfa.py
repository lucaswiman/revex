from __future__ import unicode_literals

import re

from hypothesis import given, example
from hypothesis import strategies as st

import revex
from revex.dfa import DFA, get_equivalent_states, minimize_dfa

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
