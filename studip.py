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
    IS.shared.com.remove("semester", silent=True)
    return Prop(Pred1("WhenSemester", sem_name), Ind(result), True, expires=round(time.time())+3600*24), IS.private.bel.add


@executable_rule
def get_my_courses(sem_name, auth_string, IS):
    w_courses, s_courses = get_user_courses(auth_string, semester=sem_name)
    s = " "+"\n ".join([i["name"] + " (" + (i["event_number"] if i["event_number"] else "None") + ")" for i in s_courses]) if s_courses else ""
    w = " "+"\n ".join([i["name"] + " (" + (i["event_number"] if i["event_number"] else "None") + ")" for i in w_courses]) if w_courses else ""
    txt = ""
    if len(s) > 2: txt += "Courses you take:\n"+s+"\n"
    if len(w) > 2: txt += "Courses you work for:\n"+w+"\n"
    txt = txt[:-1]
    if len(txt) < 2: txt = "You don't have any courses for that semester!"
    IS.shared.com.remove("semester", silent=True)
    return Prop(Pred1("ClassesForSemester", sem_name), Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add


@executable_rule
def session_info(auth_string, what, IS, semester=None, one_course_str=None):
    if not ibis_generals.check_for_something(IS, "bel(timerel_courses)")[0]:
        timerel_courses = get_timerelevant_courses(auth_string)
        IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
    timerel_courses = ibis_generals.check_for_something(IS, "bel(timerel_courses)")[1] #danach ist es save da
    if what == "all":
        str = "What"
    elif what == "where":
        str = "Where"
    elif what == "when":
        str = "When"
    thepred = Pred1(str+"NextKurs", one_course_str) if one_course_str else (Pred1(str+"NextSem", semester) if semester else Pred1(str+"Next"))
    txt = get_session_info(what, auth_string, semester=semester, timerel_courses=timerel_courses, one_course_str=one_course_str)
    return Prop(thepred, Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add



@executable_rule
def klausur(auth_string, course_str, IS, semester=None):
    if not ibis_generals.check_for_something(IS, "bel(timerel_courses)")[0]:
        timerel_courses = get_timerelevant_courses(auth_string)
        IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
    timerel_courses = ibis_generals.check_for_something(IS, "bel(timerel_courses)")[1] #danach ist es save da
    txt = find_klausurtermin(auth_string, course_str, timerel_courses=timerel_courses)
    return Prop(Pred1("WhenExam", course_str), Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add


@executable_rule
def test_credentials(auth_string, NEXT_MOVES):
    try:
        load_userid(auth_string, silent=False)
    except AuthentificationError:
        return State("These credentials are wrong!\nYou can re-enter them by sending /start"), NEXT_MOVES.push


@executable_rule
def classes_on(auth_string, IS, date=None, left=False):
    assert date or left
    if not ibis_generals.check_for_something(IS, "bel(timerel_courses)")[0]:
        timerel_courses = get_timerelevant_courses(auth_string)
        IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
    timerel_courses = ibis_generals.check_for_something(IS, "bel(timerel_courses)")[1] #danach ist es save da
    if not left:
        txt = get_courses_for_day(auth_string, date, None, timerel_courses)
        return Prop(Pred1("CoursesOn", date), Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add
    else:
        txt = get_courses_for_day(auth_string, parse_date("today"), None, timerel_courses, round(time.time()))
        return Prop(Pred1("CoursesLeft", date), Ind(txt), True, expires=round(time.time()) + 60), IS.private.bel.add



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

    def interpret(self, input, IS, DOMAIN, NEXT_MOVES, anyString=False, moves=None):
        res = super().interpret(input, IS, DOMAIN, NEXT_MOVES, anyString=anyString, moves=moves)
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
            elif any(isinstance(move.content, Question) and move.content.content.content == 'kurs' for move in moves):
                try:
                    tmp = ibis_generals.check_for_something(IS, "auth_string")
                    if tmp[0]: #dann kann "this" und "next" nachgucken
                        name = find_real_coursename(tmp[1].content, input)
                        if name:
                            return Answer(ShortAns(Ind(name), True))
                except ValueError:
                    pass


class studip_domain(ibis_generals.Domain):

    def get_sort_from_ind(self, answer, *args, **kwargs):
        res = self.inds.get(answer)
        if res: return res
        if "SS" in answer and any(str(i) in answer for i in range(2000, 2050)) or "WS" in answer and any(str(i)+'/'+str(i-1999).zfill(2) in answer for i in range(2000, 2050)):
            return "semester"
        if "kurs" in kwargs and answer in kwargs["kurs"]:
            return "kurs"
        if answer[0] == "d" and all(ch.isnumeric() for ch in answer[1:]):
            return "date"

    def collect_sort_info(self, forwhat, IS=None):
        try:
            if forwhat == "kurs":
                auth_string = ibis_generals.check_for_something(IS, "auth_string")
                if auth_string[0]:
                    auth_string = auth_string[1].content
                    return {"kurs": get_courses(auth_string, semester="")[0]}
        except:
            pass
        return None


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
              'ClassesForSemester': 'string',
              'WhatNext': 'string',
              'WhatNextSecOrd': 'string',
              'WhatNextSem': 'string',
              'WhatNextKurs': 'string',
              'WhereNext': 'string',
              'WhereNextSecOrd': 'string',
              'WhereNextSem': 'string',
              'WhereNextKurs': 'string',
              'WhenNext': 'string',
              'WhenNextSecOrd': 'string',
              'WhenNextSem': 'string',
              'WhenNextKurs': 'string',
              'semester': 'semester',
              'kurs': 'kurs',
              'WhenExam': 'string',
              'WhenExamSecOrd': 'string',
              'CoursesOn': 'string',
              'CoursesOnSecOrd': 'string',
              'CoursesLeft': 'string',
              'date': 'date'
              }

    preds2 = {'WhenIs': [['semester', 'WhenSemester']], #1st element is first ind needed, second is the resulting pred1
              'ClassesFor': [['semester', 'ClassesForSemester']],
              'WhatNextSecOrd': [['semester', 'WhatNextSem'], ['kurs', 'WhatNextKurs']],
              'WhereNextSecOrd': [['semester', 'WhereNextSem'], ['kurs', 'WhereNextKurs']],
              'WhenNextSecOrd': [['semester', 'WhenNextSem'], ['kurs', 'WhenNextKurs']],
              'WhenExamSecOrd': [['kurs', 'WhenExam']],
              'CoursesOnSecOrd': [['date', 'CoursesOn']]
              }

    converters = {'semester': lambda auth_string, string: get_relative_semester_name(string, *get_semesters(auth_string)),
                  'kurs': lambda auth_string, string: find_real_coursename(auth_string, string),
                  'date': lambda auth_string, string: str(parse_date(string))}

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

    domain = studip_domain(preds0, preds1, preds2, sorts, converters)

    ######################################### originaler fluginformation-kack ##########################################
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

    ######################################### elementares (anmelden) ###################################################

    domain.add_plan("!(studip)",
                   [Findout("?x.username(x)"),
                    Findout("?x.password(x)"),
                    Inform("Unfortunately, to have access to your StudIP-Files, I have to save the username and pw. The only thing I can do is to obfuscate the Username and PW to a Hex-string."),
                    ExecuteFunc(make_authstring, "?x.username(x)", "?x.password(x)"),
                    Inform("The Auth-string is: %s", ["com(auth_string)"]), #wenn inform 2 params hat und der zweite "bel" ist, zieht der die info aus dem believes.
                    ExecuteFunc(test_credentials, "?x.auth_string(x)")
                   ])

    #allow to change password/username -- command dafür ist "change" mit nem argument, aka username/pw

    ################################################# dateien ##########################################################

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

    ################################################# zeiten ###########################################################

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

    domain.add_plan("?x.y.WhenIs(y)(x)",
                    [ExecuteFunc(get_semester_inf, "?x.semester(x)", "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    ################################################# courses ##########################################################

    domain.add_plan("?x.y.ClassesFor(y)(x)",
                    [ExecuteFunc(get_my_courses, "?x.semester(x)", "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    ################################################# sessions #########################################################

    domain.add_plan("?x.WhatNext(x)",
                    [ExecuteFunc(partial(session_info, what="all"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhatNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(session_info, what="all"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(session_info, what="all"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.WhereNext(x)",
                    [ExecuteFunc(partial(session_info, what="where"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhereNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(session_info, what="where"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(session_info, what="where"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.WhenNext(x)",
                    [ExecuteFunc(partial(session_info, what="when"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhenNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(session_info, what="when"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(session_info, what="when"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.y.WhenExamSecOrd(y)(x)",
                    [ExecuteFunc(klausur, auth_string="?x.auth_string(x)", course_str="?x.kurs(x)")],
                    conditions=["com(auth_string)"])

    domain.add_plan("?x.y.CoursesOnSecOrd(y)(x)",
                    [ExecuteFunc(classes_on, auth_string="?x.auth_string(x)", date="?x.date(x)")],
                    conditions=["com(auth_string)"])

    domain.add_plan("?x.CoursesLeft(x)",
                    [ExecuteFunc(partial(classes_on, left=True), auth_string="?x.auth_string(x)")],
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
    grammar.addForm("Ask('?x.semester(x)')", "Which semester?")
    grammar.addForm("Ask('?x.kurs(x)')", "Which course?")

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