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

# TODO: docstring macros.py
from __future__ import absolute_import, division
from drython.statement import Print

from collections import Mapping

from drython.core import partition
from drython.s_expression import S, Quote, macro
from drython.statement import Elif, progn, Raise


# macros.py depends on core.py, s_expression.py, and statement.py
# macros.py does not currently require stack.py

class Scope(Mapping):
    def __len__(self):
        return len(self.vars)

    def __iter__(self):
        return iter(self.vars)

    def __init__(self, parent, local_variables=None, kwvals=None):
        self.parent = parent
        self.vars = local_variables or {}
        if kwvals:
            self.vars.update(kwvals)
        self.nonlocals = set()

    def __getitem__(self, name):
        try:
            return self.vars[name]
        except KeyError:
            try:
                return self.parent[name]
            except TypeError as err:
                Raise(NameError('name %s is not defined in scope' % repr(name)), From=err)
            except KeyError as err:
                Raise(NameError('name %s is not defined in scope' % repr(name)), From=err)

    def __setitem__(self, name, val):
        if name in self.nonlocals:
            try:
                self.parent[name] = val
            except KeyError as err:
                Raise(NameError('nonlocal %s not found' % repr(name)), From=err)
            except TypeError as err:
                Raise(NameError('nonlocal %s not found' % repr(name)), From=err)
        else:
            self.vars[name] = val

    # noinspection PyPep8Naming
    def Nonlocal(self, *names):
        self.nonlocals |= set(names)


# class SLambda(object):
#     def __init__(self, symbols, body, varg, kwonlys, kwvarg, defaults):
#         self.body = body
#         self.varg = varg
#         self.kwvarg = kwvarg
#         self.symbols, self.kwolnlys, self.defaults = \
#             map(Quote.of, (symbols, kwonlys, defaults))
#
#     def s_eval(self, scope=None):
#         symbols, kwonlys, defaults = (s.s_eval(scope) for s in (
#             self.symbols, self.kwolnlys, self.defaults))
#         kwonlys = set(kwonlys)
#         symbols_set = set(symbols)
#
#         def lx(*args, **kwargs):
#             kwvals = dict(defaults)
#             kwvals[self.kwvarg] = {k: v for k, v in kwargs.items()
#                                    if k not in symbols_set if k not in kwonlys}
#             kwvals[self.varg] = args[len(symbols):]
#             kwvals.update({k: v for k, v in kwargs.items() if k in kwonlys})
#
#             return self.body.s_eval(
#                 Scope(scope,
#                       dict(zip(symbols, args)),
#                       kwvals))
#
#         return lx


class SLambda1(object):
    def __init__(self, symbol, body):
        self.body = body
        self.symbol = symbol

    def s_eval(self, scope):
        def l1(arg):
            return self.body.s_eval(Scope(scope, {self.symbol: arg}))

        return l1


# noinspection PyPep8Naming
@macro
def L1(symbol, *body):
    return SLambda1(symbol, S(progn, *body))


# # symbols, vargs, kwonly, kwvargs
# # noinspection PyPep8Naming
# @macro
# def Lx(symbols, *body, varg=None, kwonlys=(), kwvarg=None, defaults=()):
#     """
#     lambda expression.
#     >>> from operator import add
#     >>> plus = S(Lx,(S.x,S.y),S(add,S.x,S.y))
#     >>> S(plus,40,2).s_eval()
#     42
#     >>> S(plus,20,4).s_eval()
#     24
#     """
#     # TODO: test varg, kwonlys, kwvarg, defaults
#     return SLambda(symbols, S(progn, *body), varg, kwonlys, kwvarg, defaults)


class SSetQ(object):
    def __init__(self, pairs):
        self.pairs = ((q, Quote.of(x)) for q, x in partition(pairs))

    def s_eval(self, scope):
        for var, val in self.pairs:
            scope[var] = val.s_eval(scope)


@macro
def setq(*pairs):
    """
    >>> from operator import add
    >>> S(setq,S.spam,1,S.eggs,S(add,1,S.spam)).s_eval(globals())
    >>> spam
    1
    >>> eggs
    2
    """
    return SSetQ(pairs)


class SNonlocal(object):
    def __init__(self, symbols):
        self.symbols = symbols

    def s_eval(self, scope):
        scope.Nonlocal(*self.symbols)


# noinspection PyPep8Naming
@macro
def Nonlocal(*symbols):
    return SNonlocal(symbols)


class SThunk(object):
    def __init__(self, body):
        self.body = Quote.of(body)

    def s_eval(self, scope=None):
        return lambda: self.body.s_eval(scope)


@macro
def thunk(body):
    return SThunk(body)


# noinspection PyPep8Naming
@macro
def If(boolean, then, Else=None):
    """
    >>> from operator import add, sub
    >>> S(If,S(sub,1,1),S(Print,'then')).s_eval()
    >>> S(If,S(add,1,1),S(Print,'then')).s_eval()
    then
    >>> S(If,S(add,1,1),S(Print,'then'),S(Print,'else')).s_eval()
    then
    >>> S(If,S(sub,1,1),S(Print,'then'),S(Print,'else')).s_eval()
    else
    """
    return S(s_eval,
             S((Else, then).__getitem__,
               S(bool,
                 boolean)))


@macro
def s_eval(body):
    return SEval(body)


class SEval(object):
    def __init__(self, body):
        self.body = body

    def s_eval(self, scope):
        if hasattr(self.body, 's_eval'):
            res = self.body.s_eval(scope)
            if hasattr(res, 's_eval'):
                return res.s_eval(scope)
            return res
        return self.body


# noinspection PyPep8Naming
@macro
def cond(*rest, **Else):
    assert Else.keys() <= frozenset(['Else'])
    Else = Else.get('Else', None)
    return S(Elif,
             *map(lambda x: S(thunk,
                              x),
                  rest),
             Else=S(thunk,
                    Else))


# @macro
# def AND(first=True, *rest):
#     """
#     returns the first false argument. Shortcuts evaluation of the
#     remaining S expressions.
#     >>> S(AND).eval()
#     True
#     >>> S(AND,'yes').eval()
#     'yes'
#     >>> S(AND,False).eval()
#     False
#     >>> S(AND,S(str,1),True,"yes",S(Print,'shortcut?'),S(Print,'nope')).eval()
#     shortcut?
#     """
#     return S(IF,first,S(EVAL,S(AND,*rest)),first)
#
# @macro
# def OR(scope, first=None, *rest):
#     """
#     returns the first true argument. Shortcuts evaluation of the
#     remaining S expressions.
#     >>> S(OR).eval()
#     >>> S(OR,'yes').eval()
#     'yes'
#     >>> S(OR,[]).eval()
#     []
#     >>> S(OR,[],'yes').eval()
#     'yes'
#     >>> S(OR,[],'',False,S(Print,'shortcut?'),'yes?',S(Print,'nope')).eval()
#     shortcut?
#     'yes?'
#     """
#     first = try_eval(first, scope)
#     if not rest:
#         return first
#     if first:
#         return first
#     return OR(scope, *rest)


@macro
def dot(obj, *names):
    """
    attribute and index/key access macro
    >>> 'quux'[-1]
    'x'
    >>> S(dot,'quux',[-1]).s_eval()
    'x'
    >>> ['foo','bar','baz'][1][-1]
    'r'
    >>> S(dot,['foo','bar','baz'],[1],[-1]).s_eval()
    'r'
    >>> str.join.__name__
    'join'
    >>> S(dot,str,S.join,S.__name__).s_eval(dict(join='error!'))
    'join'
    """
    res = obj
    for n in names:
        # the unattached subscripts [i] are actually lists, so n[0]
        res = res[n[0]] if isinstance(n, list) else getattr(res, n)
    return res


def _private():
    _sentinel = S(None)  # used only for is check

    global thr, thrt
    # noinspection PyShadowingNames
    @macro
    def thr(x, first=_sentinel, *rest):
        # TODO: doctest threading
        if first is _sentinel:
            return x
        return thr(S(first.func, x, *first.args, **first.kwargs), *rest)

    # noinspection PyShadowingNames
    @macro
    def thrt(x, first=_sentinel, *rest):
        # TODO: doctest threading_tail
        if first is _sentinel:
            return x
        return thrt(S(first.func, *(first.args + (x,)), **first.kwargs), *rest)


thr = None
thrt = None

_private()
del _private

# def GENX(func,iterable,predicate):
# TODO: genexprs


# def Def

# TODO: port Hy builtins/core?


# TODO: comprehension macros

# def compose1(f,g):
#     return lambda *args,**kwargs: f(g(*args,**kwargs))
#
# def compose(f,g):
#     return lambda *args,**kwargs: f(*g(*args,**kwargs))

# @macro
# def Lambda(arg,body):
#     return eval('lambda %s:body'%arg)

# TODO: doctests
# import doctest; doctest.testmod()

