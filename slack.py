import time
from slackclient import SlackClient
import config
import re
import threading


def run(token):
    members = dict()
    ts_dict = dict()
    channels = dict()
    clients = list()
    clients_users = dict()
    clients_channels = dict()

    for token_other in config.tokens:
        if token_other != token:
            clients.append(SlackClient(token_other))

    for client in clients:
        clients_users[client.token] = dict()
        ts_dict[client.token] = dict()
        for user in client.api_call("users.list")["members"]:
            clients_users[client.token][user["name"]] = user["id"]
        for channel in client.api_call("channels.list")["channels"]:
            clients_channels[channel["name"]] = channel["id"]
        for group in client.api_call("groups.list")["groups"]:
            clients_channels[group["name"]] = group["id"]

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
                if "type" in action and ( action["type"] == "team_join" or action["type"] == "user_change"):
                    members[action["user"]["id"]] = dict()
                    members[action["user"]["id"]]["name"] = action["user"]["name"]
                    members[action["user"]["id"]]["image"] = action["user"]["profile"]["image_32"]
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in config.channels and action["type"] == "message" and "subtype" in action and action["subtype"] == "message_changed":
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "-----@-----" + members[m.group(0)[2:-1]]["name"], action["message"]["text"])
                    for client in clients:
                        if action["message"]["ts"] in ts_dict[client.token]:
                            text = re.sub(r"(?:^| |\n)@(?:\d|[a-z]){1,23}(?:$| |\n)", lambda m: re.sub(r"@(?:\d|[a-z]){1,23}", lambda m2: m2.group(0) if m2.group(0) not in clients_users[client.token] else "<@" + clients_users[client.token][m2.group(0)[1:]] + ">", m.group(0)), text)
                            text = re.sub(r"-----@-----", "@", text)
                            print(client.api_call("chat.update", ts=ts_dict[client.token][action["message"]["ts"]], channel=clients_channels[channels[action["channel"]]], text=text))
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in config.channels and "type" in action and action["type"] == "message" and "text" in action and action["text"] != last_text and "user" in action:
                    last_text=action["text"]
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "-----@-----" + members[m.group(0)[2:-1]]["name"], action["text"])
                    for client in clients:
                        text = re.sub(r"(?:^| |\n)@(?:\d|[a-z]){1,23}(?:$| |\n)", lambda m: re.sub(r"@(?:\d|[a-z]){1,23}", lambda m2: m2.group(0) if m2.group(0) not in clients_users[client.token] else "<@" + clients_users[client.token][m2.group(0)[1:]] + ">", m.group(0)), text)
                        text = re.sub(r"-----@-----", "@", text)
                        ts_dict[client.token][action["ts"]] = client.api_call("chat.postMessage", channel=clients_channels[channels[action["channel"]]], text=text, username=members[action["user"]]["name"] + " @ " + team_name, icon_url=members[action["user"]]["image"])["ts"]
            time.sleep(0.1)
    else:
        print('Connection Failed, invalid token?')

for token in config.tokens:
    t = threading.Thread(target=run, args=(token,))
    t.start()
