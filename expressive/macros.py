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

"""
from _collections_abc import Mapping
from core import partition

from sexpression import S, Quote
from statement import Elif, progn


def macro(func):
    """
    Marks the func as a macro.
    In S-expressions, macros are given any S-expressions
    unevaluated, then the result is evaluated.
    """
    func.__macro__ = None
    return func

class Scope(Mapping):
    def __len__(self):
        return len(self.vars)

    def __iter__(self):
        return iter(self.vars)

    def __init__(self, parent, locals=None, kwvals=None, nonlocals=None):
        self.parent = parent
        self.vars = locals or {}
        if kwvals:
            self.vars.update(kwvals)
        self.nonlocals = nonlocals or set()

    def __getitem__(self, name):
        try:
            return self.vars[name]
        except KeyError:
            try:
                return self.parent[name]
            except TypeError as err:
                pass
            except KeyError as err:
                pass
            raise NameError('name %s is not defined in scope' % repr(name)) from err

    def __setitem__(self, name, val):
        if name in self.nonlocals:
            try:
                self.parent[name] = val
            except KeyError as err:
                pass
            except TypeError as err:
                pass
            raise NameError('nonlocal %s not found' % repr(name)) from err
        else:
            self.vars[name] = val

    def Nonlocal(self, *names):
        self.nonlocals |= set(names)

class Lambda:
    def __init__(self, symbols, body, Nonlocals):
        self.symbols = Quote.of(symbols)
        self.body = body
        self.nonlocals = Quote.of(Nonlocals)

    def eval(self, scope=None):
        symbols = self.symbols.eval(scope)
        nonlocals = self.nonlocals.eval(scope)

        def lx(*args, **kwargs):
            return self.body.eval(
                Scope(scope,
                      dict(zip(symbols, args)),
                      kwargs,
                      nonlocals))
        return lx

@macro
def Lx(symbols, *body, Nonlocals=None):
    """
    lambda expression.
    >>> from operator import add
    >>> plus = S(Lx,(S.x,S.y),S(add,S.x,S.y))
    >>> S(plus,40,2).eval()
    42
    >>> S(plus,20,4).eval()
    24
    """
    return Lambda(symbols, S(progn, *body), Nonlocals)

class SetQ:
    def __init__(self, pairs):
        self.pairs = ((q, Quote.of(x)) for q, x in partition(pairs))

    def eval(self, scope):
        for var, val in self.pairs:
            scope[var] = val.eval(scope)


@macro
def SETQ(*pairs):
    """
    >>> from operator import add
    >>> S(SETQ,S.spam,1,S.eggs,S(add,1,S.spam)).eval(globals())
    >>> spam
    1
    >>> eggs
    2
    """
    return SetQ(pairs)


class Nonlocal:
    def __init__(self, symbols):
        self.symbols = symbols

    def eval(self,scope):
        scope.Nonlocal(*self.symbols)


@macro
def NONLOCAL(*symbols):
    return Nonlocal(symbols)

class ThunkType:
    def __init__(self, body):
        self.body = Quote.of(body)

    def eval(self, scope=None):
        def thunk():
            return self.body.eval(scope)
        return thunk
@macro
def THUNK(body):
    return ThunkType(body)


@macro
def IF(Boolean, Then, Else=None):
    """
    >>> from operator import add, sub
    >>> S(IF,S(sub,1,1),S(print,'then')).eval()
    >>> S(IF,S(add,1,1),S(print,'then')).eval()
    then
    >>> S(IF,S(add,1,1),S(print,'then'),S(print,'else')).eval()
    then
    >>> S(IF,S(sub,1,1),S(print,'then'),S(print,'else')).eval()
    else
    """
    return S(EVAL,
             S((Else, Then).__getitem__,
               S(bool,
                 Boolean)))


@macro
def EVAL(body):
    return EvalType(body)

class EvalType:
    def __init__(self, body):
        self.body = body

    def eval(self,scope):
        if hasattr(self.body,'eval'):
            res = self.body.eval(scope)
            if hasattr(res,'eval'):
                return res.eval(scope)
            return res
        return self.body

@macro
def COND(*rest, Else=None):
    return S(Elif,
             *map(lambda x: S(THUNK,
                              x),
                  rest),
             Else=S(THUNK,
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
#     >>> S(AND,S(str,1),True,"yes",S(print,'shortcut?'),S(print,'nope')).eval()
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
#     >>> S(OR,[],'',False,S(print,'shortcut?'),'yes?',S(print,'nope')).eval()
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
def DOT(obj, *names):
    """
    attribute and index/key access macro
    >>> 'quux'[-1]
    'x'
    >>> S(DOT,'quux',[-1]).eval()
    'x'
    >>> ['foo','bar','baz'][1][-1]
    'r'
    >>> S(DOT,['foo','bar','baz'],[1],[-1]).eval()
    'r'
    >>> str.join
    <method 'join' of 'str' objects>
    >>> S(DOT,str,S.join).eval(dict(join='error!'))
    <method 'join' of 'str' objects>
    """
    res = obj
    for n in names:
        # the unattached subscripts [i] are actually lists, so n[0]
        res = res[n[0]] if isinstance(n, list) else getattr(res, n)
    return res


def _private():
    _sentinel = S(None)  # used only for is check

    @macro
    def THREAD(x, first=_sentinel, *rest):
        # TODO: doctest THREAD
        if first is _sentinel:
            return x
        return THREAD(S(first.func,x,*first.args,**first.kwargs),*rest)

    @macro
    def THREAD_TAIL(x, first=_sentinel, *rest):
        # TODO: doctest THREAD_TAIL
        if first is _sentinel:
            return x
        return THREAD(S(first.func,*(first.args+(x,)),**first.kwargs),*rest)

    return THREAD, THREAD_TAIL

THREAD = None
THREAD_TAIL = None
THREAD, THREAD_TAIL = _private()
del _private

