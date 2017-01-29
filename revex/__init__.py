from typing import Sequence  # noqa


from .derivative import RegularExpression
from .dfa import DEFAULT_ALPHABET
from .dfa import DFA, String  # noqa


compile = RegularExpression.compile


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):
    # type: (String, Sequence[String]) -> DFA[RegularExpression[String], String]
    return compile(regex).as_dfa(alphabet=alphabet)
