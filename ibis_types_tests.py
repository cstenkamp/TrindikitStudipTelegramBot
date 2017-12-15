# This file contains unit tests for IBIS types.
#

from ibis import *
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

class IbisTypesTests(unittest.TestCase):
    def test_Atomic(self):
        # integer
        x = Ind(123)
        self.assertEquals(x.content, 123)
        self.assertNotEqual(x.content, "123")

        # string
        x = Ind("paris")
        self.assertEquals(x.content, "paris")
        self.assertRaises(AssertionError, Ind, "1paris")
        self.assertRaises(AssertionError, Ind, "p!aris")
        self.assertRaises(AssertionError, Ind, "paris()")
        x = Ind("paris_france")
        self.assertRaises(AssertionError, Ind, "_paris")

    def test_Ans(self):
        # proposition
        ans = Ans("city(paris)")
        self.assertEquals(type(ans), Prop)
        self.assertEquals(ans.pred, Pred1("city"))
        self.assertEquals(ans.ind.content, "paris")

        # short answer
        ans = Ans("paris")
        self.assertEquals(type(ans), ShortAns)
        self.assertEquals(ans.ind.content, "paris")

        # Y/N answer
        ans = Ans("yes")
        self.assertEquals(type(ans), YesNo)
        self.assertEquals(ans.yes, True)

        ans = Ans("no")
        self.assertEquals(type(ans), YesNo)
        self.assertEquals(ans.yes, False)

    def test_Answer(self):
        # proposition
        ans = Answer("city(paris)")
        prop = ans.content
        self.assertEquals(type(prop), Prop)
        self.assertEquals(prop.pred, Pred1("city"))
        self.assertEquals(prop.ind.content, "paris")

        # short answer
        ans = Answer("paris")
        self.assertEquals(type(ans.content), ShortAns)
        self.assertEquals(ans.content.ind.content, "paris")

        # Y/N answer
        ans = Answer("yes")
        self.assertEquals(type(ans.content), YesNo)
        self.assertEquals(ans.content.yes, True)

        ans = Answer("no")
        self.assertEquals(type(ans.content), YesNo)
        self.assertEquals(ans.content.yes, False)

    def test_Prop(self):
        p = Prop("return()")
        self.assertEquals(str(p), "return()")
        self.assertEquals(p.pred, Pred0("return"))
        self.assertEquals(p.yes, True)

        p = Prop("-return()")
        self.assertEquals(str(p), "-return()")
        self.assertEquals(p.pred, Pred0("return"))
        self.assertEquals(p.yes, False)

        p = Prop("dest_city(paris)")
        self.assertEquals(str(p), "dest_city(paris)")
        self.assertEquals(p.pred, Pred1("dest_city"))
        self.assertEquals(p.ind, Ind("paris"))
        self.assertEquals(p.yes, True)

        p = Prop("-dest_city(paris)")
        self.assertEquals(str(p), "-dest_city(paris)")
        self.assertEquals(p.pred, Pred1("dest_city"))
        self.assertEquals(p.ind, Ind("paris"))
        self.assertEquals(p.yes, False)

    def test_Question(self):
        # Y/N questions
        q = Question("?return()")
        self.assertEquals(str(q), "?return()")
        self.assertEquals(type(q), YNQ)
        self.assertEquals(q.prop.pred, Pred0("return"))
        self.assertEquals(q.prop.yes, True)

        q = Question("?-return()")
        self.assertEquals(str(q), "?-return()")
        self.assertEquals(type(q), YNQ)
        self.assertEquals(q.prop.pred, Pred0("return"))
        self.assertEquals(q.prop.yes, False)

        q = Question("?dest_city(paris)")
        self.assertEquals(str(q), "?dest_city(paris)")
        self.assertEquals(type(q), YNQ)
        self.assertEquals(q.prop.pred, Pred1("dest_city"))
        self.assertEquals(q.prop.ind, Ind("paris"))
        self.assertEquals(q.prop.yes, True)

        q = Question("?-dest_city(paris)")
        self.assertEquals(str(q), "?-dest_city(paris)")
        self.assertEquals(type(q), YNQ)
        self.assertEquals(q.prop.pred, Pred1("dest_city"))
        self.assertEquals(q.prop.ind, Ind("paris"))
        self.assertEquals(q.prop.yes, False)

        # WHQ questions
        q = Question("?x.dest_city(x)")
        self.assertEquals(str(q), "?x.dest_city(x)")
        self.assertEquals(type(q), WhQ)
        self.assertEquals(q.pred, Pred1("dest_city"))

        # Alt questions
        q = AltQ(YNQ("city(paris)"), YNQ("city(london)"))
        self.assertEquals(type(q), AltQ)
        self.assertEquals(len(q.ynqs), 2)
        self.assertEquals(q.ynqs[0], YNQ("city(paris)"))
        self.assertEquals(q.ynqs[1], YNQ("city(london)"))

    def test_PlanConstructor(self):
        x = Respond("?return()")
        self.assertEquals(str(x), "Respond('?return()')")
        self.assertEquals(type(x.content), YNQ)
        
        x = ConsultDB("?return()")
        self.assertEquals(str(x), "ConsultDB('?return()')")
        self.assertEquals(type(x.content), YNQ)
        
        x = Findout("?return()")
        self.assertEquals(str(x), "Findout('?return()')")
        self.assertEquals(type(x.content), YNQ)
        
        x = Raise("?return()")
        self.assertEquals(str(x), "Raise('?return()')")
        self.assertEquals(type(x.content), YNQ)

        x = If("?return()", [Findout("?x.return_day(x)")])
        self.assertEquals(x.cond, YNQ("return()"))
        self.assertEquals(x.iftrue, tuple([Findout("?x.return_day(x)")]))
        self.assertEquals(x.iffalse, ())

if __name__ == '__main__':
    unittest.main()
