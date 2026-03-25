"""Tests for the high-level revex API."""
import re

import pytest

import revex


class TestEquivalent:
    def test_identical_regexes(self):
        assert revex.equivalent(r'abc', r'abc')

    def test_reordered_union(self):
        assert revex.equivalent(r'a|b', r'b|a')

    def test_idempotent_star(self):
        assert revex.equivalent(r'(ab)*', r'(ab)*(ab)*')

    def test_not_equivalent(self):
        assert not revex.equivalent(r'a*', r'a+')

    def test_complex_equivalence(self):
        # a? is the same as (a|)
        assert revex.equivalent(r'a?', r'a|')

    def test_character_class_equivalence(self):
        assert revex.equivalent(r'[abc]', r'a|b|c')


class TestIntersects:
    def test_overlapping(self):
        assert revex.intersects(r'a+', r'aaa')

    def test_disjoint(self):
        assert not revex.intersects(r'a+', r'b+')

    def test_partial_overlap(self):
        assert revex.intersects(r'[a-z]+', r'[x-z]+')

    def test_complex_intersection(self):
        # Strings of even length that are also multiples of 3
        assert revex.intersects(r'(aa)*', r'(aaa)*', alphabet='a')

    def test_empty_intersection(self):
        assert not revex.intersects(r'(ab)+', r'(ba)+', alphabet='ab')


class TestIsSubset:
    def test_literal_subset_of_star(self):
        assert revex.is_subset(r'aaa', r'a+')

    def test_star_not_subset_of_literal(self):
        assert not revex.is_subset(r'a+', r'aaa')

    def test_same_language(self):
        assert revex.is_subset(r'a|b', r'b|a')

    def test_charset_subset(self):
        assert revex.is_subset(r'[a-c]', r'[a-z]')

    def test_charset_not_subset(self):
        assert not revex.is_subset(r'[a-z]', r'[a-c]')


class TestSubtract:
    def test_basic_subtract(self):
        r = revex.subtract(r'[a-z]+', r'foo')
        assert r.match('bar')
        assert r.match('baz')
        assert not r.match('foo')
        assert r.match('foobar')

    def test_subtract_from_self(self):
        r = revex.subtract(r'a+', r'a+')
        assert r.as_dfa(alphabet='a').is_empty


class TestSample:
    def test_basic_sample(self):
        s = revex.sample(r'[a-z]{5}', 5, alphabet='abcdefghijklmnopqrstuvwxyz')
        assert s is not None
        assert len(s) == 5
        assert re.match(r'^[a-z]{5}$', s)

    def test_no_match_at_length(self):
        assert revex.sample(r'aaa', 5, alphabet='a') is None

    def test_sample_matches_regex(self):
        for _ in range(20):
            s = revex.sample(r'(ab|cd)+', 4, alphabet='abcd')
            assert s is not None
            assert re.match(r'^(ab|cd)+$', s)


class TestFindExample:
    def test_finds_intersection(self):
        s = revex.find_example(r'a+', r'aaa', alphabet='a')
        assert s == 'aaa'

    def test_no_intersection(self):
        assert revex.find_example(r'a+', r'b+') is None

    def test_complex_intersection(self):
        # Find a string matched by both patterns
        s = revex.find_example(r'[a-c]{3}', r'a.c', alphabet='abc')
        assert s is not None
        assert re.match(r'^[a-c]{3}$', s)
        assert re.match(r'^a.c$', s)


class TestFindDifference:
    def test_finds_difference(self):
        s = revex.find_difference(r'a+', r'aaa', alphabet='a')
        assert s is not None
        assert re.match(r'^a+$', s)
        assert not re.match(r'^aaa$', s)

    def test_no_difference_when_subset(self):
        assert revex.find_difference(r'aaa', r'a+', alphabet='a') is None

    def test_security_bypass_example(self):
        # Simulate: frontend allows [a-z0-9_]+, backend blocks admin.*
        # Find strings the backend blocks but frontend allows
        s = revex.find_difference(
            r'[a-z0-9_]+',
            r'admin[a-z0-9_]*',
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
        )
        assert s is not None
        # Should be something that matches [a-z0-9_]+ but NOT admin.*
        assert re.match(r'^[a-z0-9_]+$', s)
        assert not re.match(r'^admin[a-z0-9_]*$', s)
