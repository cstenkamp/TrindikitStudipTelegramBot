from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy import event
import pickle

import trindikit
from botserver import db


class ConversationState(db.Model):
    __tablename__ = 'conversationStates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)

    bk_is_private_agenda    = db.Column(db.String)
    bk_is_private_plan      = db.Column(db.String)
    bk_is_private_bel       = db.Column(db.String)
    bk_is_shared_com        = db.Column(db.String)
    bk_is_shared_qud        = db.Column(db.String)
    bk_is_shared_lu_speaker = db.Column(db.String)
    bk_is_shared_lu_moves   = db.Column(db.String)

    bk_mivs_input           = db.Column(db.String)
    bk_mivs_latest_speaker  = db.Column(db.String)
    bk_mivs_latest_moves    = db.Column(db.String)
    bk_mivs_next_moves      = db.Column(db.String)
    bk_mivs_output          = db.Column(db.String)
    # bk_mivs_program_state = db.Column(db.String)


    def __init__(self, user_id):
        self.user_id = user_id
        self.reset_MIVS()
        self.reset_IS()
        self.init_DB()


    def init_IS_from_DB(self):
        self.reset_IS()

        if self.bk_is_private_agenda != "":
            # for elem in self.bk_is_private_agenda.split(';'):
            #     self.IS.private.agenda.push(elem)
            self.IS.private.agenda = trindikit.stack(pickle.loads(self.bk_is_private_agenda), fixedType=object)
        if self.bk_is_private_plan != "":
            # for elem in self.bk_is_private_plan.split(';'):
            #     self.IS.private.plan.push(elem)
            self.IS.private.plan = trindikit.stack(pickle.loads(self.bk_is_private_plan), fixedType=object)
        if self.bk_is_private_bel != "":
            # self.IS.private.bel = set(self.bk_is_private_bel.split(';'))
            self.IS.private.bel = set(pickle.loads(self.bk_is_private_bel))
        if self.bk_is_shared_com != "":
            # self.IS.shared.com = set(self.bk_is_shared_com.split(';'))
            self.IS.shared.com = set(pickle.loads(self.bk_is_shared_com))
        if self.bk_is_shared_qud != "":
            self.IS.shared.qud = trindikit.stackset(pickle.loads(self.bk_is_shared_qud), fixedType=object)
            # for elem in self.bk_is_shared_qud.split(';'):
            #     self.IS.shared.qud.push(elem)
        self.IS.shared.lu.speaker = trindikit.Speaker.USR if self.bk_is_shared_lu_speaker == "USR" else trindikit.Speaker.SYS
        if self.bk_is_shared_lu_moves != "":
            self.IS.shared.lu.moves = set(pickle.loads(self.bk_is_shared_lu_moves))
            # self.IS.shared.lu.moves = set(self.bk_is_shared_lu_moves.split(';'))


    def save_IS_to_DB(self):
        odict = self.IS.asdict(recursive=True)

        self.bk_is_private_agenda = pickle.dumps(odict["private"]["agenda"])
        self.bk_is_private_plan = pickle.dumps(odict["private"]["plan"])
        self.bk_is_private_bel = pickle.dumps(odict["private"]["bel"])
        self.bk_is_shared_com = pickle.dumps(odict["shared"]["com"])
        self.bk_is_shared_qud = pickle.dumps(odict["shared"]["qud"])
        self.bk_is_shared_lu_speaker = "USR" if odict["shared"]["lu"].get("speaker", trindikit.Speaker.SYS) == trindikit.Speaker.USR else "SYS"
        self.bk_is_shared_lu_moves = pickle.dumps(odict["shared"]["lu"]["moves"])


    def reset_IS(self):
        self.IS = trindikit.record(private = trindikit.record(agenda = trindikit.stack(),
                                                              plan   = trindikit.stack(),
                                                              bel    = set()),
                                   shared  = trindikit.record(com    = set(),
                                                              qud    = trindikit.stackset(),
                                                              lu     = trindikit.record(speaker = trindikit.Speaker,
                                                                                        moves   = set())))


    def print_IS(self, prefix):
        self.IS.pprint(prefix)


    def reset_MIVS(self):
        """Initialise the MIVS. To be called from self.init()."""
        self.INPUT          = trindikit.value(str)
        self.LATEST_SPEAKER = trindikit.value(trindikit.Speaker) #initializing it with "Speaker" means that it can only take Speaker.USR or Speaker.SYS
        self.LATEST_MOVES   = set()          #sind die NEXT_MOVES von einer Iteration vorher
        self.NEXT_MOVES     = trindikit.stack(trindikit.Move)
        self.OUTPUT         = trindikit.value(str)
        self.PROGRAM_STATE  = trindikit.value(trindikit.ProgramState) #see above
        self.PROGRAM_STATE.set(trindikit.ProgramState.RUN)


    def init_MIVS_from_DB(self):
        self.reset_MIVS()
        self.INPUT.set(self.bk_mivs_input)
        self.LATEST_SPEAKER.set(trindikit.Speaker.USR if self.bk_mivs_latest_speaker == "USR" else trindikit.Speaker.SYS)
        if self.bk_mivs_latest_moves != "":
            self.LATEST_MOVES = set(self.bk_mivs_latest_moves.split(';'))
        if self.bk_mivs_next_moves != "":
            for elem in self.bk_mivs_next_moves.split(';'):
                self.NEXT_MOVES.push(elem)
        self.OUTPUT.set(self.bk_mivs_output)
        self.PROGRAM_STATE.set(trindikit.ProgramState.RUN) #must run, other stuff would be bullshit


    def save_MIVS_to_DB(self):
        self.bk_mivs_input = self.INPUT.get()
        self.bk_mivs_latest_speaker = "USR" if self.LATEST_SPEAKER.get() == trindikit.Speaker.USR else "SYS"
        self.bk_mivs_latest_moves = ';'.join([str(i) for i in list(self.LATEST_MOVES)])
        self.bk_mivs_next_moves = ';'.join([str(i) for i in list(self.NEXT_MOVES)])
        self.bk_mivs_output = self.OUTPUT.get()
        # self.bk_mivs_program_state =


    def print_MIVS(self, prefix=""):
        """Print the MIVS. To be called from self.print_state()."""
        print(prefix + "INPUT:         ", self.INPUT)
        print(prefix + "LATEST_SPEAKER:", self.LATEST_SPEAKER)
        print(prefix + "LATEST_MOVES:  ", self.LATEST_MOVES)
        print(prefix + "NEXT_MOVES:    ", self.NEXT_MOVES)
        print(prefix + "OUTPUT:        ", self.OUTPUT)
        print(prefix + "PROGRAM_STATE: ", self.PROGRAM_STATE)


    def init_DB(self):
        if self.bk_is_private_agenda is None: self.bk_is_private_agenda = ""
        if self.bk_is_private_plan is None: self.bk_is_private_plan = ""
        if self.bk_is_private_bel is None: self.bk_is_private_bel = ""
        if self.bk_is_shared_com is None: self.bk_is_shared_com = ""
        if self.bk_is_shared_qud is None: self.bk_is_shared_qud = ""
        if self.bk_is_shared_lu_speaker is None: self.bk_is_shared_lu_speaker = ""
        if self.bk_is_shared_lu_moves is None: self.bk_is_shared_lu_moves = ""
        if self.bk_mivs_input is None: self.bk_mivs_input = ""
        if self.bk_mivs_latest_speaker is None: self.bk_mivs_latest_speaker = ""
        if self.bk_mivs_latest_moves is None: self.bk_mivs_latest_moves = ""
        if self.bk_mivs_next_moves is None: self.bk_mivs_next_moves = ""
        if self.bk_mivs_output is None: self.bk_mivs_output = ""


# wenn man den IS lädt anstatt neu created muss er IS laden statt resetten
# http://docs.sqlalchemy.org/en/latest/orm/events.html#sqlalchemy.orm.events.InstanceEvents.load,
# http://docs.sqlalchemy.org/en/latest/orm/session_events.html#loaded-as-persistent
@event.listens_for(ConversationState, 'load')
def receive_load(target, context):
    target.init_DB()
    target.init_MIVS_from_DB()
    target.init_IS_from_DB()

########################################################################################################################

# def recStringDict(value):
#     result = ""
#     for key, value in list(value.items()):
#         if result: result += '\n'
#         result += prefix + key + ': '
#         if isinstance(value, dict):
#             result += '\n' + recStringDict(value)
#         else:
#             result += str(value)
#     return result
#
# def tostring(dic):
#     final = {}
#     for key, value in list(dic.items()):
#         if isinstance(value, dict):
#             final[key] = tostring(value)
#         elif isinstance(value, list):
#             final[key] = ';'.join([str(i) for i in value])
#         else:
#             final[key] = str(value)
#     return final
#
# ---------------------------------------- Nicht benötigt bei flask_sqlalchemy ----------------------------------------
#
# Base = declarative_base()
#
# class stateDB:
#
#     def __init__(self, dbname=":memory:", dbtype="sqlite"):
#         dbname = dbname+"."+dbtype if dbname != ":memory:" and "." not in dbname else dbname
#         self.engine = create_engine(dbtype+':///'+dbname, echo=False)
#         Session = sessionmaker(bind=self.engine)
#         self.session = Session()
#         Base.metadata.create_all(self.engine)
#
#
#     def create_or_add(self, chatID):
#         query = self.session.query(stateDBEntry)
#         user = query.filter(stateDBEntry.chat_id==chatID).one_or_none()
#         if user != None:
#             return user, False
#         else:
#             user = stateDBEntry(chat_id=chatID)
#             self.session.add(user)
#             self.session.commit()
#             return user, True