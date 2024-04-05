from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from uuid import uuid4
from chat import ask_question
import os
import sys


def add_to_sys_path(path):
    basedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(f"{basedir}/{path}")


add_to_sys_path("../api")
add_to_sys_path("../data")

from index_literature_data import index_data_from_directory

app = Flask(__name__, static_folder="../frontend/build", static_url_path="/")
CORS(app)


@app.route("/")
def api_index():
    return app.send_static_file("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    request_json = request.get_json()
    question = request_json.get("question")
    if question is None:
        return jsonify({"msg": "Missing question from request JSON"}), 400

    session_id = request.args.get("session_id", str(uuid4()))
    return Response(ask_question(question, session_id), mimetype="text/event-stream")


@app.cli.command()
@app.cli.argument("pdf_directory_path")
def index_data(pdf_directory_path: str):
    index_data_from_directory(pdf_directory_path)


if __name__ == "__main__":
    app.run(port=3001, debug=True)
