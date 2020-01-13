This library was a personal project around formally manipulating regular expressions.
The idea is basically as follows:
* Parse the regular expression using a custom `parsimonious` grammar into an AST.
  (See `regex_gramar.py`.)
* Compile the AST into `RegularExpression` objects using the Brzozowski derivative. (See
  http://www.drmaciver.com/2016/12/proving-or-refuting-regular-expression-equivalence/
  for background and `derivative.py`).
* Form a graphical representation of the regular expression by taking the derivative
  with respect to each letter of the alphabet. (In other words, convert it to a DFA. See
  `dfa.py`.)
* Convert the graphical representation to a matrix, whose powers can be used to compute
  probability distributions of strings that match the original regular expression. (See
  `generation.py`.)

This allows you to do the following:
* Check if two regular expressions can match the same string, which may be of interest for
  some problems. (This was the original impetus for the project, checking whether two
  rules which depend on regular expressions might both apply.) This is possible because
  the Brzozowski formalism makes negation and intersection of regular expressions easy.
* Produce strings of a given length sampled uniformly at random from the probability
  distribution of strings matching the regular expression of a given length. Hypothesis
  has since implemented a strategy that allows generation of strings matching a regular
  expression that is presumably better than this approach for the purpose of property-based
  testing. (See https://hypothesis.readthedocs.io/en/latest/data.html#hypothesis.strategies.from_regex)