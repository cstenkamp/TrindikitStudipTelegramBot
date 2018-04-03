#!/usr/bin/env python3

# This downloads files from Stud.IP, to be specific, every file from every
# course you're in.
# It currently skips files > 50 MB. Sometimes, the API also simply refuses
# to give file listings for a course -- in that case, the script simply
# skips the course.
# It tells you about everything it skips or finds to be a duplicate.
#
# The whole thing is not extensively tested or refined, I basically used
# it to download everything once on my macOS computer and that's it, so
# expect errors and rough edges.
#
# Obviously, no warranty or guarantees of any kind are made.

BASE_URL = 'https://studip.uni-osnabrueck.de/plugins.php/restipplugin/api/'

CURR_SEMESTER = "WS 2017/18"
KURSNAME = "Codierungstheorie und Kryptographie"

import settings
import json
import os
import os.path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# auth_bytes = ('%s:%s' % (USERNAME, PASSWORD)).encode('ascii')
# AUTH_STRING = codecs.encode(auth_bytes, 'base64').strip()
# AUTH_STRING = b'the_string'



def load(path, auth_string):
    return json.loads(download_file(path, auth_string).decode('utf8'))


def download_file(path, auth_string):
    r = Request(BASE_URL + path)
    r.add_header('Authorization', b'Basic %s' % auth_string)

    # for some reason, I sometimes get random "not authorized" errors
    while True:
        try:
            f = urlopen(r)
            return f.read()
        except HTTPError as e:
            if e.code != 401:
                raise
            else:
                if path == 'user': #RESOLVED change this as it is not anymore "the first time" iff path==user
                    # we sometimes get error 401 for no reason
                    # but this is the first request the script sends, so
                    # credentials may simply be wrong
                    print('not authorized -- are password and username correct?'
                          '\nif yes: simply try again', file=sys.stderr)
                    raise SystemExit
                # print('getting error 401, retrying...')
                pass


###############################################################################



win_re = re.compile(r'[<>:"/\\\|\?\*]')


def clean_filename(name):
    if name == '.':
        return 'DOT'
    elif name == '..':
        return 'DOTDOT'
    else:
        if os.name == 'posix':
            return name.replace('/', ':')
        elif os.name == 'nt':
            # untested
            return win_re.subn('_', name)[0]


#recursively load folder and search for skript
def load_folder(course_id, file_id, path, auth_string):
    data = load('documents/%s/folder%s' % (course_id, file_id), auth_string)
    #    print(data)
    #    print(data['documents'])
    for folder in data['folders']:
        if not folder['permissions']['readable']:
            print('!!! folder not readable %r' % (path + [folder['name']]), file=sys.stderr)
            continue
        load_folder(course_id, '/%s' % folder['folder_id'], path + [folder['name']], auth_string)
    for doc in data['documents']:
        if doc["name"] == "Skript":
            print(doc)
            print(doc["chdate"])
            print(round(time.time()))
            # if int(doc['filesize']) > 50 * 1024 * 1024:
            #     print('!!! filesize > 50 MB [%r, %d]' % (path + [doc['filename']], int(doc['filesize'])), file=sys.stderr)
            load_file(doc['document_id'], path + [doc['filename']],auth_string)


def load_file(file_id, components, auth_string):
    path = os.path.join(*(clean_filename(i) for i in components))
    if os.path.exists(path):
        print('>>> already exists, skipping [%s]' % path, file=sys.stderr)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        content = download_file('documents/%s/download' % file_id, auth_string)
        with open(path, 'wb') as f:
            f.write(content)
    except HTTPError as e:
        if e.code == 403:
            print('!!! could not load file %s' % path, file=sys.stderr)


log = []


def load_course(cid, path, auth_string):
    try:
        load_folder(cid, '', path, auth_string)
    except HTTPError as e:
        if e.code == 400:
            print('!!! error with course %r / %r' % (cid, path), file=sys.stderr)
        else:
            raise


def nnot(thing):
    if thing is None or not thing:
        return True
    return False


def load_folder2(cid, fid, auth_string, path="", recursive=False):
    data = load('documents/%s/folder%s' % (cid, fid), auth_string)
    allfiles = []
    if recursive:
        for folder in data['folders']:
            if folder['permissions']['readable']:
                allfiles.extend(load_folder2(cid, '/%s' % folder['folder_id'], auth_string, path + "/" + folder["name"], recursive))
    for doc in data['documents']:
        allfiles.append((path, doc))
    return allfiles


def load_file2(fid, auth_string):
    try:
        content = download_file('documents/%s/download' % fid, auth_string)
        #        with open(path, 'wb') as f:
        #            f.write(content)
        return content
    except HTTPError as e:
        if e.code == 403:
            print('!!! could not load file', file=sys.stderr)


def return_file(userid, semester, course, folder, name, auth_string):
    if nnot(userid) or nnot(course) or nnot(name):
        raise Exception("UserID, course and name must be given!")
    if nnot(semester):
        courses = [i for i in load('user/%s/courses' % userid, auth_string)['courses']['study']]
    else:
        courses = [i for i in load('user/%s/courses' % userid, auth_string)['courses']['study'] if i[
            'semester_name' == CURR_SEMESTER]]  # RESOLVED - das semester_name == muss auch noch auf 200 verschiedene Arten gehen

    demanded = []
    for course in courses:
        if course['name'] == KURSNAME:
            demanded.append(course)
    if len(demanded) > 1:
        raise Exception("more than one course is in question, please state a Semester!")
    course = demanded[0]

    #    print(course)
    cid = course['course_id']
    files = load_folder2(cid, "", auth_string, "", recursive=True)
    if not nnot(folder):
        files2 = [i[1] for i in files if i[0].contains(folder)]
    else:
        files2 = [i[1] for i in files]

    fitting = []
    for i in files2:
        if i["name"] == name:
            fitting.append(i)

    if len(fitting) > 1:
        raise Exception("more than one file is in question, state a folder!")

    for i in files:
        if i[1] == fitting[0]:
            return i


# ne generelle funktion ID-to-type and name sodass mir die ids immer reichen wenn ich namen etc will


###############################################################################


if __name__ == '__main__':
    auth_string = settings.AUTH_STRING

    userid = load('user', auth_string)['user']['user_id']
    print(userid)
    file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
    print("so far", file)
    print(load_file2(file[1]["document_id"], auth_string))

#    folders = []
##    print("COURSES", load('user/%s/courses' % userid, auth_string)['courses']['study'])
#    for course in load('user/%s/courses' % userid, auth_string)['courses']['study']:
#        if course['semester_name'] == CURR_SEMESTER:
#            if course['name'] == KURSNAME:
#                print('%s / %s' % (course['semester_name'], course['name']))
#                cid = course['course_id']
#                path = [course['semester_name'], course['name']]
#                load_course(cid, path, auth_string)
