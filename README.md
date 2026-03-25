# revex — Reversible Regular Expressions

A Python library for **formal regular expression manipulation** using
[Brzozowski derivatives](https://en.wikipedia.org/wiki/Brzozowski_derivative).

Unlike Python's `re` module, which treats regexes as opaque matchers, revex treats
them as **first-class mathematical objects** that support intersection, complement,
equivalence checking, and uniform random string generation.

## What can revex do?

```python
import revex

# Check if two regexes match the same language
revex.equivalent(r'(ab)*', r'(ab)*(ab)*')  # True

# Check if two regexes can match any common string
revex.intersects(r'[a-m]+', r'[g-z]+')  # True

# Find a concrete string matching both regexes
revex.find_example(r'[a-m]+', r'[g-z]+')  # e.g. 'g'

# Find a string matching one regex but not the other
revex.find_difference(r'[a-z]+', r'admin.*')  # e.g. 'a'

# Check if one regex's language is a subset of another
revex.is_subset(r'aaa', r'a+')  # True

# Generate a random string of exactly length N
revex.sample(r'[a-z]{3,8}', 5)  # e.g. 'qxmtf'

# Compute the set difference of two regex languages
r = revex.subtract(r'[a-z]+', r'admin.*')
r.match('user')   # True
r.match('admin')  # False
```

## When is this useful?

- **Security**: Find inputs that bypass frontend validation but reach the backend.
  Detect overlapping firewall rules. Verify PII redaction coverage.
- **Testing**: Generate strings of specific lengths uniformly at random. Create
  negative test cases from regex complements. Test regex intersections.
- **Static analysis**: Detect overlapping URL routes in web frameworks. Find dead
  regex branches. Validate schema constraints.
- **Formal verification**: Check regex equivalence after refactoring. Verify
  protocol message format coverage.

See the [full documentation](docs/) and [ROADMAP.md](ROADMAP.md) for more.

## Installation

```bash
pip install revex
```

Requires Python 3.10+. Dependencies: `networkx`, `numpy`.

## How it works

1. **Parse** the regex using Python's own `re._parser` into an AST.
2. **Compile** the AST into `RegularExpression` objects supporting the
   [Brzozowski derivative](https://en.wikipedia.org/wiki/Brzozowski_derivative).
3. **Construct a DFA** by iteratively computing derivatives with respect to each
   character in the alphabet.
4. **Analyze** the DFA: minimization, equivalence checking, language finiteness,
   longest string computation.
5. **Generate strings** uniformly at random using path weights (Bernardi & Giménez 2012).

The key insight is that **intersection and complement** have trivial derivative rules,
making operations that are exponentially expensive with NFA-based approaches simple and direct.

## Building the docs

```bash
pip install -e ".[docs]"
sphinx-build -b html docs docs/_build/html
# Open docs/_build/html/index.html
```

Requires [Graphviz](https://graphviz.org/) for diagrams: `apt install graphviz` / `brew install graphviz`.

## Running tests

```bash
pip install -e ".[dev]"
pytest revex/tests/
```

## License

Apache 2.0
