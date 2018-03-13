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

########################################################################################################################
#################################### von der api bereitgestellte sinnvolle routen ######################################
########################################################################################################################

def get_courses(user, auth_string, semester=None):
    pass #GET /user/:user_id/courses

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

def get(semesters, name):
    return [i for i in semesters if i['title'] == name][0]


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
    w_courses = [] if w_courses is None else w_courses
    s_courses = [] if s_courses is None else s_courses
    w_courses.extend([i for i in s_courses if i["perms"] not in ["autor", "user"]])
    s_courses = [i for i in s_courses if i["perms"] in ["autor", "user"]]
    if semester:
        all_semesters = load("semesters", auth_string)['semesters']
        semesterid = get(all_semesters, get_semester_name(semester))["semester_id"]
        s_courses = [i for i in s_courses if i["semester_id"] == semesterid]
        w_courses = [i for i in w_courses if i["semester_id"] == semesterid]
    return w_courses or [], s_courses or []


if __name__ == '__main__':
    # auth_bytes = ('%s:%s' % ("cstenkamp", "pw")).encode('ascii')
    # auth_string = codecs.encode(auth_bytes, 'base64').strip()
    # print(auth_string)
    auth_string = b'Y3N0ZW5rYW1wOmNoYW5nZXNfcGxlYXNl'


    w_courses, s_courses = get_user_courses(auth_string, "SS 2015")
    print(len(w_courses+s_courses))



    # kursliste =

    # file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
    # content = load_file2(file[1]["document_id"], auth_string)
    # print(content)
    # with open(p.join(dir,'file'), 'wb') as f:
    #     f.write(content)