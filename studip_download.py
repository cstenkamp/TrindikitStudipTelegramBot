BASE_URL = 'https://studip.uni-osnabrueck.de/plugins.php/restipplugin/api/'

import time
import datetime
import calendar
from dateutil import parser
import pytz
from copy import deepcopy
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import sys
from singleUser_ibis import singleUser_download

########################################################################################################################
#################################### von der api bereitgestellte sinnvolle routen ######################################
########################################################################################################################
#
# def get_courses(user, auth_string, semester=None):
#     pass #GET /user/:user_id/courses

def get_semesters(user, auth_string):
    pass #route /semesters


def get_news(user, auth_string):
    pass #GET /user/:user_id/news

def get_schedule(user, auth_string):
    pass #GET /user/:user_id/schedule und GET /user/:user_id/schedule/:semester_id

def get_zeitplan(user, auth_string):
    pass #route  /user/:user_id/schedule/:semester_id

def get_course(user, id, auth_string):
    pass #GET /course/:course_id

def get_course_files(user, id, auth_string):
    pass #GET /course/:course_id/files

def get_all_current_news(user, auth_string):
    pass #für jeden Kurs: GET /course/:course_id/news

def get_file(file_id, auth_string):
    pass #GET /file/:file_id für metadaten und GET /file/:file_id/content für content

def create_file(adsf):
    pass #POST /file/:folder_id

########################################################################################################################
############################################ generell benötigte funktionen #############################################
########################################################################################################################


class AuthentificationError(Exception):
    pass


def load(path, auth_string, check_credentials=False):
    return json.loads(download_file(path, auth_string, check_credentials).decode('utf8'))


def download_file(path, auth_string, check_credentials=False):
    r = Request(BASE_URL + path)
    r.add_header('Authorization', b'Basic %s' % auth_string)

    i = 0
    while True: #for some reason, I sometimes get random "not authorized" errors
        try:
            f = urlopen(r)
            return f.read()
        except HTTPError as e:
            if e.code == 401:
                if check_credentials:
                    print('not authorized -- are password and username correct? \nif yes: simply try again', file=sys.stderr)
                    raise AuthentificationError
                i += 1 #otherwise retry
                if i > 100:
                    raise
            else:
                raise


def download(auth_string, fid):
    try:
        content = download_file('documents/%s/download' % fid, auth_string)
        return content
    except HTTPError as e:
        if e.code == 403:
            raise Exception("Could not download!")


def load_userid(auth_string, silent=True):
    try:
        userid = load('user', auth_string, check_credentials=True)['user']['user_id']
    except AuthentificationError:
        print("Credentials wrong!")
        if not silent:
            raise AuthentificationError
    return userid


########################################################################################################################
################################################## Semester & Zeiten ###################################################
########################################################################################################################

def get(fromwhat, name):
    try: return [i for i in fromwhat if i['title'] == name][0]
    except: pass
    try: return [i for i in fromwhat if i['name'] == name][0]
    except: pass
    try: return [i for i in fromwhat if i == name][0]
    except: pass
    return []


def semesters_with_courses(userid, auth_string):
    courses = load("/user/%s/courses" % userid, auth_string)
    user_semesters = list(set(course['semester_name'] for course in courses['courses']['study']+courses['courses']['work']))
    all_semesters = load("semesters", auth_string)['semesters']
    semester_dict = {elem['title']:elem['semester_id'] for elem in all_semesters if elem['title'] in user_semesters}
    return semester_dict


def many_days(semesters, this, next, curr_sems):
    if curr_sems:
        secs = int(get(semesters,this)['seminars_end']) - int(time.time())
        return secs//60//60//24+1
    else:
        secs = int(get(semesters,next)['seminars_begin']) - int(time.time())
        return secs//60//60//24+1


def get_semester_name(string):
    result = ""
    string = string.replace("/", " / ").replace("-", " - ").replace("'", "")
    string = re.sub(r"([a-zA-Z]+)([0-9]+)", r"\1 \2", string) #trennt text von zahlen
    string = re.sub(r"([0-9]+)([a-zA-Z]+)", r"\1 \2", string) #trennt text von zahlen
    strings = [s.lower() for s in string.split() if not s.isdigit() and s != "/"]
    if "ws" in strings or "winter" in strings  or "wintersemester" in strings or "wise" in strings:
        result = "WS "
    elif "ss" in strings or "sommer" in strings or "summer" in strings or "sommersemester" in strings or "summersemester" in strings  or "sose" in strings or "suse" in strings:
        result = "SS "
    else:
        raise ValueError("Not Possible to pick Semester! Indicate if summer or winter!")
    numbers = [int(s) for s in string.split() if s.isdigit()]
    for i in range(len(numbers)):
        if len(str(numbers[i])) == 8:
            numbers.append(int(str(numbers[i])[4:]))
            numbers[i] = int(str(numbers[i])[:4])
        elif len(str(numbers[i])) == 4 and int(str(numbers[i])[:2]) == int(str(numbers[i])[2:])-1:
            numbers.append(int(str(numbers[i])[2:]))
            numbers[i] = int(str(numbers[i])[:2])
        elif len(str(numbers[i])) == 6 and int(str(numbers[i])[:2]) == 20:
            numbers.append(int(str(numbers[i])[4:]))
            numbers[i] = int(str(numbers[i])[:4])
    for i in range(len(numbers)):
        if numbers[i] > 2000:
            numbers[i] -= 2000
    if len(numbers) < 1 or not (1 <= min(numbers) <= 50):
        raise ValueError("Not Possible to pick Semester! Indicate a valid year!")
    year = min(numbers)
    if result == "WS ":
        result += str(year+2000)+"/"+str(year+1)
    else:
        result += str(year+2000)
    return result


def get_relative_semester_name(string, this, next):
    if string in ["this semester", "current semester", "this_semester"]:
        return this
    elif string in ["next semester", "upcoming semester", "the semester after this", "next_semester"]:
        return next
    else:
        return get_semester_name(string)


def get_semester_info(all_semesters, semester):
    s = get(all_semesters, semester)
    return "Semester: %s \nBegin of Semester: %s \nBegin of Lectures: %s \nEnd of Lectures: %s \nEnd of Semester: %s" \
            % (s['title'], s['begin_iso'][:10], s['seminars_begin_iso'][:10], s['seminars_end_iso'][:10], s['end_iso'][:10] )


def get_semesters(auth_string):
    all_semesters = load("semesters", auth_string)['semesters']
    this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
    next_semester = [all_semesters[i+1]['title'] for i in range(len(all_semesters)) if all_semesters[i]['title'] == this_semester][0]
    return this_semester, next_semester


def get_semester_before(auth_string, semester):
    all_semesters = load("semesters", auth_string)['semesters']
    asked_semester = [all_semesters[i-1]['title'] for i in range(1, len(all_semesters)) if all_semesters[i]['title'] == semester][0]
    return asked_semester


def debug_print_semesterstuff(auth_string, userid):
    print(semesters_with_courses(userid, auth_string))
    all_semesters = load("semesters", auth_string)['semesters']
    print(all_semesters)
    this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
    next_semester = [all_semesters[i+1]['title'] for i in range(len(all_semesters)) if all_semesters[i]['title'] == this_semester][0]
    currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
    print(many_days(all_semesters, this_semester, next_semester, currently_seminars))
    print(get_semester_info(all_semesters, 'SS 2018'))


########################################################################################################################
############################################ Kurse/Sessions & Zeiten ###################################################
########################################################################################################################

def get_user_courses(auth_string, semester=None):
    userid = load_userid(auth_string)
    courses = load("/user/%s/courses" % userid, auth_string)
    if semester:
        all_semesters = load("semesters", auth_string)['semesters']
        semesterid = get(all_semesters, get_semester_name(semester))["semester_id"]
    s_courses = courses['courses']['study'] or []
    try:
        w_courses = courses['courses']['work'] or []
    except KeyError:
        w_courses = []
    w_courses.extend([i for i in s_courses if i["perms"] not in ["autor", "user"]])
    s_courses = [i for i in s_courses if i["perms"] in ["autor", "user"]]
    if semester:
        all_semesters = load("semesters", auth_string)['semesters']
        semesterid = get(all_semesters, get_semester_name(semester))["semester_id"]
        s_courses = [i for i in s_courses if i["semester_id"] == semesterid]
        w_courses = [i for i in w_courses if i["semester_id"] == semesterid]
    return w_courses or [], s_courses or []


def get_alltimes(auth_string, semester=None, timerel_courses=None, one_course=None):
    if not one_course:
        if not (timerel_courses and not semester): #wenn nicht timerelevant-courses vom speicherstand genutzt wurde
            if semester:
                w_courses, s_courses = get_user_courses(auth_string, semester)
            else:
                w_courses, s_courses = get_user_courses(auth_string)
            timerel_courses = w_courses + s_courses
    else:
        timerel_courses = one_course if isinstance(one_course, list) else [one_course]  #wenn one_course gesetzt ist soll man nur infos VON KURS XYZ suchen

    curr_time = round(time.time())
    all_times = {}
    for course in timerel_courses:
        kurs = course["course_id"]
        kursevents = load("courses/%s/events" % kurs, auth_string)
        if all(int(event["start"]) < curr_time or event["canceled"] for event in kursevents["events"]): continue
        next_event_time = min(int(event["start"]) for event in kursevents["events"] if int(event["start"]) >= curr_time and not event["canceled"])
        next_event = [event for event in kursevents["events"] if event["start"] == str(next_event_time)][0]
        all_times[course["name"]] = next_event
    return all_times, timerel_courses


def get_timerelevant_courses(auth_string):
    current_events, all_courses = get_alltimes(auth_string)
    curr_ev_ids = [ev['course_id'] for ev in current_events.values()]
    current_courses = [course for course in all_courses if course['course_id'] in curr_ev_ids]
    return current_courses


def get_session_info(what, auth_string, semester=None, timerel_courses=None, one_course_str=None):
    one_course = get_course_by_name(auth_string, one_course_str, semester=semester, supress=True) if one_course_str else None  #throwed ggf ne exception die das dialogsystem hoffnetlich fängt und dann semester "nachliefert"

    all_times = get_alltimes(auth_string, semester, timerel_courses, one_course)[0]
    curr_time = round(time.time())

    if len(all_times) == 0:
        return "You don't have any upcoming sessions"+(" at all" if not one_course_str and not semester else " for "+(one_course if one_course else semester))+"!"
    next_time = min(int(event["start"]) for event in all_times.values())
    next_ev = [(kurs, event) for kurs, event in all_times.items() if event["start"] == str(next_time)][0] # -> dict(Kursname: Kurs)
    time_starts = next_ev[1]["iso_start"][:next_ev[1]["iso_start"].find("+")].replace("T", " at ")
    time_starts = calendar.day_abbr[datetime.datetime.fromtimestamp(int(next_ev[1]["start"])).weekday()] + ", " + time_starts # -> Mon, 2018-03-19 at 09:00:00
    starts_in = str(datetime.timedelta(seconds=int(next_ev[1]["start"]) - curr_time)) # -> 5 days, 8:19:21
    length = str(datetime.timedelta(seconds=int(next_ev[1]["end"]) - int(next_ev[1]["start"])))[:-3] # -> 9:00

    if what == "all":
        if one_course:
            txt = "Your next session of "+next_ev[0]+" is a "+next_ev[1]["categories"]+". It starts in "+starts_in+" hours ("+time_starts+") and takes "+length+" hours. It is in room "+next_ev[1]["room"]+"."
        elif semester:
            txt = "Your next session of "+semester+" is a "+next_ev[1]["categories"]+" of '"+next_ev[0]+"'. It starts in "+starts_in+" hours ("+time_starts+") and takes "+length+" hours. It is in room "+next_ev[1]["room"]+"."
        else:
            txt = "Your next session is a "+next_ev[1]["categories"]+" of '"+next_ev[0]+"'. It starts in "+starts_in+" hours ("+time_starts+") and takes "+length+" hours. It is in room "+next_ev[1]["room"]+"."
        if next_ev[1]["title"]: txt += "\nIts title is '" + next_ev[1]["title"] + "'."
        if next_ev[1]["description"]: txt += "\nIts description is '" + next_ev[1]["description"] + "'."
    elif what == "where":
        txt = "room " + next_ev[1]["room"]
    elif what == "when":
        txt = time_starts + " (in "+starts_in+" hours)"
    elif what == "what":
        txt = next_ev[0]

    return txt


def easify_coursename(name):
    i = name.lower()
    i = i.replace("&", "und")
    i = re.sub(r"\bi\b", "eins", i)
    i = re.sub(r"\bii\b", "zwei", i)
    i = re.sub(r"\biii\b", "drei", i)
    i = re.sub(r"\biv\b", "vier", i)
    i = re.sub(r"\bv\b", "fünf", i)
    i = re.sub(r"\bvi\b", "sechs", i)
    i = re.sub(r"\bvii\b", "sieben", i)
    i = re.sub(r"\bviii\b", "acht", i)
    i = re.sub(r"\b1\b", "eins", i)
    i = re.sub(r"\b2\b", "zwei", i)
    i = re.sub(r"\b3\b", "drei", i)
    i = re.sub(r"\b4\b", "vier", i)
    i = re.sub(r"\b5\b", "fünf", i)
    i = re.sub(r"\b6\b", "sechs", i)
    i = re.sub(r"\b7\b", "sieben", i)
    i = re.sub(r"\b8\b", "acht", i)
    i = i.replace("(Lecture + Tutorial)", "")
    i = i.replace("(Lecture + Practice)", "")
    j = re.sub("\(.*?\)", "", i).replace("(", "").replace(")", "")
    while j[0] == " ": j = j[:1]
    while j[-1] == " ": j = j[:-1]
    j = j.replace(" für studierende der cognitive science und für studenten mit nebenfach biologie", "") #hachja jeserich
    k = re.sub("[^a-zA-Z0-9 äöüß]", "", j)
    k = re.sub(' +', ' ', k)
    while k[0] == " ": k = k[:1]
    while k[-1] == " ": k = k[:-1]
    return i,j,k


def get_courses(auth_string, semester=""):
    w_courses, s_courses = get_user_courses(auth_string, semester=semester)
    courseinfo = [(course["name"], course["semester_name"], course['course_id'], course in w_courses) for course in w_courses+s_courses]
    coursenames = [c[0] for c in courseinfo]
    coursenames2 = [(name, *easify_coursename(name)) for name in coursenames]
    return coursenames, coursenames2


def find_real_coursename(auth_string, name, semester=""):
    coursenames, coursenames2 = get_courses(auth_string, semester="")
    results = []
    for i in coursenames:
        if i == name:
            return i
    #         results.append(i)
    # if len(results) >= 1:
    #     return results[0] if len(results) == 1 else results
    #else, falls es keinen perfekten match gab:
    for i in coursenames2:
        if any(tryit in i for tryit in easify_coursename(name)): #probiert die varianten von name jeweils für varianten von coursenames2 aus
            return i[0]
    #         results.append(i[0])
    # return results[0] if len(results) == 1 else (results or None)
    return None


class MoreThan1Exception(Exception):
    pass

class MoreThan1SemesterException(MoreThan1Exception):
    pass


def get_course_by_name(auth_string, name, semester=None, supress=False):
    w_courses, s_courses = get_user_courses(auth_string, semester=semester)
    coursename = find_real_coursename(auth_string, name)
    res = [i for i in w_courses + s_courses if i['name'] == coursename]
    if len(res) > 1:
        if not supress: raise MoreThan1SemesterException("semester,"+",".join(i["semester_name"] for i in res))
        else: return res
    elif len(res) == 1:
        return res[0]
    else:
        return


def find_klausurtermin(auth_string, course_str, semester=None, timerel_courses=None):
    try:
        one_course = get_course_by_name(auth_string, course_str, semester=semester, supress=False)
    except MoreThan1SemesterException:
        sem = get_semesters(auth_string)[0]
        for i in range(10):
            try:
                one_course = get_course_by_name(auth_string, course_str, semester=sem, supress=False)
                break
            except MoreThan1SemesterException:
                sem = get_semester_before(auth_string, sem)

    all_times = get_alltimes(auth_string, semester, timerel_courses, one_course)[0]
    curr_time = round(time.time())
    try:
        next_time = min(int(event["start"]) for event in all_times.values())
    except:
        return "There are no future events at all for that class!"
    next_ev = [event for event in all_times.values() if event["start"] >= str(next_time)]
    Klausur = None
    Nachklausur = None
    for i in next_ev:
        if i["categories"] == "Klausur":
            Klausur = i
        if i["categories"] == "Nachklausur":
            Nachklausur = i

    if Klausur == Nachklausur == None:
        return "Unfortunately, there is no information about exams for this course on Stud.IP!"

    txt = ""
    for curr in [Klausur, Nachklausur]:
        if curr:
            time_starts = curr["iso_start"][:curr["iso_start"].find("+")].replace("T", " at ")
            time_starts = calendar.day_abbr[datetime.datetime.fromtimestamp(int(next_ev[1]["start"])).weekday()] + ", " + time_starts
            starts_in = str(datetime.timedelta(seconds=int(curr["start"]) - curr_time))[:-3]
            length = str(datetime.timedelta(seconds=int(curr["end"]) - int(curr["start"])))[:-3]
            txt += "The "+("exam" if curr == Klausur else "make-up exam")+" is in "+starts_in+" hours ("+time_starts+", in room "+curr["room"]+"). It takes "+length+" hours.\n"
    return txt[:-1]


class DateAmbiguousException(Exception):
    pass


def parse_date(datestr, asInt=True):
    difference = 0
    datestr = datestr.lower()
    orig_str = deepcopy(datestr)
    datestr = datestr.replace("um", "at")
    datestr = datestr.replace("am", "").replace("sstag", "samstag")
    if datestr in ["heute", "today"]:
        datestr = round(time.time())
    if datestr in ["tomorrow", "morgen"]:
        datestr = round(time.time())+3600*24
    if datestr in ["the day after tomorrow", "day after tomorrow", "übermorgen"]:
        datestr = round(time.time())+3600*48
    if datestr in ["überübermorgen", "über-übermorgen", "über-über-morgen"]:
        datestr = round(time.time())+3600*72
    if datestr in ["gestern", "yesterday"]:
        datestr = round(time.time())-3600*24
    if datestr in ["vorgestern", "the day before yesterday", "day before yesterday"]:
        datestr = round(time.time())-3600*48
    if not isinstance(datestr, (int, float)):
        datestr = datestr.replace("january", "01").replace("januar", "01").replace("jan", "01")
        datestr = datestr.replace("february", "02").replace("februar", "02").replace("feb", "02")
        datestr = datestr.replace("march", "03").replace("märz", "03").replace("mrz", "03").replace("mar", "03")
        datestr = datestr.replace("april", "04").replace("april", "04").replace("apr", "04")
        datestr = datestr.replace("may", "05").replace("mai", "05")
        datestr = datestr.replace("june", "06").replace("juni", "06").replace("jun", "06")
        datestr = datestr.replace("july", "07").replace("juli", "07").replace("jul", "07")
        datestr = datestr.replace("august", "08").replace("aug", "08")
        datestr = datestr.replace("september", "09").replace("sep", "09")
        datestr = datestr.replace("october", "10").replace("oktober", "10").replace("oct", "10").replace("okt", "10")
        datestr = datestr.replace("november", "11").replace("nov", "11")
        datestr = datestr.replace("december", "12").replace("dezember", "12").replace("dec", "12").replace("dez", "12")
        datestr = datestr.replace("montag", "monday").replace("dienstag", "tuesday").replace("mittwoch", "wednesday")
        datestr = datestr.replace("donnerstag", "thursday").replace("freitag", "friday").replace("samstag", "saturday").replace("sonntag", "sunday")
        datestr = datestr.replace("nächste woche", "next week")
        datestr = datestr.replace("next week", "next_week")
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        tmpstr = datestr.split(" ")
        if len(tmpstr) > 1:
            datestr = [i for i in tmpstr if i in weekdays][0]
            if datestr:
                if any(i in ["last", "letzter", "letzten"] for i in tmpstr):
                    difference += -3600*24*7
                if any(i in ["next", "nächster", "nächsten", "kommender", "kommenden"] for i in tmpstr):
                    pass
                    # if datetime.datetime.fromtimestamp(time.time()).weekday() <= weekdays.index(datestr):
                    #     difference = +3600*24*7
                if weekdays.index(datestr) == datetime.datetime.fromtimestamp(time.time()).weekday() and any(i in ["next", "nächster", "nächsten", "kommender", "kommenden"] for i in tmpstr):
                    difference += +3600*24*7
                if any(i in ["last", "letzter", "letzten"] for i in tmpstr):
                    if datetime.datetime.fromtimestamp(time.time()).weekday() <= weekdays.index(datestr):
                        difference += -3600*24*7
                if any(i in ["übernächster", "übernächsten"] for i in tmpstr):
                    if datetime.datetime.fromtimestamp(time.time()).weekday() == weekdays.index(datestr):
                        difference += +3600*24*14
                    else:
                        difference += +3600*24*7
                if any(i in ["next_week"] for i in tmpstr):
                    if datetime.datetime.fromtimestamp(time.time()).weekday() <= weekdays.index(datestr):
                        difference += +3600 * 24 * 7

    if isinstance(datestr, (int, float)) and datestr > 946688461:
        datestr = str(datetime.datetime.fromtimestamp(round(datestr)))

    datestr = re.sub(' +',' ',datestr)
    unixtime = int(parser.parse(str(datestr)).date().strftime("%s"))+(3600 if not is_dst("Europe/Berlin") else 0)
    unixtime += difference

    if orig_str == calendar.day_name[datetime.datetime.fromtimestamp(time.time()).weekday()].lower():
        raise DateAmbiguousException("Do you mean to say this or next "+datestr+"?")

    if asInt:
        return "d"+str(int(parser.parse(str(datestr)).date().strftime("%s"))+(3600 if not is_dst("Europe/Berlin") else 0))
    return datetime.datetime.fromtimestamp(unixtime).date()


def is_dst(zonename):
    tz = pytz.timezone(zonename)
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now.astimezone(tz).dst() != datetime.timedelta(0)


def get_courses_for_day(auth_string, day, semester=None, timerel_courses=None, aftertime=None):
    if isinstance(day, str):
        if day[0] == "d": day = day[1:]
        day = int(day)
    if aftertime: aftertime -= 60*16
    if not (timerel_courses and not semester): #wenn nicht timerelevant-courses vom speicherstand genutzt wurde
        if semester:
            w_courses, s_courses = get_user_courses(auth_string, semester)
        else:
            w_courses, s_courses = get_user_courses(auth_string)
        timerel_courses = w_courses + s_courses
    day_end = day+24*3600-1
    all_times = {}
    rn_times = {}
    for course in timerel_courses:
        kurs = course["course_id"]
        kursevents = load("courses/%s/events" % kurs, auth_string)
        if all(int(event["start"]) > day_end or int(event["start"]) < day or event["canceled"] for event in kursevents["events"]): continue
        if not aftertime:
            all_times[course["name"]] = [event for event in kursevents["events"] if day <= int(event["start"]) <= day_end and not event["canceled"]]
        else:
            all_times[course["name"]] = [event for event in kursevents["events"] if aftertime <= int(event["start"]) <= day_end and not event["canceled"]]
            rn_times[course["name"]] = [event for event in kursevents["events"] if int(event["start"]) <= aftertime <= int(event["end"]) and not event["canceled"]]

    day = calendar.day_abbr[datetime.datetime.fromtimestamp(day).weekday()] + ", " + str(datetime.datetime.fromtimestamp(day).date())
    srtd = []
    for key, val in all_times.items():
        for event in val:
            length = str(datetime.timedelta(seconds=int(event["end"]) - int(event["start"])))[:-3]
            srtd.append((event["start"], key, event["categories"], event["title"], event["room"], event["iso_start"][event["iso_start"].find("T")+1:event["iso_start"].find("+")], event["iso_end"][event["iso_end"].find("T")+1:event["iso_end"].find("+")], length))
    if len(srtd) == 0 and not aftertime:
        return "You don't have any classes on "+str(day)+"!"
    srtd = sorted(srtd, key=lambda item: int(item[0]))
    txt = "\n".join(i[1] + " - "+i[2]+(("(topic: "+i[3]+")") if i[3] else "")+" from "+i[5]+" to "+i[6]+" ("+i[7]+"h)"+" in room "+i[4] for i in srtd)
    if aftertime and len(rn_times) > 0:
        srtd = []
        for key, val in rn_times.items():
            for event in val:
                togo = str(datetime.timedelta(seconds=int(event["end"]) - (aftertime+60*16)))[:-3]
                srtd.append((event["start"], key, event["categories"], event["title"], event["iso_end"][event["iso_end"].find("T")+1:event["iso_end"].find("+")], togo))
        if len(srtd) == 0 and len(txt) == 0:
            return "You don't have any classes on today!"
        txt2 = "Currently you are in:\n"+("\n".join(i[1] + " - "+i[2]+(("(topic: "+i[3]+")") if i[3] else "")+" until "+i[4]+" ("+i[5]+" hours to go)" for i in srtd))
        return txt2 + ("\nYou have the following classes left today:\n"+txt if len(txt) > 0 else "You don't have any classes left today.")
    else:
        return "You have the following classes on "+str(day)+":\n"+txt if len(txt) > 0 else "You don't have any classes left today."


def debug_stuff(auth_string):
    # timerel_courses = get_timerelevant_courses(auth_string)  #der wird beim ersten mal errechnet, für 72 Stunden gespeichert, und jedes mal wenn eine zeitabfrage OHNE SEMESTERANGABE KOMMT soll der das hier  nehmen stall all_courses
    timerel_courses = None
    # print(get_session_info("when", auth_string, "SS18", timerel_courses))
    # print(get_courses(auth_string, semester="")[0])
    # print(get_course_by_name(auth_string, "datenbanksysteme", semester="")) # sooo, das throwed jetzt ne MoreThan1Excption("course") oder returned, falls es nur einen gab..
                                                                            # das dialogsystem müsste diese exception fangen und dann nach semester fragen...
                                                                            # im optimalfall kann es das immer fangen, auch wenn diese funktion von einer anderen aufgerufen wird...
                                                                            # und kann aus dem error-text ("course") ne frage ("?x.course(x)") erstellen
    # print(get_session_info("what", auth_string, "", timerel_courses, "Informatik A")) # hier wird diese exception suppressed, weil get_session_info nur die zeitlich noch relevanten kurse interessiert
                                                                                        # der fehler wird uns daher wohl erst bei document-api-routen begegnen
    # print(get_session_info("all", auth_string, "", timerel_courses, "Codierungstheorie und Kryptographie"))
    # print(find_klausurtermin(auth_string, "Mathematik für anwender II"))
    # print(get_courses_for_day(auth_string, parse_date("monday"), None, timerel_courses, 1521453600))
    print(get_courses_for_day(auth_string, parse_date("16.4.2018"), None, timerel_courses))


########################################################################################################################
############################################### Dateien & Downloads ####################################################
########################################################################################################################

def crawl(auth_string, kurs_id, what, filepath, folder_id):
    if filepath.startswith("/"): filepath = filepath[1:]
    documents = load("documents/"+kurs_id+"/folder"+("/"+folder_id if folder_id else ""), auth_string)
    all_folders = {(filepath+"/" if filepath else "")+i["name"]: i["folder_id"] for i in documents[what]}
    if all_folders:
        for key, val in all_folders.items():
            all_folders = {**all_folders, **crawl(auth_string, kurs_id, what, filepath+"/"+key, val)}
    return all_folders


def get_all_files(auth_string, course, semester=None):
    kurs = get_course_by_name(auth_string, course, semester=semester)["course_id"]
    all_folders = crawl(auth_string, kurs, "folders", "", "")
    all_files = {}
    for key, val in all_folders.items():
        folder = load("documents/%s/folder/%s" % (kurs, val), auth_string)
        if folder["documents"]:
            all_files[key] = folder["documents"]
    return all_files


def list_course_files(auth_string, course, semester=None):
    all_files = get_all_files(auth_string, course, semester=semester)
    flatten = lambda l: [item for sublist in l for item in sublist]
    file_list = "\n".join(flatten([[foldername+"/"+curr["name"] for curr in foldercontent] for foldername, foldercontent in all_files.items()]))
    return ("Files:\n"+file_list) if len(file_list) > 0 else "There are no files for that course at all!"


if __name__ == '__main__':
    # auth_bytes = ('%s:%s' % ("cstenkamp", "pw")).encode('ascii')
    # auth_string = codecs.encode(auth_bytes, 'base64').strip()
    # print(auth_string)
    auth_string = b'Y3N0ZW5rYW1wOmNoYW5nZXNfcGxlYXNl'
    # userid = load_userid(auth_string)

    # kurs = get_course_by_name(auth_string, "Datenbanksysteme", semester="SS17")["course_id"]
    all_files = get_all_files(auth_string, "Datenbanksysteme")

    flatten = lambda l: [item for sublist in l for item in sublist]
    file_list = "\n".join(flatten([[foldername+"/"+curr["name"] for curr in foldercontent] for foldername, foldercontent in all_files.items()]))
    print(file_list)

            # if curr["name"] == "Skript":
            #     singleUser_download(curr["filename"], download(auth_string, curr["document_id"]))




    #/user/:id/schedule also seems to be gone

    #/news is empty

    # user/id/events seems to be gone from new API


    # kursinfo = load("courses/%s" % kurs, auth_string) #nothing interesting from here
    # print(kursinfo)


    # documents = load("documents/%s/folder" % kurs, auth_string)
    # print(documents)



    # kursliste =

    # file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
    # content = load_file2(file[1]["document_id"], auth_string)
    # print(content)
    # with open(p.join(dir,'file'), 'wb') as f:
    #     f.write(content)