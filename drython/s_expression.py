# Copyright 2015 Matthew Egan Odendahl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Symbolic-expression for Python, with macro support.

Typical module import:

    from drython.s_expression import S

S is a prefix for both symbols and s-expressions
Symbol: `S.foo`,
S-expression: `S(Print,'foo')`.
"""
# s_expression may safely depend on .core and .statement

from __future__ import absolute_import, division
from drython.statement import Print

import sys

if sys.version_info[0] == 2:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from UserString import UserString
else:
    from collections import UserString

from keyword import iskeyword
from operator import add

from drython.core import Empty
from drython.statement import Var, Raise


class SExpression(object):
    """
    S-expressions are executable data structures for metaprogramming.

    An SExpression object represents a potential function call.

    The function isn't actually called until invocation
    of the .s_eval() method, which will also .s_eval() any
    nested SEvaluable objects before applying the function.
    >>> from operator import add, mul
    >>> spam = S(add,20,4)
    >>> spam
    S(<built-in function add>,
      20,
      4)
    >>> spam.s_eval()  # same as >>> add(20,4)
    24
    >>> spam.s_eval()  # works more than once
    24

    represents >>> add(mul(4, 10), 2)  # 4*10 + 2
    >>> spam = S(add,S(mul,4,10),2)
    >>> spam.s_eval()
    42

    Even the function argument can be a nested S-expression
    >>> S(S(lambda a,b: a and b, add,mul),2,3).s_eval()
    6
    >>> S(S(lambda a,b: a or b, add,mul),2,3).s_eval()
    5

    Keywords also work
    >>> S(Print,1,2,3,sep='::').s_eval()
    1::2::3

    Important: SExpression will not peek into other data structures to evaluate
    nested SEvaluable objects. You must evaluate them explicitly, or use
    an S-expression to create the data structure.

    This doesn't print 'test'.
    >>> identity = lambda x: x
    >>> S(identity,[S(Print,'test')]).s_eval()
    [S(<built-in function print>,
      'test')]

    This does, since it uses another S-expression to make the list.
    >>> from drython.core import enlist
    >>> S(identity,S(enlist,S(Print,'test'))).s_eval()
    test
    [None]

    Explicit evaluation also works.
    >>> S(identity,[S(Print,'test').s_eval()]).s_eval()
    test
    [None]

    SExpression treats functions with the @macro decorator specially.
    These are given any nested S objects unevaluated, and return a
    new object to be evaluated.
    >>> from drython.macros import If
    >>> S(If, True, S(Print,'yes'), S(Print,'no')).s_eval()
    yes
    >>> S(If, False, S(Print,'yes'), S(Print,'no')).s_eval()
    no

    For comparison, note that a non-macro function gets any nested
    S objects pre-evaluated.
    >>> S(lambda b,t,e=None: t if b else e,
    ...   True, S(Print,'yes'), S(Print,'no')).s_eval()
    yes
    no
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def s_eval(self, scope=Empty):
        func = s_eval_in_scope(self.func, scope)
        if hasattr(func, '_macro_'):
            return s_eval_in_scope(func(*self.args, **self.kwargs), scope)
        return func(
            *(s_eval_in_scope(a, scope) for a in self.args),
            **{k: s_eval_in_scope(v, scope) for k, v in self.kwargs.items()})

    def __repr__(self):
        indent = '\n  '
        return "S({0}{1}{2})".format(
            repr(self.func),
            ',' + indent + (',' + indent).join(
                map(lambda a: repr(a).replace('\n', indent), self.args))
            if self.args else '',
            ',{0}**{1}'.format(indent, repr(self.kwargs).replace('\n', indent))
            if self.kwargs else '')


def s_eval_in_scope(element, scope):
    """
    Evaluates the element in the given scope using its s_eval method, if present.
    Otherwise returns the element unevaluated.

    >>> from operator import sub
    >>> s_eval_in_scope(S(sub,S.x,S.y), dict(x=10,y=3))
    7

    integers are not s-evaluable, so evaluate to themselves.
    >>> s_eval_in_scope(10-7, globals())
    3
    """
    if hasattr(element, 's_eval'):
        return element.s_eval(scope)
    return element


class SymbolError(NameError):
    pass


class Symbol(UserString, str):
    """
    Symbols for S-expressions.

    A Symbol represents a potential Python identifier.
    >>> spam = 1
    >>> Print(spam)
    1
    >>> no_symbol = S(Print,spam)
    >>> no_symbol  # spam already resolved to 1
    S(<built-in function print>,
      1)
    >>> with_symbol = S(Print,S.spam)
    >>> with_symbol  # S.spam is still a symbol
    S(<built-in function print>,
      S.spam)
    >>> no_symbol.s_eval()
    1

    Symbols require a containing scope
    >>> with_symbol.s_eval(globals())
    1
    >>> spam = 8

    doesn't change, was baked-in
    >>> no_symbol.s_eval(globals())
    1

    globals()['spam'] == 8
    >>> with_symbol.s_eval(globals())
    8

    value depends on scope
    >>> with_symbol.s_eval(dict(spam=42))
    42

    Macros get Symbols unevaluated. Unevaluated Symbols work like strings.
    So macros can also rewrite Symbols
    >>> S.quux + S.norf
    S.quuxnorf
    """

    def __repr__(self):
        """
        >>> S.foo
        S.foo
        >>> S.fo + S.r
        Symbol('for')
        >>> Symbol('1') + S.foo
        Symbol('1foo')
        """
        # or not self.isidentifier(): <- not in 2.7
        if (iskeyword(self)
            or not (self[0].isalpha()
                    or self[0] == '_')
            or not self[1:].replace('_', 'X').isalnum()):
            return 'Symbol(%s)' % repr(self.data)
        return 'S.' + self.data

    def s_eval(self, scope=Empty):
        """ looks up itself in scope """
        try:
            return scope[self]
        except KeyError:
            Raise(SymbolError(
                'Symbol %s is not bound in the given scope' % repr(self)
            ), From=None)
            # except TypeError as ex:
            #     Raise(SymbolError(
            #         'Symbol %s is not bound in the given scope' % repr(self)
            #     ), From=ex)


def _private():
    _gensym_counter = Var(0)

    # noinspection PyGlobalUndefined
    global gensym

    # noinspection PyRedeclaration,PyUnusedLocal
    def gensym(prefix=''):
        """
        generates a unique Symbol. Gensyms are not valid identifiers,
        but they are valid dictionary keys.

        A gensym is only unique per import of this module, when the
        gensym counter is initialized. It should not be relied upon for
        uniqueness across a network, nor in serialized persistent storage.
        gensym() locks the counter update for thread safety.

        Python normally only imports a module once and caches the
        result for any further import attempts, but this can be
        circumvented.

        gensyms are typically used by macros to avoid conflicts
        with other symbols in the environment.

        gensyms have an optional prefix for improved error messages
        and macro debugging. The suffix is the gensym count at creation.

        >>> gensym()
        Symbol('#:$1')
        >>> gensym(S.foo)  # foo prefix
        Symbol('#:foo$2')
        >>> gensym(S.foo)  # not the same symbol as above
        Symbol('#:foo$3')
        >>> gensym('foo')  # strings also work.
        Symbol('#:foo$4')
        """

        return Symbol(
            '#:{0}${1}'.format(prefix, str(_gensym_counter.set(1, add))))


_private()
del _private


def _private():
    class SSyntax(object):
        """
        prefix for creating S-expressions and Symbols.
        see help('drython.s_expression') for further details.
        """
        __slots__ = ()

        def __call__(self, func, *args, **kwargs):
            return SExpression(func, *args, **kwargs)

        def __getattribute__(self, attr):
            return Symbol(attr)

    return SSyntax()


S = _private()
del _private


# defines an interface used by SExpression, so belongs here, not in macros.py
def macro(func):
    """
    Marks the func as a macro.
    In S-expressions, macros are given any S-expressions
    unevaluated, then the result is evaluated.
    """
    func._macro_ = None
    return func
