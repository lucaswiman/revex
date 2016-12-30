from __future__ import unicode_literals

import re

from hypothesis import given, example
from hypothesis import strategies as st

import revex


example_regex = revex.compile(r'a[abc]*b[abc]*c')
example_dfa = example_regex.as_dfa(alphabet='abcd')
example_builtin_regex = re.compile(r'^a[abc]*b[abc]*c$')


@given(st.text(alphabet='abcd'))
@example('abbbbc')
def test_derivative_matches_builtin(s):
    assert example_regex.match(s) == bool(example_builtin_regex.match(s))


@given(st.text(alphabet='abcd'))
@example('abbbbc')
def test_dfa_matches_builtin(s):
    assert example_dfa.matches(s) == bool(example_builtin_regex.match(s))
