from revex.machine import RegularLanguageMachine


def test_literal_matches():
    machine = RegularLanguageMachine()
    machine.add_literals(['abc', ' ', 'do', ' ', 're', ' ', 'me'])
    assert machine.match('abc do re me')
    assert not machine.match('abc do re you')
    assert len(list(machine.match_iter('abc do re me'))) == 1
    machine.add_literals(['abc do re me'])
    assert len(list(machine.match_iter('abc do re me'))) == 2
    machine.add_literals(['abc do ', 're me'])
    assert len(list(machine.match_iter('abc do re me'))) == 3
    machine.add_literals(['abc do'])
    assert len(list(machine.match_iter('abc do'))) == 1
    assert len(list(machine.match_iter('abc do re me'))) == 3
