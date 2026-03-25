"""
revex — Reversible Regular Expressions

Formal regular expression manipulation using Brzozowski derivatives.
Supports intersection, complement, equivalence checking, and uniform
random string generation.
"""
from typing import Optional, Sequence

from .derivative import RegularExpression  # noqa
from .derivative import RegexVisitor
from .derivative import EMPTY, EPSILON  # noqa
from .dfa import DEFAULT_ALPHABET
from .dfa import DFA, String  # noqa
from .generation import DeterministicRegularLanguageGenerator, RandomRegularLanguageGenerator  # noqa


def compile(regex: str) -> RegularExpression:
    """Parse a regex pattern string into a RegularExpression object."""
    return RegexVisitor().parse(regex)


def build_dfa(regex: str, alphabet=DEFAULT_ALPHABET) -> DFA:
    """Compile a regex into a DFA over the given alphabet."""
    return compile(regex).as_dfa(alphabet=alphabet)


def equivalent(regex1: str, regex2: str, alphabet=DEFAULT_ALPHABET) -> bool:
    """
    Check whether two regexes match exactly the same language.

    >>> equivalent(r'(ab)*', r'(ab)*(ab)*')
    True
    >>> equivalent(r'a|b', r'b|a')
    True
    >>> equivalent(r'a*', r'a+')
    False
    """
    r1 = compile(regex1)
    r2 = compile(regex2)
    # Two regexes are equivalent iff their symmetric difference is empty.
    # L(r1) △ L(r2) = (L(r1) \ L(r2)) ∪ (L(r2) \ L(r1))
    # = (r1 & ~r2) | (r2 & ~r1)
    sym_diff = (r1 & ~r2) | (r2 & ~r1)
    return sym_diff.as_dfa(alphabet=alphabet).is_empty


def intersects(regex1: str, regex2: str, alphabet=DEFAULT_ALPHABET) -> bool:
    """
    Check whether two regexes can match any common string.

    >>> intersects(r'a+', r'aaa')
    True
    >>> intersects(r'a+', r'b+')
    False
    """
    r1 = compile(regex1)
    r2 = compile(regex2)
    return not (r1 & r2).as_dfa(alphabet=alphabet).is_empty


def is_subset(regex1: str, regex2: str, alphabet=DEFAULT_ALPHABET) -> bool:
    """
    Check whether every string matching regex1 also matches regex2.
    i.e., L(regex1) ⊆ L(regex2).

    >>> is_subset(r'aaa', r'a+')
    True
    >>> is_subset(r'a+', r'aaa')
    False
    """
    r1 = compile(regex1)
    r2 = compile(regex2)
    # L(r1) ⊆ L(r2) iff L(r1) ∩ L(~r2) = ∅
    return (r1 & ~r2).as_dfa(alphabet=alphabet).is_empty


def subtract(regex1: str, regex2: str) -> RegularExpression:
    """
    Return a RegularExpression matching strings in regex1 but not regex2.
    i.e., L(regex1) \\ L(regex2).

    >>> r = subtract(r'[a-z]+', r'foo|bar')
    >>> r.match('baz')
    True
    >>> r.match('foo')
    False
    """
    r1 = compile(regex1)
    r2 = compile(regex2)
    return r1 & ~r2


def sample(regex: str, length: int, alphabet=DEFAULT_ALPHABET) -> Optional[str]:
    """
    Generate a random string of exactly the given length matching the regex,
    sampled uniformly at random from all matching strings of that length.

    Returns None if no string of that length matches.

    >>> s = sample(r'[a-z]{5}', 5)
    >>> len(s)
    5
    >>> import re; bool(re.match(r'^[a-z]{5}$', s))
    True
    """
    r = compile(regex)
    dfa = r.as_dfa(alphabet=alphabet)
    gen = RandomRegularLanguageGenerator(dfa)
    return gen.generate_string(length)


def find_example(regex1: str, regex2: str, alphabet=DEFAULT_ALPHABET, max_length: int = 20) -> Optional[str]:
    """
    Find a concrete string matching both regexes, or None if their
    languages don't intersect (up to max_length).

    Useful for security analysis: finding inputs that match two
    different rule sets simultaneously.

    >>> find_example(r'a+', r'aaa')
    'aaa'
    >>> find_example(r'a+', r'b+') is None
    True
    """
    r1 = compile(regex1)
    r2 = compile(regex2)
    intersection = r1 & r2
    dfa = intersection.as_dfa(alphabet=alphabet)
    if dfa.is_empty:
        return None
    gen = DeterministicRegularLanguageGenerator(dfa)
    for s in gen.matching_strings_iter():
        if len(s) <= max_length:
            return s
        break
    return None


def find_difference(regex1: str, regex2: str, alphabet=DEFAULT_ALPHABET, max_length: int = 20) -> Optional[str]:
    """
    Find a concrete string that matches regex1 but NOT regex2, or None
    if regex1 is a subset of regex2 (up to max_length).

    Useful for verifying that a "fixed" regex still covers all cases
    of the original, or finding bypass strings.

    >>> find_difference(r'a+', r'aaa')
    'a'
    >>> find_difference(r'aaa', r'a+') is None
    True
    """
    diff = subtract(regex1, regex2)
    dfa = diff.as_dfa(alphabet=alphabet)
    if dfa.is_empty:
        return None
    gen = DeterministicRegularLanguageGenerator(dfa)
    for s in gen.matching_strings_iter():
        if len(s) <= max_length:
            return s
        break
    return None
