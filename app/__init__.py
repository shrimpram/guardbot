import os

from dotenv import load_dotenv
from flask import Flask
from slack_sdk import WebClient
from slackeventsapi import SlackEventAdapter

load_dotenv()

app = Flask(__name__)

app.client = WebClient(token=os.environ["SLACK_TOKEN"])
SlackEventAdapter(
    signing_secret=os.environ["SIGNING_SECRET"],
    endpoint="/slack/events",
    server=app
)

from . import commands
