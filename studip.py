import os
import settings
from cfg_grammar import *
from ibis_types import *
import trindikit
import ibis_generals
import codecs
from singleUser_ibis import singleUser_download
import inspect
import functools
from studip_download import *
import time
import functools
from threading import Thread
import userDB
import importlib
import bothelper


############################################# decorators for executable rules ##########################################


class partial(functools.partial):
    def __repr__(self):
        return "functools.partial(%r, %s)" % (self.func,', '.join(repr(a) for a in self.args))
    @property
    def __name__(self):
        return "partial(%r)" % self.func.__name__


def executable_rule(function):
    argkeys, varargs, varkw, defaults = inspect.getargspec(function)
    argkeys = argkeys[1:] #remove the self for now
    replacekeys = [i for i in argkeys if i.isupper() and i != "DM"] #IS, NEXT_MOVES, etc ist uppercase and will be replaced
    usr = "DM" if "DM" in argkeys else None
    optionals = inspect.signature(function).parameters["optionals"].default if "optionals" in argkeys else None

    @functools.wraps(function)
    def wrappedfunc(*args, **kw):
        new_kw = dict((key, getattr(args[1], key, None)) for key in replacekeys) #args[1] ist der DM (der als parameter für update-rules speziell behandelt wird), hier werden alle gepacslockten daran gehängt
        new_kw = {**new_kw, **kw} #für die partials mit what
        if usr: new_kw["DM"] = args[0]
        try:
            if not new_kw["optionals"]: new_kw["optionals"] = optionals
        except: pass
        result = function(*args[1:], **new_kw)
        return result
    return wrappedfunc


def catchMoreThanOne(function):
    @functools.wraps(function)
    def wrappedfunc(*args, **kw):
        ibis = args[1]
        try:
            return function(*args, **kw)
        except MoreThan1Exception as e:
            possible_cands = e.args[0].split(",")[1:]
            what = e.args[0].split(",")[0]
            question = "?x." + what + "(x)"
            ibis.IS.shared.com.remove(what, silent=True)
            ibis.IS.private.bel.remove(what, silent=True)
            postponed_plan = ibis.IS.private.plan.pop()  # ersetzte es durch If(semester) []...
            if what == "semester":
                warning = State("You underspecified which course you mean! Do you mean " + kw["course_str"] + " in " + " or ".join(possible_cands) + "?")
            elif what == "filename":
                warning = State("You underspecified which file you mean! Do you mean " + kw["filename"] + " in " + " or ".join(["'"+i+"'" for i in possible_cands]) + "?")
            ibis.NEXT_MOVES.push(warning) #TODO - die kann man bestimmt zu telegram-links machen, sodass man beim draufklicken die direkt sendet!!!
            ibis.IS.private.plan.push(If(question, [postponed_plan]))
            ibis.IS.private.plan.push(Findout(question))
            return False
        return function(*args, **kw)
    return wrappedfunc


def catchNameAmbiguous(function):
    @functools.wraps(function)
    def wrappedfunc(*args, **kw):
        ibis = args[1]
        try:
            return function(*args, **kw)
        except NameAmbiguousException as e:
            possible_cands = e.args[0].split(",")[1:]
            what = e.args[0].split(",")[0]
            question = "?x." + what + "(x)"
            ibis.IS.shared.com.remove(what, silent=True)
            ibis.IS.private.bel.remove(what, silent=True)
            postponed_plan = ibis.IS.private.plan.pop()  # ersetzte es durch If(semester) []...
            if what == "filename":
                warning = State("There is no file with that name! Do you mean " + " or ".join(["'"+i+"'" for i in possible_cands]) + "?")
            ibis.NEXT_MOVES.push(warning)
            ibis.IS.private.plan.push(If(question, [postponed_plan]))
            ibis.IS.private.plan.push(Findout(question))
            return False
        return function(*args, **kw)
    return wrappedfunc

########################################################################################################################
#################################################### APICONNECTOR ######################################################
########################################################################################################################

#TODO - die könnten generateMove nutzen
#generateMove hat: def generateMove(self, move): try- prop.pred.content == "price": return ... except pass return super(TravelGrammar, self).generateMove(move)

class Studip_Connector(ibis_generals.API_Connector):

    def answerQuestion(self, question, context):
        raise NotImplementedError #TODO - implement (ist wie das consultDB)


    @executable_rule
    def make_authstring(self, username, pw, IS):
        auth_bytes = ('%s:%s' % (username, pw)).encode('ascii')
        auth_string = codecs.encode(auth_bytes, 'base64').strip()
        return Prop(Pred1("auth_string"), Ind(auth_string), True), IS.shared.com.add


    @executable_rule
    def is_VLZeit(self, auth_string, NEXT_MOVES):
        all_semesters = load("semesters", auth_string)['semesters']
        this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
        currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
        return Answer(YesNo(currently_seminars)), NEXT_MOVES.push


    @executable_rule
    def semesterdays(self, auth_string, what, IS):
        all_semesters = load("semesters", auth_string)['semesters']
        this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
        next_semester = [all_semesters[i+1]['title'] for i in range(len(all_semesters)) if all_semesters[i]['title'] == this_semester][0]
        currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
        if what == "db":
            if currently_seminars:
                return Prop(Pred1("DaysBreak"), Ind(str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), True, expires=round(time.time()) + 3600), IS.private.bel.add
            else:
                return Prop(Pred1("DaysBreak"), Ind("The break is right now!"), True, expires=round(time.time())+3600), IS.private.bel.add
        elif what == "wb":
            return Prop(Pred1("WhenBreak"), Ind("In "+str(get_semester_info(all_semesters, next_semester))), True, expires=round(time.time())+3600*240), IS.private.bel.add
        elif what == "wl":
            return Prop(Pred1("WhenLectures"), Ind(str(get_semester_info(all_semesters, next_semester))), True, expires=round(time.time()) + 3600 * 240), IS.private.bel.add
        else: #what == "dl"
            if not currently_seminars:
                return Prop(Pred1("DaysLectures"), Ind("In "+str(many_days(all_semesters, this_semester, next_semester, currently_seminars))+" days"), True, expires=round(time.time())+3600), IS.private.bel.add
            else:
                return Prop(Pred1("DaysLectures"), Ind("There are lectures right now!"), True, expires=round(time.time())+3600), IS.private.bel.add


    @executable_rule
    def get_semester_inf(self, sem_name, auth_string, IS):
        all_semesters = load("semesters", auth_string)['semesters']
        result = get_semester_info(all_semesters, sem_name)
        IS.shared.com.remove("semester", silent=True)
        return Prop(Pred1("WhenSemester", sem_name), Ind(result), True, expires=round(time.time())+3600*24), IS.private.bel.add


    @executable_rule
    def get_my_courses(self, sem_name, auth_string, IS):
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
    def session_info(self, auth_string, what, IS, semester=None, one_course_str=None):
        if not self.getContext(IS, "timerel_courses", "bel")[0]:
            timerel_courses = get_timerelevant_courses(auth_string)
            IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
        timerel_courses = self.getContext(IS, "timerel_courses", "bel")[1] #danach ist es save da
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
    def klausur(self, auth_string, course_str, IS, semester=None):
        if not self.getContext(IS, "timerel_courses", "bel")[0]:
            timerel_courses = get_timerelevant_courses(auth_string)
            IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
        timerel_courses = self.getContext(IS, "timerel_courses", "bel")[1] #danach ist es save da
        txt = find_klausurtermin(auth_string, course_str, timerel_courses=timerel_courses)
        return Prop(Pred1("WhenExam", course_str), Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add


    @executable_rule
    def test_credentials(self, auth_string, NEXT_MOVES):
        try:
            load_userid(auth_string, silent=False)
            return True
        except AuthentificationError:
            return State("These credentials are wrong!\nYou can re-enter them by sending /start"), NEXT_MOVES.push


    @executable_rule
    def classes_on(self, auth_string, IS, date=None, left=False):
        assert date or left
        if not self.getContext(IS, "timerel_courses", "bel")[0]:
            timerel_courses = get_timerelevant_courses(auth_string)
            IS.private.bel.add(Knowledge(Pred1("timerel_courses"), timerel_courses, True, expires=round(time.time()) + 3600 * 72))
        timerel_courses = self.getContext(IS, "timerel_courses", "bel")[1] #danach ist es save da
        if not left:
            txt = get_courses_for_day(auth_string, date, None, timerel_courses)
            return Prop(Pred1("CoursesOn", date), Ind(txt), True, expires=round(time.time()) + 3600 * 24), IS.private.bel.add
        else:
            txt = get_courses_for_day(auth_string, parse_date("today"), None, timerel_courses, round(time.time()))
            return Prop(Pred1("CoursesLeft", date), Ind(txt), True, expires=round(time.time()) + 60), IS.private.bel.add


    @catchMoreThanOne
    @executable_rule
    def show_files(self, auth_string, course_str, IS, optionals={"semester": None}):
        if optionals["semester"] != None: optionals["semester"] = optionals["semester"].content[1].content #TODO eine unpack-funktion, die bei "None" gar nichts macht und je nach typ richtig entpackt
        file_list = list_course_files(auth_string, course_str, semester=optionals["semester"])
        return Prop(Pred1("ListFiles", course_str), Ind(file_list), True, expires=round(time.time()) + 3600*0.5), IS.private.bel.add, ["course_str", "semester"]


    @catchNameAmbiguous
    @catchMoreThanOne
    @executable_rule
    def download_a_file(self, auth_string, course_str, filename, IS, DM, optionals={"semester": None}):
        """"Download a file from Codierungstheorie und Kryptographie"""
        if optionals["semester"] != None: optionals["semester"] = optionals["semester"].content[1].content
        file = download_studip_file(auth_string, course_str, filename, semester=optionals["semester"])
        if settings.MULTIUSER:
            chat_id = userDB.get_user_by_ID(DM.user_id)[0].chat_id
            # bothelper.send_file(chat_id, file["filename"], download(auth_string, file["document_id"]))
            thread = Thread(target=bothelper.send_file, args=(chat_id, file["filename"], download(auth_string, file["document_id"])))
            thread.start()
        else:
            singleUser_download(file["filename"], download(auth_string, file["document_id"]))

        return Prop(Pred1("DownloadFile", course_str), Ind("The file you requested is on its way!"), True, expires=round(time.time()) + 30), IS.private.bel.add, ["course_str", "semester", "filename"]


def create_studip_APIConnector():
    return Studip_Connector()

########################################################################################################################
######################################################## GRAMMAR #######################################################
########################################################################################################################

class StudIP_grammar(CFG_Grammar):

    def interpret(self, input, IS, DOMAIN, NEXT_MOVES, APICONNECTOR, anyString=False, moves=None):
        res = super().interpret(input, IS, DOMAIN, NEXT_MOVES, APICONNECTOR, anyString=anyString, moves=moves)
        if res:
            return res
        else: #bspw empty set
            if any(isinstance(move.content, Question) and move.content.content.content == 'semester' for move in moves):
                try:
                    tmp = APICONNECTOR.getContext(IS, "auth_string")
                    if tmp[0]: #dann kann "this" und "next" nachgucken
                        this, next = get_semesters(tmp[1].content)
                        return Answer(ShortAns(Ind(get_relative_semester_name(input, this, next)), True))
                    else:
                        return Answer(ShortAns(Ind(get_semester_name(input)), True))
                except ValueError:
                    pass
            elif any(isinstance(move.content, Question) and move.content.content.content == 'kurs' for move in moves):
                try:
                    tmp = APICONNECTOR.getContext(IS, "auth_string")
                    if tmp[0]: #dann kann "this" und "next" nachgucken
                        name = find_real_coursename(tmp[1].content, input)
                        if name:
                            return Answer(ShortAns(Ind(name), True))
                except ValueError:
                    pass


def create_studip_grammar(lan="en"):
    #generation-grammar
    grammarpath = os.path.join(settings.PATH, "grammars")
    genGrammar = importlib.import_module(".studip_gen_"+lan, "grammars").StudIP_gen_grammar
    # genGrammar = __import__(os.path.join(grammarpath, "studip_gen_"+lan+".py")).StudIP_gen_grammar
    class combinedGrammar(StudIP_grammar, genGrammar):
        pass
    grammar = combinedGrammar()
    grammar.addForms()
    #understanding-grammar
    cfgrammarpath = os.path.join(grammarpath, "studip"+"_"+lan+".fcfg")
    grammar.loadGrammar(cfgrammarpath)
    return grammar


########################################################################################################################
######################################################## DOMAIN ########################################################
########################################################################################################################


class Studip_domain(ibis_generals.Domain):

    def get_sort_from_ind(self, answer, *args, **kwargs):
        res = self.inds.get(answer)
        if res: return res
        if "SS" in answer and any(str(i) in answer for i in range(2000, 2050)) or "WS" in answer and any(str(i)+'/'+str(i-1999).zfill(2) in answer for i in range(2000, 2050)):
            return "semester"
        if "kurs" in kwargs and answer in kwargs["kurs"]:
            return "kurs"
        if answer[0] == "d" and all(ch.isnumeric() for ch in answer[1:]):
            return "date"

    def collect_sort_info(self, forwhat, APICONNECTOR, IS=None):
        try:
            if forwhat == "kurs":
                auth_string = APICONNECTOR.getContext(IS, "auth_string")
                if auth_string[0]:
                    auth_string = auth_string[1].content
                    return {"kurs": get_courses(auth_string, semester="")[0]}
        except:
            pass
        return None


def create_studip_domain(APICONNECTOR):
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
              'date': 'date',
              'ListFilesSecOrd': 'string',
              'ListFiles': 'string',
              'DownloadFileSecOrd': 'string',
              'DownloadFile': 'string'  #TODO - dass man nicht mehr das ohne sec-ord angeben muss bei SecOrdQs!!
              }

    #TODO - das wird higher-order-pred, wo das resultat auch ein weiteres HOPred sein kann!
    preds2 = {'WhenIs': [['semester', 'WhenSemester']], #1st element is first ind needed, second is the resulting pred1
              'ClassesFor': [['semester', 'ClassesForSemester']],
              'WhatNextSecOrd': [['semester', 'WhatNextSem'], ['kurs', 'WhatNextKurs']],
              'WhereNextSecOrd': [['semester', 'WhereNextSem'], ['kurs', 'WhereNextKurs']],
              'WhenNextSecOrd': [['semester', 'WhenNextSem'], ['kurs', 'WhenNextKurs']],
              'WhenExamSecOrd': [['kurs', 'WhenExam']],
              'CoursesOnSecOrd': [['date', 'CoursesOn']],
              'ListFilesSecOrd': [['kurs', 'ListFiles']],
              'DownloadFileSecOrd': [['kurs', 'DownloadFile']]
              }

    # TODO - einig werden ob die converters bei der grammar oder beim funktionsaufruf genutzt werden!

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

    domain = Studip_domain(preds0, preds1, preds2, sorts, converters)

    ######################################### elementares (anmelden) ###################################################

    domain.add_plan("!(studip)",
                   [Findout("?x.username(x)"),
                    Findout("?x.password(x)"),
                    Inform("Unfortunately, to have access to your StudIP-Files, I have to save the username and pw. The only thing I can do is to obfuscate the Username and PW to a Hex-string."),
                    ExecuteFunc(APICONNECTOR.make_authstring, "?x.username(x)", "?x.password(x)"),
                    Inform("The Auth-string is: %s", ["com(auth_string)"]), #wenn inform 2 params hat und der zweite "bel" ist, zieht der die info aus dem believes.
                    ExecuteFunc(APICONNECTOR.test_credentials, "?x.auth_string(x)")
                   ])

    #allow to change password/username -- command dafür ist "change" mit nem argument, aka username/pw

    ################################################# zeiten ###########################################################

    domain.add_plan("!(Vorlesungszeit)",
                    [ExecuteFunc(APICONNECTOR.is_VLZeit, "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])


    domain.add_plan("?x.DaysLectures(x)",
                    [ExecuteFunc(partial(APICONNECTOR.semesterdays, what="dl"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.WhenLectures(x)",
                    [ExecuteFunc(partial(APICONNECTOR.semesterdays, what="wl"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.DaysBreak(x)",
                    [ExecuteFunc(partial(APICONNECTOR.semesterdays, what="db"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.WhenBreak(x)",
                    [ExecuteFunc(partial(APICONNECTOR.semesterdays, what="wb"), "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    domain.add_plan("?x.y.WhenIs(y)(x)",
                    [ExecuteFunc(APICONNECTOR.get_semester_inf, "?x.semester(x)", "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    ################################################# courses ##########################################################

    domain.add_plan("?x.y.ClassesFor(y)(x)",
                    [ExecuteFunc(APICONNECTOR.get_my_courses, "?x.semester(x)", "?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    ################################################# sessions #########################################################

    domain.add_plan("?x.WhatNext(x)",
                    [ExecuteFunc(partial(APICONNECTOR.session_info, what="all"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhatNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="all"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="all"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.WhereNext(x)",
                    [ExecuteFunc(partial(APICONNECTOR.session_info, what="where"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhereNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="where"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="where"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.WhenNext(x)",
                    [ExecuteFunc(partial(APICONNECTOR.session_info, what="when"), "?x.auth_string(x)")],
                    conditions = ["com(auth_string)"])

    domain.add_plan("?x.y.WhenNextSecOrd(y)(x)",
                    [If("?x.semester(x)",
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="when"), semester="?x.semester(x)", auth_string="?x.auth_string(x)")],
                        [ExecuteFunc(partial(APICONNECTOR.session_info, what="when"), one_course_str="?x.kurs(x)", auth_string="?x.auth_string(x)")])],
                        conditions=["com(auth_string)"])

    domain.add_plan("?x.y.WhenExamSecOrd(y)(x)",
                    [ExecuteFunc(APICONNECTOR.klausur, auth_string="?x.auth_string(x)", course_str="?x.kurs(x)")],
                    conditions=["com(auth_string)"])

    domain.add_plan("?x.y.CoursesOnSecOrd(y)(x)",
                    [ExecuteFunc(APICONNECTOR.classes_on, auth_string="?x.auth_string(x)", date="?x.date(x)")],
                    conditions=["com(auth_string)"])

    domain.add_plan("?x.CoursesLeft(x)",
                    [ExecuteFunc(partial(APICONNECTOR.classes_on, left=True), auth_string="?x.auth_string(x)")],
                    conditions=["com(auth_string)"])

    ################################################# dateien (new) ####################################################

    domain.add_plan("?x.y.ListFilesSecOrd(y)(x)",
                    [ExecuteFunc(APICONNECTOR.show_files, auth_string="?x.auth_string(x)", course_str="?x.kurs(x)", optionals={"semester": "?x.semester(x)"})],
                    conditions=["com(auth_string)"])


    domain.add_plan("?x.y.DownloadFileSecOrd(y)(x)",
                    [If("?x.kurs(x)",
                        [Findout("?x.filename(x)"),
                         ExecuteFunc(APICONNECTOR.download_a_file, auth_string="?x.auth_string(x)", course_str="?x.kurs(x)", filename="?x.filename(x)", optionals={"semester": "?x.semester(x)"})],
                        [Inform("The function was re-structured! You need to say 'Download from <course>'!")])],
                    conditions=["com(auth_string)"])


    return domain

