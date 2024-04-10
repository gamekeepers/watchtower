import os
import sys
import time
import uuid

import traceback

import torch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from transformers import AutoModelForMaskedLM, AutoTokenizer
from qdrant_client import models, QdrantClient

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "literature-docs")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "naver/splade-cocondenser-ensembledistil")


def get_tokenizer_model(model_id):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForMaskedLM.from_pretrained(model_id)
    return tokenizer, model


# TODO: appropriate time taking process elsewhere
s_time = time.time()
tokenizer, model = get_tokenizer_model(EMBEDDING_MODEL)
print(f"Time taken to load model: {time.time() - s_time} seconds")


def setup_qdrant_collection():
    q_client = QdrantClient(QDRANT_URL)
    if not QDRANT_URL:
        raise ValueError(
            "Please provide QDRANT_URL"
        )
    try:
        # if collection doesnt exist
        if not q_client.collection_exists(QDRANT_COLLECTION):
            q_client.recreate_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config={},
                sparse_vectors_config={
                    "text": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        )
                    )
                },
            )
    except ConnectionRefusedError:
        print(f"QDRANT_URL={QDRANT_URL} is not reachable")
        sys.exit(1)
    except Exception as err:
        # print(traceback.format_exc())
        print(f"QDRANT_URL={QDRANT_URL} is not reachable")


def compute_vector(text: str):
    """
    Computes a vector from logits and attention mask using ReLU, log, and max operations.

    Args:
    logits (torch.Tensor): The logits output from a model.
    attention_mask (torch.Tensor): The attention mask corresponding to the input tokens.

    Returns:
    torch.Tensor: Computed vector.
    """
    assert isinstance(text, str)
    tokens = tokenizer(text, return_tensors="pt")
    output = model(**tokens)
    logits, attention_mask = output.logits, tokens.attention_mask
    relu_log = torch.log(1 + torch.relu(logits))
    weighted_log = relu_log * attention_mask.unsqueeze(-1)
    max_val, _ = torch.max(weighted_log, dim=1)
    vec = max_val.squeeze()

    return vec, tokens


def extract_and_map_sparse_vector(vector, tokenizer):
    """
    Extracts non-zero elements from a given vector and maps these elements to their human-readable tokens using a tokenizer. The function creates and returns a sorted dictionary where keys are the tokens corresponding to non-zero elements in the vector, and values are the weights of these elements, sorted in descending order of weights.

    This function is useful in NLP tasks where you need to understand the significance of different tokens based on a model's output vector. It first identifies non-zero values in the vector, maps them to tokens, and sorts them by weight for better interpretability.

    Args:
    vector (torch.Tensor): A PyTorch tensor from which to extract non-zero elements.
    tokenizer: The tokenizer used for tokenization in the model, providing the mapping from tokens to indices.

    Returns:
    dict: A sorted dictionary mapping human-readable tokens to their corresponding non-zero weights.
    """

    # Extract indices and values of non-zero elements in the vector
    cols = vector.nonzero().squeeze().cpu().tolist()
    weights = vector[cols].cpu().tolist()

    # Map indices to tokens and create a dictionary
    idx2token = {idx: token for token, idx in tokenizer.get_vocab().items()}
    token_weight_dict = {idx2token[idx]: round(weight, 2) for idx, weight in zip(cols, weights)}

    # Sort the dictionary by weights in descending order
    sorted_token_weight_dict = {k: v for k, v in
                                sorted(token_weight_dict.items(), key=lambda item: item[1], reverse=True)}

    return sorted_token_weight_dict


def chunk_docs(docs, chunk_size=512, chunk_overlap=256):
    """
    Splits a list of documents into smaller chunks of text.

    Args:
    docs (list): A list of documents to be split into chunks.
    chunk_size (int): The size of each chunk.
    chunk_overlap (int): The number of overlapping tokens between adjacent chunks.

    Returns:
    list: A list of dictionaries, each containing the chunked text and metadata of a document.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(tokenizer,
                                                                              chunk_size=chunk_size,
                                                                              chunk_overlap=chunk_overlap
                                                                              )

    return text_splitter.transform_documents(docs)


def index_vector(payload):
    q_client = QdrantClient(QDRANT_URL)
    try:
        vec, tokens = compute_vector(payload["text"])
        indices = vec.nonzero().numpy().flatten()
        values = vec.detach().numpy()[indices]
        point_id = str(uuid.uuid4())
        q_client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    payload=payload,
                    vector={
                        "text": models.SparseVector(
                            indices=indices.tolist(), values=values.tolist()
                        )
                    },
                )
            ],
        )
    except Exception as err:
        print(traceback.format_exc())


def check_if_indexed(paper_hash):
    q_client = QdrantClient(QDRANT_URL)

    result = q_client.count(
        collection_name=QDRANT_COLLECTION,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(key="paper_hash", match=models.MatchValue(value=paper_hash)),
            ]
        ),
        exact=True,
    )
    # print(type(result))
    # print(result)
    return int(result.count) > 0


def delete_index(paper_hash):
    q_client = QdrantClient(QDRANT_URL)
    q_client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="paper_hash",
                        match=models.MatchValue(value=paper_hash),
                    ),
                ],
            )
        )
    )


def get_context_docs(query_text):
    q_client = QdrantClient(QDRANT_URL)
    query_vec, query_tokens = compute_vector(query_text)
    # query_vec.shape

    # query_expansion = vector_util.extract_and_map_sparse_vector(query_vec, tokenizer)
    # print(query_expansion)

    query_indices = query_vec.nonzero().numpy().flatten()
    query_values = query_vec.detach().numpy()[query_indices]

    # Searching for similar documents
    result = q_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=models.NamedSparseVector(
            name="text",
            vector=models.SparseVector(
                indices=query_indices,
                values=query_values,
            ),
        ),
        with_vectors=True,
    )
    docs = [Document(page_content=doc.payload["text"], metadata=doc.payload) for doc in result]
    return docs
