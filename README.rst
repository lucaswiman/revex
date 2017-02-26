==========================
REVEX: REVerse Expressions
==========================

This library generates examples given regular expressions. The main intention of this library is for use in software testing:

- Property based testing of validation regular expressions (e.g. for a phone number). Example generation allows you to check that the values recognized by the validation can actually be processed elsewhere in the system.
- Fake data generation for use in test suites. For example, this could allow a very flexible backend for something like the `faker <http://faker.readthedocs.io/en/master/>`_ package.

It can also be used for some kinds of analysis on regular languages, for example determining:

- Whether a regular expression recognizes a finite language.
- Whether two regular expressions are equivalent, or can be jointly satisfied.
- Visualization of DFAs.

The roadmap for this project includes supporting random generation of strings matching arbitrary context-free BNF grammars, which should allow significantly expanding the set of data which can be generated (e.g. JSON documents matching a spec.)

Installation
------------

    .. code-block:: python

        pip install revex

Usage Examples
--------------

Consider the language of strings on the alphabet `abc`, which begin with b and have length congruent to 10 mod 15. This can be represented as follows:

    .. code-block:: python

        >>> from revex import compile
        >>> r = (compile('b([abc]{3})*') & compile('([abc]{5})*'))
        >>> print(r)
        (b([abc][abc][abc])*)∩([abc][abc][abc][abc][abc])*
        >>> r.as_dfa('abc')._draw(full=True)

Which generates the following visualization:

.. image:: https://cloud.githubusercontent.com/assets/123110/21747066/c2a956f2-d50f-11e6-9f5a-90e79cd6cf06.png

We can also introspect aspects of the language, and generate examples which match the regular expression:

    .. code-block:: python

        >>> r.as_dfa('abc').has_finite_language
        False
        >>> (r & compile('a{0,50}')).as_dfa('abc').has_finite_language
        True
        >>> from revex.generation import *
        >>> RandomRegularLanguageGenerator(r.as_dfa('abc')).generate_string(9)
        >>> RandomRegularLanguageGenerator(r.as_dfa('abc')).generate_string(10)
        'baaaacaabc'
        >>> RandomRegularLanguageGenerator(r.as_dfa('abc')).generate_string(10)
        'bacabbabbc'
        >>> RandomRegularLanguageGenerator(r.as_dfa('abc')).generate_string(10)
        'babcababaa'
        >>> list(DeterministicRegularLanguageGenerator((r & compile('b(a{0,50})')).as_dfa('abc')).matching_strings_iter())
        ['baaaaaaaaa', 'baaaaaaaaaaaaaaaaaaaaaaaa', 'baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']

`RandomRegularLanguageGenerator.generate_string(n)` will choose a string of length n *uniformly at random* among strings of length `n` matched by the regular expression. For example, consider the following regular expression, which matches comma-separated lists of numbers 01-20:

    .. code-block:: python

        >>> from revex import compile
        >>> from revex.generation import RandomRegularLanguageGenerator
        >>> from collections import Counter
        >>> import random
        >>> d20 = compile(r'((0[1-9]|1[0-9]|20),)*(0[1-9]|1[0-9]|20)')
        >>> gen = RandomRegularLanguageGenerator(d20.as_dfa(',0123456789'))
        >>> gen.generate_string(3 * 10 - 1)
        '10,18,03,04,09,20,01,11,06,05'
        >>> rolls = gen.generate_string(3 * 20000 - 1)
        >>> counts = Counter(rolls.split(','))
        >>> counts.values()
        dict_values([1042, 979, 975, 1013, 1042, 1043, 995, 996, 967, 986, 961, 1002, 986, 1032, 1040, 1068, 926, 963, 978, 1006])
        >>> max(counts.values()) - min(counts.values())
        142
        >>> random_counts = Counter(random.choice(range(20)) for _ in range(20000))
        >>> max(random_counts.values()) - min(random_counts.values())
        176

Here's another example, playing with a simple regex for validating ipv4 IPs:

    .. code-block:: python

        >>> from revex.dfa import construct_integer_dfa
        >>> ipv4 = compile(r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)').as_dfa('0123456789.')
        >>> ipv4.longest_string
        '000.000.000.000'
        >>> [gen.generate_string(length) for length in range(0, len(ipv4.longest_string) + 1)]
        [None, None, None, None, None, None, None, '8.2.2.4', '9.2.80.8', '2.63.58.8', '9.43.231.6', '241.5.3.155', '054.40.18.72', '121.63.97.176', '127.45.197.203', '139.035.147.186']
        >>> construct_integer_dfa(ipv4)._draw()

.. image:: https://cloud.githubusercontent.com/assets/123110/21747203/1bd5031c-d514-11e6-9db7-a18dd9dfd539.png
    :width: 800px
    :align: center

How does it work?
-----------------

Regular expressions are parsed using a custom grammar into an abstract syntax tree. The syntax tree is processed using `the Brzozowski derivative <http://www.ccs.neu.edu/home/turon/re-deriv.pdf>`_ into a `deterministic finite automaton (DFA) <https://en.wikipedia.org/wiki/Deterministic_finite_automaton>`_. Random strings are generated by counting walks of the given length to any accepting states in the DFA to create a discrete probability distribution at each state in the DFA. The DFA is then traversed according to this distribution, and the set of randomly chosen transitions are a string recognized by the DFA.
