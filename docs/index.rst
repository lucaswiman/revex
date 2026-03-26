revex — Reversible Regular Expressions
======================================

**revex** is a Python library for formal regular expression manipulation
using `Brzozowski derivatives <https://en.wikipedia.org/wiki/Brzozowski_derivative>`_.

Unlike the standard ``re`` module, which treats regexes as opaque matchers,
revex treats them as **first-class mathematical objects** that can be
intersected, complemented, compared for equivalence, and used to generate
strings.

Quick Example
-------------

.. code-block:: python

   import revex

   # Are these two regexes equivalent?
   revex.equivalent(r'(ab)*', r'(ab)*(ab)*')  # True

   # Do these regexes overlap?
   revex.intersects(r'[a-m]+', r'[g-z]+')  # True

   # Find a concrete string matching both
   revex.find_example(r'[a-m]+', r'[g-z]+')  # e.g. 'g'

   # Find a string matching one but not the other
   revex.find_difference(r'[a-z]+', r'admin.*')  # e.g. 'a'

   # Generate a random string of exactly length 5
   revex.sample(r'[a-z]{3,8}', 5)  # e.g. 'qxmtf'

   # Check if one regex is a subset of another
   revex.is_subset(r'aaa', r'a+')  # True


.. toctree::
   :maxdepth: 2
   :caption: Contents

   algorithm
   api
   security
   roadmap
