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
Stack-based combinator algebra for Python.
"""

from functools import lru_cache
from itertools import permutations
from core import Tuple, List
from collections import deque, Mapping

# To avoid circular dependencies in this package,
# stack.py shall depend only on the core.py and statement.py modules.
# statement.py is not required in the current version.

class Stack:
    """
    Stack is an executable data structure for metaprogramming.

    Pushing a special type of function, called a combinator, onto a
    Stack applies the combinator to elements from the stack.
    """
    def __init__(self, *args, rest=None):
        self.head = rest
        for w in args:
            if isinstance(w, Combinator):
                self.head = w(self).head
            else:
                self.head = (self.head, w)

    def __iter__(self):
        """
        Stack returns its elements in the reverse of insertion order,
        hence the name.
        >>> list(Stack(1,2,3))
        [3, 2, 1]
        """
        def it():
            head = self.head
            while head:
                yield head[1]
                head = head[0]
        return it()

    def __repr__(self):
        return 'Stack' + repr(tuple(reversed(self)))
        # return 'Stack(head=%s)' % repr(self.head)

    def __reversed__(self):
        """
        returns elements in insertion order.
        >>> list(reversed(Stack(1,2,3)))
        [1, 2, 3]
        """
        return reversed(tuple(self))

    def push(self, *args):
        """
        push an element on top of the stack. Does not mutate this stack.

        Because Stack is implemented as a linked list, the new stack
        can (and does) share its tail with the original. Unlike
        strings, Pushing to a long stack doesn't double the memory
        required, it just adds a link.

        >>> spam = Stack()
        >>> spam.push(1)
        Stack(1,)
        >>> spam  # original is still there.
        Stack()

        Returns the new stack.
        >>> Stack().push(1).push(2).push(3).push(4)
        Stack(1, 2, 3, 4)

        Same as above
        >>> Stack().push(1, 2, 3, 4)
        Stack(1, 2, 3, 4)

        Pushing a stack word executes it
        >>> Stack().push(1, dup, 2)
        Stack(1, 1, 2)

        Chaning push after *unpacking
        >>> Stack().push(*[1, 2, 3]).push(dup)
        Stack(1, 2, 3, 3)
        """
        return Stack(*args, rest=self.head)

    def pop(self, depth=1):
        r"""
        >>> four = Stack(1,2,3,4)
        >>> four.pop()  # depth defaults to 1
        (Stack(1, 2, 3), 4)
        >>> four.pop(1)
        (Stack(1, 2, 3), 4)
        >>> four.pop(2)  # order preserved.
        (Stack(1, 2), 3, 4)
        >>> four.pop(3)
        (Stack(1,), 2, 3, 4)
        >>> four.pop(4)
        (Stack(), 1, 2, 3, 4)
        >>> stack, a, b = four.pop(2)
        >>> print(stack, a, b, sep='\n')
        Stack(1, 2)
        3
        4
        >>> try:
        ...     four.pop(5)
        ...     assert False
        ... except IndexError as ie:
        ...     print(ie)
        Stack underflow
        """
        xs = deque()
        head = self.head
        try:
            while depth > 0:
                depth -= 1
                xs.appendleft(head[1])
                head = head[0]
        except TypeError as te:
            raise IndexError('Stack underflow') from te
        return Tuple(Stack(rest=head), *xs)

    def peek(self, depth=None):
        """
        >>> Stack(1,2,3).peek()
        3
        >>> Stack(1,2,3).peek(1)
        [3]
        >>> Stack(1,2,3).peek(2)  # order preserved
        [2, 3]
        >>> Stack(1,2,3).peek(3)
        [1, 2, 3]
        >>> try:
        ...     Stack(1,2,3).peek(4)
        ...     assert False
        ... except IndexError as ie:
        ...     print(ie)
        Stack underflow
        """
        if depth:
            stack, *res = self.pop(depth)
        else:
            stack, res = self.pop()
        return res


# ###
# Combinator constructors
# ###

class Combinator:
    """
    Marks func as a combinator. Combinators act on a Stack, and return a Stack.

    A list containing combinators is not itself a combinator, but a kind of
    quoted program. Some combinators consume these quoted programs.
    """
    def __init__(self, func):
        self.func = func

    def __call__(self, stack):
        return self.func(stack)

    def __repr__(self):
        return self.func.__name__


@lru_cache()  # memoized
def op(func, depth=2):
    """
    converts a binary Python function into a combinator
    >>> from operator import add, mul
    >>> Stack(2, 3, op(add))
    Stack(5,)
    >>> Stack(2, 3, op(mul)).peek()
    6
    >>> Stack(4, 2, 3, op(add), op(mul)).peek()
    20

    you can specify a different arity
    >>> Stack(1,2,3,4,5,op(Tuple,4))
    Stack(1, (2, 3, 4, 5))

    but the default assumption is two arguments
    >>> Stack(1,2,3,op(Tuple))
    Stack(1, (2, 3))
    """
    class OpCombinator(Combinator):
        def __repr__(self):
            name = func.__name__
            if func.__name__.startswith('<'):
                name = repr(func)
            if depth == 2:
                return "op(%s)" % name
            return "op({0}, {1})".format(name, depth)

    @OpCombinator
    def op_combinator(stack):
        stack, *args = stack.pop(depth)
        return stack.push(func(*args))
    return op_combinator


def op1(func):
    """ short for op(func, 1). Unary Python function to combinator"""
    return op(func, 1)


def defcombinator(*args):
    """ Creates a new combinator from a composition of other combinators."""
    @Combinator
    def phrase(stack):
        return stack.push(*args)
    return phrase


# ##
# Stack manipulation combinators
# ##


@Combinator
def pop(stack):
    """
    discards the top of the stack
    >>> Stack(..., 'a', pop)
    Stack(Ellipsis,)
    """
    stack, a = stack.pop()
    return stack


@Combinator
def dup(stack):
    """
    duplicates the top of the stack
    >>> Stack(..., 'a', dup)
    Stack(Ellipsis, 'a', 'a')
    """
    return stack.push(stack.peek())


@Combinator
def nop(stack):
    """ no-operation. Returns stack unchanged. """
    return stack


@Combinator
def swap(stack):
    """
    swaps the top two elements of the stack
    >>> Stack(..., 'a', 'b', swap)
    Stack(Ellipsis, 'b', 'a')
    """
    stack, a, b = stack.pop(2)
    return stack.push(b, a)

# creates all depth-3 stack permutation functions
for _cs in permutations('abc'):
    if _cs[0] == 'a':
        # abc is nop
        # acb is swap
        continue
    exec('''
@Combinator
def {0}(stack):
    """
    permutes the top three elements of the stack,
    >>> Stack(..., 'a', 'b', 'c', {0})
    Stack(Ellipsis, '{1}', '{2}', '{3}')
    """
    stack, a, b, c = stack.pop(3)
    return stack.push({1},{2},{3})

    '''.format(''.join(_cs), *_cs))
del _cs


# creates all depth-4 stack permutation functions
for _cs in permutations('abcd'):
    if _cs[0] == 'a':
        continue  # depth < 4; already defined above
    exec('''
@Combinator
def {0}(stack):
    """
    permutes the top four elements of the stack,
    >>> Stack(..., 'a', 'b', 'c', 'd', {0})
    Stack(Ellipsis, '{1}', '{2}', '{3}', '{4}')
    """
    stack, a, b, c, d = stack.pop(4)
    return stack.push({1},{2},{3},{4})

    '''.format(''.join(_cs), *_cs))
del _cs


# popd = defcombinator((pop,), dip)
@Combinator
def popd(stack):
    """
    pops one deeper
    >>> Stack(..., 'a', 'b', popd)
    Stack(Ellipsis, 'b')
    """
    stack, a, b = stack.pop(2)
    return stack.push(b)


# dupd = defcombinator((dup,), dip)
@Combinator
def dupd(stack):
    """
    duplicates one deeper
    >>> Stack(..., 'a', 'b', dupd)
    Stack(Ellipsis, 'a', 'a', 'b')
    """
    stack, a, b = stack.pop(2)
    return stack.push(a, a, b)


# ##
# Operator combinators
# ##


@Combinator
def quote(stack):
    """
    wraps the top n elements in a list
    >>> Stack('a','b','c',2,quote)
    Stack('a', ['b', 'c'])
    """
    stack, depth = stack.pop()
    stack, *args = stack.pop(depth)
    return stack.push(args)


@Combinator
def choice(stack):
    stack, b, t, f = stack.pop(3)
    return stack.push(t if b else f)


# ##
# Quotation Combinators
# ##

@Combinator
def do(stack):
    """
    The do combinator applies an ordinary Python function to a
    list of arguments.
    (The print function returns None)
    >>> Stack([1,2,3],print,do)
    1 2 3
    Stack(None,)

    Keywords are also supported with a dictionary
    >>> Stack([1,2,3],dict(sep=':'),print,do)
    1:2:3
    Stack(None,)

    Use an empty list for no arguments
    >>> Stack([],dict,do)
    Stack({},)

    Any non-Mapping iterable will do for the arguments list.
    Any Mapping will do for the keywords dictionary
    """
    stack, kwargs, func = stack.pop(2)
    if isinstance(kwargs, Mapping):
        stack, args = stack.pop()
        return stack.push(func(*args, **kwargs))
    return stack.push(func(*kwargs))  # kwargs was just args


@Combinator
def dip(stack):
    stack, x, p = stack.pop(2)
    return stack.push(*p).push(x)


@Combinator
def cons(stack):
    stack, p, q = stack.pop(2)
    return stack.push(List(p, *q))

@Combinator
def take(stack):
    stack, p, q = stack.pop(2)
    return stack.push(list(p)+[q])

@Combinator
def Ic(stack):
    """
    the I combinator. Unquotes the iterable by pushing its elements.
    >>> from operator import add
    >>> Stack([1,2,op(add)], Ic)
    Stack(3,)
    """
    stack, x = stack.pop()
    return stack.push(*x)

@Combinator
def Jc(stack):
    stack, p, q, r, s = stack.pop(4)
    return stack.push(q, p, *s).push(r, *s)

@Combinator
def Bc(stack):
    stack, p, q = stack.pop()
    return stack.push(*p).push(*q)

@Combinator
def Sc(stack):
    stack, p, q, r = stack.pop(3)
    return stack.push(List(p, *q), p, *r)

@Combinator
def Tc(stack):
    stack, p, q = stack.pop(2)
    return stack.push(q, *p)

Cc = defcombinator([swap], dip, Ic)

# Kc = defcombinator([pop], dip, Ic)
@Combinator
def Kc(stack):
    stack, p, q = stack.pop(2)
    return stack.push(*q)

Wc = defcombinator([dup], dip, Ic)


@Combinator
def Xc(stack):
    p = stack.peek()
    return stack.push(*p)


@Combinator
def dipd(stack):
    stack, x, y, p = stack.pop(3)
    return stack.push(*p).push(x, y)


@Combinator
def dipdd(stack):
    stack, x, y, z, p = stack.pop(4)
    return stack.push(*p).push(x, y, z)


@Combinator
def step(stack):
    stack, it, p = stack.pop(2)
    for a in it:
        stack.push(a).push(*p)


@Combinator
def nullary(stack):
    stack, p = stack.pop()
    return stack.push(stack.push(*p).peek())


@Combinator
def cleave(stack):
    stack, x, p, q = stack.pop(3)
    return stack.push(
        stack.push(x, *p).peek(),
        stack.push(x, *q).peek())


@Combinator
def ifte(stack):
    """
    the if-then-else combinator
    >>> Stack([True],[['was true'],print,do],[["wasn't"],print,do],ifte)
    was true
    Stack(None,)
    >>> Stack([False],[['was true'],print,do],[["wasn't"],print,do],ifte)
    wasn't
    Stack(None,)
    """
    stack, b, t, e = stack.pop(3)
    return stack.push(*(t if Stack(*b).peek() else e))


@Combinator
def times(stack):
    stack, n, p = stack.pop(2)
    for i in range(n):
        stack = stack.push(*p)


@Combinator
def infra(stack):
    stack, a, p = stack.pop(2)
    return stack.push(Stack(*reversed(a)).push(*p))


@Combinator
def subspace(stack):
    stack, a, p = stack.pop(2)
    return stack.push(Stack(*a).push(*p))


class Def:
    """
    Define a Python function from stack words.
    >>> from operator import mul
    >>> square = Def(dup,op(mul))
    >>> square(7)
    49
    >>> square(4)
    16
    >>> square
    Def(dup, op(mul))
    """
    def __init__(self, *words, minargs=None, maxargs=None):
        self.words, self.min_args, self.max_args = words, minargs, maxargs

    def __call__(self, *args):
        if self.min_args is not None and len(args) < self.min_args:
            raise TypeError("{0}() missing {1} required positional arguments",
                            repr(self), self.min_args-len(args))
        if self.max_args is not None and len(args) > self.max_args:
            raise TypeError(
                "{0}() takes {1} positional arguments, but {2} were given",
                repr(self), self.max_args, len(args))
        return Stack(*args).push(*self.words).peek()

    def __repr__(self):
        return "Def"+repr(tuple(self.words))

