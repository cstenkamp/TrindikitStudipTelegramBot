import requests
import urllib

import settings
import userDB
from botserver import db
from ibis_types import Greet

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def handle_update(update, ibis):
    text = update["message"]["text"]
    chat = update["message"]["chat"]["id"]
    # gucke chat in DB nach, wenns noch nicht existiert akzeptierst du nur start und fragst nach Namen etc
    user, did_create = userDB.create_or_add_user(chat)

    print("-----------------------------------------------------")
    print("USER WROTE", text)
    print("-----------------------------------------------------")

    if did_create:
        if text == "/start":
            send_message("New user! You were added to the system", chat)
        else:
            send_message("New User that didn't send /start", chat)
        user.state.IS.private.agenda.push(Greet())
        ibis.respond(user)
    else:
        if user.asked_restart or user.asked_stop:
            if text == "yes":
                user.state.reset_IS()
                user.state.reset_MIVS()
                send_message("Consider it done.", chat)
                if user.asked_restart:
                    user.state.IS.private.agenda.push(Greet())
                    ibis.respond(user)
            elif text == "no":
                send_message("Ok, won't do", chat)
            else:
                send_message("Count that as 'no'.", chat)
            user.asked_restart = False
            user.asked_stop = False
        elif text == "/start":
            send_message("Do you want to start over?", chat)
            user.asked_restart = True
        elif text == "/stop":
            send_message("Do you want me to delete your data?", chat)
            user.asked_stop = True
        elif text == "/showIS":
            send_message(user.state.IS.pformat(), chat)
        elif text.startswith("/"):
            send_message("Unknown command", chat)
        else:
            ibis.handle_message(text, user)


    user.state.save_IS_to_DB()
    user.state.save_MIVS_to_DB()
    db.session.add(user.state)
    db.session.commit()


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = settings.URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


# ---------------------------- Diese hier sind nicht mehr nötig bei webhooks ----------------------------
#
# import json
#
# def get_json_from_url(url):
#     content = get_url(url)
#     js = json.loads(content)
#     return js
#
#
# def get_updates(offset=None):
#     url = URL + "getUpdates"
#     if offset:
#         url += "?offset={}".format(offset)
#     js = get_json_from_url(url)
#     return js
#
#
# def get_last_update_id(updates): #not needed when using webhooks
#     update_ids = []
#     for update in updates["result"]:
#         update_ids.append(int(update["update_id"]))
#     return max(update_ids)
#
#
# def handle_updates(updates):
#     for update in updates["result"]:
#         handle_update(update)
#
#
# def get_last_chat_id_and_text(updates):
#     num_updates = len(updates["result"])
#     last_update = num_updates - 1
#     text = updates["result"][last_update]["message"]["text"]
#     chat_id = updates["result"][last_update]["message"]["chat"]["id"]
#     return (text, chat_id)
#
#
# def build_keyboard(items):
#     keyboard = [[item] for item in items]
#     reply_markup = {"keyboard":keyboard, "one_time_keyboard": True}
#     return json.dumps(reply_markup)
#
#
# def main():
#     users.create_or_add(345)
#     last_update_id = None
#     while True:
#         updates = get_updates(last_update_id)
#         if len(updates["result"]) > 0:
#             last_update_id = get_last_update_id(updates) + 1
#             handle_updates(updates)
#         time.sleep(0.5)
#
#
# if __name__ == '__main__':
#     main()
