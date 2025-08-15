import datetime
import os
import re
import sqlite3

from flask import Response
from flask import current_app as app
from flask import jsonify, request

from . import app

client = app.client


def get_db():
    db_path = os.environ["DB_PATH"]
    connection = sqlite3.connect(db_path, check_same_thread=False)
    return connection


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


def id_from_mention(mention):
    mention_pattern = r"<@([^|>]+)\|[^>]+>"
    mention_regex = re.match(mention_pattern, mention)

    if not mention_regex:
        return

    return mention_regex.group(1)


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
    connection = get_db()
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


@app.route("/commands/leaderboard", methods=["POST"])
def leaderboard():
    payload = request.form
    channel_id = str(payload.get("channel_id"))

    connection = get_db()
    cn = connection.cursor()
    cn.execute(
        """
    SELECT
        s.student_id,
        SUM(p.amount) AS total_points
    FROM points AS p
    INNER JOIN students AS s
        ON p.student_id = s.student_id
    GROUP BY s.name
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


@app.route("/commands/student", methods=["POST"])
def student():
    payload = request.form
    channel_id = str(payload.get("channel_id"))
    user_id = str(payload.get("user_id"))
    text = str(payload.get("text"))

    parts = text.split(maxsplit=2)

    mention = parts[0]

    student_id = id_from_mention(mention)

    if not student_id:
        client.chat_postEphemeral(
            channel=channel_id, user=user_id, text=("Please mention a student.")
        )
        return Response(), 200

    valid_columns = [
        "student_id",
        "name",
        "school",
        "grade",
        "season_goal",
        "argument_specialty",
    ]

    modifiable_columns = [
        "name",
        "school",
        "grade",
        "season_goal",
        "argument_specialty",
    ]

    if len(parts) == 1:
        connection = get_db()
        cn = connection.cursor()
        cn.execute(
            "SELECT * FROM students WHERE student_id = ?",
            (student_id,),
        )
        row = cn.fetchone()
        cn.close()

        if not row:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="No record found for that student.",
            )
        else:
            student_id, name, school, grade, goal, specialty = row
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=(
                    f"*Student ID:* {student_id}\n"
                    + f"*Name:* {name}\n"
                    + f"*School:* {school or '_none_'}\n"
                    + f"*Grade:* {grade if grade is not None else '_none_'}\n"
                    + f"*Season Goal:* {goal or '_none_'}\n"
                    + f"*Argument Specialty:* {specialty or '_none_'}"
                ),
            )
        return Response(), 200

    column = parts[1]
    if column not in valid_columns:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"Please select one of the following columns to list: {valid_columns}",
        )
        return Response(), 200

    if len(parts) == 2:
        column = parts[1]

        connection = get_db()
        cn = connection.cursor()
        cn.execute(
            f"SELECT name, {column} FROM students WHERE student_id = ?",
            (student_id,),
        )
        row = cn.fetchone()
        cn.close()

        if not row:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="No record found for that student.",
            )
        else:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=(
                    f"{row[0]}, {column}: {row[1] if row[1] is not None else '_none_'}"
                ),
            )
        return Response(), 200

    if column not in modifiable_columns:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"This column is not modifiable!",
        )
        return Response(), 200

    if len(parts) == 3:
        if not is_staff(user_id) and student_id != user_id:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="You can only modify your own information.",
            )
            return Response(), 200

        value = parts[2]

        connection = get_db()
        cn = connection.cursor()
        cn.execute(
            f"UPDATE students SET {column} = ? WHERE student_id = ?",
            (value, student_id),
        )
        connection.commit()
        cn.close()

        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"Updated *{column}* for {mention} to `{value}`.",
        )

        return Response(), 200

    wrong_format(channel_id, user_id)
    return Response(), 200


def parse_slack_message_url(url):
    try:
        # Slack often wraps URLs in <>
        clean_url = url.strip("<>")

        parts = clean_url.split("/")

        archives_index = parts.index("archives")

        # Channel ID should be right after 'archives'
        if len(parts) <= archives_index + 1:
            return None, None

        channel_id = parts[archives_index + 1]

        # Timestamp should be right after channel ID and start with 'p'
        if len(parts) <= archives_index + 2:
            return None, None

        timestamp_part = parts[archives_index + 2]

        if not timestamp_part.startswith("p"):
            return None, None

        timestamp_raw = timestamp_part[1:]

        # Convert timestamp format: 1755226511875879 -> 1755226511.875879
        if len(timestamp_raw) >= 10:
            seconds = timestamp_raw[:10]
            microseconds = timestamp_raw[10:] if len(timestamp_raw) > 10 else "000000"
            timestamp = f"{seconds}.{microseconds}"
        else:
            timestamp = timestamp_raw

        return channel_id, timestamp

    except (ValueError, IndexError):
        return None, None


def get_message_reactions(channel_id, timestamp):
    response = client.reactions_get(channel=channel_id, timestamp=timestamp)
    return response


def parse_emoji_name(emoji_input):
    # If it's in :name: format, extract the name
    if emoji_input.startswith(":") and emoji_input.endswith(":"):
        return emoji_input[1:-1]  # Remove the colons

    # Otherwise return as-is (in case user inputs just the name)
    return emoji_input


def add_users_to_channel(channel_id, user_ids):
    response = client.conversations_invite(channel=channel_id, users=user_ids)
    return response


def channel_from_mention(channel_text):
    match = re.match(r"<#([A-Z0-9]+)\|.*>", channel_text)
    if match:
        return match.group(1)

    return channel_text


@app.route("/commands/add-reactors", methods=["POST"])
def add_reactors():
    """
    Slack slash command handler
    Expected format: /add-reactors <message_url> <emoji> <target_channel>
    """
    try:
        # Parse the command text
        command_text = request.form.get("text", "").strip()

        if not command_text:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "Usage: /add-reactors <message_url> <emoji> <target_channel>\nExample: /add-reactors https://workspace.slack.com/archives/C123/p123456 👍 #general",
                }
            )

        # Split the command into parts
        parts = command_text.split()

        if len(parts) != 3:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "Invalid format. Usage: /add-reactors <message_url> <emoji> <target_channel>",
                }
            )

        message_url, emoji, target_channel = parts

        # Parse message URL
        source_channel_id, timestamp = parse_slack_message_url(message_url)

        if not source_channel_id or not timestamp:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": "Invalid message URL. Please provide a valid Slack message link.",
                }
            )

        # Parse target channel
        target_channel_id = channel_from_mention(target_channel)

        if not target_channel_id:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"Could not find channel: {target_channel}",
                }
            )

        # Get message reactions
        reactions_data = get_message_reactions(source_channel_id, timestamp)

        if not reactions_data.get("ok"):
            error_msg = reactions_data.get("error", "Unknown error")
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"Error getting message reactions: {error_msg}",
                }
            )

        # Find users who reacted with the specified emoji
        emoji_name = parse_emoji_name(emoji)
        target_users = []

        message = reactions_data.get("message", {})
        reactions = message.get("reactions", [])

        for reaction in reactions:
            if reaction.get("name") == emoji_name:
                target_users.extend(reaction.get("users", []))
                break

        if not target_users:
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"No users found who reacted with {emoji} to that message.",
                }
            )

        # Add users to target channel
        invite_result = add_users_to_channel(target_channel_id, target_users)

        if invite_result.get("ok"):
            user_count = len(target_users)
            return jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"Successfully added {user_count} user{'s' if user_count != 1 else ''} who reacted with {emoji} to {target_channel}!",
                }
            )
        else:
            error_msg = invite_result.get("error", "Unknown error")
            return jsonify(
                {
                    "response_type": "ephemeral",
                    "text": f"Error adding users to channel: {error_msg}",
                }
            )

    except Exception as e:
        print(f"Error in add_reactors: {e}")
        return jsonify(
            {
                "response_type": "ephemeral",
                "text": "An unexpected error occurred. Please try again.",
            }
        )
