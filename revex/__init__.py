from typing import AnyStr  # noqa


from .derivative import RegularExpression
from .dfa import DEFAULT_ALPHABET
from .dfa import DFA, AlphabetType  # noqa


compile = RegularExpression.compile


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):
    # type: (AnyStr, AlphabetType) -> DFA[RegularExpression, AnyStr]
    return compile(regex).as_dfa(alphabet=alphabet)
