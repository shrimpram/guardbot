import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
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


def init_students():
    student_group_id = "S093H39222W"

    resp = client.usergroups_users_list(usergroup=student_group_id)

    if not resp:
        print("Couldn't fetch members for students")
        return

    members = resp["users"]
    assert members is not None

    cn = connection.cursor()
    for user_id in members:
        info = client.users_info(user=user_id)["user"]

        if not info:
            return

        profile = info["profile"]

        name = profile.get("real_name") or profile.get("display_name") or info["name"]

        cn.execute("SELECT student_id FROM students WHERE student_id = ?", (user_id,))
        if cn.fetchone():
            print(f"Student {user_id} ({name}) already exists, skipping")
            continue

        print(f"Adding student {user_id} ({name})")

        cn.execute(
            """
                INSERT INTO students
                  (student_id, name)
                VALUES (?, ?)
            """,
            (user_id, name),
        )

    cn.connection.commit()
    cn.close()


if __name__ == "__main__":
    init_students()
