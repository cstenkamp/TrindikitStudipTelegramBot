# -*- encoding: utf-8 -*-

#
# ibis.py
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
from ibis_rules import get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg
import pickle
from copy import deepcopy
import os.path

######################################################################
# IBIS grammar
######################################################################

class Grammar(object):
    """The simplest grammar, using dialogue moves as surface strings.
    
    Override generate and interpret if you want to use a real grammar.
    """

    def generate(self, moves):
        """Generate a surface string from a set of dialogue moves."""
        return self.joinPhrases(self.generateMove(move) for move in moves)

    def generateMove(self, move):
        return str(move)

    def joinPhrases(self, phrases):
        str = ""
        for p in phrases:
            if str != "": str += " "
            str += p
            if not (p[-1] == "." or p[-1] == "?" or p[-1] == "!"):
                str += "."
        return str

    def interpret(self, input):
        """Parse an input string into a dialogue move or a set of moves."""
        try: return eval(input)
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
        self.addForm("'Greet'()", 'Hello')
        self.addForm("'Quit'()", 'Goodbye')
        self.addForm("icm:neg*sem", 'I don\'t understand')

    def addForm(self, move, output):
        self.forms[move] = output

    def generateMove(self, move):
        try: output = self.generateICM(move)
        except:
            s = str(move)
            try: output = self.forms[s]
            except KeyError: output = s
        return output

    def generateICM(self, move):
        assert isinstance(move, ICM)
        try: return self.generateIcmPerPos(move)
        except: raise

    def generateIcmPerPos(self, icm):
        assert icm.level == "per"
        assert icm.polarity == "pos"
        return "I heard you say " + icm.icm_content

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
        self.preds0 = set(preds0)
        self.preds1 = dict(preds1)
        self.sorts = dict(sorts)
        self.inds = dict((ind,sort) for sort in self.sorts 
                         for ind in self.sorts[sort])
        self.plans = {}

    def add_plan(self, trigger, plan):
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
        assert isinstance(answer, (ShortAns, Prop))
        assert isinstance(question, Question)
        if isinstance(question, WhQ):
            if isinstance(answer, Prop):
                return answer.pred == question.pred
            elif not isinstance(answer, YesNo):
                sort1 = self.inds.get(answer.ind.content)
                sort2 = self.preds1.get(question.pred.content)
                return sort1 and sort2 and sort1 == sort2
        elif isinstance(question, YNQ):
            return (isinstance(answer, YesNo) or
                    isinstance(answer, Prop) and answer == question.prop)
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
        for construct in reversed(self.plans.get(question)):
            planstack.push(construct)
        return planstack


######################################################################
# IBIS information state
######################################################################

class IBISInfostate(DialogueManager):
    def init_IS(self):
        """Definition of the IBIS information state."""
        self.IS = record(private = record(agenda = stack(),
                                          plan   = stack(), 
                                          bel    = set()),
                         shared  = record(com    = set(),
                                          qud    = stackset(),
                                          lu     = record(speaker = Speaker,
                                                          moves   = set())))

        self.pload("CurrState.pkl")

    def print_IS(self, prefix=""):
        """Pretty-print the information state."""
        self.IS.pprint(prefix)

    def pload(self, filename):
        pass
        # from ibis_types import ConsultDB
        # asdf = ConsultDB("?x.penis(x)") #equal to ConsultDB(Question("?x.penis(x)"))
        # print(asdf)
        # print(asdf.content)
        # print(asdf.contentclass)
        # exit(-1)
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                tmp_dict = pickle.load(f)
                print(tmp_dict)
    #        self.__dict__.update(tmp_dict)

    def print_type(self, what, indent=""):
        if indent == "":
            print(type(what))
        if isinstance(what, dict):
            for key, val in what.items():
                print(indent,key,":",type(val))
                if type(val) == dict:
                    self.print_type(val, indent+"  ")
                elif isinstance(val, str):
                    print(indent+"  ",val, type(val))
                elif hasattr(val, '__getitem__'):
                    for i in val:
                        print(indent+"  ", i, type(i))
        else:
            print(indent, type(what))


    def psave(self, filename):
        #TODO: type mitspeichern (record, ...)
        odict = self.IS.asdict(recursive=True)
        print("####NOW")
        self.print_type(odict["private"])
        # odict["shared"] = None
        # odict["private"]["plan"] = odict["private"]["plan"][:1]
        # print("####MIDDLE")
        # self.print_type(odict["private"])
        # print("####MIDDLE2")
        # if len(odict["private"]["plan"]) > 0:
        #     print(odict["private"]["plan"][0])
        #     print(type(odict["private"]["plan"][0]))
        #     print(odict["private"]["plan"][0].contentclass)
        #     print(odict["private"]["plan"][0].content)
        #     asdf = odict["private"]["plan"][0]
        #     with open(filename, 'wb') as f:
        #         pickle.dump(odict["private"]["plan"][0], f, pickle.HIGHEST_PROTOCOL)
        #     with open(filename, 'rb') as f:
        #         tmp_dict = pickle.load(f)

        print("####END")
        with open(filename, 'wb') as f:
            pickle.dump(odict, f, pickle.HIGHEST_PROTOCOL)

######################################################################
# IBIS dialogue manager
######################################################################

class IBISController(DialogueManager):
    def control(self):
        """The IBIS control algorithm."""
        self.IS.private.agenda.push(Greet())
        self.print_state()
        while True:
            self.select()
            if self.NEXT_MOVES:
                self.generate()
                self.output()
                self.update()
                self.print_state()
            if self.PROGRAM_STATE.get() == ProgramState.QUIT:
                break
            self.input()
            if self.interpret() == "exit": #obviously also runs it
                break
            self.update()
            self.print_state()

class IBIS(IBISController, IBISInfostate, StandardMIVS, SimpleInput, SimpleOutput, DialogueManager):
    """The IBIS dialogue manager. 
    
    This is an abstract class: methods update and select are not implemented.
    """
    def __init__(self, domain, database, grammar):
        self.DOMAIN = domain
        self.DATABASE = database
        self.GRAMMAR = grammar

    def reset(self): #called by DialogueManager.run
        self.init_IS()
        self.init_MIVS()

    def print_state(self):
        if VERBOSE["IS"] or VERBOSE["MIVS"]:
            print("+------------------------ - -  -")
        if VERBOSE["MIVS"]:
            self.print_MIVS(prefix="| ")
        if VERBOSE["IS"] and VERBOSE["MIVS"]:
            print("|")
        if VERBOSE["IS"]:
            self.print_IS(prefix="| ")
        if VERBOSE["IS"] or VERBOSE["MIVS"]:            
            print("+------------------------ - -  -")
            print()

######################################################################
# IBIS-1
######################################################################


class IBIS1(IBIS):
    """The IBIS-1 dialogue manager."""

    def update(self):
        self.IS.private.agenda.clear()
        self.grounding()
        maybe(self.integrate)
        maybe(self.downdate_qud)
        maybe(self.load_plan)
        repeat(self.exec_plan)
        self.psave("CurrState.pkl")
        
    grounding    = rule_group(get_latest_moves)
    integrate    = rule_group(integrate_usr_ask, integrate_sys_ask,
                                integrate_answer, integrate_greet,
                                integrate_usr_quit, integrate_sys_quit)
    downdate_qud = rule_group(downdate_qud)
    load_plan    = rule_group(recover_plan, find_plan)
    exec_plan    = rule_group(remove_findout, remove_raise, exec_consultDB, execute_if)

    def select(self):
        if not self.IS.private.agenda:
            maybe(self.select_action)
        maybe(self.select_icm)
        maybe(self.select_move)

    select_action = rule_group(select_respond, select_from_plan, reraise_issue)
    select_move   = rule_group(select_answer, select_ask, select_other)
    select_icm    = rule_group(select_icm_sem_neg)