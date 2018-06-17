# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2017 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Parser for the environment markers micro-language defined in PEP 508.
"""

# Note: In PEP 345, the micro-language was Python compatible, so the ast
# module could be used to parse it. However, PEP 508 introduced operators such
# as ~= and === which aren't in Python, necessitating a different approach.

import os
import sys
import platform
import re

from .compat import python_implementation, urlparse, string_types
from .util import in_venv, parse_marker

__all__ = ['interpret']

def _is_literal(o):
    if not isinstance(o, string_types) or not o:
        return False
    return o[0] in '\'"'

class Evaluator(object):
    """
    This class is used to evaluate marker expessions.
    """

    operations = {
        '==': lambda x, y: x == y,
        '===': lambda x, y: x == y,
        '~=': lambda x, y: x == y or x > y,
        '!=': lambda x, y: x != y,
        '<':  lambda x, y: x < y,
        '<=':  lambda x, y: x == y or x < y,
        '>':  lambda x, y: x > y,
        '>=':  lambda x, y: x == y or x > y,
        'and': lambda x, y: x and y,
        'or': lambda x, y: x or y,
        'in': lambda x, y: x in y,
        'not in': lambda x, y: x not in y,
    }

    def evaluate(self, expr, context):
        """
        Evaluate a marker expression returned by the :func:`parse_requirement`
        function in the specified context.
        """
        if isinstance(expr, string_types):
            if expr[0] in '\'"':
                result = expr[1:-1]
            else:
                if expr not in context:
                    raise SyntaxError('unknown variable: %s' % expr)
                result = context[expr]
        else:
            assert isinstance(expr, dict)
            op = expr['op']
            if op not in self.operations:
                raise NotImplementedError('op not implemented: %s' % op)
            elhs = expr['lhs']
            erhs = expr['rhs']
            if _is_literal(expr['lhs']) and _is_literal(expr['rhs']):
                raise SyntaxError('invalid comparison: %s %s %s' % (elhs, op, erhs))

            lhs = self.evaluate(elhs, context)
            rhs = self.evaluate(erhs, context)
            result = self.operations[op](lhs, rhs)
        return result

def default_context():
    # Chaquopy: there are two copies of this module: pip uses the one in `packaging`.
    from ..packaging import markers
    return markers.default_environment()

evaluator = Evaluator()

def interpret(marker, execution_context=None):
    """
    Interpret a marker and return a result depending on environment.

    :param marker: The marker to interpret.
    :type marker: str
    :param execution_context: The context used for name lookup.
    :type execution_context: mapping
    """
    try:
        expr, rest = parse_marker(marker)
    except Exception as e:
        raise SyntaxError('Unable to interpret marker syntax: %s: %s' % (marker, e))
    if rest and rest[0] != '#':
        raise SyntaxError('unexpected trailing data in marker: %s: %s' % (marker, rest))
    # Chaquopy: calling default_context on demand rather than during module import, since it
    # now depends on pip.options.
    context = default_context()
    if execution_context:
        context.update(execution_context)
    return evaluator.evaluate(expr, context)
