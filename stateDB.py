from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String

import trindikit

from botserver import db



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




# class stateDBEntry(Base):
#     __tablename__ = 'conversationState'
#
#     chat_id = Column(Integer, primary_key=True)
#
#     private_agenda = Column(String)
#     private_plan = Column(String)
#     private_bel = Column(String)
#     shared_com = Column(String)
#     shared_qud = Column(String)
#     shared_lu_speaker = Column(String)
#     shared_lu_moves = Column(String)
#
#     mvis_input = Column(String)
#     mvis_latest_speaker = Column(String)
#     mvis_lastest_move = Column(String)
#     mvis_next_moves = Column(String)
#     mvis_output = Column(String)
#     mvis_program_state = Column(String)
#
#     # def __repr__(self):
#     #     return "<User(chat_id='%i', name='%s')>" % (self.chat_id, self.name)



class conversationState():
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.reset_MIVS()
        self.reset_IS()

    def init_IS_from_DB(self):
        pass

    def reset_IS(self):
        self.IS = trindikit.record(private = trindikit.record(agenda = trindikit.stack(),
                                          plan   = trindikit.stack(),
                                          bel    = set()),
                         shared  = trindikit.record(com    = set(),
                                          qud    = trindikit.stackset(),
                                          lu     = trindikit.record(speaker = trindikit.Speaker,
                                                          moves   = set())))

    def save_IS_to_DB(self):
        pass

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
        pass


    def save_MIVS_to_DB(self):
        pass

    def print_MIVS(self, prefix=""):
        """Print the MIVS. To be called from self.print_state()."""
        print(prefix + "INPUT:         ", self.INPUT)
        print(prefix + "LATEST_SPEAKER:", self.LATEST_SPEAKER)
        print(prefix + "LATEST_MOVES:  ", self.LATEST_MOVES)
        print(prefix + "NEXT_MOVES:    ", self.NEXT_MOVES)
        print(prefix + "OUTPUT:        ", self.OUTPUT)
        print(prefix + "PROGRAM_STATE: ", self.PROGRAM_STATE)



# class user():
#     def __init__(self, chat_id):
#         self.state = conversationState(chat_id)



if __name__ == "__main__":
    pass
    # usr = user(123)
    # print(usr.state.IS)
    # print(usr.state.INPUT)


    # db = stateDB("conversationStates")
    # user, created = db.create_or_add(123)
    # print("CREATE", user, created)
    #
    # users = db.session.query(stateDBEntry)
    # for i in users:
    #     print("LOOK", i)
    #
    #     print(i.private_agenda)
