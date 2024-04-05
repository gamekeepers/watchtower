from dotenv import load_dotenv
from langchain_community.chat_message_histories import SQLChatMessageHistory

import vector_util
from llm_integrations import get_llm

from flask import render_template, stream_with_context, current_app
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(f"{BASE_DIR}/../.env")

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "")

SESSION_ID_TAG = "[SESSION_ID]"
SOURCE_TAG = "[SOURCE]"
DONE_TAG = "[DONE]"


@stream_with_context
def ask_question(question, session_id):
    yield f"data: {SESSION_ID_TAG} {session_id}\n\n"
    current_app.logger.debug("Chat session ID: %s", session_id)

    chat_history = SQLChatMessageHistory(
        session_id=session_id, connection_string=f"sqlite:///{SQLITE_DB_PATH}"
    )

    if len(chat_history.messages) > 0:
        # create a condensed question
        condense_question_prompt = render_template(
            "condense_question_prompt.txt",
            question=question,
            chat_history=chat_history.messages,
        )
        condensed_question = get_llm().invoke(condense_question_prompt).content
    else:
        condensed_question = question

    current_app.logger.debug("Condensed question: %s", condensed_question)
    current_app.logger.debug("Question: %s", question)

    docs = vector_util.get_context_docs(condensed_question)

    for doc in docs:
        doc_source = {**doc.metadata, "page_content": doc.metadata["text"]}
        doc_source["name"] = f"{doc.metadata['section_title']}: {doc.metadata['paper_title']}"
        doc_source["url"] = f"file://{doc.metadata['pdf_path']}"
        current_app.logger.debug(
            "Retrieved document passage from: %s", doc.metadata["paper_title"]
        )
        yield f"data: {SOURCE_TAG} {json.dumps(doc_source)}\n\n"

    qa_prompt = render_template(
        "rag_prompt.txt",
        question=question,
        docs=docs,
        chat_history=[]  # chat_history.messages,
    )
    # print(f"QA Prompt: {qa_prompt}")
    answer = ""
    for chunk in get_llm().stream(qa_prompt):
        content = chunk.content.replace(
            "\n", " "
        )  # the stream can get messed up with newlines
        yield f"data: {content}\n\n"
        answer += chunk.content

    yield f"data: {DONE_TAG}\n\n"
    current_app.logger.debug("Answer: %s", answer)

    chat_history.add_user_message(question)
    chat_history.add_ai_message(answer)
