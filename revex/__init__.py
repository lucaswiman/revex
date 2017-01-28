from typing import AnyStr  # noqa


from .derivative import RegularExpression
from .dfa import DEFAULT_ALPHABET
from .dfa import DFA, AlphabetType  # noqa


compile = RegularExpression.compile


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):  # type: (AnyStr, AlphabetType) -> DFA
    return compile(regex).as_dfa(alphabet=alphabet)
