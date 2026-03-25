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

Lark (v1.3.1, ~5,700 GitHub stars, ~325K weekly PyPI downloads) is the dominant modern Python parser library. It supports LALR(1), Earley, and CYK parsing, with grammar terminals defined as regex patterns. Lark already uses the [`interegular`](https://github.com/MegaIng/interegular) library (by Lark's author) for basic terminal regex overlap detection — but interegular is limited and inactive:

| Capability | interegular | revex |
|---|---|---|
| Regex intersection (emptiness check) | ✅ | ✅ |
| Complement / negation | ❌ | ✅ |
| Concrete witness string generation | ❌ | ✅ |
| Equivalence checking | ❌ | ✅ |
| Subset checking | ❌ | ✅ |
| Uniform random string generation | ❌ | ✅ |
| DFA minimization | ❌ | ✅ |
| Lookahead/lookbehind support | ❌ | ✅ |
| Active maintenance | ❌ (no releases in 12+ months) | ✅ |

Revex could serve as a **more capable replacement for interegular** in Lark's ambiguity detection pipeline.

### Proposed API: `revex.lark` module

```python
from revex.lark import GrammarAnalyzer

analyzer = GrammarAnalyzer(r"""
    start: (KEYWORD | IDENT)+
    KEYWORD: "if" | "else" | "while" | "for"
    IDENT: /[a-zA-Z_]\w*/
    %ignore /\s+/
""")

# Find terminal regex overlaps with concrete witness strings
overlaps = analyzer.find_overlaps()
# → [('KEYWORD', 'IDENT', 'if')]

# Generate test strings for a terminal
examples = analyzer.generate_examples('IDENT', count=10)
# → ['x', 'a1', '_foo', '__init__', 'bar_baz', ...]

# Check subset relationships between terminals
analyzer.check_subset('KEYWORD', 'IDENT')  # True — all keywords are identifiers

# Suggest terminal priorities based on subset analysis
analyzer.suggest_priorities()
# → [('KEYWORD', 'IDENT', 'KEYWORD should have higher priority')]
```

**CLI tool**:
```bash
$ python -m revex.lark analyze my_grammar.lark
Terminal Overlap Report:
  KEYWORD × IDENT: overlap detected, witness="if"
  NUMBER × FLOAT: overlap detected, witness="42"

Terminal Examples:
  IDENT: x, _a, foo123, __init__, bar_baz
  NUMBER: 0, 42, 100, 9999
  KEYWORD: if, else, while, for
```

### What revex could do for Lark users

**Terminal ambiguity detection**: When two terminal regexes can match the same string, the grammar is ambiguous at the lexer level. Unlike interegular (which only reports a boolean), revex produces a **concrete witness string** demonstrating the collision:

```python
from revex.lark import GrammarAnalyzer

grammar = '''
    start: IDENTIFIER | KEYWORD
    IDENTIFIER: /[a-z_][a-z0-9_]*/
    KEYWORD: /if|else|while|for|return/
'''
overlaps = GrammarAnalyzer(grammar).find_overlaps()
# → [('IDENTIFIER', 'KEYWORD', 'if')]
```

**Terminal coverage testing**: Generate test strings for each terminal, ensuring the lexer handles all cases:

```python
examples = GrammarAnalyzer(grammar).generate_examples('IDENTIFIER', count=10)
# → ['x', 'foo', '_bar', 'a1b2', ...]
```

**Boundary-case generation for fuzzing**: Generate strings near the boundary between two terminals — strings that match one but not the other, and strings that match both:

```python
# Strings in IDENT but not KEYWORD, and vice versa
boundary = analyzer.generate_boundary_strings('KEYWORD', 'IDENT')
# → {'only_KEYWORD': [], 'only_IDENT': ['x', '_if'], 'both': ['if', 'else']}
```

**Terminal optimization**: Detect redundant or overlapping terminal patterns and suggest simplifications.

### Parsing with derivatives (research direction)

The Brzozowski derivative approach has been extended to context-free grammars in academic research:

- **Might, Darais & Spiewak, "Parsing with Derivatives" (ICFP 2011)**: Showed that derivatives can be computed for CFGs, treating them as "recursive regular expressions." The core implementation is ~30 lines. The hardest part is computing nullability via least fixed points.
- **Adams, Hollenbeck & Might, "On the Complexity and Performance of Parsing with Derivatives" (PLDI 2016)**: Proved the approach is O(n³), not exponential as previously believed. Simple modifications yield practical performance.
- **"Derivative Grammars" (OOPSLA 2019)**: A symbolic approach generating derivative grammars, achieving O(n²) space and O(n³) time.

Existing implementations:
- [**derpy**](https://github.com/agoose77/derpy) (Python) — CFG parsing with derivatives
- [**parseback**](https://github.com/djspiewak/parseback) (Scala) — production-oriented, incorporates PLDI 2016 refinements
- [**cfg**](https://github.com/mmottl/cfg) (OCaml) — CFG union, diff, intersection operations

Revex's `RegularExpression` class hierarchy (`EMPTY`, `EPSILON`, `CharSet`, `Union`, `Intersection`, `Complement`, `Star`, `Concatenation`) mirrors exactly the algebraic structure that Might et al. extended to CFGs. The theoretical path to extension: add a `Reference` node type with lazy evaluation and fixed-point nullability computation. However, this would be a substantial undertaking and would change the library's scope significantly.

A more practical approach for Lark integration would be to:
1. Analyze terminals (regexes) using revex's existing capabilities
2. Use Lark's own Earley/LALR parsing for the grammar rules
3. Combine both to provide grammar-level analysis (ambiguity detection, test generation)

### Grammar-based fuzzing ecosystem

The grammar fuzzing ecosystem in Python includes:

| Tool | Grammar Format | Approach | Notable Results |
|---|---|---|---|
| [**Grammarinator**](https://github.com/renatahodovan/grammarinator) | ANTLR v4 | Generation + mutation + recombination, libFuzzer/AFL++ integration | 100+ bugs in JerryScript |
| [**Gramatron**](https://www.nebelwelt.net/files/21ISSTA.pdf) | Custom CFG | Coverage-guided, grammar automatons; 24% more coverage, 98% faster | Research tool |
| [**Domato**](https://github.com/googleprojectzero/domato) | Custom CFG | Generation-based, DOM-focused | Multiple browser CVEs |
| [**Dharma**](https://github.com/MozillaSecurity/dharma) | Custom `.dg` | Generation-based | Mozilla security testing |
| [**ISLa**](https://www.fuzzingbook.org/html/FuzzingWithConstraints.html) | CFG + constraints | Constraint-solving over grammars | Semantically valid generation |
| **Hypothesis `from_lark`** | Lark EBNF | Property-based testing with shrinking | Widely used |

**Gap revex fills**: None of these tools analyze whether grammar terminals overlap or are ambiguous. They generate from grammars but do not reason about the regex patterns defining terminals. Revex provides the missing **regex intelligence layer** that makes grammar-based fuzzers smarter about lexer boundaries.

## Existing related work

### interegular
The [`interegular`](https://github.com/MegaIng/interegular) library (by Lark's author, ~47 GitHub stars, ~42K weekly downloads) provides regex intersection checking using FSM construction. Built on [`greenery`](https://github.com/qntm/greenery). Limitations:
- No complement operation
- No string generation or witness examples
- No DFA minimization
- No equivalence/subset checking
- No lookahead/lookbehind support
- Inactive maintenance (no releases in 12+ months)

Revex provides a strict superset of interegular's functionality and could replace it as Lark's terminal analysis backend.

### greenery
The [`greenery`](https://github.com/qntm/greenery) library by qntm provides FSM construction from regexes with intersection and complement. Uses the same algebraic approach as revex (Brzozowski-style) but is JavaScript-first (the Python version is a port). Less actively maintained than revex.

## Longer-term / research directions

- [ ] **Symbolic DFA construction**: instead of enumerating characters in an alphabet, use character class predicates as edge labels. This would make DFA construction tractable for Unicode regexes without explosion.
- [ ] **Counted repetition optimization**: `a{1000}` currently creates 1000 concatenation nodes. A dedicated `Repeat(r, min, max)` node type could keep the AST compact and enable smarter derivative computation.
- [ ] **Regex simplification / normalization**: given a regex, produce a "simplified" equivalent regex (fewer alternations, merged character classes, etc.).
- [ ] **Regex diff**: given two regexes, produce a human-readable description of how their languages differ (example strings in one but not the other).
- [ ] **Antichain-based language inclusion**: implement the antichain algorithm for checking L(r1) ⊆ L(r2) without full DFA construction, which is exponentially more efficient for many cases.
- [ ] **Lark terminal analysis tool**: standalone CLI tool that reads a Lark grammar file and reports terminal overlaps, generates test strings, and suggests optimizations.
