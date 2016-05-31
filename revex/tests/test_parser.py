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
