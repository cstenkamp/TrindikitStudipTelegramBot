import codecs
from studip_downloader import *
import os.path as p
import os

# auth_bytes = ('%s:%s' % ("cstenkamp", "changes_please")).encode('ascii')
# AUTH_STRING = codecs.encode(auth_bytes, 'base64').strip()
# print(AUTH_STRING)
AUTH_STRING = b'Y3N0ZW5rYW1wOmNoYW5nZXNfcGxlYXNl'


if __name__ == '__main__':
    auth_string = AUTH_STRING



    userid = load('user', auth_string)['user']['user_id']
    file = return_file(userid, None, "Codierungstheorie und Kryptographie", None, "Skript", auth_string)
    content = load_file2(file[1]["document_id"], auth_string)
    print(content)
    with open(p.join(dir,'file'), 'wb') as f:
        f.write(content)

#    folders = []
##    print("COURSES", load('user/%s/courses' % userid, auth_string)['courses']['study'])
#    for course in load('user/%s/courses' % userid, auth_string)['courses']['study']:
#        if course['semester_name'] == CURR_SEMESTER:
#            if course['name'] == KURSNAME:
#                print('%s / %s' % (course['semester_name'], course['name']))
#                cid = course['course_id']
#                path = [course['semester_name'], course['name']]
#                load_course(cid, path, auth_string)
