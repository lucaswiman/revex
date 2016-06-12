from itertools import islice
import re

import itertools

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


def test_initial_substring():
    machine = RegularLanguageMachine('[a][b][c][d][e]')
    assert machine.match('abcde')
    # This terminates the search before reaching the exit node of the graph.
    # We shouldn't match or continue trying to traverse the string.
    assert not machine.match('abc')


def test_complex_regex():
    # regex to recognize IPv4 addresses. From
    # https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html  # nopep8
    ipv4 = r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    actual = re.compile('^%s$' % ipv4)
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
    m3 = RegularLanguageMachine('(a[b-c]*|[x-z]+)')
    assert m3.match('abbb')
    assert m3.match('zxy')
    assert not m3.match('ax')


def test_dot_any():
    m = RegularLanguageMachine('.+')
    assert m.match('a')
    assert m.match('b')


def test_inverted_charset():
    m = RegularLanguageMachine('[^abc]')
    assert m.match('d')
    assert not m.match('a')
    assert not m.match('b')
    assert not m.match('c')


def test_open_ended_range():
    m = RegularLanguageMachine('a{,5}')
    for i in range(6):
        assert m.match('a' * i)
    assert not m.match('a' * 6)
    m2 = RegularLanguageMachine('a{3,}')
    for i in range(3):
        assert not m2.match('a' * i)
    for i in range(3, 10):
        assert m2.match('a' * i)


def test_buggy_machine_building():
    # Fun non-deterministic bug in constructing some machines.
    node_factory = itertools.count()
    for _ in range(8):
        m = RegularLanguageMachine('a{0,2}[a-z]', node_factory=node_factory)
        assert not m.match('a' * 3 + 'q')
