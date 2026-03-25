API Reference
=============

High-Level Functions
--------------------

These are the main entry points for using revex. They accept regex
pattern strings and return results directly.

.. autofunction:: revex.compile

.. autofunction:: revex.build_dfa

.. autofunction:: revex.equivalent

.. autofunction:: revex.intersects

.. autofunction:: revex.is_subset

.. autofunction:: revex.subtract

.. autofunction:: revex.sample

.. autofunction:: revex.find_example

.. autofunction:: revex.find_difference


RegularExpression Classes
--------------------------

The internal regex representation. You typically get these from
:func:`revex.compile` rather than constructing them directly.

.. autoclass:: revex.derivative.RegularExpression
   :members: match, derivative, accepting, as_dfa

Operators on ``RegularExpression`` objects:

- ``r1 + r2`` — Concatenation
- ``r1 | r2`` — Union
- ``r1 & r2`` — Intersection
- ``~r`` — Complement
- ``r * n`` — Repeat *n* times

.. autoclass:: revex.derivative.CharSet
.. autoclass:: revex.derivative.CharClass
.. autoclass:: revex.derivative.Concatenation
.. autoclass:: revex.derivative.Union
.. autoclass:: revex.derivative.Intersection
.. autoclass:: revex.derivative.Complement
.. autoclass:: revex.derivative.Star


DFA
---

.. autoclass:: revex.dfa.DFA
   :members: match, add_state, add_transition, is_empty, has_finite_language,
             longest_string, find_invalid_nodes, construct_isomorphism

.. autofunction:: revex.dfa.get_equivalent_states

.. autofunction:: revex.dfa.minimize_dfa

.. autofunction:: revex.dfa.construct_integer_dfa


String Generation
-----------------

.. autoclass:: revex.generation.RandomRegularLanguageGenerator
   :members: generate_string, valid_lengths_iter

.. autoclass:: revex.generation.DeterministicRegularLanguageGenerator
   :members: generate_string, valid_lengths_iter, matching_strings_iter


Exceptions
----------

.. autoclass:: revex.dfa.EmptyLanguageError
.. autoclass:: revex.dfa.InfiniteLanguageError
