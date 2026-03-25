# Revex Roadmap

## What revex does that nothing else does

Revex provides **formal regular expression manipulation** in Python:

- **Regex intersection & complement**: Given two regexes, determine if their languages overlap, or compute the regex matching everything *not* matched by a given regex. No other Python library does this.
- **Regex equivalence checking**: Determine whether two regexes match exactly the same set of strings, using Brzozowski derivative-based DFA construction.
- **Uniform random string generation by length**: Generate strings of a *specific length* sampled uniformly at random from the language of a regex. Hypothesis's `from_regex` generates strings matching a regex but cannot target specific lengths or guarantee uniform sampling.
- **DFA construction & minimization**: Convert regexes to minimal DFAs, enabling graph-theoretic analysis (finite language detection, longest string computation).

These capabilities are useful for **static analysis**, **testing**, **schema validation**, and **formal verification** of systems that use regexes.

## What revex does NOT need to duplicate

- **String generation for property-based testing**: Hypothesis's `from_regex()` is battle-tested and widely used. Revex should not try to replace it for general fuzzing/PBT.
- **Regex matching at runtime**: Python's `re` module and the `regex` package are optimized for this. Revex's matching is via derivatives (educational/analytical, not performance-oriented).
- **Regex syntax highlighting/linting**: Tools like `ruff`, `pylint`, and IDE plugins handle this.

## Near-term improvements (v0.1–v0.2)

### Robustness & correctness
- [ ] Handle Unicode character classes (`\w`, `\d`, `\s`) beyond ASCII printable range
- [ ] Support `re.IGNORECASE`, `re.DOTALL`, `re.MULTILINE` flags in the parser
- [ ] Add support for `\b` (word boundary) assertions
- [ ] Improve error messages for unsupported features (backreferences, conditional groups)

### API & usability
- [ ] Add `revex.equivalent(regex1, regex2)` convenience function
- [ ] Add `revex.intersects(regex1, regex2)` convenience function
- [ ] Add `revex.is_subset(regex1, regex2)` — does L(r1) ⊆ L(r2)?
- [ ] Add `revex.subtract(regex1, regex2)` — L(r1) \ L(r2)
- [ ] Provide a `revex.sample(regex, length=N)` convenience function
- [ ] Write proper documentation with examples

### Performance
- [ ] Cache DFA construction results (same regex → same DFA)
- [ ] Investigate lazy DFA construction (only explore states on demand)
- [ ] Profile and optimize hot paths in derivative computation

## Integration opportunities

### As a Hypothesis extension (`hypothesis-revex`)
Revex could provide a Hypothesis strategy that complements `from_regex`:

- **`regex_intersection_strategy(r1, r2)`**: Generate strings matching *both* regexes. Useful when testing systems with multiple regex constraints.
- **`regex_complement_strategy(r)`**: Generate strings that do *not* match a regex. Useful for negative testing.
- **`uniform_length_strategy(r, length=N)`**: Generate strings of exactly length N matching a regex, sampled uniformly. Useful when string length is semantically significant (fixed-width formats, protocol fields).

This should be a *separate package* so revex's heavier dependencies (numpy, networkx) don't burden users who just want Hypothesis.

### For static analysis / linting

Revex's regex intersection and subset checking could power lint rules:

- **Detect overlapping regex routes** in web frameworks (Flask, Django, FastAPI): warn when two URL patterns can match the same path.
- **Detect dead regex branches**: in `r'(foo|fo+)'`, the second branch is a superset of the first.
- **Validate regex constraints in schemas**: if a JSON Schema says a field must match `r'\d{3}-\d{4}'`, verify that the test data generator can actually produce matching strings.
- **Type narrowing**: if a value is known to match regex R1 and code checks it against R2, the type after the check is the intersection.

These could be packaged as:
- A `ruff` plugin or standalone linter
- A `mypy` plugin for type narrowing with `re.match` guards
- A library for framework-specific route analysis

### For formal verification / model checking
- **Protocol conformance**: verify that a regex describing valid messages is a subset of (or equivalent to) a protocol specification regex.
- **Firewall rule analysis**: determine if two sets of regex-based packet filters overlap.
- **Access control**: verify that URL path regexes in authorization rules cover all intended paths without gaps or overlaps.

## Longer-term / research directions

- [ ] **Symbolic DFA construction**: instead of enumerating characters in an alphabet, use character class predicates as edge labels. This would make DFA construction tractable for Unicode regexes without explosion.
- [ ] **Counted repetition optimization**: `a{1000}` currently creates 1000 concatenation nodes. A dedicated `Repeat(r, min, max)` node type could keep the AST compact and enable smarter derivative computation.
- [ ] **Regex simplification / normalization**: given a regex, produce a "simplified" equivalent regex (fewer alternations, merged character classes, etc.).
- [ ] **Regex diff**: given two regexes, produce a human-readable description of how their languages differ (example strings in one but not the other).
- [ ] **Antichain-based language inclusion**: implement the antichain algorithm for checking L(r1) ⊆ L(r2) without full DFA construction, which is exponentially more efficient for many cases.
