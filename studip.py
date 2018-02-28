import os
import settings
from cfg_grammar import *
from ibis_types import Findout, If, ConsultDB, Ind, Inform, ExecuteFunc, State, Statement
import trindikit
import ibis_generals
import codecs
from studip_downloader import load, return_file, load_file2
from singleUser_ibis import singleUser_download
import inspect
import functools

if settings.MULTIUSER:
    import multiUser_ibis
    PATH = "/var/www/studIPBot"
    import bothelper
else:
    PATH = "/home/chris/Documents/UNI/sem_9/dialog_systems/Projekt/My_Trindikit/"
    import singleUser_ibis


def executable_rule(function):
    argkeys, varargs, varkw, defaults = inspect.getargspec(function)
    replacekeys = [i for i in argkeys if i.isupper()] #IS, NEXT_MOVES, etc ist uppercase and will be replaced
    noreplacekeys = [i for i in argkeys if not i.isupper()]

    @functools.wraps(function)
    def wrappedfunc(*args, **kw):
        new_kw = dict((key, getattr(args[0], key, None)) for key in replacekeys) #args[0] ist der DM (der als parameter für update-rules speziell behandelt wird), hier werden alle gepacslockten daran gehängt
        result = function(*noreplacekeys, **new_kw)
        return result
    return wrappedfunc


@executable_rule
def make_authstring(username, pw, IS):
    auth_bytes = ('%s:%s' % (username, pw)).encode('ascii')
    auth_string = codecs.encode(auth_bytes, 'base64').strip()
    return Prop(Pred1("auth_string"), Ind(auth_string), True), IS.shared.com.add


def download_file(auth_string):
    if settings.MULTIUSER:
        bothelper.send_message("yep, will do", settings.MY_CHAT_ID)
        try:
            userid = load('user', auth_string)['user']['user_id']
            file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
            bothelper.send_file(settings.MY_CHAT_ID, file[1]["filename"], load_file2(file[1]["document_id"], auth_string))
        except SystemExit:
            bothelper.send_message("Wrong Username/PW", settings.MY_CHAT_ID)
    else:
        try:
            userid = load('user', auth_string)['user']['user_id']
            file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
            singleUser_download(file[1]["filename"], load_file2(file[1]["document_id"], auth_string))
        except SystemExit:
            pass


def download_file2(auth_string, coursename, filename):
    print(auth_string, coursename, filename)
    if settings.MULTIUSER:
        bothelper.send_message("yep, will do", settings.MY_CHAT_ID)
        try:
            userid = load('user', auth_string)['user']['user_id']
            file = return_file(userid, None, coursename, None, filename, auth_string)
            bothelper.send_file(settings.MY_CHAT_ID, file[1]["filename"], load_file2(file[1]["document_id"], auth_string))
        except SystemExit:
            bothelper.send_message("Wrong Username/PW", settings.MY_CHAT_ID)



def create_domain():
    preds0 = 'return', 'needvisa', 'studip'
    # TODO - warum ist "return" ein zero-order-predicate? Dann ist es ja schon fulfilled - 0-order-predicates are propositions, aka sentences.
    # TODO - you can see the difference in the plan even: Findout(WhQ(Pred1('class'))), Findout(YNQ(Prop((Pred0('return'), None, True))))
    # TODO - The YNQ does already has the answer, and is thus a Proposition, and YNQs can be converted from that. Why is such a thing not a 1-place-predicate of the domain Boolean?
    # --- main ding das mich stört: warum ist es YNQ(Prop((Pred0('return'), None, True))) und nicht YNQ(Pred0('return')) --> warum muss es nochmal in ner Prop sein wo noch Truth-value bei ist

    preds1 = {'price': 'int',
              'how': 'means',
              'dest_city': 'city',
              'depart_city': 'city',
              'depart_day': 'day',
              'class': 'flight_class',
              'return_day': 'day',
              'username': 'string',
              'password': 'string',
              'coursename': 'string', #'studip_course'
              'filename': 'string' #'studip_filename'
              }

    means = 'plane', 'train'
    cities = 'paris', 'london', 'berlin'
    days = 'today', 'tomorrow', 'monday', 'tuesday','wednesday','thursday','friday','saturday','sunday'
    classes = 'first', 'second', 'krypto'
    courses = 'krypto', 'krypto2'

    sorts = {'means': means,
             'city': cities,
             'day': days,
             'flight_class': classes,
             'studip_course': courses
             }

    domain = ibis_generals.Domain(preds0, preds1, sorts)

    domain.add_plan("?x.price(x)",
                   [Findout("?x.how(x)"),
                    Findout("?x.dest_city(x)"),
                    Findout("?x.depart_city(x)"),
                    Findout("?x.depart_day(x)"),
                    Findout("?x.class(x)"),
                    Findout("?return()"),
                    If("?return()",
                        [Findout("?x.return_day(x)")]),
                    ConsultDB("?x.price(x)")  #das was precond der update-rule ist, nicht die funktion von unten!
                   ])

    domain.add_plan("!(visa)",
                   [Findout("?x.dest_city(x)")
                    ])

    domain.add_plan("!(studip)",
                   [Findout("?x.username(x)"),
                    Findout("?x.password(x)"),
                    Inform("Unfortunately, to have access to your StudIP-Files, I have to save the username and pw. The only thing I can do is to obfuscate the Username and PW to a Hex-string."),
                    ExecuteFunc(make_authstring, "?x.username(x)", "?x.password(x)"),
                    Inform("The Auth-string is: %s", ["bel(auth_string)"]) #wenn inform 2 params hat und der zweite "bel" ist, zieht der die info aus dem believes.
                   ])

    domain.add_plan("!(download)",
                    [Findout("?x.coursename(x)"),
                     ExecuteFunc(download_file, "?x.auth_string(x)")
                    ], conditions = [
                     "bel(auth_string)"
                    ])

    domain.add_plan("!(download2)",
                    [Findout("?x.coursename(x)"),
                     Findout("?x.filename(x)"),
                     ExecuteFunc(download_file2, "?x.auth_string(x)", "?x.coursename(x)", "?x.filename(x)")
                    ], conditions = [
                     "bel(auth_string)"
                    ])

    domain.add_plan("!(Vorlesungszeit)",
                    [ExecuteFunc(download_file, "?x.auth_string(x)")],
                    conditions = ["bel(auth_string)"])


    #allow to change password/username -- command dafür ist "change" mit nem argument, aka username/pw



    return domain


class TravelDB(ibis_generals.Database):

    def __init__(self):
        self.entries = []

    def consultDB(self, question, context):
        depart_city = self.getContext(context, "depart_city")
        dest_city = self.getContext(context, "dest_city")
        day = self.getContext(context, "depart_day")
        do_return = self.getContext(context, "return")
        entry = self.lookupEntry(depart_city, dest_city, day, do_return)
        price = entry['price']
        return Prop(Pred1("price"), Ind(price), True)

    def lookupEntry(self, depart_city, dest_city, day, do_return):
        for e in self.entries:
            if e['from'] == depart_city and e['to'] == dest_city and e['day'] == day and e['return'] == do_return:
                return e
        assert False

    def getContext(self, context, pred):
        for prop in context:
            if prop.pred.content == pred:
                try:
                    return prop.ind.content
                except AttributeError: #NoneType
                    return prop.yes #bei Yes-No-Questions
        assert False

    def addEntry(self, entry):
        self.entries.append(entry)


class TravelGrammar(ibis_generals.SimpleGenGrammar, CFG_Grammar):
    def generateMove(self, move):
        try:
            assert isinstance(move, Answer)
            prop = move.content
            assert isinstance(prop, Prop)
            assert prop.pred.content == "price"
            return "The price is " + str(prop.ind.content)
        except:
            return super(TravelGrammar, self).generateMove(move)


def loadIBIS():
    grammar = TravelGrammar()
    grammar.loadGrammar(os.path.join(PATH,"travel.fcfg"))
    grammar.addForm("Ask('?x.how(x)')", "How do you want to travel?")
    grammar.addForm("Ask('?x.dest_city(x)')", "Where do you want to go?")
    grammar.addForm("Ask('?x.depart_city(x)')", "From where are you leaving?")
    grammar.addForm("Ask('?x.depart_day(x)')", "When do you want to leave?")
    grammar.addForm("Ask('?x.return_day(x)')", "When do you want to return?")
    grammar.addForm("Ask('?x.class(x)')", "First or second class?")
    grammar.addForm("Ask('?return()')", "Do you want a return ticket?")

    grammar.addForm("Ask('?x.username(x)')", "Before we start, I need to know your username. What is it?")
    grammar.addForm("Ask('?x.password(x)')", "Next up, your password please.")
    grammar.addForm("State('wtf')", "Uhm, wtf")
    grammar.addForm("Ask('?x.coursename(x)')", "From which course do you want to download?")
    grammar.addForm("Ask('?x.filename(x)')", "Which file from that course do you want to download?")

    database = TravelDB()
    database.addEntry({'price': '232', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': False})
    database.addEntry({'price': '345', 'from': 'paris', 'to': 'london', 'day': 'today', 'return': False})
    database.addEntry({'price': '432', 'from': 'berlin', 'to': 'paris', 'day': 'today', 'return': True})

    domain = create_domain()

    if settings.MULTIUSER:
        ibis = multiUser_ibis.IBIS2(domain, database, grammar)
    else:
        ibis = singleUser_ibis.IBIS1(domain, database, grammar)
    return ibis




######################################################################
# Running the dialogue system
######################################################################

if __name__=='__main__':
    if not settings.MULTIUSER:
        ibis = loadIBIS()
        ibis.init()
        ibis.control()
    else:
        print("Multiuser is on")