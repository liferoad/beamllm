#  Copyright 2023 Google LLC

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# standard libraries
import os
import time
import uuid
from concurrent.futures import TimeoutError

# third party libraries
import mesop as me
import mesop.labs as mel
from dotenv import load_dotenv
from google.cloud import pubsub_v1
from rich.console import Console
from rich.markdown import Markdown

# Load environment variables from .env file
load_dotenv()

# rich console
console = Console()

# Set project ID and Pub/Sub topic names
project_id = os.environ["PROJECT_ID"]
topic_a_name = os.environ["INPUT_TOPIC"]
topic_b_name = os.environ["OUTPUT_TOPIC"]

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

topic_a_path = publisher.topic_path(project_id, topic_a_name)
topic_b_path = subscriber.topic_path(project_id, topic_b_name)

# create a chat subscription for this chat with a session id
session_id = str(uuid.uuid4())
filter = f'attributes.id="{session_id}"'
subscription_path = subscriber.subscription_path(project_id, f"{topic_b_name}-{session_id}")

# Create the subscription for this chat with the filter
try:
    subscriber.create_subscription(request={"name": subscription_path, "topic": topic_b_path, "filter": filter})
except Exception as e:
    # Subscription likely already exists
    print(f"Subscription may already exist: {e}")

is_message_received = False
current_time = time.time()
bot_response = {}
is_debug = False


def callback(message):
    bot = message.data.decode("utf-8")
    id = message.attributes.get("id")

    global is_message_received
    global current_time
    is_message_received = True
    message.ack()
    # output
    processing_time = time.time() - current_time
    if is_debug:
        markdown = Markdown(bot)
        console.log(f"[bold green]Bot {id[-4:]}[/bold green]:", markdown, f"processing time(s):{processing_time:.2f}")
    global bot_response
    bot_response = {"processing_time": processing_time, "content": bot, "bot_id": id}


streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

console.log(f"Listening for messages on [bold cyan]{subscription_path}[/bold cyan]..\n")
console.log(f"Session id: [bold cyan]{session_id}[/bold cyan]..\n")


@me.page(
    title="BeamLLM Demo Chat",
)
def page():
    mel.chat(transform, title="BeamLLM Demo Chat", bot_user=f"Chat {session_id}")


def transform(input: str, history: list[mel.ChatMessage]):
    global is_message_received
    publisher.publish(topic_a_path, data=input.encode("utf-8"), id=session_id)

    is_message_received = False
    global current_time
    current_time = time.time()

    while not is_message_received:
        try:
            streaming_pull_future.result(timeout=5)
        except TimeoutError:
            continue
    return bot_response["content"]
