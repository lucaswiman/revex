The Brzozowski Derivative Algorithm
====================================

This page explains the core algorithm that powers revex: the
**Brzozowski derivative** of regular expressions. This is a beautiful
piece of theoretical computer science from 1964 that converts regular
expressions directly into DFAs without going through NFAs.

What is a derivative?
---------------------

The **Brzozowski derivative** of a regular expression *R* with respect to
a character *c*, written *∂R/∂c*, is a new regular expression that matches
the string *s* if and only if *R* matches *cs*. In other words: it "peels off"
the first character and returns what's left.

.. math::

   \frac{\partial R}{\partial c} = \{ s \mid cs \in L(R) \}

For example:

- :math:`\partial(\texttt{abc})/\partial\texttt{a} = \texttt{bc}` — after consuming "a", we need to match "bc".
- :math:`\partial(\texttt{abc})/\partial\texttt{b} = \emptyset` — "abc" doesn't start with "b".
- :math:`\partial(\texttt{a*})/\partial\texttt{a} = \texttt{a*}` — after consuming one "a" from ``a*``, we still accept any number of "a"s.

Derivative Rules
----------------

The derivative is defined recursively on the structure of the regex:

**Atomic types:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Expression *R*
     - Derivative *∂R/∂c*
   * - :math:`\emptyset` (empty set)
     - :math:`\emptyset`
   * - :math:`\varepsilon` (empty string)
     - :math:`\emptyset`
   * - Literal *a*
     - :math:`\varepsilon` if *c = a*, else :math:`\emptyset`
   * - ``.`` (any char)
     - :math:`\varepsilon`

**Compound types:**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Expression *R*
     - Derivative *∂R/∂c*
   * - :math:`R_1 \cdot R_2` (concatenation)
     - :math:`(\partial R_1/\partial c) \cdot R_2 \;\cup\; (\text{if } \varepsilon \in L(R_1)) \; \partial R_2/\partial c`
   * - :math:`R_1 | R_2` (union)
     - :math:`\partial R_1/\partial c \;|\; \partial R_2/\partial c`
   * - :math:`R_1 \& R_2` (intersection)
     - :math:`\partial R_1/\partial c \;\&\; \partial R_2/\partial c`
   * - :math:`\sim R` (complement)
     - :math:`\sim (\partial R/\partial c)`
   * - :math:`R^*` (Kleene star)
     - :math:`(\partial R/\partial c) \cdot R^*`

The key insight is that **intersection and complement have trivial
derivative rules**, while in the standard NFA→DFA approach, these
operations require exponentially expensive constructions.


From Derivatives to DFAs
-------------------------

The derivative construction naturally produces a DFA. The idea is:

1. Start with the original regex *R* as the start state.
2. For each character *c* in the alphabet, compute *∂R/∂c*. Each result
   is a new state.
3. Repeat for each new state until no new states appear.
4. A state is **accepting** if its regex matches the empty string (ε ∈ L(R)).

This process always terminates because there are only finitely many
structurally distinct derivatives of any regular expression (up to
algebraic simplification).

.. graphviz::
   :caption: DFA for the regex ``(a|b)*a`` over alphabet {a, b}

   digraph {
       rankdir=LR;
       node [shape=circle];

       start [shape=point, width=0.1];
       q0 [label="(a|b)*a"];
       q1 [label="(a|b)*a|ε", shape=doublecircle];
       q2 [label="(a|b)*a"];

       start -> q0 [label=" start"];
       q0 -> q1 [label=" a"];
       q0 -> q0 [label=" b"];
       q1 -> q1 [label=" a"];
       q1 -> q2 [label=" b"];
       q2 -> q1 [label=" a"];
       q2 -> q2 [label=" b"];
   }

Each state in this DFA is **labeled by the regex it represents** — the regex
you'd need to match from that point onward. This is a unique feature of the
derivative construction.

Matching Strings
----------------

To check whether a string *s = c₁c₂...cₙ* matches regex *R*:

1. Compute :math:`R_1 = \partial R/\partial c_1`
2. Compute :math:`R_2 = \partial R_1/\partial c_2`
3. Continue until :math:`R_n = \partial R_{n-1}/\partial c_n`
4. Accept if :math:`\varepsilon \in L(R_n)` (the final regex matches the empty string).

.. graphviz::
   :caption: Matching "ab" against ``(a|b)*a``: trace through the derivative chain

   digraph {
       rankdir=LR;
       node [shape=box, style=rounded];

       r0 [label="(a|b)*a"];
       r1 [label="(a|b)*a | ε", color=green, fontcolor=green];
       r2 [label="(a|b)*a"];

       r0 -> r1 [label=" ∂/∂a"];
       r1 -> r2 [label=" ∂/∂b"];

       note [shape=plaintext, label="Not accepting → 'ab' does not match"];
       r2 -> note [style=dashed, arrowhead=none];
   }

Regex Set Operations
--------------------

The real power of the Brzozowski approach is that **set operations on
regex languages become trivial**:

**Intersection** — *L(R₁) ∩ L(R₂)*:

.. code-block:: python

   import revex

   # Strings of 'a' with even length AND divisible by 3
   r1 = revex.compile(r'(aa)*')    # even length
   r2 = revex.compile(r'(aaa)*')   # length divisible by 3
   r_both = r1 & r2                 # length divisible by 6!

   r_both.match('a' * 6)   # True
   r_both.match('a' * 12)  # True
   r_both.match('a' * 4)   # False (not div by 3)
   r_both.match('a' * 9)   # False (not even)

**Complement** — everything NOT matched by *R*:

.. code-block:: python

   # Strings that do NOT match the pattern
   r = revex.compile(r'admin.*')
   not_admin = ~r
   not_admin.match('user_page')  # True
   not_admin.match('admin_panel')  # False

**Equivalence** — do two regexes match the same language?

.. code-block:: python

   # These are the same language
   revex.equivalent(r'(a|b)*', r'(a*b*)*')  # True

This works by checking if the symmetric difference is empty:
:math:`L(R_1) \triangle L(R_2) = \emptyset` iff :math:`R_1 \equiv R_2`.

.. graphviz::
   :caption: Set operations on regex languages visualized as Venn diagrams

   digraph {
       rankdir=TB;
       node [shape=plaintext];

       subgraph cluster_0 {
           label="Intersection: L(R₁) ∩ L(R₂)";
           style=rounded;
           i [label=<
               <TABLE BORDER="0"><TR><TD>
               Only strings matching<BR/>
               <B>both</B> R₁ and R₂
               </TD></TR></TABLE>
           >];
       }
       subgraph cluster_1 {
           label="Complement: ~R₁";
           style=rounded;
           c [label=<
               <TABLE BORDER="0"><TR><TD>
               All strings that<BR/>
               do <B>not</B> match R₁
               </TD></TR></TABLE>
           >];
       }
       subgraph cluster_2 {
           label="Difference: R₁ \\ R₂";
           style=rounded;
           d [label=<
               <TABLE BORDER="0"><TR><TD>
               Strings matching R₁<BR/>
               but <B>not</B> R₂
               </TD></TR></TABLE>
           >];
       }
   }


DFA Minimization
----------------

After constructing a DFA, revex can **minimize** it using
`Hopcroft's algorithm <https://en.wikipedia.org/wiki/DFA_minimization>`_.
This merges equivalent states — states where no input string can
distinguish between them.

.. code-block:: python

   from revex.dfa import minimize_dfa
   import revex

   dfa = revex.build_dfa(r'(a|b)*a(a|b)')
   print(f"Original: {len(dfa.nodes)} states")

   min_dfa = minimize_dfa(dfa)
   print(f"Minimized: {len(min_dfa.nodes)} states")

Minimized DFAs have a unique structure (up to isomorphism), which means
you can check regex equivalence by minimizing both DFAs and checking
for graph isomorphism.


String Generation
-----------------

Given a DFA, revex can generate strings of a specific length **uniformly
at random**. This uses the algorithm from:

    Bernardi & Giménez, *"A Linear Algorithm for the Random Generation
    of Regular Languages"*, Algorithmica 62(1), 2012.

The idea:

1. Compute a **path weight matrix**: for each state and path length *n*,
   how many paths of length *n* lead from that state to an accepting state?
2. Use these weights as a probability distribution to choose transitions.
3. Walk the DFA, choosing each transition proportionally to the number of
   accepting paths it leads to.

This guarantees **uniform sampling**: every string of length *n* in the
language has equal probability of being generated.

.. code-block:: python

   import revex

   # Generate 10 random 8-character "words"
   for _ in range(10):
       word = revex.sample(r'[a-z]+', 8,
                           alphabet='abcdefghijklmnopqrstuvwxyz')
       print(word)

.. graphviz::
   :caption: Path weights enable uniform random walks through the DFA

   digraph {
       rankdir=LR;
       node [shape=circle];

       start [shape=point, width=0.1];
       q0 [label="start\nw=1.0"];
       q1 [label="s1\nw=0.6"];
       q2 [label="s2\nw=0.4"];
       q3 [label="accept", shape=doublecircle];

       start -> q0;
       q0 -> q1 [label=" a (60%)"];
       q0 -> q2 [label=" b (40%)"];
       q1 -> q3 [label=" c"];
       q2 -> q3 [label=" d"];
   }

The weights at each state tell us the probability of reaching an
accepting state — this guides the random walk to produce uniformly
distributed strings.


Computational Complexity
------------------------

- **DFA construction**: O(2ⁿ) states in the worst case, where *n* is the
  size of the regex. In practice, most regexes produce much smaller DFAs.
- **Derivative computation**: O(n) per character, where *n* is the size
  of the regex expression tree.
- **Matching**: O(|s| · n) for string *s* via derivatives, or O(|s|) via
  the pre-constructed DFA.
- **Equivalence checking**: O(|Σ| · 2ⁿ) in the worst case (construct
  DFA for the symmetric difference).
- **String generation**: O(|s|) per string after O(|Q|²) preprocessing,
  where |Q| is the number of DFA states.

For most practical regexes, the DFA has a manageable number of states
and all operations are fast.


References
----------

- Brzozowski, J.A. (1964). *"Derivatives of Regular Expressions"*.
  Journal of the ACM, 11(4), 481–494.
- Owens, S., Reppy, J., & Turon, A. (2009). *"Regular-expression
  derivatives re-examined"*. Journal of Functional Programming, 19(2), 173–190.
- Bernardi, O. & Giménez, O. (2012). *"A Linear Algorithm for the Random
  Generation of Regular Languages"*. Algorithmica, 62(1), 130–145.
- MacIver, D. (2016). `"Proving or Refuting Regular Expression Equivalence"
  <http://www.drmaciver.com/2016/12/proving-or-refuting-regular-expression-equivalence/>`_.
