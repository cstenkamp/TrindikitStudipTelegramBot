BASE_URL = 'https://studip.uni-osnabrueck.de/plugins.php/restipplugin/api/'

import codecs
import json
import re
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import codecs
from studip_downloader import *
import os.path as p
import os
import time
import datetime
import calendar

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


def load_userid(auth_string):
    try:
        userid = load('user', auth_string, check_credentials=True)['user']['user_id']
    except AuthentificationError:
        print("Credentials wrong!")
        exit()
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
################################################## Semester & Zeiten ###################################################
########################################################################################################################

def get_user_courses(auth_string, semester=None):
    userid = load_userid(auth_string)
    courses = load("/user/%s/courses" % userid, auth_string)
    if semester:
        all_semesters = load("semesters", auth_string)['semesters']
        semesterid = get(all_semesters, get_semester_name(semester))["semester_id"]
    s_courses = courses['courses']['study'] or []
    w_courses = courses['courses']['work'] or []
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
        return "You don't have any upcoming sessions"+(" at all" if not one_course_str else " for "+one_course_str)+"!"
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
        txt = time_starts + " (in "+starts_in+"hours )"
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


class MoreThan1Exception(Exception):
    pass


def get_course_by_name(auth_string, name, semester=None, supress=False):
    w_courses, s_courses = get_user_courses(auth_string, semester=semester)
    coursename = find_real_coursename(auth_string, name)
    res = [i for i in w_courses + s_courses if i['name'] == coursename]
    if len(res) > 1:
        if not supress: raise MoreThan1Exception("course")
        else: return res
    else:
        return res[0]







if __name__ == '__main__':
    # auth_bytes = ('%s:%s' % ("cstenkamp", "pw")).encode('ascii')
    # auth_string = codecs.encode(auth_bytes, 'base64').strip()
    # print(auth_string)
    auth_string = b'Y3N0ZW5rYW1wOmNoYW5nZXNfcGxlYXNl'
    userid = load_userid(auth_string)

    # timerel_courses = get_timerelevant_courses(auth_string)  #der wird beim ersten mal errechnet, für 72 Stunden gespeichert, und jedes mal wenn eine zeitabfrage OHNE SEMESTERANGABE KOMMT soll der das hier  nehmen stall all_courses
    timerel_courses = None
    # print(get_session_info("when", auth_string, "SS18", timerel_courses))

    # print(get_courses(auth_string, semester="SS18"))

    # print(get_course_by_name(auth_string, "datenbanksysteme", semester="")) # sooo, das throwed jetzt ne MoreThan1Excption("course") oder returned, falls es nur einen gab..
                                                                            # das dialogsystem müsste diese exception fangen und dann nach semester fragen...
                                                                            # im optimalfall kann es das immer fangen, auch wenn diese funktion von einer anderen aufgerufen wird...
                                                                            # und kann aus dem error-text ("course") ne frage ("?x.course(x)") erstellen

    # print(get_session_info("what", auth_string, "", timerel_courses, "Informatik A")) # hier wird diese exception suppressed, weil get_session_info nur die zeitlich noch relevanten kurse interessiert
                                                                                        # der fehler wird uns daher wohl erst bei document-api-routen begegnen




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