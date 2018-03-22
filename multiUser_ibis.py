import settings
from trindikit import stack, DialogueManager, record, stackset, Speaker, ProgramState, StandardMIVS, SimpleInput, SimpleOutput, maybe, do, repeat, rule_group, _TYPEDICT, update_rule
from ibis_types import Ask, Question, Answer, Ans, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit
from ibis_rules import *#get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg, handle_empty_plan_agenda_qud, integrate_usr_impr, exec_inform
import pickle
import os.path
import requests
import urllib
from botserver import db
import bothelper

# TODO Flyweight-pattern nutzen, sodass jede ibis-instanz nur den Stand der Datenbank hat, und die Methoden von ner gemeinsamen erbt


class TGramOutput(SimpleOutput):
    @update_rule
    def output(NEXT_MOVES, OUTPUT, LATEST_SPEAKER, LATEST_MOVES, USER):
        """Print the string in OUTPUT to standard output.

        After printing, the set of NEXT_MOVES is moved to LATEST_MOVES,
        and LATEST_SPEAKER is set to SYS.
        """
        print("S to", str(USER.chat_id) + ":", OUTPUT.get() or "[---]")
        print()
        bothelper.send_message(str(OUTPUT.get()), USER.chat_id)
        LATEST_SPEAKER.set(Speaker.SYS)
        LATEST_MOVES.clear()
        LATEST_MOVES.update(NEXT_MOVES)
        if settings.MERGE_SUBSQ_MESSAGES:
            NEXT_MOVES.clear()
        else:
            del NEXT_MOVES.elements[0]

######################################################################
# IBIS dialogue manager
######################################################################

class IBISController(DialogueManager):
    def print_state(self, user):
        if settings.VERBOSE["IS"] or settings.VERBOSE["MIVS"]:
            print("+----- "+str(user.chat_id)+" ------------- - -  -")
        if settings.VERBOSE["MIVS"]:
            user.state.print_MIVS(prefix="| ")
        if settings.VERBOSE["IS"] and settings.VERBOSE["MIVS"]:
            print("|")
        if settings.VERBOSE["IS"]:
            user.state.print_IS(prefix="| ")
        if settings.VERBOSE["IS"] or settings.VERBOSE["MIVS"]:
            print("+------------------------ - -  -")
            print()



#contains..         print_state      interpret        generate+output do,maybe,repeat
class MultiUserIBIS(IBISController,  SimpleInput,     TGramOutput,    DialogueManager):
    """The IBIS dialogue manager. 
    
    This is an abstract class: methods update and select are not implemented.
    """
    def __init__(self, domain, apiConnector, grammar):
        self.DOMAIN = domain
        self.APICONNECTOR = apiConnector
        self.GRAMMAR = grammar


    def init(self):
        pass


    def handle_message(self, message, user):
        user.state.INPUT.set(message)
        user.state.LATEST_SPEAKER.set(Speaker.USR)
        self.interpret(user)
        self.update(user)
        self.print_state(user)
        self.respond(user)


    def respond(self, user):
        self.select(user)  # puts the next appropriate thing onto the agenda
        while user.state.NEXT_MOVES:
            self.generate(user)  # sets output
            self.output(user)  # prints output  #kann gut sein dass generate, output, input und intepret nicht mit user als param klappen, weil die nicht ge rule_group ed werden
            self.update(user)  # integrates answers, ..., loads & executes plan
            self.print_state(user)




######################################################################
# IBIS-1
######################################################################



class IBIS2(MultiUserIBIS):
    """The IBIS-1 dialogue manager."""
    # select -> generate -> output -> update -> input -> update

    def update(self, user):
        user.state.IS.private.agenda.clear()
        self.grounding(user)()
        repeat(self.expire(user))
        maybe(self.integrate(user))
        maybe(self.downdate_qud(user))
        maybe(self.clarify(user))
        maybe(self.pre_loadplan(user))
        maybe(self.load_plan(user))
        repeat(self.exec_plan(user))
        maybe(self.downdate_qud2(user))
        maybe(self.finalize_IS(user))

    #rule_group returns "lambda self: do(self, *rules)" with rules specified here... NOT ANYMORE:
    #rule_group returns lambda self, user=None: lambda: do(self, user, *rules) <- es kriegt ERST rules (siehe hier drunter), und DAS erwarted dann noch self und user (siehe hier drüber), und returned eine funktion (nicht ihr result, deswegen das nested lambda)
    grounding    = rule_group(get_latest_moves)
    expire       = rule_group(expire_expirables)
    integrate    = rule_group(integrate_usr_ask, integrate_sys_ask, integrate_usr_impr,
                                integrate_answer, integrate_greet,      #integrate macht aus question+answer proposition! aus "?return()" und "YesNo(False)" wird "Prop((Pred0('return'), None, False))", und das auf IS.shared.com gepackt
                                integrate_usr_quit, integrate_sys_quit)
    downdate_qud  = rule_group(downdate_qud)
    clarify       = rule_group(clarify_pred2)
    pre_loadplan  = rule_group(integrate_secordq_clarify)
    load_plan     = rule_group(mention_command_conditions, recover_plan, find_plan1, find_plan2)
    exec_plan     = rule_group(remove_findout, remove_raise, exec_consultDB, execute_if, exec_inform, exec_func)
    downdate_qud2 = rule_group(downdate_qud_commands)
    finalize_IS = rule_group(make_command_old, handle_empty_plan_agenda_qud)

    def select(self, user):
        if not user.state.IS.private.agenda:
            maybe(self.select_action(user))
        maybe(self.select_icm(user))
        maybe(self.select_move(user))

    select_action = rule_group(select_respond, select_from_plan, reraise_issue)
    select_move   = rule_group(select_answer, select_ask, select_other)
    select_icm    = rule_group(select_icm_sem_neg)