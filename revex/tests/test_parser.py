from itertools import islice

from revex.machine import RegularLanguageMachine


def test_string_literal_regex():
    machine = RegularLanguageMachine('abc')
    assert machine.match('abc')
    assert not machine.match('abcd')
    assert not machine.match('ab')


def test_star():
    machine = RegularLanguageMachine('a*')
    assert machine.match('')
    assert machine.match('a')
    assert machine.match('aa')
    assert not machine.match('b')


def test_plus():
    machine = RegularLanguageMachine('a+')
    assert not machine.match('')
    assert machine.match('a')
    assert machine.match('aa')
    assert not machine.match('b')


def test_union():
    machine = RegularLanguageMachine('a|b|c')
    assert machine.match('a')
    assert machine.match('b')
    assert machine.match('c')
    assert not machine.match('abc')


def test_group():
    machine = RegularLanguageMachine('(ab)+')
    assert machine.match('ab')
    assert machine.match('abab')
    assert not machine.match('aba')


def test_char_range():
    machine = RegularLanguageMachine('[-a-z1-9]')
    assert machine.match('a')
    assert machine.match('b')
    assert machine.match('z')
    assert machine.match('5')
    assert machine.match('-')
    assert not machine.match(',')
    assert not machine.match('0')


def test_complex_regex():
    # regex to recognize IPv4 addresses. From
    # https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html  # nopep8
    ipv4 = r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    import re
    actual = re.compile(ipv4)
    machine = RegularLanguageMachine(ipv4)
    assert actual.match('127.0.0.1')
    assert machine.match('127.0.0.1')
    assert actual.match('250.250.250.25')
    assert machine.match('250.250.250.25')
    for expr in islice(machine.reverse_string_iter(), 0, 10000):
        assert machine.match(expr)
        assert actual.match(expr)


def test_that_various_regexes_should_parse():
    m1 = RegularLanguageMachine('a+(bc)*')
    assert m1.match('aaa')
    assert m1.match('abcbc')
    m2 = RegularLanguageMachine('a+(bc)*[0-9]')
    assert m2.match('abc0')
    assert not m2.match('abcc0')
