from flask import Flask, request
import os
from whispercpp import Whisper
import ffmpeg
import numpy as np
import openai
from notion_client import Client
import threading
import json

notion = Client(auth="NOTION_API_TOKEN")
w = Whisper.from_pretrained("tiny.en")


def create_notion_page(
    name, summary, todos, database_id="NOTION_DATABASE_ID"
):
    """
    Create a new Notion page with a summary in the body and a todo list.

    Parameters:
    - api_token (str): Your Notion integration API token.
    - database_id (str): ID of the Notion database.
    - name (str): Name of the new page.
    - summary (str): Summary content for the new page.
    - todos (list): List of to-do items.

    Returns:
    Response data from the Notion API.
    """

    data = {
        "parent": {"database_id": database_id},
        "properties": {"Name": {"title": [{"text": {"content": name}}]}},
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": summary}}]},
            },
            *[
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {"rich_text": [{"text": {"content": todo_item}}]},
                }
                for todo_item in todos
            ],
        ],
    }

    response = notion.pages.create(**data)
    return response


app = Flask(__name__)


def process_dialogue(dialogue):
    # Step 1: send the conversation and available functions to GPT
    messages = [{"role": "user", "content": dialogue}]
    functions = [
        {
            "name": "return_summary_and_todos",
            "description": "You are making a summary page for this dialogue. Return a title, a summary, and any to-do items",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "A title for the summary page.",
                    },
                    "summary": {
                        "type": "string",
                        "description": "The summary of the dialogue.",
                    },
                    "todos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The todo items. Return an empty list if there are no todo items.",
                    },
                },
                "required": ["summary", "todos", "title"],
            },
        }
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        functions=functions,
        function_call="auto",  # auto is default, but we'll be explicit
    )
    response_message = response["choices"][0]["message"]
    print('response', response_message)
    # Step 2: check if GPT wanted to call a function
    if response_message.get("function_call"):
        # Step 3: call the function

        function_name = response_message["function_call"]["name"]
        assert function_name == "return_summary_and_todos"
        function_args = json.loads(response_message["function_call"]["arguments"])
        print(function_args)

        return function_args
    else:
        raise RuntimeError("GPT-4 did not call a function")

def process_audio(file_path):
    print("processing audio")
    try:
        y, _ = (
            ffmpeg.input(
                "/home/ubuntu/life-upgrade-hackathon-backend/uploads/audio.m4a",
                threads=0,
            )
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=16000)
            .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    arr = np.frombuffer(y, np.int16).flatten().astype(np.float32) / 32768.0

    transcription = w.transcribe(arr)
    print("transcription:", transcription)

    result = process_dialogue(transcription)
    print(result)

    create_notion_page(result["title"], result["summary"], result["todos"])


@app.route("/upload", methods=["POST"])
def upload_file():
    print("got upload request")
    uploaded_file = request.files["file"]
    file_path = os.path.join("uploads", "audio.m4a")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    uploaded_file.save(file_path)

    threading.Thread(target=process_audio, args=(file_path,)).start()

    return "File uploaded successfully.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
