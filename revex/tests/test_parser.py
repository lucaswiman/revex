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
