"""
>>> False
from drython.expression import *
from threading import enumerate
import gc
@generator
def foo(Yield):
    Yield(1)
    Yield(2)
def echo():
    reply = yield
    while True:
        reply = yield reply
e1 = echo()
@generator
def echo2(Yield):
    reply = Yield()
    while True:
        reply = Yield(reply)
e2 = echo2()
e2.send(None)
del e2
gc.collect()
print(enumerate())
"""
from __future__ import print_function  # pragma: no cover
import unittest  # pragma: no cover


class TestStatement(unittest.TestCase):  # pragma: no cover
    def test_pass(self):
        from drython.statement import Pass
        self.assertRaises(TypeError, lambda: Pass.__class__())
    def test_dest(self):
        from drython.statement import dest
        eq = self.assertEqual
        raises = self.assertRaises
        eq(dest((), ()), {})
        eq(dest((), {}), {})
        eq(dest({}, {}), {})
        eq(dest({}, ()), {})
        raises(ValueError, lambda: dest('a', ''))
        raises(ValueError, lambda: dest('', 'a'))
        raises(ValueError, lambda: dest([list, 'a', list, 'b'], ''))

        t123 = (1, 2, 3)
        l123 = [1, 2, 3]
        q1 = ('x', 'y', 'z')
        a1 = dict(x=1, y=2, z=3)
        eq(dest(q1, t123), a1)
        eq(dest(q1, l123), a1)
        eq(dest(q1, 'abc'), dict(x='a', y='b', z='c'))
        raises(ValueError, lambda: dest(q1, 'ab'))
        raises(ValueError, lambda: dest(q1, 'abcd'))

        eq(dest(('x', list, 'star'), 'abc'),
           dict(x='a', star=['b', 'c']))
        eq(dest((list, 'star', 'x'), 'abc'),
           dict(x='c', star=['a', 'b']))
        eq(dest(('x', list, 'star', 'y'), 'abc'),
           dict(x='a', y='c', star=['b']))
        eq(dest(('x', list, 'star', 'y'), 'aABCDc'),
           dict(x='a', y='c', star=['A', 'B', 'C', 'D']))
        eq(dest(('x', list, 'star', 'y'), 'ac'),
           dict(x='a', y='c', star=[]))
        eq(dest([all, 'xs', 'x0', list, 'x12'], 'abc'),
           dict(xs='abc', x0='a', x12=['b', 'c']))


if __name__ == '__main__':  # pragma: no cover
    print('in test main')

    import doctest
    import coverage

    cov = coverage.Coverage()
    cov.start()
    print('coverage started')

    doctest.testfile('../README.md')
    doctest.testmod()

    import drython

    doctest.testmod(m=drython)

    from drython import core, statement, expression, stack, combinator, \
        s_expression, macro

    for m in (
    core, statement, expression, stack, combinator, s_expression):
        doctest.testmod(m=m)
    try:
        pass
        unittest.main()
    finally:
        print('unittests completed')
        cov.stop()
        print('coverage stopped')
        cov.save()
        cov.html_report()
        print('coverage report generated')
