# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import string

import hypothesis
import pytest
from hypothesis import strategies as st

from revex import compile
from revex.derivative import REGEX, EPSILON
from revex.regex_grammar import ESCAPABLE_CHARS, CHARSET_ESCAPABLE_CHARS


class RE(object):
    def __init__(self, pattern):
        self.base_re = re.compile(r'\A(%s)\Z' % pattern)
        self.re = compile(pattern)

    def match(self, string):
        assert bool(self.base_re.match(string)) == self.re.match(string)
        return self.re.match(string)


def test_empty():
    assert compile('') == EPSILON
    assert RE('(a|)').match('')
    assert RE('(a|)').match('a')
    assert RE('a|').match('')
    assert RE('a|').match('a')


def test_string_literal_regex():
    regex = RE('abc')
    assert regex.match('abc')
    assert not regex.match('abcd')
    assert not regex.match('ab')


def test_star():
    regex = RE('a*')
    assert regex.match('')
    assert regex.match('a')
    assert regex.match('aa')
    assert not regex.match('b')


def test_plus():
    regex = RE('a+')
    assert not regex.match('')
    assert regex.match('a')
    assert regex.match('aa')
    assert not regex.match('b')


def test_union():
    regex = RE('a|b|c')
    assert regex.match('a')
    assert regex.match('b')
    assert regex.match('c')
    assert not regex.match('abc')


def test_group():
    regex = RE('(ab)+')
    assert regex.match('ab')
    assert regex.match('abab')
    assert not regex.match('aba')


def test_char_range():
    regex = RE('[-a-z1-9]')
    assert regex.match('a')
    assert regex.match('b')
    assert regex.match('z')
    assert regex.match('5')
    assert regex.match('-')
    assert not regex.match(',')
    assert not regex.match('0')


def test_initial_substring():
    regex = RE('[a][b][c][d][e]')
    assert regex.match('abcde')
    # This terminates the search before reaching the exit node of the graph.
    # We shouldn't match or continue trying to traverse the string.
    assert not regex.match('abc')


def test_that_various_regexes_should_parse():
    m1 = RE('a+(bc)*')
    assert m1.match('aaa')
    assert m1.match('abcbc')
    m2 = RE('a+(bc)*[0-9]')
    assert m2.match('abc0')
    assert not m2.match('abcc0')
    m3 = RE('(a[b-c]*|[x-z]+)')
    assert m3.match('abbb')
    assert m3.match('zxy')
    assert not m3.match('ax')


def test_dot_any():
    m = RE('.+')
    assert m.match('a')
    assert m.match('b')


def test_inverted_charset():
    m = RE('[^abc]')
    assert m.match('d')
    assert not m.match('a')
    assert not m.match('b')
    assert not m.match('c')


def test_inverted_range():
    m = RE('[^a-c]')
    assert m.match('d')
    assert not m.match('dlaskdfmlksadmfl')
    assert not m.match('a')
    assert not m.match('b')
    assert not m.match('c')


def test_inverted_range_and_charset():
    m = RE('[^h-jab-def]')
    for c in 'gklmnopqrstuvwxyz':
        assert m.match(c)
    for c in 'abcdefhij':
        assert not m.match(c)
    assert m.match('-')
    assert m.match('^')


def test_open_ended_range():
    m = RE('a{,5}')
    for i in range(6):
        assert m.match('a' * i)
    assert not m.match('a' * 6)
    m2 = RE('a{3,}')
    for i in range(3):
        assert not m2.match('a' * i)
    for i in range(3, 10):
        assert m2.match('a' * i)


def test_repeat():
    regex = RE('a{0,2}[a-z]')
    assert regex.match('q')
    assert regex.match('a' * 1 + 'q')
    assert regex.match('a' * 2 + 'q')
    assert not regex.match('a' * 3 + 'q')

    assert compile('a{3}') == compile('aaa')

    assert compile('ba{3}') == compile('baaa')
    assert compile('(ba){3}') == compile('bababa')

    assert RE('{').match('{')
    assert RE('a{}').match('a{}')


def test_character_class_space():
    assert RE(r'\s+').match('\n\t ')
    assert not RE(r'\s+').match('\\s')
    assert RE(r'\S+').match('ab')
    assert not RE(r'\S+').match('\n\t ')
    assert not RE(r'\S+').match('a b')


def test_character_class_digit():
    assert RE(r'\d+').match('123')
    assert not RE(r'\d+').match('abc')
    assert not RE(r'\D+').match('123')
    assert RE(r'\D+').match('abc')


def test_character_class_word():
    assert RE(r'\w+').match('aA0_')
    assert not RE(r'\W+').match('aA0_')


def test_comment():
    assert RE(r'f(?# comment )oo').match('foo')
    assert RE(r'f(?# also (a comment \) )oo').match('foo')


def test_noncapturing_group():
    # Non-capturing groups aren't semantically meaningful yet, but shouldn't
    # lead to syntax errors.
    assert RE(r'f(?:oo)').match('foo')


def test_lookaround_grammar():
    assert REGEX.parse(r'foo(?=bar).*')
    assert REGEX.parse(r'foo(?=bar)')
    assert REGEX.parse(r'foo(?=(ab)*)')
    assert REGEX.parse(r'foo(?!bar)')
    assert REGEX.parse(r'.*(?<=bar)foo')
    assert REGEX.parse(r'.*(?<!bar)foo')
    RE(r'foo(?=bar).*')


def test_lookaround_match():
    assert RE(r'foo(?=bar).*').match('foobarasdf')
    assert RE(r'foo(?=bar).*').match('foobar')
    assert not RE(r'foo(?!bar).*').match('foobar')
    assert RE(r'foo(?!bar).*').match('foobaz')
    assert not RE(r'foo(?=bar)').match('foobar')

    assert RE(r'.*(?<=foo)bar').match('foobar')
    assert not RE(r'.*(?<=foo)bar').match('foodbar')

    assert not RE(r'.*(?<!foo)bar').match('foobar')
    assert RE(r'.*(?<!foo)bar').match('foodbar')


def test_grouped_lookaround():
    assert RE(r'(a(?=bar).).*(?=baz).*').match('abarbbaz')
    assert RE(r'(a(?=bar)).*(?=baz).*').match('abarbbaz')
    assert RE(r'a((a(?=bar))|c).*').match('ac')
    assert RE(r'a(a(?=bar)|c).*').match('ac')
    assert RE(r'a(a(?=bar)|c).*').match('aabar')

    assert not RE(r'(a(?!bar).).*(?=baz).*').match('abarbbaz')
    assert not RE(r'(a(?!bar)).*(?=baz).*').match('abarbbaz')
    assert RE(r'a((a(?!bar))|c).*').match('ac')
    assert RE(r'a(a(?!bar)|c).*').match('ac')
    assert not RE(r'a(a(?!bar)|c).*').match('aabar')


def test_escaped_characters():
    assert 'a' == '\x61'
    assert 'b' == '\u0062'
    assert 'c' == '\143'
    assert RE(r'\x61\u0062\143').match('abc')
    assert RE(r'[\x61][\u0062][\143]').match('abc')
    assert RE(r'[\x61-\143]+').match('abc')
    assert RE(r'\u00a3\u00A3').match('££')
    assert RE(r'\U0001f62b').match(u'😫')
    assert RE(r'\x00').match('\x00')
    assert RE(r'\u0000').match('\x00')
    assert RE(r'\000').match('\x00')

    assert RE(r'[\)]').match(')')
    assert not RE(r'[\)]').match('\\')

    assert RE(r'[[]').match('[')
    assert RE(r'[\]]').match(']')
    assert not RE(r'[\]]').match('\\')
    assert RE(r']').match(']')
    assert RE(r'\[a]').match('[a]')
    assert RE(r'\[\[]').match('[[]')
    assert RE(r'[\]]').match(']')
    assert RE(r'[a]\]').match('a]')
    assert RE(r'\{}').match('{}')

    escapable_chars = '.$^\\*+()|{}?]['
    for char in escapable_chars:
        assert RE(r'\%s' % char).match(char)
    for char in escapable_chars:
        assert RE(r'[\%s]' % char).match(char)

    assert RE(r'\r').match('\r')
    assert RE(r'\n').match('\n')
    assert RE(r'\t').match('\t')
    assert RE(r'\v').match('\v')


def test_escaped_character_range():
    assert re.compile(r'[\x61-\u0062]*').match('ab')
    assert RE(r'[\x61-\u0062]*').match('ab')


def test_email_validation_example():
    # Regression test for parsing bug discovered when examining an email
    # validation regex from http://emailregex.com/
    regex = r'''(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])'''   # noqa
    assert RE(regex).match('foo@bar.com')


def test_url_validation_example():
    # Regression test for severe performance bug discovered when examining a
    # URL validation regex from https://mathiasbynens.be/demo/url-regex
    # (@diegoperini)
    regex = r'(?:(?:https?|ftp)://)(?:\S+(?::\S*)?@)?(?:(?!10(?:\.\d{1,3}){3})(?!127(?:\.\d{1,3}){3})(?!169\.254(?:\.\d{1,3}){2})(?!192\.168(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))(?::\d{2,5})?(?:/[^\s]*)?'  # noqa
    assert REGEX.parse(regex)
    assert RE(regex).match('http://foo.com/bar')


@hypothesis.given(
    st.text(min_size=1, max_size=1),
    st.sampled_from(ESCAPABLE_CHARS),
)
@hypothesis.settings()
@hypothesis.example('\n', '\\')
def test_escaped_char(char, escapee):
    RE(r'\{escapee}'.format(escapee=escapee)).match(char)  # Asserts the same as builtin re.compile.
    RE(r'\{escapee}'.format(escapee=escapee)).match('\\' + char)


@hypothesis.given(
    st.text(min_size=1, max_size=1),
    st.sampled_from(CHARSET_ESCAPABLE_CHARS),
)
def test_escaped_char_range_endpoint(char, escapee):
    RE(r'[\{escapee}-\{escapee}]'.format(escapee=escapee)).match(char)


@hypothesis.given(
    st.text(min_size=1, max_size=1),
    st.sampled_from(CHARSET_ESCAPABLE_CHARS),
)
def test_escaped_char_set(char, escapee):
    RE(r'[\{escapee}]'.format(escapee=escapee)).match(char)


@hypothesis.given(
    st.sampled_from(string.printable),
    st.sampled_from('wWdDsSnrt'),
)
def test_special_charset_chars(char, escapee):
    RE(r'[\{escapee}]'.format(escapee=escapee)).match(char)


@pytest.mark.xfail(
    reason='TODO: correctly handle charclasses outside of ASCII range',
    raises=AssertionError,
)
def test_special_charset_chars_unicode():
    assert RE(r'[\w]').match('ª')


@hypothesis.given(st.text(min_size=1, max_size=1))
def test_hard_character_range_example(char):
    # Via https://twitter.com/mountain_ghosts/status/847130837644709888
    regex = r'[ -\/:-@\[-`\{-~]'
    assert REGEX.parse(regex)
    RE(regex).match(char)  # Asserts the same as builtin re.compile.
