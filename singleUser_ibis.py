from trindikit import stack, DialogueManager, record, stackset, Speaker, ProgramState, StandardMIVS, SimpleInput, SimpleOutput, maybe, do, repeat, rule_group, VERBOSE, _TYPEDICT
from ibis_types import Ask, Question, Answer, Ans, ICM, ShortAns, Prop, YesNo, YNQ, AltQ, WhQ, PlanConstructor, Greet, Quit
from ibis_rules import get_latest_moves, integrate_usr_ask, integrate_sys_ask, integrate_answer, integrate_greet, integrate_usr_quit, integrate_sys_quit, downdate_qud, recover_plan, find_plan, remove_findout, remove_raise, exec_consultDB, execute_if, select_respond, select_from_plan, reraise_issue, select_answer, select_ask, select_other, select_icm_sem_neg, handle_empty_plan_agenda_qud
from ibis_generals import SimpleGenGrammar, Grammar, Database, Domain
import pickle
import os.path


######################################################################
# IBIS information state
######################################################################

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
                                                  plan   = stack(tmp_dict["private"]["plan"], PlanConstructor),
                                                  # TODO: warum ist das beim normalen initialisieren ein PlanConstructor?
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
                print(indent ,key ,":" ,type(val))
                if type(val) == dict:
                    self.print_type(val, indent +"  ")
                elif isinstance(val, str):
                    print(indent +"  " ,val, type(val))
                elif hasattr(val, '__getitem__'):
                    for i in val:
                        print(indent +"  ", i, type(i))
        else:
            print(indent, type(what))


    def psave_IS(self, filename):
        # TODO you know what, ich speicher den Kram in ner Datenbank. ==> SQLAlchemy, die ibis-klasse extended Base=declarative_base(), und für die werte .IS und .MVIS gibt es entsprechungen
        # TODO Flyweight-pattern nutzen, sodass jede ibis-instanz nur den Stand der Datenbank hat, und die Methoden von ner gemeinsamen erbt
        odict = self.IS.asdict(recursive=True)
        with open(filename, 'wb') as f:
            pickle.dump(odict, f, pickle.HIGHEST_PROTOCOL)

######################################################################
# IBIS dialogue manager
######################################################################

class IBISController(DialogueManager):
    def control(self):
        """The IBIS control algorithm."""
        if not self.IS.private.plan:
            self.IS.private.agenda.push(Greet())
        self.print_state()
        while True:
            self.select()  # puts the next appropriate thing onto the agenda
            if self.NEXT_MOVES:
                self.generate()  # sets output
                self.output(None)  # prints output
                self.update()  # integrates answers, ..., loads & executes plan
                self.print_state()
            if self.PROGRAM_STATE.get() == ProgramState.QUIT:
                break
            self.input()
            res = self.interpret()  # obviously also runs it
            if res == "exit":
                break

            self.update()
            self.print_state()


# contains..  control()     IS + init_IS   MVIS+init      interpret+input  generate+output do,maybe,repeat
class IBIS(IBISController, IBISInfostate, StandardMIVS,  SimpleInput,     SimpleOutput,   DialogueManager):
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

######################################################################
# IBIS-1
######################################################################



class IBIS1(IBIS):
    """The IBIS-1 dialogue manager."""

    def update(self):

        self.IS.private.agenda.clear()
        self.grounding()()
        maybe(self.integrate())
        maybe(self.downdate_qud())
        maybe(self.load_plan())
        repeat(self.exec_plan())
        maybe(self.handle_empty_plan_agenda_qud())
        self.psave_IS("CurrState.pkl")

    # rule_group returns "lambda self: do(self, *rules)" with rules specified here... NOT ANYMORE:
    # rule_group returns lambda self, user=None: lambda: do(self, user, *rules) <- es kriegt ERST rules (siehe hier drunter), und DAS erwarted dann noch self und user (siehe hier drüber), und returned eine funktion (nicht ihr result, deswegen das nested lambda)
    grounding    = rule_group(get_latest_moves)
    integrate    = rule_group(integrate_usr_ask, integrate_sys_ask,
                              integrate_answer, integrate_greet,
                              # integrate macht aus question+answer proposition! aus "?return()" und "YesNo(False)" wird "Prop((Pred0('return'), None, False))", und das auf IS.shared.com gepackt
                              integrate_usr_quit, integrate_sys_quit)
    downdate_qud = rule_group(downdate_qud)
    load_plan    = rule_group(recover_plan, find_plan)
    exec_plan    = rule_group(remove_findout, remove_raise, exec_consultDB, execute_if)
    handle_empty_plan_agenda_qud = rule_group(handle_empty_plan_agenda_qud)

    def select(self):
        if not self.IS.private.agenda:
            maybe(self.select_action())
        maybe(self.select_icm())
        maybe(self.select_move())

    select_action = rule_group(select_respond, select_from_plan, reraise_issue)
    select_move   = rule_group(select_answer, select_ask, select_other)
    select_icm    = rule_group(select_icm_sem_neg)