import os
import logging
from functools import lru_cache
from typing import List
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Setup Logging
logger = logging.getLogger("RAG")

# Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db")
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "documents")

@lru_cache(maxsize=1)
def get_embedding_function():
    logger.info("Loading Embedding Model (gemma2:2b)...")
    return OllamaEmbeddings(model="gemma2:2b")

def get_vector_store():
    # Chroma handles persistence automatically in this dir
    return Chroma(
        persist_directory=DATA_DIR,
        embedding_function=get_embedding_function()
    )

def ingest_docs():
    """Checks documents folder and ingests new PDFs into ChromaDB."""
    if not os.path.exists(DOCS_DIR):
        logger.warning(f"Documents directory not found: {DOCS_DIR}")
        return

    files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if not files:
        logger.info("No PDF documents found to ingest.")
        return

    vector_store = get_vector_store()
    
    # Check if DB is already populated to avoid duplicate ingestion
    # A simple check: if we have any documents, assume initially ingested.
    # In a real system, we'd check file hashes.
    existing_docs = vector_store.get(limit=1)
    if existing_docs and existing_docs['ids']:
        logger.info("Vector store already contains documents. Skipping re-ingestion.")
        return

    logger.info(f"Found {len(files)} PDFs. Starting ingestion...")
    
    all_splits = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for file in files:
        file_path = os.path.join(DOCS_DIR, file)
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)
            logger.info(f"Processed {file}: {len(splits)} chunks.")
        except Exception as e:
            logger.error(f"Failed to load {file}: {e}")

    if all_splits:
        vector_store.add_documents(documents=all_splits)
        logger.info(f"Successfully ingested {len(all_splits)} chunks into ChromaDB.")

def get_retriever():
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": 3})
