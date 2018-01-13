from trindikit import stack, DialogueManager, record, stackset, Speaker, ProgramState, StandardMIVS, SimpleInput, SimpleOutput, maybe, do, repeat, rule_group, VERBOSE, _TYPEDICT, update_rule
from ibis_types import Ask, Question, Answer, Ans, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit
from ibis_rules import get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg, handle_empty_plan_agenda_qud
from ibis import IBISController, IBISInfostate
import sys
from bothelper import send_message
import pickle
import os.path



class TgramOutput(DialogueManager):
    """Naive implementations of a generation module and an output module.

    Apart from the standard MIVS - NEXT_MOVES, LATEST_MOVES, OUTPUT and
    LATEST_SPEAKER - a GRAMMAR is required with the method:

      - GRAMMAR.generate(set of moves), returning a string.
    """

    @update_rule
    def generate(NEXT_MOVES, OUTPUT, GRAMMAR):
        """Convert NEXT_MOVES to a string and put in OUTPUT.

        Calls GRAMMAR.generate to convert the set of NEXT_MOVES
        into a string, which is put in OUTPUT.
        """
        OUTPUT.set(GRAMMAR.generate(NEXT_MOVES))


    @update_rule
    def output(NEXT_MOVES, OUTPUT, LATEST_SPEAKER, LATEST_MOVES):
        """Print the string in OUTPUT to standard output.

        After printing, the set of NEXT_MOVES is moved to LATEST_MOVES,
        and LATEST_SPEAKER is set to SYS.
        """
        # send_message(OUTPUT.get())
        LATEST_SPEAKER.set(Speaker.SYS)
        LATEST_MOVES.clear()
        LATEST_MOVES.update(NEXT_MOVES)
        NEXT_MOVES.clear()



class TgramInput(object):
    """Naive implementations of an input module and an interpretation module.

    Apart from the standard MIVS - LATEST_MOVES, INPUT and LATEST_SPEAKER -
    a GRAMMAR is required with the method:

      - GRAMMAR.interpret(string), returning a move or a sequence of moves.
    """

    @update_rule
    def interpret(INPUT, LATEST_MOVES, GRAMMAR):
        """Convert an INPUT string to a set of LATEST_MOVES.

        Calls GRAMMAR.interpret to convert the string in INPUT
        to a set of LATEST_MOVES.
        """
        LATEST_MOVES.clear()
        if INPUT.value != '':
            move_or_moves = GRAMMAR.interpret(INPUT.get())
            if INPUT.value == "exit" or INPUT.value == "reset":
                return INPUT.value
            elif not move_or_moves:  # geeez, ich will nen ANN nutzen dass per NLI text-->Speech act macht
                if VERBOSE["NotUnderstand"]:
                    print("Did not understand:", INPUT)
                    print()
            elif isinstance(move_or_moves, Move):
                LATEST_MOVES.add(move_or_moves)
            else:
                LATEST_MOVES.update(move_or_moves)

    @update_rule
    def input(INPUT, LATEST_SPEAKER):
        """Inputs a string from standard input.

        The string is put in INPUT, and LATEST_SPEAKER is set to USR.
        """
        try:
            str = input("U> ")
        except EOFError:
            print("EOF")
            sys.exit()
        INPUT.set(str)
        LATEST_SPEAKER.set(Speaker.USR)
        print()



# contains..    IS + init_IS   MVIS+init     interpret+input  generate+output do,maybe,repeat
class TgramIBIS(IBISInfostate, StandardMIVS, TgramInput,     TgramOutput,   DialogueManager):
    """The IBIS dialogue manager.

    This is an abstract class: methods update and select are not implemented.
    """

    def __init__(self, domain, database, grammar):
        self.DOMAIN = domain
        self.DATABASE = database
        self.GRAMMAR = grammar

    def init(self):  # called by DialogueManager.run
        self.init_IS()
        self.init_MIVS()

    def reset(self):
        self.reset_IS()
        self.reset_MIVS()

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
