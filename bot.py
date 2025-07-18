import os
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
from slack_sdk import WebClient
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# attach the adapter to the same app
slack_events_adapter = SlackEventAdapter(
    signing_secret=os.environ["SIGNING_SECRET"], endpoint="/slack/events", server=app
)

client = WebClient(token=os.environ["SLACK_TOKEN"])
BOT_ID = client.api_call("auth.test")["user_id"]


@slack_events_adapter.on("message")
def message(payload):
    print(payload)
    event = payload["event"]

    # Slack sends messages from bots too—ignore those
    if event.get("subtype") is not None:
        return

    if event.get("user") == BOT_ID:
        return

    # Check if this is a private channel (channel_type "group")
    # channel_id = event["channel"]
    # Respond to the same channel
    # client.chat_postMessage(
    #     channel=channel_id,
    #     text="Hello World",
    #     # thread_ts=event.get("ts"),  # optional: reply in thread
    # )


@app.route("/commands/points", methods=["POST"])
def points():
    payload = request.form
    channel_id = str(payload.get("channel_id"))
    user_id = str(payload.get("user_id"))
    text = str(payload.get("text"))

    print(payload)

    if is_staff(user_id) == False:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="This command is only invokable by staff.",
        )
        return Response(), 200

    try:
        mention, value_str, justification = text.split(maxsplit=2)
    except ValueError:
        wrong_format(channel_id, user_id)
        return Response(), 200

    try:
        value = int(value_str)
    except ValueError:
        wrong_format(channel_id, user_id)
        return Response(), 200

    if not (mention.startswith("<") and mention.endswith(">")):
        wrong_format(channel_id, user_id)
        return Response(), 200

    client.chat_postMessage(
        channel=channel_id,
        text=f"You are about to add {value} points from {mention} for {justification}?",
    )

    return Response(), 200


def is_staff(user_id: str) -> bool:
    staff_group_id = "S08SRKF1LSY"
    staff_group_users = client.usergroups_users_list(usergroup=staff_group_id)["users"]
    return user_id in str(staff_group_users)


def wrong_format(channel_id, user_id):
    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text="Please enter the command in the correct format!",
    )


if __name__ == "__main__":
    app.run(port=3000)
