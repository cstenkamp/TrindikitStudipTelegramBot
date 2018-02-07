# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy import Column, Integer, String
from botserver import db
from datetime import datetime
from stateDB import ConversationState

# Base = declarative_base()
#
# class userDB:
#
#     def __init__(self, dbname=":memory:", dbtype="sqlite"):
#         dbname = dbname+"."+dbtype if dbname != ":memory:" and "." not in dbname else dbname
#         self.engine = create_engine(dbtype+':///'+dbname, echo=False)
#         Session = sessionmaker(bind=self.engine)
#         self.session = Session()
#         Base.metadata.create_all(self.engine)
#t
#
#     def create_or_add(self, chatID):
#         query = self.session.query(User)
#         user = query.filter(User.chat_id==chatID).one_or_none()
#         if user != None:
#             return user, False
#         else:
#             user = User(chat_id=chatID)
#             self.session.add(user)
#             self.session.commit()
#             return user, Truet


def create_or_add_user(chatID):
    db.create_all()
    user = User.query.filter(User.chat_id==chatID).one_or_none()
    if user != None:
        user.state = ConversationState.query.filter(ConversationState.user_id == user.id).one_or_none()
        #TODO - hier ne abfrage falls das None ist. Stranger case, kann aber eintreten
        return user, False
    else:
        user = User(chat_id=chatID)
        db.session.add(user)
        db.session.commit()
        user.state = ConversationState(user_id=user.id)
        db.session.add(user.state)
        db.session.commit()
        return user, True


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String)
    createdate = db.Column(db.DateTime)


    def __repr__(self):
        return "<User(id='%i', chat_id='%i', name='%s', created at='%s')>" % (self.id, self.chat_id, self.name, str(self.createdate))


    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.createdate = datetime.now()
        # self.state = ConversationState(self.chat_id)



if __name__ == "__main__":
    pass
    # db = userDB("users")
    # user, created = db.create_or_add(123)
    # print("CREATE", user, created)
    #
    # users = db.session.query(User)
    # for i in users:
    #     print("LOOK", i)


#
#
# Base.metadata.create_all(engine)
# ed_user = User(name='ed', fullname='Ed Jones', password='edspassword')
# ed_user2 = User(name='ed', fullname='Ed Jones', password='edspassword')
# print("!!!!!", ed_user is ed_user2)
# session.add(ed_user)
# session.add(ed_user2)
#
# our_user = session.query(User).filter_by(name='ed')
# for i in our_user:
#     print(i, ed_user is i) #nur eins True, weil wegen identity map: this very instance existiert schon und wird nur wiederhergestellt
#
# print("---")
#
# session.add_all([
#     User(name='wendy', fullname='Wendy Williams', password='foobar'),
#     User(name='mary', fullname='Mary Contrary', password='xxg527'),
#     User(name='ed', fullname='Fred Flinstone', password='blah')])
#
# session.commit()
#
# our_user = session.query(User).filter_by(name='ed')
# for i in our_user:
#     print(i, ed_user is i) #nur eins, weil wegen identity map: this very instance existiert schon und wird nur wiederhergestellt
#
# print("---")
#
# for u in session.query(User).order_by(User.id)[1:3]:
#     print(u)
#
# print("---")
#
#
# query = session.query(User).filter(User.name.like('%ed')).order_by(User.id)
# user = query.filter(User.id == 1).one_or_none()
# print(user)
#
#
# from sqlalchemy import ForeignKey
# from sqlalchemy.orm import relationship
#
# class Address(Base):
#     __tablename__ = 'addresses'
#     id = Column(Integer, primary_key=True)
#     email_address = Column(String, nullable=False)
#     user_id = Column(Integer, ForeignKey('users.id'))
#
#     user = relationship("User", back_populates="addresses")
#
#     def __repr__(self):
#         return "<Address(email_address='%s')>" % self.email_address
#
# User.addresses = relationship("Address", order_by=Address.id, back_populates="user")
#
# Base.metadata.create_all(engine)
# session.commit()