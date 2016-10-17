# Copyright 2015, 2016 Matthew Egan Odendahl
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
Basic utilities for use with the other modules.
"""

# Other modules in this package may require core. To avoid circular
# dependencies, core.py shall not depend on any other modules in this
#  package.


from __future__ import absolute_import, division, print_function
from abc import ABCMeta, abstractmethod

from collections import Mapping
import sys
from itertools import islice, chain
from functools import wraps

if sys.version_info[0] == 2:  # pragma: no cover
    # noinspection PyUnresolvedReferences
    from itertools import izip_longest as zip_longest
else:  # pragma: no cover
    from itertools import zip_longest

# This is to avoid depending on statement.Print(). A bug in Jython
# prevents from __future__ import print_statement from working in
# doctests.
Print = print

_exclude_from__all__ = set(globals().keys())
__test__ = {}


def _private():
    class EmptyType(Mapping, tuple):
        """
        Represents an immutable empty Mapping/tuple
        It's similar to None, but supports * and **
        >>> (lambda *args: tuple(args))(*Empty)
        ()
        >>> (lambda **kwargs: kwargs)(**Empty)
        {}
        >>> list(Empty)
        []
        >>> bool(Empty)
        False
        >>> (1,) + Empty + (2,)
        (1, 2)
        >>> () == Empty
        True
        >>> {} == Empty
        True

        A common mistake in Python is to use a mutable default:
        >>> foo = lambda x={}: x
        >>> foo()
        {}
        >>> foo()['spam'] = 'spam'
        >>> foo()  # surprise!
        {'spam': 'spam'}

        Empty doesn't have this problem, but is still a readonly Mapping
        >>> foo = lambda x=Empty: x
        >>> foo()['spam'] = 'spam'  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: ...
        >>> foo()
        Empty
        """
        __slots__ = ()

        __len__ = tuple.__len__
        __iter__ = tuple.__iter__

        def __new__(cls, *args, **kwargs):
            return tuple.__new__(cls)

        def __init__(self):
            tuple.__init__(self)

        def __getitem__(self, key):
            raise KeyError(key)

        def __repr__(self):
            return 'Empty'

        def __eq__(self, other):
            if other == set() or other == {}:
                return True
            else:
                return tuple.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        def __hash__(self):
            return 0

    __test__[EmptyType.__name__] = EmptyType.__doc__

    res = EmptyType()

    def __init__(self):
        raise TypeError("cannot create 'EmptyType' instances")

    EmptyType.__init__ = __init__
    return res


Empty = _private()
del _private


# class Arguments(Mapping):
#     def __getitem__(self, key):
#         return self.kwargs.get(key, self.args[key])
#
#     def __iter__(self):
#         def it():
#             for i in range(len(self.args)):
#                 yield i
#             for k in self.kwargs:
#                 yield k
#         return it
#
#     def __len__(self):
#         return len(self.args) + len(self.kwargs)
#
#     def __init__(self, *args, **kwargs):
#         self.args = tuple(args)
#         self.kwargs = MappingProxyType(kwargs)
#
#     def apply(self, func):
#         return func(*self.args, **self.kwargs)

def star(func):
    """
    Converts a potentially multiple-argument function to a function of
    one iterable.
    >>> nums = [1, 2, 3]
    >>> Print(*nums)
    1 2 3
    >>> star(Print)(nums)
    1 2 3
    """
    return lambda arg: func(*arg)


def unstar(func):
    """
    Converts a function of one iterable to a function of its elements.
    The inverse of star().
    >>> list((1, 2, 3))
    [1, 2, 3]
    >>> unstar(list)(1, 2, 3)
    [1, 2, 3]
    """
    return lambda *args: func(args)


def stars(func):
    """
    Converts a potentially multiple-argument function to a function of
    one mapping.
    >>> cba = dict(c='C', b='B', a='A')
    >>> test = (lambda a, b, c: Print(a, b, c))
    >>> test(**cba)
    A B C
    >>> stars(test)(cba)
    A B C
    """
    return lambda kwargs: func(**kwargs)


def unstars(func):
    """
    Converts a function of one mapping to a function of keyword args
    >>> test = lambda mapping: Print(mapping)
    >>> test(dict(a='A'))
    {'a': 'A'}
    >>> unstars(test)(a='A')
    {'a': 'A'}
    """
    return lambda **kwargs: func(kwargs)


_sentinel = object()


def partition(iterable, n=2, step=None, fillvalue=_sentinel):
    """
    Chunks iterable into tuples of length n. (default pairs)
    >>> list(partition(range(10)))
    [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9)]

    The remainder, if any, is not included.
    >>> list(partition(range(10), 3))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]

    Keep the remainder by using a fillvalue.
    >>> list(partition(range(10), 3, fillvalue=None))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, None, None)]
    >>> list(partition(range(10), 3, fillvalue='x'))
    [(0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 'x', 'x')]

    The step defaults to n, but can be more to skip elements.
    >>> list(partition(range(10), 2, 3))
    [(0, 1), (3, 4), (6, 7)]

    Or less for a sliding window with overlap.
    >>> list(partition(range(5), 2, 1))
    [(0, 1), (1, 2), (2, 3), (3, 4)]
    """
    step = step or n
    slices = (islice(iterable, start, None, step) for start in range(n))
    if fillvalue is _sentinel:
        return zip(*slices)
    else:
        return zip_longest(*slices, fillvalue=fillvalue)


def interleave(*iterables):
    """
    >>> ''.join(interleave('ABC','xyz'))
    'AxByCz'
    >>> ' '.join(interleave('ABC','xyz','123'))
    'A x 1 B y 2 C z 3'
    """
    return chain.from_iterable(zip(*iterables))


def identity(x):
    """
    The identity function. Returns its argument.
    not to be confused with the id() builtin
    >>> identity('foo')
    'foo'
    """
    return x


def apply(func, *args, **stargs):
    """
    applies a function to arguments.
    >>> apply(Print, 1, 2, 3)
    1 2 3

    also unpacks arguments with the special keywords star and stars

    # like Print(1, 2, *(3, 4), **dict(sep='::'))
    >>> apply(Print, 1, 2, star=(3, 4), stars=dict(sep='::'))
    1::2::3::4
    """
    return func(*args + tuple(stargs.get('star', ())),
                **stargs.get('stars', Empty))


def assign_attr(obj, name, val, oper=None):
    """
    does an augmented assignment to the named attr of obj
    returns obj.

    does a simple replacement if no operator is specified

    usually used in combination with the operator module,
    though any appropriate binary function may be used.
    >>> from operator import add, iadd
    >>> spam = lambda:None
    >>> assign_attr(assign_attr(spam,'eggs',40),'eggs',1,add).eggs
    41
    >>> assign_attr(spam,'eggs',1,iadd).eggs
    42
    """
    if oper:
        setattr(obj, name, oper(getattr(obj, name), val))
    else:
        setattr(obj, name, val)
    return obj


def assign_item(obj, index, val, oper=None):
    """
    does an augmented assignment to the indexed (keyed)
    item of obj. returns obj for chaining.

    does a simple replacement if no operator is specified

    usually used in combination with the operator module,
    though any appropriate binary function may be used.
    >>> from operator import add
    >>> spam = [40]
    >>> assign_item(spam,0, 2,add)
    [42]
    >>> assign_item(globals(),'eggs',  12)['eggs']
    12
    >>> eggs
    12
    """
    if oper:
        obj[index] = oper(obj[index], val)
    else:
        obj[index] = val
    return obj


def delitem(obj, index):
    """
    Deletes the element in obj at index, and returns obj for chaining
    >>> spam = [1, 2, 3]
    >>> delitem(spam, 1)
    [1, 3]
    >>> spam = {'one': 1, 'two': 2}
    >>> delitem(spam, 'one')
    {'two': 2}
    >>> (delitem(globals(), 'spam'), None)[-1]
    >>> try:
    ...    spam
    ...    assert False
    ... except NameError as ne:
    ...    Print(repr(ne))
    NameError("name 'spam' is not defined",)
    """
    del obj[index]
    return obj


# def update(mapping, **bindings):
#     """
#     >>> spam = lambda:None
#     >>> update(spam.__dict__, foo=1, bar=2)
#     >>> spam.foo
#     >>> spam.bar
#     """
#     mapping.update(bindings)
#     return mapping
#
#
# def funcall(func, *args, **kwargs):
#     """
#     Immediately calls the function with the given arguments.
#     """
#     return func(*args, **kwargs)
#
#
# def apply(func, *args, **kwargs):
#     """
#     Partially applies any given arguments to func and returns a function of args and kwargs
#     for the remainder.
#     """
#     # TODO: doctest apply
#     return (lambda a=(), kw=Empty:
#             functools.partial(func, *args, **kwargs)(*a, **kw))


class attrs(object):
    """
    Attribute view of a dictionary.

    Provides Lua-like syntactic sugar when the dictionary has string
    keys that are also valid Python identifiers, which is a common
    occurrence in Python, for example, calling vars() on an object
    returns such a dict.
    >>> spam = {}
    >>> atspam = attrs(spam)

    get and set string keys as attrs
    >>> atspam.one = 1
    >>> atspam.one
    1
    >>> atspam
    attrs({'one': 1})

    changes write through to underlying dict
    >>> spam
    {'one': 1}

    calling the object returns the underlying dict for direct access
    to all dict methods and syntax
    >>> list(
    ...  atspam().items()
    ... )
    [('one', 1)]
    >>> atspam()['one'] = 42
    >>> atspam()
    {'one': 42}

    del removes the key
    >>> del atspam.one
    >>> atspam
    attrs({})
    """
    __slots__ = 'dictionary'

    def __init__(self, dictionary):
        object.__setattr__(self, 'dictionary', dictionary)

    def __call__(self):
        return object.__getattribute__(self, 'dictionary')

    def __getattribute__(self, attr):
        try:
            return self()[attr]
        except KeyError as ke:
            raise AttributeError(*ke.args)

    def __setattr__(self, attr, val):
        self()[attr] = val

    def __delattr__(self, attr):
        try:
            del self()[attr]
        except KeyError as ke:
            raise AttributeError(*ke.args)

    def __repr__(self):
        return "attrs(" + repr(self()) + ")"


# decorator = (lambda d: lambda *args,**kwargs:
#     lambda f:  d(f,*args,**kwargs))
def decorator(arged_decorator):
    """Decorator-with-arguments decorator.

    Decorators can't take arguments, but you can work around this via
    currying, that is, call a decorator factory function with
    arguments that generates a new decorator function (with the
    arguments already built in) on the fly. The @ syntax works with
    these function calls, but it makes defining decorators with
    arguments difficult, especially when using callable classes. This
    decorator decorator abstracts and simplifies the process by
    turning a function of multiple arguments into a decorator factory.

    The function this decorates must take a function as its first
    argument. The remaining arguments will come from the factory call
    @decorator
    >>> @decorator
    ... def before_after(block,before,after):
    ...     def wrapped(name):
    ...         Print(before)
    ...         block(name)
    ...         Print(after)
    ...     return wrapped

    <meet> becomes the first argument to the original before_after
    >>> @before_after("Hello","Goodbye")
    ... def meet(name):
    ...     Print(name)

    >>> meet("World")
    Hello
    World
    Goodbye
    """

    @wraps(arged_decorator)
    def args_taker(*args, **kwargs):
        def func_taker(f):
            return arged_decorator(f, *args, **kwargs)

        return func_taker

    return args_taker


def call(cls):
    """
    reinterprets a class definition as a function call

    Use the magic names FN, STAR, and STARS, for the function,
    positional arguments, and keyword arguments, respectively.
    >>> @call
    ... class spam:
    ...   FN = Print
    ...   STAR = (1,2,3)
    ...   STARS = dict(sep='::')
    1::2::3
    >>> Print(*(1,2,3), **dict(sep='::'))
    1::2::3

    Often args you would normally pass positionally have keyword
    names that you can use instead, but sometimes they don't.
    Class namespaces are dictionaries, and thus unordered.
    Use an underscore-prefixed number for individual positional args.

    Non-magic names become individual keyword args.
    >>> @call
    ... class spam: FN=Print; _0=1; _1=2; _2=3; sep='::'
    1::2::3

    STARS overrides keyword arguments,
    and STAR appends positional arguments
    >>> @call
    ... class spam:
    ...   FN=Print; _0=1; _1=2; sep = ', '
    ...   STAR=(3,); STARS=dict(sep='::')
    1::2::3

    Note that '__doc__', '__module__', '__dict__', and '__weakref__'
    are ignored, since an empty class may already have them. You can use
    STARS if you must pass ignored or magic names as arguments.
    >>> @call
    ... class spam:
    ...   def FN(__doc__, FN):
    ...     return __doc__ - FN
    ...   STARS = dict(__doc__=44, FN=2)

    A call class results in an assignment to the class name.
    >>> spam
    42

    This means that you can usefully nest call classes, using the result
    of an inner call class directly as the argument to the outer call
    class. You can also use function definitions with magic names.

    Here is a nested function call
    >>> spam = list(filter(lambda x: x>5 and x%3>0,range(16)))
    >>> spam
    [7, 8, 10, 11, 13, 14]

    And the equivalent as nested call classes
    >>> del spam
    >>> @call
    ... class spam:
    ...   FN = list
    ...   @call
    ...   class _0:
    ...     FN = filter
    ...     def _0(x):
    ...       return x > 5 and x % 3 > 0
    ...     _1 = range(16)
    >>> spam
    [7, 8, 10, 11, 13, 14]
    """
    args = []
    kwargs = dict(cls.__dict__)
    FN = kwargs['FN']
    STAR = kwargs.get('STAR', ())
    STARS = kwargs.get('STARS', Empty)
    i = 0
    try:
        # save and remove positional arguments from kwargs
        while True:
            s = '_' + str(i)
            args.append(kwargs[s])
            del kwargs[s]
            i += 1
    except KeyError:
        pass
    # remove ignored and magic names from kwargs
    for s in ('__doc__','__module__','__dict__','__weakref__',
              'FN','STARS','STAR'):
        try:
            del kwargs[s]
        except KeyError:
            pass
    kwargs.update(STARS)
    return FN(*chain(args,STAR),**kwargs)


if sys.version_info[0] >= 3:  # pragma: no cover
    exec ("class Abstract(metaclass=ABCMeta):pass")
else:  # pragma: no cover
    class Abstract(object):
        __metaclass__ = ABCMeta


class SEvaluable(Abstract):
    _s_evaluable_ = None

    @abstractmethod
    def s_eval(self, scope):
        pass  # pragma: no cover


__all__ = [e for e in globals().keys()
           if not e.startswith('_')
           if e not in _exclude_from__all__]
