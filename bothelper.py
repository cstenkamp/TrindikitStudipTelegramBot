import json
import requests
import time
import urllib
from userDB import userDB
import os
from os.path import join


PATH = "/var/www/studIPBot" if os.name != "nt" else ""
TOKEN = "491105485:AAFrSueGnkjLee79ne9MhvBSLrpB2VHEnec"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
MY_CHAT_ID = 163601520
users = userDB(join(PATH,"users.sqlite"))

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates"
    if offset:
        url += "?offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates): #not needed when using webhooks
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def handle_update(update):
    text = update["message"]["text"]
    chat = update["message"]["chat"]["id"]
    # gucke chat in DB nach, wenns noch nicht existiert akzeptierst du nur start und fragst nach Namen etc
    user, did_create = users.create_or_add(chat)

    if did_create:
        if text == "/start":
            send_message("Hello, new user! You were added to the system", chat)
        else:
            send_message("New User that didn't send /start", chat)
    else:
        if text == "/start":
            send_message("Do you want to start over?", chat)
        elif text == "/stop":
            send_message("Do you want me to delete your data?", chat)
        elif text.startswith("/"):
            send_message("Unkown command", chat)
        else:
            send_message("YOU SAID: "+text, chat)


    #
    # items = db.get_items(chat)
    # if text == "/done":
    #     keyboard = build_keyboard(items)
    #     send_message("Select an item to delete", chat, keyboard)
    # elif text == "/start":
    #     send_message(
    #         "Welcome to your personal To Do list. Send any text to me and I'll store it as an item. Send /done to remove items",
    #         chat)
    # elif text.startswith("/"):
    #     return
    # elif text == "Penis":
    #     send_message(
    #         "PENIS",
    #         chat)
    # elif text in items:
    #     db.delete_item(text, chat)
    #     items = db.get_items(chat)
    #     keyboard = build_keyboard(items)
    #     send_message("Select an item to delete", chat, keyboard)
    # else:
    #     db.add_item(text, chat)
    #     items = db.get_items(chat)
    #     message = "\n".join(items)
    #     send_message(message, chat)


def handle_updates(updates):
    for update in updates["result"]:
        handle_update(update)


def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def build_keyboard(items):
    keyboard = [[item] for item in items]
    reply_markup = {"keyboard":keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


# def main():
#
#     users.create_or_add(345)
#     # last_update_id = None
#     # while True:
#     #     updates = get_updates(last_update_id)
#     #     if len(updates["result"]) > 0:
#     #         last_update_id = get_last_update_id(updates) + 1
#     #         handle_updates(updates)
#     #     time.sleep(0.5)
#
#
# if __name__ == '__main__':
#     main()
