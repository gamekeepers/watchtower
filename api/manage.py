import sys

import ujson

from langchain.docstore.document import Document
from dotenv import load_dotenv
import os
import typer
import hashlib
from tqdm.auto import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def add_to_syspath(relative_path):
    sys.path.insert(0, f"{BASE_DIR}/{relative_path}")


add_to_syspath("..")

from api import db_util, pdf_util, vector_util

app = typer.Typer()

load_dotenv(f"{BASE_DIR}/../.env")


def parse_pdf(pdf_path=""):
    # generate md5 hash for file
    file_content = open(pdf_path, "rb").read()
    md5_hash = hashlib.md5(file_content).hexdigest()
    # print(f"md5_hash={md5_hash}")
    sqlite_client = db_util.get_connection()
    # if exists, return content from sqlite
    # TODO: move low level code to db_util
    cursor = sqlite_client.cursor()
    cursor.execute("SELECT content FROM literatures WHERE md5_hash=?", (md5_hash,))
    row = cursor.fetchone()
    if row:
        # print(f"Found content in sqlite for md5_hash={md5_hash}")
        article_content = ujson.loads(row[0])
        article_content["pdf_path"] = pdf_path
        article_content["paper_hash"] = md5_hash
        return article_content

    article_content = pdf_util.parse_pdf_by_grobid(pdf_path)

    title = article_content.get("bibliography", {"title": ""}).get("title", "")
    # store article_content in sqlite
    sqlite_client.execute("INSERT INTO literatures (md5_hash, title, content) VALUES (?, ?, ?)",
                          (md5_hash, title, ujson.dumps(article_content)))
    sqlite_client.commit()
    # add pdf path
    article_content["pdf_path"] = pdf_path
    article_content["paper_hash"] = md5_hash
    return article_content


@app.command()
def process_pdf(pdf_path: str, overwrite: bool = False):
    """
    Process pdf at pdf_path
    Args:
        pdf_path: path to pdf file
        overwrite: overwrite index if true, else skip indexing

    Returns:

    """
    filename = os.path.basename(pdf_path)
    page_count = pdf_util.count_pages(pdf_path)
    filesize = os.path.getsize(pdf_path) / (1024 * 1024)
    # TODO: move max page count to config
    if page_count > 20:
        print(f"Skipping large file: {filename}")
        return
    print(f"page_count={page_count}, size={filesize}|abs_path: {pdf_path}")
    article_content = parse_pdf(pdf_path)
    if not overwrite and vector_util.check_if_indexed(article_content["paper_hash"]):
        # print(f"Already indexed {pdf_path}")
        return
    elif overwrite:
        print(f"Overwriting index for {article_content['paper_hash']}")
        vector_util.delete_index(article_content["paper_hash"])

    paragraphs = pdf_util.get_paragraphs_from_pdf_content(article_content)
    if not paragraphs:
        print(f"No paragraphs found in {filename}")
        return
    para_docs = [Document(page_content=para["text"],
                          metadata=para) for para in paragraphs]
    chunked_para_docs = vector_util.chunk_docs(para_docs)
    print(f"filesize: {filesize}, #pages: {page_count}, #paragraphs: {len(para_docs)}, #chunks: {len(chunked_para_docs)}  for {filename}")
    for chunk in chunked_para_docs:
        chunk.metadata["text"] = chunk.page_content
    # print(chunked_para_docs[0])
    # index vectors corresponding to each paragraph

    for chunk in tqdm(chunked_para_docs):
        payload = {**chunk.metadata, "pdf_path": pdf_path}
        vector_util.index_vector(payload)


# takes in argument directory path or glob pattern
@app.command()
def index_data_from_directory(directory_path: str):
    # loop over all files that are pdfs
    # TODO: Add support for glob patterns
    print(f"Indexing data from directory: {directory_path}")
    for file in tqdm(os.listdir(directory_path)):
        if file.endswith(".pdf"):
            abs_path = os.path.abspath(os.path.join(directory_path, file))
            process_pdf(abs_path)


@app.command()
def set_data_stores():
    # set SQLITE_DB_PATH directory
    db_util.setup_sqlite_db()
    # set QDRANT_COLLECTION
    vector_util.setup_qdrant_collection()


if __name__ == "__main__":
    app()
