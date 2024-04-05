import hashlib

import traceback

import os
import PyPDF2
import requests
import ujson
from grobid.tei import Parser

# GROBID is used to parse pdfs. Modify this if you want to use a different URL
GROBID_URL = os.getenv("GROBID_URL", "http://localhost:8080")


def count_pages(file_path):
    # opened file as reading (r) in binary (b) mode
    file = open(file_path, 'rb')
    # store data in pdfReader
    reader = PyPDF2.PdfReader(file)
    # count number of pages
    totalPages = len(reader.pages)

    return totalPages


def parse_pdf_by_grobid(pdf_path=""):
    # request grobid endpoint
    try:
        file_content = open(pdf_path, "rb").read()
        md5_hash = hashlib.md5(file_content).hexdigest()

        url = f"{GROBID_URL}/api/processFulltextDocument"
        xml_content = requests.post(url, files={'input': open(pdf_path, 'rb')}, data={})
        parser = Parser(xml_content.text)
        article = parser.parse()
        article_content = ujson.loads(article.to_json())
        article_content["md5_hash"] = md5_hash
        article_content["pdf_path"] = pdf_path
        return article_content
        # return ujson.loads(article.to_json())  # raises Runtim
    except FileNotFoundError:
        print(f"File not found: {pdf_path}")
    except Exception as err:
        print(traceback.format_exc())


def get_paragraphs_from_pdf_content(pdf_content) -> list:
    paragraphs = []
    # append abstract
    title = pdf_content.get("bibliography", {"title": ""}).get("title", "")

    abstract = pdf_content.get("abstract", "")
    sections = pdf_content["sections"]
    if abstract:
        sections.insert(0, abstract)
    # title = article_content["title"]
    for section_id, section in enumerate(sections):
        section_title = section["title"]
        for para_id, para in enumerate(section["paragraphs"]):
            para["pdf_path"]= pdf_content["pdf_path"]
            para["para_id"] = f"{section_id}_{para_id}"
            para["paper_title"] = title
            para["section_title"] = section_title
            paragraphs.append(para)
    return paragraphs
