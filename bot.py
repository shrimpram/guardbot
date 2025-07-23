import datetime
import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, request
from slack_sdk import WebClient
from slackeventsapi import SlackEventAdapter

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

connection = sqlite3.connect(os.environ["DB_PATH"], check_same_thread=False)

app = Flask(__name__)

slack_events_adapter = SlackEventAdapter(
    signing_secret=os.environ["SIGNING_SECRET"], endpoint="/slack/events", server=app
)

client = WebClient(token=os.environ["SLACK_TOKEN"])
BOT_ID = client.api_call("auth.test")["user_id"]


@slack_events_adapter.on("message")
def message(payload):
    print(payload)


@app.route("/commands/points", methods=["POST"])
def points():
    payload = request.form
    channel_id = str(payload.get("channel_id"))
    user_id = str(payload.get("user_id"))
    text = str(payload.get("text"))

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

    mention_pattern = r"<@([^|>]+)\|[^>]+>"
    mention_regex = re.match(mention_pattern, mention)

    if not mention_regex:
        wrong_format(channel_id, user_id)
        return Response(), 200

    student_id = mention_regex.group(1)

    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text=f"You added {value} points to {mention} for {justification}.",
    )

    today = datetime.date.today().isoformat()
    cn = connection.cursor()
    cn.execute(
        """
    INSERT INTO points (
        student_id,
        award_date,
        amount,
        coach_id,
        reason
    ) VALUES (?, ?, ?, ?, ?)
        """,
        (student_id, today, value, user_id, justification),
    )
    cn.connection.commit()
    cn.close()

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


@app.route("/commands/leaderboard", methods=["POST"])
def leaderboard():
    payload = request.form
    channel_id = str(payload.get("channel_id"))

    cn = connection.cursor()
    cn.execute(
        """
    SELECT
        s.student_id,
        SUM(p.amount) AS total_points
    FROM points AS p
    INNER JOIN students AS s
        ON p.student_id = s.student_id
    GROUP BY s.student_name
    ORDER BY total_points DESC
    LIMIT 5
        """
    )

    results = cn.fetchall()
    cn.close()

    leaderboard_arr = []
    for i, (mention, total_points) in enumerate(results, 1):
        leaderboard_arr.append(f"{i}. <@{mention}>: {total_points} points")

    leaderboard = "\n".join(leaderboard_arr)

    client.chat_postMessage(
        channel=channel_id,
        text="*Vanguard Points Leaderboard*" + "\n" + leaderboard,
    )
    return Response(), 200


if __name__ == "__main__":
    app.run(port=3000)
