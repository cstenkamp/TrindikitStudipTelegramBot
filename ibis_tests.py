# This file contains unit tests for IBIS semantics.
#

from ibis import Domain
from ibis_types import Answer, Question, Prop
import unittest

####################### such that basestring can be used ######################
try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring
####################### such that basestring can be used ######################

class IbisTests(unittest.TestCase):
    preds0 = 'return'

    preds1 = {'price': 'int',
              'dest_city': 'city'}

    means = 'plane', 'train'
    cities = 'paris', 'london', 'berlin'

    sorts = {'means': means,
             'city': cities}

    domain = Domain(preds0, preds1, sorts)


    def test_relevant(self):
        # Y/N questions
        que = Question("?return()")

        ans = Answer("yes")
        self.assertTrue(self.domain.relevant(ans.content, que))
        
        ans = Answer("no")
        self.assertTrue(self.domain.relevant(ans.content, que))

        ans = Answer("paris")
        self.assertFalse(self.domain.relevant(ans.content, que))


        # WHQ questions
        que = Question("?x.dest_city(x)")

        ans = Answer("paris")
        self.assertTrue(self.domain.relevant(ans.content, que))

        ans = Answer("-paris")
        self.assertTrue(self.domain.relevant(ans.content, que))

        ans = Answer("dest_city(paris)")
        self.assertTrue(self.domain.relevant(ans.content, que))

        ans = Answer("five")
        self.assertFalse(self.domain.relevant(ans.content, que))

        ans = Answer("-five")
        self.assertFalse(self.domain.relevant(ans.content, que))


    def test_resolves(self):
        # Y/N questions
        que = Question("?return()")

        ans = Answer("yes")
        self.assertTrue(self.domain.resolves(ans.content, que))
        
        ans = Answer("no")
        self.assertTrue(self.domain.resolves(ans.content, que))

        ans = Answer("paris")
        self.assertFalse(self.domain.resolves(ans.content, que))


        # WHQ questions
        que = Question("?x.dest_city(x)")

        ans = Answer("paris")
        self.assertTrue(self.domain.resolves(ans.content, que))

        ans = Answer("-paris")
        self.assertFalse(self.domain.resolves(ans.content, que))

        ans = Answer("dest_city(paris)")
        self.assertTrue(self.domain.resolves(ans.content, que))

        ans = Answer("five")
        self.assertFalse(self.domain.resolves(ans.content, que))

        ans = Answer("-five")
        self.assertFalse(self.domain.resolves(ans.content, que))


    def test_combine(self):
        # Y/N questions
        que = Question("?return()")

        ans = Answer("yes")
        res = Prop("return()")
        self.assertEqual(self.domain.combine(que, ans.content), res)

        ans = Answer("no")
        res = Prop("-return()")
        self.assertEqual(self.domain.combine(que, ans.content), res)


        # WHQ questions
        que = Question("?x.dest_city(x)")

        ans = Answer("paris")
        res = Prop("dest_city(paris)")
        self.assertEqual(self.domain.combine(que, ans.content), res)

        ans = Answer("-paris")
        res = Prop("-dest_city(paris)")
        self.assertEqual(self.domain.combine(que, ans.content), res)

        ans = Answer("dest_city(paris)")
        res = Prop("dest_city(paris)")
        self.assertEqual(self.domain.combine(que, ans.content), res)

if __name__ == '__main__':
    unittest.main()
