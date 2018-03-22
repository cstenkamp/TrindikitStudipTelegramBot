# -*- encoding: utf-8 -*-

#
# ibis_types.py
# Copyright (C) 2009, Peter Ljunglöf. All rights reserved.
#

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published 
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# and the GNU Lesser General Public License along with this program.  
# If not, see <http://www.gnu.org/licenses/>.

from trindikit import Type, is_sequence, Move, SingletonMove
from types import FunctionType, MethodType
import functools
import time

######################################################################
# IBIS semantic types
######################################################################

# Atomic types: individuals, predicates, sorts

class Atomic(Type):
    """Abstract base class for semantic classes taking a string argument.
    
    Do not create instances of this class, use instead the subclasses:
      - Ind
      - Pred0
      - Pred1
      - Sort
    """
    contentclass = str
    
    def __init__(self, atom):
        assert isinstance(atom, (str, int, bytes))
        assert atom not in ("", "yes", "no")
        try:
            atom = int(atom)
        except ValueError:
            if not isinstance(atom, bytes):
                assert atom[0].isalpha()
                # assert all(ch.isalnum() or ch in "_-+: \n" for ch in atom)
                atom = atom.replace("'", "*")
                assert all(ch.isalnum() or ch in "_-+: \n.?()/!öüä,*" for ch in atom)
        self.content = atom
    
    def __str__(self):
        return "%s" % self.content.__str__()

class Ind(Atomic): 
    """Individuals."""
    def _typecheck(self, context):
        assert self.content in context.inds

class Pred0(Atomic): 
    """0-place predicates."""
    def _typecheck(self, context):
        assert self.content in context.preds0


class Pred1(Atomic): 
    """1-place predicates."""
    def apply(self, ind):
        """Apply the predicate to an individual, returning a proposition."""
        assert isinstance(ind, Ind), "%s must be an individual" % ind
        return Prop(self, ind)

    def _typecheck(self, context):
        assert self.content in context.preds1

    def __init__(self, *args, **kwargs):
        # print("PRED1",*args, **kwargs) #HIER
        # self._typecheck(args[0])
        super(Pred1, self).__init__(args[0], **{})
        if len(args) > 1:
            self.arg2 = args[1]
        if kwargs.get("createdfrom"):
            self.createdfrom = kwargs["createdfrom"]


    def __str__(self):
        return self.content.__str__()

    def __repr__(self):
        if hasattr(self, "arg2") and self.arg2:
            return "Pred1(" + self.content + ", " + self.arg2 if isinstance(self.arg2, str) else self.arg2.content + ")"
        else:
            return "Pred1("+self.content+")"


class Pred2(Atomic):
    """2-place predicates."""
    def apply(self, ind):
        """Apply the predicate to an individual, returning a 1st order predicate."""
        assert isinstance(ind, Ind), "%s must be an individual" % ind
        return Pred1(self, ind)

    def _typecheck(self, context):
        assert self.content in context.preds2

    def __init__(self, pred, domaincontext, *args, **kwargs):
        # print("PRED2", *args, **kwargs) #HIER
        # # self._typecheck(pred)
        # print(pred, type(pred))
        assert isinstance(pred, (str, Pred2))
        self.arg1 = domaincontext.preds2.get(pred, "") #bspw ['semester', 'WhenSemester'] -> means: you need to get to know semester, such that it becomes the 1-order-predicate "WhenSemester"
        if isinstance(pred, str) and len(pred) > 0:
            if pred.startswith('?x.y.') and pred.endswith('(y)(x)'):
                self.appliedContent = pred[3:-3]
                self.content = self.appliedContent[2:-3]
            elif pred.startswith('?x.') and pred.endswith('(x)'):
                self.appliedContent = pred
                self.content = self.appliedContent[3:-3]
            else:
                self.content = pred
                self.appliedContent = pred
        else:
            self.content = pred.content #noo clue warum die Pred1 und Pred2 immer 2 mal gerunnt werden, einmal mit string und einmal mit PredX als argument >.<
            self.appliedContent = pred.content

    def __str__(self):
        if hasattr(self, "arg1"):
            cnt = ""
            for candidate in self.arg1:
                if len(candidate) > 1:
                    cnt += str(candidate[0])
            return self.content+"("+cnt+")" if len(cnt) > 0 else self.content
        return self.content

    def __repr__(self):
        return "Pred2("+self.content+", "+str(self.arg1)+")"



class Sort(Pred1): 
    """Sort."""
    def _typecheck(self, context):
        assert self.content in context.sorts


# Sentences: answers, questions

##################################################################################################################
# Sentence as base
##################################################################################################################

class Sentence(Type): 
    """Superclass for answers and questions."""
    def __new__(cls, sent, *args, **kw):
        if cls is Sentence:
            assert isinstance(sent, str)
            assert not args and not kw
            if sent.startswith('?'):
                return Question(sent)
            else:
                return Ans(sent)
        else:
            return Type.__new__(cls, sent, *args, **kw)

    def __getnewargs__(self): #https://stackoverflow.com/questions/37753425/cannot-unpickle-pickled-object sonst kann man nicht picklen/unpicklen
        return (self.content, )

    # def __repr__(self):
    #     return self.content.__repr__()


######################################################################
# Answer base class + its derivatives (propositions, short answers, y/n-answers)
######################################################################

class Ans(Sentence): 
    """Abstract base class for all kinds of answers.
    
    Currently there are the following answer classes:
    
      - Prop(pred, [ind], [yes]), where pred is a Pred0 or Pred1,
                                  ind is an Ind and yes is a bool.
      - ShortAns(ind, [yes]), where ind is an Ind and yes is a bool.
      - YesNo(yes), where yes is a bool.
    
    To create an answer, use any of the constructors above,
    or call the abstract constructor with a string, Ans("..."):
    
      - Ans("pred(ind)"), Ans("pred()") -> Prop("...")
      - Ans("ind") -> ShortAns("...")
      - Ans("yes"), Ans("no") -> YesNo("...")
    """
    def __new__(cls, ans, *args, **kw):
        if cls is Ans:
            assert isinstance(ans, str)
            assert not args and not kw
            if ans in ('yes', 'no'):
                return YesNo(ans)
            elif '(' not in ans and ')' not in ans:
                return ShortAns(ans)
            elif '(' in ans and ans.endswith(')'):
                return Prop(ans)
            else:
                raise SyntaxError("Could not parse answer: %s" % ans)
        else:
            return Sentence.__new__(cls, ans, *args, **kw)

    # def __repr__(self):
    #     return self.content.__repr__()

class Knowledge(Ans):
    def __init__(self, pred, ind=None, yes=True, expires=None):
        assert (isinstance(pred, (Pred0, Pred1, Pred2, str)))
        self.content = pred, ind, yes
        self.pred = pred
        self.ind = ind
        self.yes = yes
        self.expires = expires
    def __hash__(self):
        return hash((type(self), self.content[0], str(self.content[1]), self.content[2]))
    def __str__(self):
        return "Knowledge(Pred1("+str(self.content[0])+"), <not shown>)"+(" - expires in "+str(self.expires)+" secs" if self.expires else "")
    def __repr__(self):
        return "Knowledge(Pred1("+str(self.content[0])+"), <not shown>)"+(" - expires in "+str(self.expires)+" secs" if self.expires else "")


class Prop(Ans): 
    """Proposition."""
    def __init__(self, pred, ind=None, yes=True, expires=None):
        assert (isinstance(pred, (Pred0, str)) and ind is None or
                isinstance(pred, Pred1) and isinstance(ind, Ind)), \
                ("%s must be a predicate, and %s must be None or an individual" % 
                 (pred, ind))
        assert isinstance(yes, bool), "%s must be a bool" % yes
        if isinstance(pred, str):
            assert '(' in pred and pred.endswith(')'), \
                "'%s' must be of the form '[-] pred ( [ind] )'" % pred
            pred = pred[:-1]
            if pred.startswith('-'):
                yes = not yes
                pred = pred[1:]
            pred, _, ind = pred.partition('(')
            if ind:
                pred = Pred1(pred)
                ind = Ind(ind)
            else:
                pred = Pred0(pred)
                ind = None
        self.content = pred, ind, yes
        self.expires = expires
    
    @property
    def pred(self): return self.content[0]
    @property
    def ind(self): return self.content[1]
    @property
    def yes(self): return self.content[2]
    
    def __neg__(self):
        pred, ind, yes = self.content
        return Prop(self.pred, self.ind, not self.yes)
    
    def __str__(self):
        pred, ind, yes = self.content
        if self.expires:
            return "%s%s(%s) - expires in %s" % ("" if yes else "-", pred, ind or "", self.expires)
        else:
            return "%s%s(%s)" % ("" if yes else "-", pred, ind or "")

    def __repr__(self):
        if self.expires:
            expires_in = int(self.__dict__['expires'])-round(time.time())
            if expires_in > 0:
                return "Prop({0}) - expires in {1} secs".format(self.__dict__['content'], expires_in)
            else:
                return "Prop({}) - expired".format(self.__dict__['content'])
        else:
            return "Prop({})".format(self.__dict__['content'])
        # return "%s(%r)" % (self.__class__, self.__dict__)


    def _typecheck(self, context):
        pred, ind, yes = self.content
        assert (isinstance(pred, Pred0) and ind is None or
                isinstance(pred, Pred1) and isinstance(ind, Ind))
        assert isinstance(yes, bool)
        pred._typecheck(context)
        if ind is not None: 
            ind._typecheck(context)
            assert context.preds1[pred.content] == context.inds[ind.content]

class ShortAns(Ans): 
    """Short answer."""
    contentclass = Ind
    
    def __init__(self, ind, yes=True):
        assert isinstance(yes, bool), "%s must be a boolean" % yes
        assert isinstance(ind, (Ind, str)), "%s must be an individual" % ind
        if isinstance(ind, str):
            if ind.startswith('-'):
                ind = ind[1:]
                yes = not yes
            ind = Ind(ind)
        self.content = ind, yes

    @property
    def ind(self): return self.content[0]
    @property
    def yes(self): return self.content[1]

    def __neg__(self):
        ind, yes = self.content
        return ShortAns(ind, not yes)

    def __str__(self):
        ind, yes = self.content
        return "%s%s" % ("" if yes else "-", ind)

    def _typecheck(self, context):
        ind, yes = self.content
        assert isinstance(ind, Ind)
        assert isinstance(yes, bool)
        ind._typecheck(context)

class YesNo(ShortAns):
    """Yes/no-answer."""
    contentclass = bool
    
    def __init__(self, yes):
        assert isinstance(yes, (bool, str)), "%s must be a boolean" % yes
        if isinstance(yes, str):
            assert yes in ("yes", "no"), "'%s' must be 'yes' or 'no'" % yes
            yes = yes == "yes"
        self.content = yes

    @property
    def yes(self): return self.content

    def __neg__(self):
        return YesNo(not self.content)

    def __str__(self):
        return "yes" if self.content else "no"



######################################################################
# Question base class + its derivatives (wh-questions, y/n-questions, alternative questions)
######################################################################

class Question(Sentence): 
    """Abstract base class for all kinds of questions.
    
    Currently there are the following question classes:
      - WhQ(pred), where pred is a Pred1
      - YNQ(prop), where prop is a Prop
      - AltQ(ynq1, ynq2, ...), where ynq1, ... are YNQs
    
    To create a Question, use any of the constructors above,
    or call the abstract constructor with a string, Question("..."):

      - Question("?x.pred(x)") -> WhQ("pred")
      - Question("?prop") -> YNQ("prop")
    """
    def __new__(cls, que, *args, **kw):
        """Parse a string into a Question.
    
        "?x.pred(x)" -> WhQ("pred")
        "?prop" -> YNQ("prop")
        """
        if cls is Question:
            # print("QUESTION's que:", que)
            assert isinstance(que, str)
            if que.startswith('?x.y.') and que.endswith('(y)(x)'):
                return SecOrdQ(que[5:-6], args[0])
            assert not args and not kw #second-order-question erwartet als zweites arg die domain
            if que.startswith('?x.') and que.endswith('(x)'):
                return WhQ(que[3:-3])
            elif que.startswith('?'):
                return YNQ(que[1:])
            else:
                raise SyntaxError("Could not parse question: %s" % que)
        else:
            return Sentence.__new__(cls, que, *args, **kw)


class SecOrdQ(Question):
    contentclass = Pred2

    def __init__(self, pred, domaincontext=None):
        assert isinstance(pred, (Pred2, str))
        if isinstance(pred, str):
            self.content = Pred2(pred, domaincontext)
        else:
            self.content = pred


    def _typecheck(self, context=None):
        assert isinstance(self.content, self.contentclass)
        if hasattr(self.content, '_typecheck'):
            self.content._typecheck(context)


    def __repr__(self):
        return "SecOrdQ({})".format(self.content)

    def __str__(self):
        if hasattr(self.content, "arg1"):
            return "?x.y." + str(self.content) + "(x)"
        return "?x.y." + str(self.content) + "(y)(x)"


class WhQ(Question):
    """Wh-question."""
    contentclass = Pred1

    def __init__(self, pred):
        assert isinstance(pred, (Pred1, str))
        if isinstance(pred, str):
            if pred.startswith('?x.') and pred.endswith('(x)'):
                pred = pred[3:-3]
            pred = Pred1(pred)
        self.content = pred


    @property
    def pred(self): return self.content

    def __str__(self):
        if hasattr(self.content, "arg2"):
            return "?x.%s(%s)(x)" % (self.content.__str__(), self.content.arg2)
        else:
            return "?x.%s(x)" % self.content.__str__()

    def __repr__(self):
        return "WhQ("+str(self.content)+")"


class YNQ(Question): 
    """Yes/no-question."""
    contentclass = Prop
    
    def __init__(self, prop):
        assert isinstance(prop, (Prop, str))
        if isinstance(prop, str):
            if prop.startswith('?'):
                prop = prop[1:]
            prop = Prop(prop)
        self.content = prop
    
    @property
    def prop(self): return self.content
    
    def __str__(self):
        return "?%s" % self.content.__str__()

class AltQ(Question): 
    """Alternative question."""
    def __init__(self, *ynqs):
        if len(ynqs) == 1 and is_sequence(ynqs[0]):
            ynqs = ynqs[0]
        if not all(isinstance(q, (YNQ, str)) for q in ynqs):
            raise TypeError("all AltQ arguments must be y/n-questions")
        self.content = tuple((q if isinstance(q, YNQ) else Question(q))
                             for q in ynqs)

    @property
    def ynqs(self): return self.content

    def __str__(self):
        return "{" + " | ".join(map(str, self.content)) + "}"

    def _typecheck(self, context):
        assert all(isinstance(q, YNQ) for q in self.content)
        for q in self.content:
            q._typecheck(context)


######################################################################
# Command base class
######################################################################

class Command(Sentence):
    def __new__(cls, cmd, *args, **kw):
        if cls is Command:
            assert isinstance(cmd, str)
            assert not args and not kw
            assert cmd.startswith("!(")
            cmd = cmd[2:-1]
            return Sentence.__new__(cls, cmd, *args, **kw)

    def __init__(self, cmd):
        self.content = cmd
        self.new = True

    def __str__(self):
        return "cmd: %s" % self.content.__str__()


######################################################################
# Statement base class
######################################################################

class Statement(Sentence):
    def __new__(cls, cmd, *args, **kw):
        if cls is Statement:
            assert isinstance(cmd, str)
            assert not args and not kw
            return Sentence.__new__(cls, cmd, *args, **kw)

    def __init__(self, sent):
        self.content = sent

    def __str__(self):
        return "statement: %s" % self.content.__str__()


##################################################################################################################
# IBIS dialogue moves
##################################################################################################################

class Imperative(Move):
    contentclass = Command

class State(Move):
    contentclass = Statement
    def __str__(self):
        return self.content.content

class Greet(SingletonMove): pass

class Quit(SingletonMove): pass

class Ask(Move): 
    contentclass = Question

    def __str__(self):
        return "Ask('%s')" % self.content.__str__()

    def __repr__(self):
        if hasattr(self, 'askedby'):
            return "Ask('%s' by %s)" % (self.content.__str__(), self.askedby)
        else:
            return "Ask('%s')" % self.content.__str__()

    def __init__(self, *args, **kwargs):
        self.askedby = kwargs.get('askedby', 'SYS')
        kwargs.pop('askedby', None)
        super().__init__(*args, **kwargs)



class Answer(Move): 
    contentclass = Ans

class ICM(Move):
    contentclass = object
    
    def __init__(self, level, polarity, icm_content=None):
        self.content = (level, polarity, icm_content)

    def __str__(self):
        s = "icm:" + self.level + "*" + self.polarity
        if self.icm_content:
            s += ":'" + self.icm_content + "'"
        return s

    @property
    def level(self): return self.content[0]
    @property
    def polarity(self): return self.content[1]
    @property
    def icm_content(self): return self.content[2]

##################################################################################################################
# IBIS plan constructors
##################################################################################################################

class PlanConstructor(Type): 
    """An abstract base class for plan constructors."""

class ClarifyPred2(PlanConstructor):
    contentclass = Question

    def __str__(self):
        return "ClarifyPred2('%s')" % self.content.__str__()


class Respond(PlanConstructor):
    contentclass = Question

    def __str__(self):
        return "Respond('%s')" % self.content.__str__()


class ConsultDB(PlanConstructor):
    contentclass = Question

    def __str__(self):
        return "ConsultDB('%s')" % self.content.__str__()


class Findout(PlanConstructor):
    contentclass = Question

    def __str__(self):
        return "Findout('%s')" % self.content.__str__()

class Raise(PlanConstructor):
    contentclass = Question

    def __str__(self):
        return "Raise('%s')" % self.content.__str__()


# Complex plan constructs

class ExecuteFunc(PlanConstructor):
    contentclass = (FunctionType, functools.partial, MethodType)

    def __init__(self, funcname, *params, **kwparams):
        assert isinstance(funcname, self.contentclass)
        self.content = funcname
        self.params = params
        self.kwparams = kwparams

    def __str__(self):
        return "ExecuteFunc('%s') needing params %s" % (self.content.__name__, self.params)


class Inform(PlanConstructor):
    contentclass = Statement

    def __init__(self, formatstr, replacers=[]):
        assert isinstance(formatstr, str)
        self.content = formatstr
        self.replacers = replacers

    def __str__(self):
        return "Inform('%s')" % self.content.__str__()

    def _typecheck(self, context=None):
        return True


class If(PlanConstructor):
    """A conditional plan constructor, consisting of a condition,
    a true branch and an optional false branch.
    """
    
    def __init__(self, cond, iftrue, iffalse=()):
        if isinstance(cond, str):
            cond = Question(cond)
        self.cond = cond
        self.iftrue = tuple(iftrue)
        self.iffalse = tuple(iffalse)
    
    @property
    def content(self):
        return (self.cond, self.iftrue, self.iffalse)

    def _typecheck(self, context):
        assert isinstance(self.cond, Question)
        assert all(isinstance(m, PlanConstructor) for m in self.iftrue)
        assert all(isinstance(m, PlanConstructor) for m in self.iffalse)
        self.cond._typecheck(context)
        for m in self.iftrue:
            m._typecheck(context)
        for m in self.iffalse:
            m._typecheck(context)

    def __str__(self):
        return "If('%s', %s, %s)" % (self.cond.__str__(),
                                     self.iftrue.__str__(),
                                     self.iffalse.__str__())



def unpack(what):
    # print(".                        unpacking", what, type(what))
    if type(what) == Answer:
        return unpack(what.content)
    elif type(what) == Prop:
        return unpack(what.ind)
    elif type(what) == Pred1:
        return unpack(what.content)
    elif type(what) == Ind:
        return unpack(what.content)
    return str(what)