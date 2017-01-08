import re

from revex.derivative import (
    EMPTY, EPSILON, Symbol, Concatenation, Intersection, Union, Complement, Star, RegexVisitor,
    CharSet)


a, b, c = map(Symbol, 'abc')

TYPE_TO_EXAMPLE = {
    # The __new__ hacking (automatic simplification) makes it slightly
    # difficult to construct examples of the different types of objects, here
    # we construct them, then verify the types to set up the tests.
    CharSet: a | b,
    Concatenation: a + b,
    Intersection: (a + b) & Star(a | b),
    Union: Star(a) | Star(b),
    Complement: ~(Star(a)),
    Star: Star(a | b),
}


def compile(regex):
    return RegexVisitor().parse(regex)


def test_type_setup():
    for k, v in TYPE_TO_EXAMPLE.items():
        assert type(v) is k


def test_complementation():
    assert (~(~a).derivative('b')) == EMPTY
    for example in TYPE_TO_EXAMPLE.values():
        assert ~(~example) == example


def test_matching():
    assert (a + b).match('ab')
    assert not (a + b).match('abc')
    assert not a.match('abc')
    assert (~a).match('')
    assert (~a).match('abc')
    assert (~a).match('q')
    assert ((a + b) | c).match('ab')
    assert ((a + b) | c).match('c')
    assert not (a & b).match('a')

    assert (Star(a) & Star(a + a | b)).match('aa')
    assert not (Star(a) & Star(a + a | b)).match('aaa')
    assert (Star(a) & Star(a + a | b)).match('aaaa')


def test_equality_and_construction():
    assert a != b

    # Union/intersection operations should be independent of ordering.
    left, right = Star(a), (Star(a) | Star(b))
    assert (left | right) == (right | left)
    assert (left & right) == (right & left)

    # Complementation should distribute inwards when possible.
    assert isinstance(~TYPE_TO_EXAMPLE[Union], Intersection)
    assert isinstance(~TYPE_TO_EXAMPLE[Intersection], Union)

    assert (a & b) is EMPTY
    assert a + EPSILON == a
    assert EPSILON + a == a
    assert EPSILON + EPSILON == EPSILON
    assert ((a | Star(b)) + (b | Star(a))).accepting

    assert (Star(a) + b).derivative('b') == EPSILON
    assert (Star(a) + b).derivative('a') == Star(a) + b
    assert (Star(a) + b).derivative('c') == EMPTY
    assert Star(EMPTY) is EMPTY
    assert Star(EPSILON) is EPSILON

    assert ~a & b == b
    assert not (a + b != a + b)
    assert a + b != a + c
    assert a.derivative('b') == EMPTY
    assert EMPTY + b == a + EMPTY == EMPTY
    assert a & EMPTY == EMPTY + a == EMPTY
    assert a | EMPTY == EMPTY | a == a
    assert Star(a) & EPSILON == EPSILON & Star(a) == EPSILON
    assert a & EPSILON == EPSILON & a == EMPTY
    assert a & Symbol('a') == a
    assert a | Symbol('a') == a

    assert compile(r'[^ab]') & compile(r'[bc]') == compile('c')
    assert compile(r'[^a]') & compile(r'[a]') == EMPTY
    assert compile(r'[^ab]') & compile(r'[b]') == EMPTY
    assert compile(r'[^ab]') & compile(r'[^bc]') == compile('[^abc]')


def test_concatenation_is_associative():
    assert (a + b) + c == a + (b + c)


def test_union_is_associative():
    assert (Star(a) | Star(b)) | c == Star(a) | (Star(b) | c)


def test_intersection_is_associative():
    assert (
        (Star(a | b | c) & Star(b | c)) & Star(a | b) ==
        (Star(a | b | c) & (Star(b | c) & Star(a | b))))


def test_accepting():
    assert EPSILON.accepting
    assert not EMPTY.accepting
    assert Star(a).accepting
    assert (Star(a) + a).derivative('a').derivative('a').accepting


def test_str_repr():
    assert str(CharSet('abc', negated=True)) == '[^abc]'
    assert str(CharSet('abc', negated=False)) == '[abc]'
    assert str(compile('[acb]*')) == '[abc]*'

    assert str(compile('.*')) == '.*'
    assert repr(compile('.*')) == 'Star(DOT)'
    assert str(compile('..')) == '..'
    assert repr(compile('..')) == 'DOT+DOT'


def test_parser():
    assert compile('ab|c') == (a + b) | c
    assert compile('[a-c]*') == Star(a | b | c)
    assert compile('[abc]') == a | b | c
    assert compile('[^abc]') == CharSet('abc', negated=True)
    assert compile('[^a-c]') == CharSet('abc', negated=True)
    assert compile(r'\.') == CharSet('.', negated=False)
    assert compile(r'[.]') == CharSet('.', negated=False)
    assert compile(r'[\.]') == CharSet('.', negated=False)
    assert compile(r'a?') == a | EPSILON


def test_complex_regex():
    # regex to recognize IPv4 addresses. From
    # https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html  # noqa
    ipv4 = r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    actual = re.compile('^%s$' % ipv4)
    regex = compile(ipv4)
    dfa = regex.as_dfa()
    examples = [
        '127.0.0.1',
        '250.250.250.25',
        '000.000.000.000',
        'abc',
        '256.256.256.256',
        '1234.123.123.123',
    ]
    for example in examples:
        assert 1 == len({bool(actual.match(example)),
                         regex.match(example),
                         dfa.match(example)})
