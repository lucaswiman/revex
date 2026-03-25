# Revex Roadmap

## What revex does that nothing else does

Revex provides **formal regular expression manipulation** in Python:

- **Regex intersection & complement**: Given two regexes, determine if their languages overlap, or compute the regex matching everything *not* matched by a given regex. No other Python library does this.
- **Regex equivalence checking**: Determine whether two regexes match exactly the same set of strings, using Brzozowski derivative-based DFA construction.
- **Uniform random string generation by length**: Generate strings of a *specific length* sampled uniformly at random from the language of a regex. Hypothesis's `from_regex` generates strings matching a regex but cannot target specific lengths or guarantee uniform sampling.
- **DFA construction & minimization**: Convert regexes to minimal DFAs, enabling graph-theoretic analysis (finite language detection, longest string computation).
- **Concrete witness generation**: Given two regexes, find a concrete example string demonstrating their intersection, difference, or non-equivalence.

These capabilities are useful for **static analysis**, **testing**, **security analysis**, **schema validation**, and **formal verification** of systems that use regexes.

## What revex does NOT need to duplicate

- **String generation for property-based testing**: Hypothesis's `from_regex()` is battle-tested and widely used. Revex should not try to replace it for general fuzzing/PBT.
- **Regex matching at runtime**: Python's `re` module and the `regex` package are optimized for this. Revex's matching is via derivatives (educational/analytical, not performance-oriented).
- **Regex syntax highlighting/linting**: Tools like `ruff`, `pylint`, and IDE plugins handle this.

## Security applications

Revex's regex algebra enables security analyses that standard regex libraries can't express:

### Firewall / WAF rule analysis
Given allow-list and block-list regexes, find strings that match both (misconfigurations) or neither (gaps). Generate concrete example strings as proof-of-concept.

### URL route overlap detection
Web frameworks dispatch by regex. Overlapping routes cause ambiguity — `revex.intersects()` and `revex.find_example()` identify which routes conflict and produce concrete conflicting URLs.

### Input validation bypass
When frontend validates with regex R1 and backend with R2, `revex.find_difference(R2, R1)` finds inputs that bypass frontend validation but reach the backend.

### Regex equivalence after patching
After fixing a vulnerable regex, `revex.equivalent()` verifies the fix doesn't change the matched language, or `revex.find_difference()` shows exactly what changed.

### Secret / PII coverage verification
Verify that log-redaction regexes cover all PII patterns: `revex.is_subset(pii_pattern, redaction_pattern)`.

## Near-term improvements (v0.1–v0.2)

### Robustness & correctness
- [ ] Handle Unicode character classes (`\w`, `\d`, `\s`) beyond ASCII printable range
- [ ] Support `re.IGNORECASE`, `re.DOTALL`, `re.MULTILINE` flags in the parser
- [ ] Add support for `\b` (word boundary) assertions
- [ ] Improve error messages for unsupported features (backreferences, conditional groups)

### API & usability
- [x] Add `revex.equivalent(regex1, regex2)` convenience function
- [x] Add `revex.intersects(regex1, regex2)` convenience function
- [x] Add `revex.is_subset(regex1, regex2)` — does L(r1) ⊆ L(r2)?
- [x] Add `revex.subtract(regex1, regex2)` — L(r1) \ L(r2)
- [x] Add `revex.sample(regex, length=N)` convenience function
- [x] Add `revex.find_example(regex1, regex2)` — concrete witness string
- [x] Add `revex.find_difference(regex1, regex2)` — concrete difference witness
- [x] Sphinx documentation with algorithm explanation and diagrams
- [ ] Publish to PyPI
- [ ] Add CLI tool for quick regex analysis

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

## Context-free grammar extensions (Lark integration)

### Motivation
Lark is the most popular modern Python parser library (~4.6k GitHub stars, active development). Lark grammars define **terminals** using regex patterns and **rules** using EBNF. Revex's regex algebra could provide valuable analysis capabilities for Lark grammars.

### What revex could do for Lark users

**Terminal ambiguity detection**: Lark terminals are defined as regexes. When two terminal regexes can match the same string, the grammar is ambiguous at the lexer level. Revex can detect this:

```python
# Hypothetical API
from revex.lark import analyze_terminals

grammar = '''
    start: IDENTIFIER | KEYWORD
    IDENTIFIER: /[a-z_][a-z0-9_]*/
    KEYWORD: /if|else|while|for|return/
'''
overlaps = analyze_terminals(grammar)
# → [('IDENTIFIER', 'KEYWORD', example='if')]
```

**Terminal coverage testing**: Generate test strings for each terminal, ensuring the lexer handles all cases:

```python
from revex.lark import generate_terminal_examples
examples = generate_terminal_examples(grammar, per_terminal=10)
# → {'IDENTIFIER': ['x', 'foo', '_bar', ...], 'KEYWORD': ['if', 'else', ...]}
```

**Terminal optimization**: Detect redundant or overlapping terminal patterns and suggest simplifications.

### Parsing with derivatives (research direction)

The Brzozowski derivative approach has been extended to context-free grammars in academic research:

- **Matt Might et al., "Parsing with Derivatives" (ICFP 2011)**: Showed that derivatives can be computed for CFGs, enabling a parsing algorithm that is elegant but has worst-case exponential complexity.
- **Adams et al., "Compiling to Categories" (2017)**: Improved the practical performance of parsing with derivatives.

These are theoretically interesting but not yet practical for production use. The key challenge is that CFG derivatives can grow exponentially (unlike regular expression derivatives, which are always finite).

A more practical approach for Lark integration would be to:
1. Analyze terminals (regexes) using revex's existing capabilities
2. Use Lark's own Earley/LALR parsing for the grammar rules
3. Combine both to provide grammar-level analysis (ambiguity detection, test generation)

### Grammar-based fuzzing

The grammar fuzzing ecosystem in Python includes:
- **Grammarinator** — ANTLR-grammar-based fuzzer, active development
- **Dharma** — Mozilla's grammar-based fuzzer
- **ISLa** — constraint-based grammar fuzzer with formal semantics

Revex could complement these by providing **regex-level analysis** of grammar terminals, ensuring fuzzers generate interesting edge cases at token boundaries.

## Existing related work

### interegular
The `interegular` library (by Lark's author) already provides regex intersection checking using FSM construction. It's lightweight (~500 LOC) but:
- No complement operation
- No string generation
- No DFA minimization
- No equivalence checking beyond intersection emptiness

Revex provides a superset of interegular's functionality. A potential path is to position revex as the "full-featured" option for users who need more than basic intersection checking.

### greenery
The `greenery` library provides FSM construction from regexes with intersection and complement. It's unmaintained (last release 2020). Revex's Brzozowski approach is more elegant and extensible.

## Longer-term / research directions

- [ ] **Symbolic DFA construction**: instead of enumerating characters in an alphabet, use character class predicates as edge labels. This would make DFA construction tractable for Unicode regexes without explosion.
- [ ] **Counted repetition optimization**: `a{1000}` currently creates 1000 concatenation nodes. A dedicated `Repeat(r, min, max)` node type could keep the AST compact and enable smarter derivative computation.
- [ ] **Regex simplification / normalization**: given a regex, produce a "simplified" equivalent regex (fewer alternations, merged character classes, etc.).
- [ ] **Regex diff**: given two regexes, produce a human-readable description of how their languages differ (example strings in one but not the other).
- [ ] **Antichain-based language inclusion**: implement the antichain algorithm for checking L(r1) ⊆ L(r2) without full DFA construction, which is exponentially more efficient for many cases.
- [ ] **Lark terminal analysis tool**: standalone CLI tool that reads a Lark grammar file and reports terminal overlaps, generates test strings, and suggests optimizations.
