import json
import time
import urllib

import requests
from slackclient import SlackClient
import re
import threading

c = threading.Condition()
threads = dict()
shared_files = dict()

def run(token, other_tokens, channel_names):
    members = dict()
    ts_dict = dict()
    channels = dict()
    clients = list()
    clients_users = dict()
    clients_channels = dict()

    for other_token in other_tokens:
        if other_token != token:
            clients.append(SlackClient(other_token))

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
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in channel_names and action["type"] == "message" and "subtype" in action and action["subtype"] == "message_changed":
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "-----@-----" + members[m.group(0)[2:-1]]["name"], action["message"]["text"])
                    for client in clients:
                        if action["message"]["ts"] in ts_dict[client.token]:
                            text = re.sub(r"(?:^| |\n)@(?:\d|[a-z]){1,23}(?:$| |\n)", lambda m: re.sub(r"@(?:\d|[a-z]){1,23}", lambda m2: m2.group(0) if m2.group(0)[1:] not in clients_users[client.token] else "<@" + clients_users[client.token][m2.group(0)[1:]] + ">", m.group(0)), text)
                            text = re.sub(r"-----@-----", "@", text)
                            print(client.api_call("chat.update", ts=ts_dict[client.token][action["message"]["ts"]], channel=clients_channels[channels[action["channel"]]], text=text))
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in channel_names and action["type"] == "message" and "subtype" in action and action["subtype"] == "group_leave":
                    response = client.api_call("chat.postMessage",
                                               channel=clients_channels[channels[action["channel"]]], text="@" + members[action["user"]]["name"] + " was removed from the chat in " + team_name,
                                               username="xSlack",
                                               icon_emoji=":heavy_minus_sign:")
                elif "channel" in action and action["channel"] in channels and channels[action["channel"]] in channel_names and action["type"] == "message" and "subtype" in action and action["subtype"] == "group_join":
                    response = client.api_call("chat.postMessage",
                                               channel=clients_channels[channels[action["channel"]]], text="@" + members[action["user"]]["name"] + " was added to the chat in " + team_name,
                                               username="xSlack",
                                               icon_emoji=":heavy_plus_sign:")
                elif "ts" in action and "channel" in action and action["channel"] in channels and channels[action["channel"]] in channel_names and "type" in action and action["type"] == "message" and "text" in action and "user" in action:
                    text = re.sub(r"<@U(?:\d|\w){8}>", lambda m: "-----@-----" + members[m.group(0)[2:-1]]["name"], action["text"])
                    text = re.sub(r"<@U(?:\d|\w){8}\|(?:\d|[a-z]){1,23}>", lambda m: "-----@-----" + m.group(0)[12:-1], text)
                    for client in clients:
                        text = re.sub(r"(?:^| |\n)@(?:\d|[a-z]){1,23}(?:$| |\n)", lambda m: re.sub(r"@L(?:\d|[a-z]){1,23}", lambda m2: m2.group(0) if m2.group(0)[1:] not in clients_users[client.token] else "<@" + clients_users[client.token][m2.group(0)[1:]] + ">", m.group(0)), text)
                        text = re.sub(r"-----@-----", "@", text)
                        if "subtype" in action and action["subtype"] == "file_share":
                            c.acquire()
                            file_info = {"ts": action["ts"], "name": action["file"]["name"], "id": action["file"]["id"], "child_ids": dict()}
                            file_is_old = False
                            for file in shared_files[client.token]:
                                if sc.token in file["child_ids"] and file["child_ids"][sc.token] == action["file"]["id"] and float(file["ts"]) > time.time()-2*60:
                                    file_is_old = True

                            if not file_is_old:
                                req = urllib.request.Request(action["file"]["url_private_download"])
                                req.add_header('Authorization', 'Bearer ' + sc.token)
                                resp = urllib.request.urlopen(req)
                                files = dict()
                                files['file'] = resp.read()
                                get = dict()
                                get["filename"] = action["file"]["name"]
                                get["title"] = action["file"]["title"]
                                get["channels"] = clients_channels[channels[action["channel"]]]
                                get["filetype"] = action["file"]["filetype"]
                                get["token"] = client.token
                                get["username"] = members[action["user"]]["name"] + " @ " + team_name
                                get["icon_url"] = members[action["user"]]["image"]
                                if "initial_comment" in action["file"] and "comment" in action["file"]["initial_comment"]:
                                    get["initial_comment"] = "File uploaded by @" + members[action["user"]]["name"] + " in " +  team_name + "\n\n" + action["file"]["initial_comment"]["comment"]
                                else:
                                    get["initial_comment"] = "File uploaded by @" + members[action["user"]]["name"] + " in " + team_name

                                upload_response = json.loads(requests.post('https://slack.com/api/files.upload?' + urllib.parse.urlencode(get), files=files).text)
                                file_info["child_ids"][client.token] = upload_response["file"]["id"]

                            shared_files[sc.token].append(file_info)
                            c.release()
                        else:
                            if "attachments" in action:
                                response = client.api_call("chat.postMessage", channel=clients_channels[channels[action["channel"]]], text=text, username=members[action["user"]]["name"] + " @ " + team_name, icon_url=members[action["user"]]["image"], attachments=action["attachments"])
                            else:
                                response = client.api_call("chat.postMessage",
                                                           channel=clients_channels[channels[action["channel"]]],
                                                           text=text,
                                                           username=members[action["user"]]["name"] + " @ " + team_name,
                                                           icon_url=members[action["user"]]["image"])
                            if "ts" in response:
                                ts_dict[client.token][action["ts"]] = response["ts"]
                            else:
                                print(response)
            time.sleep(0.1)
    else:
        print('Connection Failed, invalid token?')

def init(config):
    tokens = dict()
    other_tokens = dict()
    for channel in config["channels"]:
        for token in channel["tokens"]:
            if not token in tokens:
                tokens[token] = list()
            tokens[token].append(channel["name"])

    for token, channels in tokens.items():
        other_tokens[token] = list()
        for channel in channels:
            for other_channel in config["channels"]:
                if other_channel["name"]  == channel:
                    for other_token in other_channel["tokens"]:
                        other_tokens[token].append(other_token)


    for token, channels in tokens.items():
        shared_files[token] = list()
        threads[token] = threading.Thread(target=run, args=(token,other_tokens[token],channels))
        threads[token].start()

    for token in tokens:
        threads[token].join()