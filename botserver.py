############################### externe imports ####################################
from flask import Flask, request, redirect, url_for
import json
from flask_sqlalchemy import SQLAlchemy
import settings

####################################################################################

app = Flask(__name__) #that's what's imported in the wsgi file
app.config.from_object(__name__)
app.config.update(
    SESSION_COOKIE_NAME = 'session_studipbot',
    SESSION_COOKIE_PATH = '/studipbot/'
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+settings.DBPATH+settings.DBNAME
db = SQLAlchemy(app)

######################## interne imports, NACH creation der db #####################
from bothelper import handle_update, send_message
# import travel
import studip

####################################################################################

@app.route("/", methods=["POST", "GET"])
def botupdate2():
    if request.method == 'POST':
        update = request.data.decode("utf8")
        update = json.loads(update)
        # ibis = travel.loadIBIS()
        ibis = studip.loadIBIS()
        ibis.init()
        handle_update(update, ibis)
        return "" #"" = 200 responsee
    else:
        return "This page is reserved for the Telegram-studIP-Bot (/)"



@app.route("/deploycomplete", methods=["POST", "GET"])
def deploycomplete():
    if request.method == 'POST':
        data = request.get_json()
        update = data["event"]+" of "+data["project_name"]+" on "+data["server_name"]+" "+data["result"]+" (commit "+data["commit"]["id"]+" from "+data["created_at"]+")"
        send_message(update, str(settings.MY_CHAT_ID))
        return update
    else:
        return "This must be called via a POST-webhook!"



# def save_to_file(text):
#     with open("/tmp/output.txt", "w") as text_file:
#         text_file.write(text)

####################################################################################

if __name__ == "__main__":
    app.run(host="0.0.0.0")