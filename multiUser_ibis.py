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


from trindikit import stack, DialogueManager, record, stackset, Speaker, ProgramState, StandardMIVS, SimpleInput, SimpleOutput, maybe, do, repeat, rule_group, VERBOSE, _TYPEDICT, update_rule
from ibis_types import Ask, Question, Answer, Ans, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit
from ibis_rules import get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg, handle_empty_plan_agenda_qud
import pickle
import os.path
import requests
import urllib
# from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base
# ORM_Base = declarative_base()


######################################################################
# IBIS information state
######################################################################

##### IS and MIVS will be in an extra class, such that they can be saved in a DB #####
# class ConversationState(ORM_Base):
#     __tablename__ = 'conversationState'
#
#     id = Column(Integer, primary_key=True)
#     name = Column(String)
#     fullname = Column(String)
#     password = Column(String)


class IBISInfostate(DialogueManager):
    def init_IS(self):
        """Definition of the IBIS information state."""
        # self.engine = create_engine('sqlite:///DB.sqlite', echo=False)
        # Session = sessionmaker(bind=self.engine)
        # self.session = Session()

        self.pload_IS("CurrState.pkl")


    def reset_IS(self):
        self.IS = record(private = record(agenda = stack(),
                                          plan   = stack(),
                                          bel    = set()),
                         shared  = record(com    = set(),
                                          qud    = stackset(),
                                          lu     = record(speaker = Speaker,
                                                          moves   = set())))


    def print_IS(self, prefix=""):
        """Pretty-print the information state."""
        self.IS.pprint(prefix)

    def pload_IS(self, filename):
        # asdf = ConsultDB("?x.penis(x)") #equal to ConsultDB(Question("?x.penis(x)"))
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                tmp_dict = pickle.load(f)

                self.IS = record(private = record(agenda = stack(tmp_dict["private"]["agenda"]),
                                                  plan   = stack(tmp_dict["private"]["plan"], PlanConstructor), #TODO: warum ist das beim normalen initialisieren ein PlanConstructor?
                                                  bel    = set(tmp_dict["private"]["bel"])),
                                 shared  = record(com    = set(tmp_dict["shared"]["com"]),
                                                  qud    = stackset(tmp_dict["shared"]["qud"], object),
                                                  lu     = record(speaker = Speaker.USR,
                                                                  moves   = set(tmp_dict["shared"]["lu"]["moves"]))))
        else:
            self.reset_IS()

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


    def psave_IS(self, filename):
        #TODO you know what, ich speicher den Kram in ner Datenbank. ==> SQLAlchemy, die ibis-klasse extended Base=declarative_base(), und für die werte .IS und .MVIS gibt es entsprechungen
        #TODO Flyweight-pattern nutzen, sodass jede ibis-instanz nur den Stand der Datenbank hat, und die Methoden von ner gemeinsamen erbt
        odict = self.IS.asdict(recursive=True)
        with open(filename, 'wb') as f:
            pickle.dump(odict, f, pickle.HIGHEST_PROTOCOL)




######################################################################
# can't use send_message from bothelper >.<
######################################################################

MY_CHAT_ID = 163601520
TOKEN = "491105485:AAFrSueGnkjLee79ne9MhvBSLrpB2VHEnec"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


class TGramOutput(SimpleOutput):
    @update_rule
    def output(NEXT_MOVES, OUTPUT, LATEST_SPEAKER, LATEST_MOVES, USER):
        """Print the string in OUTPUT to standard output.

        After printing, the set of NEXT_MOVES is moved to LATEST_MOVES,
        and LATEST_SPEAKER is set to SYS.
        """
        print("S to", str(USER.state.chat_id) + ":", OUTPUT.get() or "[---]")
        print()
        send_message(OUTPUT.get(), MY_CHAT_ID)
        LATEST_SPEAKER.set(Speaker.SYS)
        LATEST_MOVES.clear()
        LATEST_MOVES.update(NEXT_MOVES)
        NEXT_MOVES.clear()

######################################################################
# IBIS dialogue manager
######################################################################

class IBISController(DialogueManager):
    def print_state(self, user):
        if VERBOSE["IS"] or VERBOSE["MIVS"]:
            print("+----- "+str(user.state.chat_id)+" ------------- - -  -")
        if VERBOSE["MIVS"]:
            user.state.print_MIVS(prefix="| ")
        if VERBOSE["IS"] and VERBOSE["MIVS"]:
            print("|")
        if VERBOSE["IS"]:
            user.state.print_IS(prefix="| ")
        if VERBOSE["IS"] or VERBOSE["MIVS"]:
            print("+------------------------ - -  -")
            print()

    # def control(self, user):
    #     """The IBIS control algorithm."""
    #     if not user.state.IS.private.plan:
    #         user.state.IS.private.agenda.push(Greet())
    #     self.print_state(user)
    #     while True:
    #         self.select(user)          #puts the next appropriate thing onto the agenda
    #         if user.state.NEXT_MOVES:
    #             self.generate(user)    #sets output
    #             self.output(user)      #prints output  #kann gut sein dass generate, output, input und intepret nicht mit user als param klappen, weil die nicht ge rule_group ed werden
    #             self.update(user)      #integrates answers, ..., loads & executes plan
    #             self.print_state(user)
    #         if user.state.PROGRAM_STATE.get() == ProgramState.QUIT:
    #             break
    #         self.input(user)
    #         res = self.interpret(user) #obviously also runs it
    #         if res == "exit":
    #             break
    #
    #         self.update(user)
    #         self.print_state(user)



#contains..         control()        interpret+input  generate+output do,maybe,repeat
class MultiUserIBIS(IBISController,  SimpleInput,     TGramOutput,   DialogueManager):
    """The IBIS dialogue manager. 
    
    This is an abstract class: methods update and select are not implemented.
    """
    def __init__(self, domain, database, grammar):
        self.DOMAIN = domain
        self.DATABASE = database
        self.GRAMMAR = grammar

    def init(self):
        pass

    def handle_message(self, message, user):
        user.state.INPUT.set(message)
        user.state.LATEST_SPEAKER.set(Speaker.USR)

        res = self.interpret(user)  # obviously also runs it
        # if res == "exit":
        #     break

        self.update(user)
        self.print_state(user)

        self.select(user)  # puts the next appropriate thing onto the agenda
        if user.state.NEXT_MOVES:
            self.generate(user)  # sets output
            self.output(
                user)  # prints output  #kann gut sein dass generate, output, input und intepret nicht mit user als param klappen, weil die nicht ge rule_group ed werden
            self.update(user)  # integrates answers, ..., loads & executes plan
            self.print_state(user)
        # if user.state.PROGRAM_STATE.get() == ProgramState.QUIT:
        #     break
        self.input(user)


    # def init(self): #called by DialogueManager.run
    #     self.init_IS()
    #     self.init_MIVS()
    # 
    # def reset(self):
    #     self.reset_IS()
    #     self.reset_MIVS()



######################################################################
# IBIS-1
######################################################################



class IBIS2(MultiUserIBIS):
    """The IBIS-1 dialogue manager."""

    def update(self, user):
        user.state.IS.private.agenda.clear()
        self.grounding(user)()
        maybe(self.integrate(user))
        maybe(self.downdate_qud(user))
        maybe(self.load_plan(user))
        repeat(self.exec_plan(user))
        maybe(self.handle_empty_plan_agenda_qud(user))

    #rule_group returns "lambda self: do(self, *rules)" with rules specified here... NOT ANYMORE:
    #rule_group returns lambda self, user=None: lambda: do(self, user, *rules) <- es kriegt ERST rules (siehe hier drunter), und DAS erwarted dann noch self und user (siehe hier drüber), und returned eine funktion (nicht ihr result, deswegen das nested lambda)
    grounding    = rule_group(get_latest_moves)
    integrate    = rule_group(integrate_usr_ask, integrate_sys_ask,
                                integrate_answer, integrate_greet,      #integrate macht aus question+answer proposition! aus "?return()" und "YesNo(False)" wird "Prop((Pred0('return'), None, False))", und das auf IS.shared.com gepackt
                                integrate_usr_quit, integrate_sys_quit)
    downdate_qud = rule_group(downdate_qud)
    load_plan    = rule_group(recover_plan, find_plan)
    exec_plan    = rule_group(remove_findout, remove_raise, exec_consultDB, execute_if)
    handle_empty_plan_agenda_qud = rule_group(handle_empty_plan_agenda_qud)

    def select(self, user):
        if not user.state.IS.private.agenda:
            maybe(self.select_action(user))
        maybe(self.select_icm(user))
        maybe(self.select_move(user))

    select_action = rule_group(select_respond, select_from_plan, reraise_issue)
    select_move   = rule_group(select_answer, select_ask, select_other)
    select_icm    = rule_group(select_icm_sem_neg)