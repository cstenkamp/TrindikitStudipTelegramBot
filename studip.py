import os
import settings
from cfg_grammar import *
from ibis_types import *
import trindikit
import ibis_generals
import codecs
from studip_downloader import load, return_file, load_file2
from singleUser_ibis import singleUser_download
import inspect
import functools
from studip_download import *
import time
from functools import partial

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

    @functools.wraps(function)
    def wrappedfunc(*args, **kw):
        new_kw = dict((key, getattr(args[0], key, None)) for key in replacekeys) #args[0] ist der DM (der als parameter für update-rules speziell behandelt wird), hier werden alle gepacslockten daran gehängt
        new_kw = {**new_kw, **kw} #für die partials mit what
        result = function(*args[1:], **new_kw)
        return result
    return wrappedfunc


@executable_rule
def make_authstring(username, pw, IS):
    auth_bytes = ('%s:%s' % (username, pw)).encode('ascii')
    auth_string = codecs.encode(auth_bytes, 'base64').strip()
    return Prop(Pred1("auth_string"), Ind(auth_string), True), IS.shared.com.add


@executable_rule
def is_VLZeit(auth_string, NEXT_MOVES):
    all_semesters = load("semesters", auth_string)['semesters']
    this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
    currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
    return Answer(YesNo(currently_seminars)), NEXT_MOVES.push


@executable_rule
def semesterdays(auth_string, what, NEXT_MOVES, IS):
    all_semesters = load("semesters", auth_string)['semesters']
    this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
    next_semester = [all_semesters[i+1]['title'] for i in range(len(all_semesters)) if all_semesters[i]['title'] == this_semester][0]
    currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
    if what == "db":
        if currently_seminars:
            return Prop(Pred1("DaysBreak"), Ind(str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), True, expires=round(time.time()) + 3600), IS.private.bel.add
            # return State(str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), NEXT_MOVES.push
        else:
            return Prop(Pred1("DaysBreak"), Ind("The break is right now!"), True, expires=round(time.time())+3600), IS.private.bel.add
            # return State("The Break is right now!"), NEXT_MOVES.push
    elif what == "wb":
        return Prop(Pred1("WhenBreak"), Ind(str(get_semester_info(all_semesters, next_semester))), True, expires=round(time.time())+3600*240), IS.private.bel.add
    elif what == "wl":
        return Prop(Pred1("WhenLectures"), Ind(str(get_semester_info(all_semesters, next_semester))), True, expires=round(time.time()) + 3600 * 240), IS.private.bel.add
        # return State(get_semester_info(all_semesters, next_semester)), NEXT_MOVES.push
    else: #what == "dl"
        if not currently_seminars:
            return Prop(Pred1("DaysLectures"), Ind(str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), True, expires=round(time.time())+3600), IS.private.bel.add
            # return State(str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), NEXT_MOVES.push
        else:
            return Prop(Pred1("DaysLectures"), Ind("There are lectures right now!"), True, expires=round(time.time())+3600), IS.private.bel.add
            # return State("There are Lectures right now!"), NEXT_MOVES.push


@executable_rule
def get_semester_inf(sem_name, auth_string, IS):
    all_semesters = load("semesters", auth_string)['semesters']
    result = get_semester_info(all_semesters, sem_name)
    IS.shared.com.remove("semester")
    return Prop(Pred1("WhenSemester", sem_name), Ind(result), True, expires=round(time.time())+3600*240), IS.private.bel.add



@executable_rule
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


@executable_rule
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


class StudIP_grammar(CFG_Grammar):

    def interpret(self, input, DOMAIN, anyString=False, moves=None, IS=None):
        res = super().interpret(input, DOMAIN, anyString=anyString, moves=moves, IS=IS)
        if res:
            return res
        else: #bspw empty set
            if any(isinstance(move.content, Question) and move.content.content.content == 'semester' for move in moves):
                try:
                    tmp = ibis_generals.check_for_something(IS, "auth_string")
                    if tmp[0]: #dann kann "this" und "next" nachgucken
                        this, next = get_semesters(tmp[1].content)
                        return Answer(ShortAns(Ind(get_relative_semester_name(input, this, next)), True))
                    else:
                        return Answer(ShortAns(Ind(get_semester_name(input)), True))
                except ValueError:
                    pass



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
              'filename': 'string', #'studip_filename'
              'DaysLectures': 'int',
              'DaysBreak': 'int',
              'WhenLectures': 'int',
              'WhenBreak': 'int',
              'WhenSemester': 'string',
              'semester': 'semester'
              }

    preds2 = {'WhenIs': ['semester', 'WhenSemester']} #1st element is first ind needed, second is the resulting pred1!

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

    domain = ibis_generals.Domain(preds0, preds1, preds2, sorts)

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
                    Inform("The Auth-string is: %s", ["com(auth_string)"]) #wenn inform 2 params hat und der zweite "bel" ist, zieht der die info aus dem believes.
                   ])

    #allow to change password/username -- command dafür ist "change" mit nem argument, aka username/pw

    domain.add_plan("!(download)",
                    [Findout("?x.coursename(x)"),
                     ExecuteFunc(download_file, "?x.auth_string(x)")
                    ], conditions = [
                     "com(auth_string)"
                    ])

    domain.add_plan("!(download2)",
                    [Findout("?x.coursename(x)"),
                     Findout("?x.filename(x)"),
                     ExecuteFunc(download_file2, "?x.auth_string(x)", "?x.coursename(x)", "?x.filename(x)")
                    ], conditions = [
                     "com(auth_string)"
                    ])

    domain.add_plan("!(Vorlesungszeit)",
                    [ExecuteFunc(is_VLZeit, "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])


    domain.add_plan("?x.DaysLectures(x)",
                    [ExecuteFunc(partial(semesterdays, what="dl"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.WhenLectures(x)",
                    [ExecuteFunc(partial(semesterdays, what="wl"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.DaysBreak(x)",
                    [ExecuteFunc(partial(semesterdays, what="db"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.WhenBreak(x)",
                    [ExecuteFunc(partial(semesterdays, what="wb"), "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])


    domain.add_plan("?x.y.WhenIs(y)(x)", #TODO - hier kommt die meldung "can't be done weil following info missing ist..." nicht mehr!
                    [ExecuteFunc(get_semester_inf, "?x.semester(x)", "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])





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


class TravelGrammar(ibis_generals.SimpleGenGrammar, StudIP_grammar):
    def generateMove(self, move):
        try:
            assert isinstance(move, Answer)
            prop = move.content
            assert isinstance(prop, Prop)
            if prop.pred.content == "price":
                return "The price is " + str(prop.ind.content)
            else:
                return prop.ind.content
        except:
            pass
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

    grammar.addForm("Answer(YesNo(False))", "No.")
    grammar.addForm("Answer(YesNo(True))", "Yes.")

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