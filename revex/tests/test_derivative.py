from revex.derivative import (
    EMPTY, EPSILON, Symbol, Concatenation, Intersection, Union, Complement, Star, RegexVisitor)


a, b, c = map(Symbol, 'abc')

TYPE_TO_EXAMPLE = {
    # The __new__ hacking (automatic simplification) makes it slightly
    # difficult to construct examples of the different types of objects, here
    # we construct them, then verify the types to set up the tests.
    Symbol: a,
    Concatenation: a + b,
    Intersection: (a + b) & Star(a | b),
    Union: a | b,
    Complement: ~a,
    Star: Star(a | b),
}

def test_type_setup():
    for k, v in TYPE_TO_EXAMPLE.items():
        assert type(v) is k

def test_complementation():
    assert (~(~a).derivative('b')) == EMPTY
    for example in TYPE_TO_EXAMPLE.values():
        assert ~(~example) == example


def test_matching():
    assert (a + b).matches('ab')
    assert not (a + b).matches('abc')
    assert not a.matches('abc')
    assert (~a).matches('')
    assert (~a).matches('abc')
    assert (~a).matches('q')
    assert ((a + b) | c).matches('ab')
    assert ((a + b) | c).matches('c')
    assert not (a & b).matches('a')

    assert (Star(a) & Star(a + a | b)).matches('aa')
    assert not (Star(a) & Star(a + a | b)).matches('aaa')
    assert (Star(a) & Star(a + a | b)).matches('aaaa')


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


def test_parser():
    assert RegexVisitor().parse('ab|c') == (a + b) | c
    assert RegexVisitor().parse('[a-c]*') == Star(a | b | c)
    assert RegexVisitor().parse('[abc]') == a | b | c
    assert RegexVisitor().parse('[^abc]') == ~a & ~b & ~c
    assert RegexVisitor().parse('[^a-c]') == ~a & ~b & ~c
    from pytest import set_trace; set_trace()
