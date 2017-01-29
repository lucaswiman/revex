from typing import Sequence  # noqa

from .derivative import RegularExpression  # noqa
from .derivative import RegexVisitor
from .dfa import DEFAULT_ALPHABET
from .dfa import DFA, String  # noqa


def compile(regex):  # type: (String) -> RegularExpression
    return RegexVisitor().parse(regex)


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):
    # type: (String, Sequence[String]) -> DFA[RegularExpression]
    return compile(regex).as_dfa(alphabet=alphabet)
