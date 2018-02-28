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


def semesters_with_courses(userid, auth_string):
    courses = load("/user/%s/courses" % userid, auth_string)
    user_semesters = list(set(course['semester_name'] for course in courses['courses']['study']))
    all_semesters = load("semesters", auth_string)['semesters']
    semester_dict = {elem['title']:elem['semester_id'] for elem in all_semesters if elem['title'] in user_semesters}
    return semester_dict

###############################################################################


#
# win_re = re.compile(r'[<>:"/\\\|\?\*]')
#
#
# def clean_filename(name):
#     if name == '.':
#         return 'DOT'
#     elif name == '..':
#         return 'DOTDOT'
#     else:
#         if os.name == 'posix':
#             return name.replace('/', ':')
#         elif os.name == 'nt':
#             # untested
#             return win_re.subn('_', name)[0]
#

# #recursively load folder and search for skript
# def load_folder(course_id, file_id, path, auth_string):
#     data = load('documents/%s/folder%s' % (course_id, file_id), auth_string)
#     #    print(data)
#     #    print(data['documents'])
#     for folder in data['folders']:
#         if not folder['permissions']['readable']:
#             print('!!! folder not readable %r' % (path + [folder['name']]), file=sys.stderr)
#             continue
#         load_folder(course_id, '/%s' % folder['folder_id'], path + [folder['name']], auth_string)
#     for doc in data['documents']:
#         if doc["name"] == "Skript":
#             print(doc)
#             print(doc["chdate"])
#             print(round(time.time()))
#             # if int(doc['filesize']) > 50 * 1024 * 1024:
#             #     print('!!! filesize > 50 MB [%r, %d]' % (path + [doc['filename']], int(doc['filesize'])), file=sys.stderr)
#             load_file(doc['document_id'], path + [doc['filename']],auth_string)


# def load_file(file_id, components, auth_string):
#     path = p.join(*(clean_filename(i) for i in components))
#     if p.exists(path):
#         print('>>> already exists, skipping [%s]' % path, file=sys.stderr)
#         return
#     os.makedirs(p.dirname(path), exist_ok=True)
#     try:
#         content = download_file('documents/%s/download' % file_id, auth_string)
#         with open(path, 'wb') as f:
#             f.write(content)
#     except HTTPError as e:
#         if e.code == 403:
#             print('!!! could not load file %s' % path, file=sys.stderr)
#
#
# log = []
#
#
# def load_course(cid, path, auth_string):
#     try:
#         load_folder(cid, '', path, auth_string)
#     except HTTPError as e:
#         if e.code == 400:
#             print('!!! error with course %r / %r' % (cid, path), file=sys.stderr)
#         else:
#             raise

#
# def nnot(thing):
#     if thing is None or not thing:
#         return True
#     return False
#
#
# def load_folder2(cid, fid, auth_string, path="", recursive=False):
#     data = load('documents/%s/folder%s' % (cid, fid), auth_string)
#     allfiles = []
#     if recursive:
#         for folder in data['folders']:
#             if folder['permissions']['readable']:
#                 allfiles.extend(load_folder2(cid, '/%s' % folder['folder_id'], auth_string, path + "/" + folder["name"], recursive))
#     for doc in data['documents']:
#         allfiles.append((path, doc))
#     return allfiles
#
#
# def load_file2(fid, auth_string):
#     try:
#         content = download_file('documents/%s/download' % fid, auth_string)
#         #        with open(path, 'wb') as f:
#         #            f.write(content)
#         return content
#     except HTTPError as e:
#         if e.code == 403:
#             print('!!! could not load file', file=sys.stderr)
#


#
# def return_file(userid, semester, course, folder, name, auth_string):
#     if nnot(userid) or nnot(course) or nnot(name):
#         raise Exception("UserID, course and name must be given!")
#     if nnot(semester):
#         courses = [i for i in load('user/%s/courses' % userid, auth_string)['courses']['study']]
#     else:
#         courses = [i for i in load('user/%s/courses' % userid, auth_string)['courses']['study'] if i[
#             'semester_name' == CURR_SEMESTER]]  # TODO - das semester_name == muss auch noch auf 200 verschiedene Arten gehen
#     demanded = []
#     for course in courses:
#         if course['name'] == KURSNAME:
#             demanded.append(course)
#     if len(demanded) > 1:
#         raise Exception("more than one course is in question, please state a Semester!")
#     course = demanded[0]
#
#     #    print(course)
#     cid = course['course_id']
#     files = load_folder2(cid, "", auth_string, "", recursive=True)
#     if not nnot(folder):
#         files2 = [i[1] for i in files if i[0].contains(folder)]
#     else:
#         files2 = [i[1] for i in files]
#
#     fitting = []
#     for i in files2:
#         if i["name"] == name:
#             fitting.append(i)
#
#     if len(fitting) > 1:
#         raise Exception("more than one file is in question, state a folder!")
#
#     for i in files:
#         if i[1] == fitting[0]:
#             return i


# ne generelle funktion ID-to-type and name sodass mir die ids immer reichen wenn ich namen etc will


###############################################################################
def get(semesters, name):
    return [i for i in semesters if i['title'] == name][0]

def many_days(semesters, this, next, curr_sems):
    if curr_sems:
        secs = int(get(semesters,this)['seminars_end']) - int(time.time())
        return secs//60//60//24+1, True
    else:
        secs = int(get(semesters,next)['seminars_begin']) - int(time.time())
        return secs//60//60//24+1, True


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
    if string in ["this semester", "current semester"]:
        return this
    elif string in ["next semester", "upcoming semester", "the semester after this"]:
        return next
    else:
        return get_semester_name(string)


def get_semester_info(all_semesters, semester):
    s = get(all_semesters, semester)
    return "Semester: %s \nBegin of Semester: %s \nBegin of Lectures: %s \nEnd of Lectures: %s \nEnd of Semester: %s" \
            % (s['title'], s['begin_iso'][:10], s['seminars_begin_iso'][:10], s['seminars_end_iso'][:10], s['end_iso'][:10] )


def is_VLZeit(auth_string):
    userid = load_userid(auth_string)
    all_semesters = load("semesters", auth_string)['semesters']
    currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
    return "yes" if currently_seminars else "no"


if __name__ == '__main__':
    # auth_bytes = ('%s:%s' % ("cstenkamp", "changes_please")).encode('ascii')
    # auth_string = codecs.encode(auth_bytes, 'base64').strip()
    # print(auth_string)
    auth_string = b'Y3N0ZW5rYW1wOmNoYW5nZXNfcGxlYXNl'

    userid = load_userid(auth_string)
    print(userid)
    print(semesters_with_courses(userid, auth_string))

    all_semesters = load("semesters", auth_string)['semesters']
    this_semester = [i["title"] for i in all_semesters if int(i["begin"]) < time.time() < int(i["end"])][0]
    next_semester = [all_semesters[i+1]['title'] for i in range(len(all_semesters)) if all_semesters[i]['title'] == this_semester][0]
    currently_seminars = not (time.time() < int(get(all_semesters, this_semester)['seminars_begin']) or time.time() > int(get(all_semesters, this_semester)['seminars_end']))
    print(many_days(all_semesters, this_semester, next_semester, currently_seminars))
    print(get_semester_info(all_semesters, 'SS 2018'))



    # kursliste =

    # file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
    # content = load_file2(file[1]["document_id"], auth_string)
    # print(content)
    # with open(p.join(dir,'file'), 'wb') as f:
    #     f.write(content)