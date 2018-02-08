from botserver import db
from datetime import datetime
from stateDB import ConversationState


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

    asked_restart = db.Column(db.Boolean)
    asked_stop = db.Column(db.Boolean)

    username = db.Column(db.String)
    auth_str = db.Column(db.String)

    def __repr__(self):
        return "<User(id='%i', chat_id='%i', name='%s', created at='%s')>" % (self.id, self.chat_id, self.name, str(self.createdate))


    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.createdate = datetime.now()
        self.asked_restart = False
        self.asked_stop = False
