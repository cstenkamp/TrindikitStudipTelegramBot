# -*- encoding: utf-8 -*-
#
# ibis_generals.py
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


from trindikit import stack
from ibis_types import *#Ask, Question, Answer, Ans, Command, Imperative, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit

######################################################################
# IBIS grammar
######################################################################

class Grammar(object): #wird überschrieben von (s.u.) und dann nochmal in travel
    """The simplest grammar, using dialogue moves as surface strings.
    
    Override generate and interpret if you want to use a real grammar.
    """

    def generate(self, moves):
        """Generate a surface string from a set of dialogue moves."""
        return self.joinPhrases(self.generateMove(move) for move in moves)

    def generateMove(self, move): #wird 2 mal überschrieben
        return str(move)

    def joinPhrases(self, phrases):
        str = ""
        for p in phrases:
            if str != "": str += " "
            str += p
            if not (p[-1] == "." or p[-1] == "?" or p[-1] == "!"):
                str += "."
        return str

    def interpret(self, input, DOMAIN, anyString=False, moves=None, IS=None): #Haupt-Sache von cfg_grammar überschrieben wird
        """Parse an input string into a dialogue move or a set of moves."""
        try: return eval(input) #parses a string as a python expression (eval("1+2") =3)
        except: pass
        try: return Ask(Question(input))
        except: pass
        try: return Imperative(Command(input))
        except: pass
        try: return Answer(Ans(input))
        except: pass
        return None

######################################################################
# Simple generation grammar
######################################################################

class SimpleGenGrammar(Grammar):
    def __init__(self):
        self.forms = dict()
        self.addForm("'Greet'()", 'Hello') #könnten genauso gut in travel.py definiert sein, oder in ner Template-Datenbank
        self.addForm("'Quit'()", 'Goodbye')
        self.addForm("icm:sem*neg", 'I don\'t understand') #this was wrong order (see chap.4 of https://pdfs.semanticscholar.org/0066/b5c5b49e1a7eb4ea95ee22984b695ec5d2c5.pdf)

    def addForm(self, move, output):
        self.forms[move] = output

    def generateMove(self, move):
        try: output = self.generateICM(move)
        except:
            s = str(move)
            try: output = self.forms[s]
            except KeyError: output = s
        return output

    def generateICM(self, move): #Interactive Communication Management
        assert isinstance(move, ICM)
        try: return self.generateIcmPerPos(move)
        except: raise

    def generateIcmPerPos(self, icm): #positive, perception level. Print WHAT you heard.
        assert icm.level == "per"
        assert icm.polarity == "pos"
        return "I heard you say " + icm.icm_content

    #was noch fehlen wird ist - icm:acc∗neg:Content (noegative acceptence) - realized
    #as explanation (“Sorry, Paris is not a valid destination city”)

######################################################################
# IBIS database
######################################################################

class Database(object):
    """An IBIS database, meant to be subclassed."""
    
    def consultDB(self, question, context):
        """Looks up the answer to 'question', given the propositions
        in the 'context' set. Returns a proposition. 
        """
        raise NotImplementedError

######################################################################
# IBIS domain
######################################################################

class Domain(object):
    """An IBIS domain, consisting of predicates, sorts and individuals.
    
    Domain(preds0, preds1, sorts) creates a new domain, provided that:
      - preds0 is a set of 0-place predicates
      - preds1 is a dict of 1-place predicates, 
        where each predicate is mapped to its sort
      - sorts is a dict of sorts, 
        where each sort is mapped to a collection of its individuals.
    """
    
    def __init__(self, preds0, preds1, preds2, sorts):
        self.preds0 = set(preds0)                           # return
        self.preds1 = dict(preds1)                          # city, day-of, ...
        self.preds2 = dict(preds2)
        self.sorts = dict(sorts)                            # {'city': ('paris', 'london', 'berlin')}
        self.inds = dict((ind,sort) for sort in self.sorts 
                         for ind in self.sorts[sort])       # {'berlin': 'city', 'train': 'means', 'today': 'day', 'tuesday': 'day', ...}
        self.plans = {}

    def get_sort_from_ind(self, answer):
        res = self.inds.get(answer)
        if res: return res
        if "SS" in answer and any(str(i) in answer for i in range(2000, 2050)) or "WS" in answer and any(str(i)+'/'+str(i-1999).zfill(2) in answer for i in range(2000, 2050)):
            return "semester"

    def get_sort_from_question(self, question):
        return self.preds1.get(question)


    def add_plan(self, trigger, plan, conditions=[]):  #("?x.price(x)", [Findout("?x.how(x)")])
        """Add a plan to the domain."""
        assert isinstance(trigger, (Question, Command, str)), \
            "The plan trigger %s must be a Question" % trigger
        if isinstance(trigger, str):
            try:
                trigger = Question(trigger, self) #second-order-questions brauchen die preds2-typen argh Kill me
            except:
                try:
                    trigger = Question(trigger)
                except:
                    trigger = Command(trigger)
        assert trigger not in self.plans, \
            "There is already a plan with trigger %s" % trigger
        # print("TRIGGERTYPE", type(trigger))
        trigger._typecheck(self)
        for m in plan:
            m._typecheck(self)
        if len(conditions) == 0:
            self.plans[trigger] = {"plan": tuple(plan)}
        else:
            self.plans[trigger] = {"plan": tuple(plan), "conditions": tuple(conditions)}


    def relevant(self, answer, question):
        """True if 'answer' is relevant to 'question'."""
        if not isinstance(answer, (ShortAns, Prop)): #YesNo is a subclass of ShortAns
            return False
        if not isinstance(question, Question):
            return False
        if isinstance(question, WhQ):
            if isinstance(answer, Prop):
                return answer.pred == question.pred
            elif not isinstance(answer, YesNo):  #bleibt nur ShortAns selbst
                sort1 = self.get_sort_from_ind(answer.ind.content)
                sort2 = self.get_sort_from_question(question.pred.content)
                return (sort1 and sort2 and sort1 == sort2) or sort2 == "string" #letzterer Fall ist freetextquestion
        elif isinstance(question, YNQ):
            # integrate macht aus question+answer proposition! aus "?return()" und "YesNo(False)" wird "Prop((Pred0('return'), None, False))", und das auf IS.shared.com gepackt
            # print("#####")                                                                      # OB YESNOANS DIE QUESTION RESOLVED (dann wird aus YesNo(False) ne Prop) # OB DIE ENTSTANDENE PROP WAS VOM QUD RESOLVED
            # print("Answer", answer, type(answer))                                               # Answer no <class 'ibis_types.YesNo'>                                   # Answer -return() <class 'ibis_types.Prop'>
            # print("Question.prop", question.prop, type(question.prop))                          # Question.prop return() <class 'ibis_types.Prop'>                       # Question.prop return() <class 'ibis_types.Prop'>
            # print("Answer.content", answer.content, type(answer.content))                       # Answer.content False <class 'bool'>                                    # Question.prop.content (Pred0('return'), None, True) <class 'tuple'>
            # print("Question.prop.content", question.prop.content, type(question.prop.content))  # Question.prop.content (Pred0('return'), None, True) <class 'tuple'>    # Question.prop.content (Pred0('return'), None, True) <class 'tuple'>
            return isinstance(answer, YesNo) or \
                    (isinstance(answer, Prop) and type(answer) == type(question.prop) and answer.content[:1] == question.prop.content[:1]) #der dritte teil des tuples IST ANDERS wenn ein "Nein" auf eine "Ja"-Frage geantwortet wrid!
        elif isinstance(question, AltQ):
            return any(answer == ynq.prop for ynq in question.ynqs)


    def resolves(self, answer, question):
        """True if 'question' is resolved by 'answer'."""
        if self.relevant(answer, question):
            if isinstance(question, YNQ):
                return True
            return answer.yes == True
        return False


    def combine(self, question, answer):
        """Return the proposition that is the result of combining 'question' 
        with 'answer'. This presupposes that 'answer' is relevant to 'question'.
        """
        assert self.relevant(answer, question)
        if isinstance(question, WhQ):
            if isinstance(answer, ShortAns):
                prop = question.pred.apply(answer.ind)
                if not answer.yes:
                    prop = -prop
                return prop
        elif isinstance(question, YNQ):
            if isinstance(answer, YesNo):
                prop = question.prop
                if prop.yes != answer.yes:
                    prop = -prop
                return prop
        return answer


    def get_plan(self, question, IS):
        """Return (a new copy of) the plan that is relevant to 'question', 
        or None if there is no relevant plan.
        """
        missings = self.check_for_plan(question, IS)
        if len(missings) > 0:
            return False, missings
        planstack = stack(PlanConstructor)
        # print(question, type(question))
        if self.plans.get(question) is not None:
            for construct in reversed(self.plans.get(question)["plan"]):
                planstack.push(construct)
        return True, planstack


    def check_for_plan(self, question, IS):
        plan = self.plans.get(question)
        if plan is not None:
            if len(plan.get("conditions", [])) == 0:
                return []
            else:
                mustbe = [False] * len(plan.get("conditions"))
                relevants = {}
                for ind, cond in enumerate(plan.get("conditions")):
                    must, cont = check_for_something(IS, cond)
                    mustbe[ind] = must
                    relevants[cond] = cont
                if all(mustbe):
                    return []
                else:
                    missing = list(zip(plan.get("conditions"), mustbe))
                    missing = [i[0] for i in missing if not i[1]]
                    return missing
        return []


def check_for_something(IS, something):
    if something.startswith("bel("):
        relevantpart = something[4:-1]
        for j in IS.private.bel:
            if isinstance(j, Prop):
                if str(j.content[0]) == relevantpart:
                    return True, j.content[1]
    elif something.startswith("com("):
        relevantpart = something[4:-1]
        for j in IS.shared.com:
            if isinstance(j, Prop):
                if str(j.content[0]) == relevantpart:
                    return True, j.content[1]
    else:
        tmp = check_for_something(IS, "bel("+something+")")
        if tmp[0]:
            return tmp
        else:
            return check_for_something(IS, "com("+something+")")
    return False, None