"""
Parse Python regex patterns into revex RegularExpression objects using
Python's own internal regex parser (re._parser / sre_parse).

This replaces the previous parsimonious-based grammar, which was fragile
and broke across parsimonious versions due to escaping issues.
"""

import re
import re._constants as sre_constants
import re._parser as sre_parse
import string
from functools import reduce
from operator import or_

MAXREPEAT = sre_constants.MAXREPEAT


# Character class expansions (ASCII printable only, matching old behavior)
_charclass_cache = {}


def _charclass_chars(category):
    """Return the set of ASCII printable characters matching a category."""
    if category not in _charclass_cache:
        mapping = {
            sre_constants.CATEGORY_DIGIT: r'\d',
            sre_constants.CATEGORY_NOT_DIGIT: r'\D',
            sre_constants.CATEGORY_WORD: r'\w',
            sre_constants.CATEGORY_NOT_WORD: r'\W',
            sre_constants.CATEGORY_SPACE: r'\s',
            sre_constants.CATEGORY_NOT_SPACE: r'\S',
        }
        pattern = mapping.get(category)
        if pattern is None:
            raise NotImplementedError(f'Unsupported category: {category}')
        compiled = re.compile(pattern)
        chars = ''.join(c for c in string.printable if compiled.match(c))
        _charclass_cache[category] = chars
    return _charclass_cache[category]


def _is_negated_category(category):
    return category in (
        sre_constants.CATEGORY_NOT_DIGIT,
        sre_constants.CATEGORY_NOT_WORD,
        sre_constants.CATEGORY_NOT_SPACE,
    )


def _category_to_charclass_char(category):
    """Map sre category constants to the single-letter charclass char (d/D/w/W/s/S)."""
    mapping = {
        sre_constants.CATEGORY_DIGIT: 'd',
        sre_constants.CATEGORY_NOT_DIGIT: 'D',
        sre_constants.CATEGORY_WORD: 'w',
        sre_constants.CATEGORY_NOT_WORD: 'W',
        sre_constants.CATEGORY_SPACE: 's',
        sre_constants.CATEGORY_NOT_SPACE: 'S',
    }
    return mapping.get(category)


def parse_pattern(pattern):
    """
    Parse a regex pattern string and return a revex RegularExpression.

    Uses Python's internal regex parser for robust, correct parsing.
    """
    # Import here to avoid circular imports
    from revex.derivative import (
        EMPTY, EPSILON, DOT, WHATEVER,
        CharSet, CharClass, Concatenation, Union, Star, Complement,
        LookAhead, LookBehind,
    )

    parsed = sre_parse.parse(pattern)
    return _convert_sequence(parsed.data)


def _convert_sequence(items):
    """Convert a sequence of sre_parse items to a RegularExpression."""
    from revex.derivative import EPSILON, Concatenation
    from functools import reduce
    import operator

    if not items:
        return EPSILON

    parts = [_convert_item(item) for item in items]
    return reduce(operator.add, parts, EPSILON)


def _convert_item(item):
    """Convert a single sre_parse (opcode, av) pair to a RegularExpression."""
    from revex.derivative import (
        EMPTY, EPSILON, DOT, WHATEVER,
        CharSet, CharClass, Concatenation, Union, Star, Complement,
        LookAhead, LookBehind,
    )

    opcode, av = item

    if opcode == sre_constants.LITERAL:
        return CharSet([chr(av)])

    elif opcode == sre_constants.NOT_LITERAL:
        return CharSet([chr(av)], negated=True)

    elif opcode == sre_constants.ANY:
        return DOT

    elif opcode == sre_constants.IN:
        return _convert_charset(av)

    elif opcode == sre_constants.BRANCH:
        # av is (None, [branch1_items, branch2_items, ...])
        _, branches = av
        parts = [_convert_sequence(branch) for branch in branches]
        return reduce(or_, parts)

    elif opcode == sre_constants.SUBPATTERN:
        # av is (group, add_flags, del_flags, items)
        _, _, _, items = av
        return _convert_sequence(items)

    elif opcode == sre_constants.MAX_REPEAT or opcode == sre_constants.MIN_REPEAT:
        min_count, max_count, items = av
        inner = _convert_sequence(items)
        return _convert_repeat(inner, min_count, max_count)

    elif opcode == sre_constants.ASSERT:
        direction, items = av
        inner = _convert_sequence(items)
        if direction == 1:
            # Positive lookahead (?=...)
            return LookAhead(inner + WHATEVER, EPSILON)
        elif direction == -1:
            # Positive lookbehind (?<=...)
            return LookBehind(EPSILON, WHATEVER + inner)
        else:
            raise NotImplementedError(f'Unknown assert direction: {direction}')

    elif opcode == sre_constants.ASSERT_NOT:
        direction, items = av
        inner = _convert_sequence(items)
        if direction == 1:
            # Negative lookahead (?!...)
            return LookAhead(~(inner + WHATEVER), EPSILON)
        elif direction == -1:
            # Negative lookbehind (?<!...)
            return LookBehind(EPSILON, ~(WHATEVER + inner))
        else:
            raise NotImplementedError(f'Unknown assert_not direction: {direction}')

    elif opcode == sre_constants.AT:
        # Anchors like ^, $, \b — for now treat as epsilon (matching old behavior
        # which didn't handle anchors)
        return EPSILON

    elif opcode == sre_constants.GROUPREF:
        raise NotImplementedError(
            'Backreferences are not supported (they make the language non-regular)')

    elif opcode == sre_constants.GROUPREF_EXISTS:
        raise NotImplementedError(
            'Conditional backreferences are not supported')

    else:
        raise NotImplementedError(f'Unsupported regex opcode: {opcode}')


def _convert_repeat(inner, min_count, max_count):
    """Convert a repeat expression."""
    from revex.derivative import EPSILON, Star
    import operator
    from functools import reduce

    if max_count == MAXREPEAT:
        # Open-ended: inner{min,}
        base = reduce(operator.add, [inner] * min_count, EPSILON) if min_count > 0 else EPSILON
        return base + Star(inner)
    else:
        # Bounded: inner{min,max}
        base = reduce(operator.add, [inner] * min_count, EPSILON) if min_count > 0 else EPSILON
        opt = reduce(
            or_,
            [reduce(operator.add, [inner] * n, EPSILON)
             for n in range(0, max_count - min_count + 1)])
        return base + opt


def _convert_charset(items):
    """Convert an IN [...] expression to a CharSet or Union."""
    from revex.derivative import CharSet, CharClass
    import operator
    from functools import reduce

    negated = False
    chars = set()
    charclass_parts = []

    for opcode, av in items:
        if opcode == sre_constants.NEGATE:
            negated = True
        elif opcode == sre_constants.LITERAL:
            chars.add(chr(av))
        elif opcode == sre_constants.RANGE:
            lo, hi = av
            chars.update(chr(c) for c in range(lo, hi + 1))
        elif opcode == sre_constants.CATEGORY:
            cc_char = _category_to_charclass_char(av)
            if cc_char is not None:
                # Use CharClass for proper identity/display
                charclass_parts.append(CharClass(cc_char))
            else:
                chars.update(_charclass_chars(av))
        else:
            raise NotImplementedError(f'Unsupported charset opcode: {opcode}')

    if charclass_parts and not chars and not negated:
        # Pure character class like \d, \w, \s
        if len(charclass_parts) == 1:
            return charclass_parts[0]
        return reduce(operator.or_, charclass_parts)

    if charclass_parts:
        # Mix of chars and charclasses — expand charclasses into chars
        for cc in charclass_parts:
            if cc.negated:
                # For negated charclasses inside [...], we need the complementary chars
                # This is complex; expand to actual chars
                import string
                all_printable = set(string.printable)
                chars.update(all_printable - set(cc.chars))
            else:
                chars.update(cc.chars)

    return CharSet(chars, negated=negated)
