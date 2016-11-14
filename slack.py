import time
from slackclient import SlackClient
import config
import re

for token in config.tokens:
    members = dict()
    ts_dict = dict()
    channels = dict()
    clients = list()
    for token_other in config.tokens:
        if token_other != token:
            clients.append(SlackClient(token_other))
    sc = SlackClient(token)

    if sc.rtm_connect():  # connect to a Slack RTM websocket
        last_text = ""
        team_name = sc.api_call("team.info")["team"]["name"]
        for member in sc.api_call("users.list")["members"]:
            members[member["id"]] = dict()
            members[member["id"]]["name"] = member["name"]#member_info["name"]
            members[member["id"]]["image"] = member["profile"]["image_32"]
        for channel in sc.api_call("channels.list")["channels"]:
            channels[channel["id"]] = channel["name"]
        for group in sc.api_call("groups.list")["groups"]:
            channels[group["id"]] = group["name"]
        while True:
            for action in sc.rtm_read():
                print(action)
                if "channel" in action:
                    print(action["channel"])
                    print(channels)
                if "type" in action and ( action["type"] == "team_join" or action["type"] == "user_change"):
                    members[action["user"]["id"]] = dict()
                    members[action["user"]["id"]]["name"] = action["user"]["name"]
                    members[action["user"]["id"]]["image"] = action["user"]["profile"]["image_32"]
                elif "channel" in action and action["channel"] in config.channels and "type" in action and action["type"] == "message" and "subtype" in action and action["subtype"] == "message_changed" and action["message"]["ts"] in ts_dict:
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "@" + members[m.group(0)[2:-1]]["name"], action["message"]["text"])
                    for token_other in config.tokens:
                        if token_other != token:
                            sc.api_call("chat.update", token=token_other, ts=ts_dict[action["message"]["ts"]], channel=action["channel"], text=text)
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in config.channels and "type" in action and action["type"] == "message" and "text" in action and action["text"] != last_text and "user" in action:
                    last_text=action["text"]
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "@" + members[m.group(0)[2:-1]]["name"], action["text"])
                    for client in clients:
                        ts_dict[action["ts"]] = client.api_call("chat.postMessage", channel=channels[action["channel"]], text=text, username=members[action["user"]]["name"] + " @ " + team_name, icon_url=members[action["user"]]["image"])["ts"]
            time.sleep(0.1)
    else:
        print('Connection Failed, invalid token?')