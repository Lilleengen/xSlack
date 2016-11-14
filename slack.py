import time
from slackclient import SlackClient
import config
import re

token = config.key
members = dict()
ts_dict = dict()
sc = SlackClient(token)
if sc.rtm_connect():  # connect to a Slack RTM websocket
    last_text = ""
    team_name = sc.api_call("team.info")["team"]["name"]
    for member in sc.api_call("users.list")["members"]:
        members[member["id"]] = dict()
        members[member["id"]]["name"] = member["name"]#member_info["name"]
        members[member["id"]]["image"] = member["profile"]["image_32"]
    while True:
        for action in sc.rtm_read():
            print(action)
            if "type" in action and ( action["type"] == "team_join" or action["type"] == "user_change"):
                members[action["user"]["id"]] = dict()
                members[action["user"]["id"]]["name"] = action["user"]["name"]
                members[action["user"]["id"]]["image"] = action["user"]["profile"]["image_32"]
            elif "type" in action and action["type"] == "message" and "subtype" in action and action["subtype"] == "message_changed" and action["message"]["ts"] in ts_dict:
                text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "@" + members[m.group(0)[2:-1]]["name"], action["message"]["text"])
                sc.api_call("chat.update", ts=ts_dict[action["message"]["ts"]], channel=action["channel"], text=text)
            elif "type" in action and action["type"] == "message" and "text" in action and action["text"] != last_text and "user" in action:
                last_text=action["text"]
                text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "@" + members[m.group(0)[2:-1]]["name"], action["text"])
                ts_dict[action["ts"]] = sc.api_call("chat.postMessage", channel=action["channel"], text=text, username=members[action["user"]]["name"] + " @ " + team_name, icon_url=members[action["user"]]["image"])["ts"]
        time.sleep(0.1)
else:
    print('Connection Failed, invalid token?')