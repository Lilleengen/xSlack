import time
from slackclient import SlackClient

token = 'xoxp-'  # found at https://api.slack.com/web#authentication
members = dict()

sc = SlackClient(token)
if sc.rtm_connect():  # connect to a Slack RTM websocket
    last_text = ""
    for member in sc.api_call("channels.info", channel="C28DS27GV")["channel"]["members"]:
        print(str(member))
        member_info = sc.api_call("users.info", user=member)["user"]
        members[member] = dict()
        members[member]["name"] = member_info["name"]
        members[member]["image"] = member_info["profile"]["image_32"]
    while True:
        for action in sc.rtm_read():
            print(action)
            if "type" in action and action["type"] == "message" and action["text"] != last_text:
                last_text=action["text"]
                sc.api_call("chat.postMessage", channel=action["channel"], text=action["text"], username=members[action["user"]]["name"], icon_url=members[action["user"]]["image"])
        time.sleep(0.1)
else:
    print('Connection Failed, invalid token?')