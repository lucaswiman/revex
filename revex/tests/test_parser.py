from itertools import islice
import re

from revex.machine import RegularLanguageMachine
from revex.derivative import RegularExpression


def test_string_literal_regex():
    regex = RegularExpression.compile('abc')
    assert regex.match('abc')
    assert not regex.match('abcd')
    assert not regex.match('ab')


def test_star():
    regex = RegularExpression.compile('a*')
    assert regex.match('')
    assert regex.match('a')
    assert regex.match('aa')
    assert not regex.match('b')


def test_plus():
    regex = RegularExpression.compile('a+')
    assert not regex.match('')
    assert regex.match('a')
    assert regex.match('aa')
    assert not regex.match('b')


def test_union():
    regex = RegularExpression.compile('a|b|c')
    assert regex.match('a')
    assert regex.match('b')
    assert regex.match('c')
    assert not regex.match('abc')


def test_group():
    regex = RegularExpression.compile('(ab)+')
    assert regex.match('ab')
    assert regex.match('abab')
    assert not regex.match('aba')


def test_char_range():
    regex = RegularExpression.compile('[-a-z1-9]')
    assert regex.match('a')
    assert regex.match('b')
    assert regex.match('z')
    assert regex.match('5')
    assert regex.match('-')
    assert not regex.match(',')
    assert not regex.match('0')


def test_initial_substring():
    regex = RegularExpression.compile('[a][b][c][d][e]')
    assert regex.match('abcde')
    # This terminates the search before reaching the exit node of the graph.
    # We shouldn't match or continue trying to traverse the string.
    assert not regex.match('abc')


def test_complex_regex():
    # regex to recognize IPv4 addresses. From
    # https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9780596802837/ch07s16.html  # noqa
    ipv4 = r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    actual = re.compile('^%s$' % ipv4)
    regex = RegularLanguageMachine(ipv4)
    assert actual.match('127.0.0.1')
    assert regex.match('127.0.0.1')
    assert actual.match('250.250.250.25')
    assert regex.match('250.250.250.25')
    for expr in islice(regex.reverse_string_iter(), 0, 10000):
        assert regex.match(expr)
        assert actual.match(expr)


def test_that_various_regexes_should_parse():
    m1 = RegularExpression.compile('a+(bc)*')
    assert m1.match('aaa')
    assert m1.match('abcbc')
    m2 = RegularExpression.compile('a+(bc)*[0-9]')
    assert m2.match('abc0')
    assert not m2.match('abcc0')
    m3 = RegularExpression.compile('(a[b-c]*|[x-z]+)')
    assert m3.match('abbb')
    assert m3.match('zxy')
    assert not m3.match('ax')


def test_dot_any():
    m = RegularExpression.compile('.+')
    assert m.match('a')
    assert m.match('b')


def test_inverted_charset():
    m = RegularExpression.compile('[^abc]')
    assert m.match('d')
    assert not m.match('a')
    assert not m.match('b')
    assert not m.match('c')


def test_inverted_range():
    m = RegularExpression.compile('[^a-c]')
    assert m.match('d')
    assert not m.match('a')
    assert not m.match('b')
    assert not m.match('c')


def test_inverted_range_and_charset():
    m = RegularExpression.compile('[^h-jab-def]')
    for c in 'gklmnopqrstuvwxyz':
        assert m.match(c)
    for c in 'abcdefhij':
        assert not m.match(c)
    assert m.match('-')
    assert m.match('^')


def test_open_ended_range():
    m = RegularExpression.compile('a{,5}')
    for i in range(6):
        assert m.match('a' * i)
    assert not m.match('a' * 6)
    m2 = RegularExpression.compile('a{3,}')
    for i in range(3):
        assert not m2.match('a' * i)
    for i in range(3, 10):
        assert m2.match('a' * i)


def test_repeat():
    regex = RegularExpression.compile('a{0,2}[a-z]')
    assert regex.match('q')
    assert regex.match('a' * 1 + 'q')
    assert regex.match('a' * 2 + 'q')
    assert not regex.match('a' * 3 + 'q')
