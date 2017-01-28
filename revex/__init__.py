from typing import AnyStr


from .derivative import RegularExpression
from .dfa import DEFAULT_ALPHABET, DFA, AlphabetType


compile = RegularExpression.compile


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):  # type: (AnyStr, AlphabetType) -> DFA
    return compile(regex).as_dfa(alphabet=alphabet)
