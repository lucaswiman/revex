Security Applications
=====================

Revex's regex set operations enable several security-relevant analyses
that are difficult or impossible with standard regex libraries.

Firewall & WAF Rule Analysis
-----------------------------

When security rules are defined by regexes, misconfigurations can
create gaps or contradictions. Revex can find them.

**Problem**: A WAF has an allow-list and a block-list. Are there
requests that match both (contradiction) or neither (gap)?

.. code-block:: python

   import revex

   allow_pattern = r'/api/(users|products)/[a-z0-9]+'
   block_pattern = r'/api/users/admin[a-z0-9]*'

   # Find a request that's both allowed AND blocked
   conflict = revex.find_example(allow_pattern, block_pattern)
   # → '/api/users/admin' — a contradiction in the rules!

   # Find what the block rule catches that the allow rule permits
   blocked = revex.find_difference(allow_pattern, block_pattern)
   # → Shows exactly which requests get through


URL Route Overlap Detection
-----------------------------

Web frameworks dispatch requests by matching URLs against regex
patterns. Overlapping routes cause ambiguity — the wrong handler
may execute.

.. code-block:: python

   import revex

   routes = [
       (r'/user/[a-z]+', 'user_profile'),
       (r'/user/admin', 'admin_panel'),
       (r'/user/[a-z]+/settings', 'user_settings'),
   ]

   # Check all pairs for overlap
   for i, (r1, name1) in enumerate(routes):
       for r2, name2 in routes[i+1:]:
           if revex.intersects(r1, r2):
               example = revex.find_example(r1, r2)
               print(f"OVERLAP: {name1} and {name2}")
               print(f"  Example: {example}")

   # Output:
   # OVERLAP: user_profile and admin_panel
   #   Example: /user/admin


Input Validation Bypass
-----------------------

When frontend and backend use different regexes to validate the
same input, the gap between them is an attack surface.

.. code-block:: python

   import revex

   frontend_validation = r'[a-zA-Z0-9_]+'
   backend_validation = r'[a-zA-Z0-9_.@]+'

   # What does the backend accept that the frontend rejects?
   bypass = revex.find_difference(backend_validation, frontend_validation)
   # → A string with '.' or '@' that bypasses frontend validation


Regex Equivalence After "Fixing"
---------------------------------

After patching a vulnerable regex, verify the fix doesn't change
the matched language (avoiding regressions) or does change it in
exactly the intended way.

.. code-block:: python

   import revex

   original = r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}'
   fixed = r'((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'

   # The "fixed" version is strictly more restrictive
   assert revex.is_subset(fixed, original, alphabet='0123456789.')

   # Find an example the original accepts but the fix rejects
   bypass = revex.find_difference(original, fixed, alphabet='0123456789.')
   # → e.g. '999.999.999.999' — not a valid IP!


Secret / PII Coverage Verification
------------------------------------

Verify that a log-redaction regex covers all patterns it should:

.. code-block:: python

   import revex

   ssn_pattern = r'[0-9]{3}-[0-9]{2}-[0-9]{4}'
   redaction_pattern = r'[0-9]{3}-[0-9]{2,4}-[0-9]{3,4}'

   # Does the redaction pattern catch ALL SSNs?
   if revex.is_subset(ssn_pattern, redaction_pattern, alphabet='0123456789-'):
       print("All SSNs will be redacted")
   else:
       leak = revex.find_difference(ssn_pattern, redaction_pattern,
                                    alphabet='0123456789-')
       print(f"LEAK: SSN like '{leak}' would not be redacted!")
