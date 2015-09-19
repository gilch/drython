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

# TODO: docstring core.py module

# Other modules in this package may require core.
# To avoid circular dependencies, core.py shall not depend on any other modules in this package.


# noinspection PyPep8Naming
from abc import ABCMeta, abstractmethod


def Tuple(*args):
    """
    returns args as a tuple
    >>> Tuple(1, 2, 3)
    (1, 2, 3)
    """
    return args


# noinspection PyPep8Naming
def List(*args):
    """
    returns args as a list
    >>> List(1, 2, 3)
    [1, 2, 3]
    """
    return list(args)


# noinspection PyPep8Naming
def Set(*args):
    """
    returns args as a set
    >>> Set(1, 2, 3) == {1, 2, 3}
    True
    """
    return set(args)


# noinspection PyPep8Naming
def Dict(*args):
    """
    pairs args and makes a dictionary with them
    >>> Dict(1, 2)
    {1: 2}
    >>> Dict(1, 2,  3, 4,  5, 6)[3]
    4
    >>> Dict(1, 2,
    ...      3, 4) == {1: 2, 3: 4}
    True
    """
    return dict(partition(args))


class Namespace:
    """
    An "empty" object for containing attrs.
    Not completely empty since it inherits from object
    >>> spam = Namespace(foo=1)
    >>> spam
    Namespace(foo=1)
    >>> spam.foo
    1
    >>> spam.bar = 2
    >>> spam.bar
    2
    """

    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    def __repr__(self):
        return 'Namespace({0})'.format(
            ', '.join('{0}={1}'.format(k, repr(v))
                      for k, v in self.__dict__.items()))


# prog1 = lambda *body: body[0]
# prog1.__doc__ = '''\
# returns the first argument.
# >>> prog1(1, 1+1, 1+1+1)
# 1
# '''


def _private():
    from itertools import islice, zip_longest

    _sentinel = object()

    global partition

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


partition = None
_private()
del _private


def identity(x):
    """
    The identity function. Returns is argument.
    not to be confused with the id() builtin
    >>> identity('foo')
    'foo'
    """
    return x


def akw(*args, **kwargs):
    return args, kwargs


def apply(func, *params, arkwarg):
    # TODO: doctest apply
    args, kwargs = arkwarg
    return func(*(params + args), **kwargs)

# def unzip(iterable):
#     """
#     transpose the iterable.
#     >>> list(unzip([(1, 2), (3, 4)]))
#     [(1, 3), (2, 4)]
#     """
#     return zip(*iterable)


class SEvaluable(metaclass=ABCMeta):
    @abstractmethod
    def s_eval(self, scope):
        pass


