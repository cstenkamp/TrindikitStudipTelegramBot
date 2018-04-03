import platform
import sys
import os

if os.path.exists(os.path.join(os.path.dirname(sys.argv[0]),"set_vars.py")):
    import set_vars #don't remove, this is needed to set the env-vars

###################################################### LOGIN ###########################################################

try:
    URL = os.environ["STUDIPBOT_URL"]
except:
    raise Exception("There is no URL specified for the Stud.IP-Bot, it should be an environment-variable!")

try:
    auth_str = os.environ["STUDIPBOT_AUTH_STRING"]
    AUTH_STRING = bytearray(auth_str,'utf8')
except:
    raise Exception("There is no AUTH_STRING specified for the Stud.IP-Bot, it should be an environment-variable!")

MY_CHAT_ID = 163601520

#################################################### SETTINGS ##########################################################

VERBOSE = {"IS": False, "MIVS": False, "UpdateRules": False, "Precondition": False, "Parse": 0, "NotUnderstand": False, "Question": False}
MERGE_SUBSQ_MESSAGES = False
USE_GRAMMAR = "studip"
GRAMMAR_LAN = "en"

################################################## FOR MULTIUSER #######################################################

try:    MULTIUSER = os.environ["STUDIPBOT_USE_MULTIUSER"].lower() in ['true', '1', 't', 'y', 'yes']
except: MULTIUSER = platform.linux_distribution()[0] != "debian"

DBPATH = '/var/www/studIPBot/'
DBNAME = "user_states.db"


################################################## FOR SINGLEUSER ######################################################

SAVE_IS = False
USE_SAVED = True

########################################################################################################################

# if MULTIUSER:
#     PATH = "/var/www/studIPBot"
# else:
#     PATH = "/home/chris/Documents/Projects/Trindikit"

PATH = os.path.dirname(__file__)