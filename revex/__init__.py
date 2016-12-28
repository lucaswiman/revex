from .derivative import RegularExpression
from .machine import DEFAULT_ALPHABET


compile = RegularExpression.compile


def build_dfa(regex, alphabet=DEFAULT_ALPHABET):
    return compile(regex).as_dfa(alphabet=alphabet)
