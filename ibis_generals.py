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


from trindikit import stack, DialogueManager, record, stackset, Speaker, ProgramState, StandardMIVS, SimpleInput, SimpleOutput, maybe, do, repeat, rule_group, VERBOSE, _TYPEDICT
from ibis_types import Ask, Question, Answer, Ans, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit
from ibis_rules import get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg, handle_empty_plan_agenda_qud
import pickle
import os.path

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

    def interpret(self, input): #Haupt-Sache die cfg_grammar überschreibt
        """Parse an input string into a dialogue move or a set of moves."""
        try: return eval(input) #parses a string as a python expression (eval("1+2") =3)
        except: pass
        try: return Ask(Question(input))
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
    
    def __init__(self, preds0, preds1, sorts):
        self.preds0 = set(preds0)                           # return
        self.preds1 = dict(preds1)                          # city, day-of, ...
        self.sorts = dict(sorts)                            # {'city': ('paris', 'london', 'berlin')}
        self.inds = dict((ind,sort) for sort in self.sorts 
                         for ind in self.sorts[sort])       # {'berlin': 'city', 'train': 'means', 'today': 'day', 'tuesday': 'day', ...}
        self.plans = {}

    def add_plan(self, trigger, plan):  #("?x.price(x)", [Findout("?x.how(x)")])
        """Add a plan to the domain."""
        assert isinstance(trigger, (Question, str)), \
            "The plan trigger %s must be a Question" % trigger
        if isinstance(trigger, str):
            trigger = Question(trigger)
        assert trigger not in self.plans, \
            "There is already a plan with trigger %s" % trigger
        trigger._typecheck(self)
        for m in plan:
            m._typecheck(self)
        self.plans[trigger] = tuple(plan)

    def relevant(self, answer, question):
        """True if 'answer' is relevant to 'question'."""
        assert isinstance(answer, (ShortAns, Prop)) #YesNo is a subclass of ShortAns
        assert isinstance(question, Question)
        if isinstance(question, WhQ):
            if isinstance(answer, Prop):
                return answer.pred == question.pred
            elif not isinstance(answer, YesNo):  #bleibt nur ShortAns selbst
                sort1 = self.inds.get(answer.ind.content)
                sort2 = self.preds1.get(question.pred.content)
                return sort1 and sort2 and sort1 == sort2
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

    def get_plan(self, question):
        """Return (a new copy of) the plan that is relevant to 'question', 
        or None if there is no relevant plan.
        """       
        planstack = stack(PlanConstructor)
        # print(question, type(question))
        for construct in reversed(self.plans.get(question)):
            planstack.push(construct)
        return planstack
