from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.document_loaders import PyPDFLoader

from langchain_community.vectorstores import FAISS

from langchain_community.embeddings import HuggingFaceEmbeddings

# =========================
# LOAD EMBEDDING MODEL
# =========================

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# =========================
# PROCESS PDF
# =========================

def process_pdf(pdf_path):

    # Load PDF
    loader = PyPDFLoader(pdf_path)

    documents = loader.load()

    # Split text into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    docs = text_splitter.split_documents(
        documents
    )

    # Create vector database
    vectorstore = FAISS.from_documents(
        docs,
        embedding_model
    )

    # Save vector database locally
    vectorstore.save_local("faiss_index")

    return vectorstore

# =========================
# SEARCH KNOWLEDGE BASE
# =========================

def search_knowledge(query):

    # Load vector database
    vectorstore = FAISS.load_local(
        "faiss_index",
        embedding_model,
        allow_dangerous_deserialization=True
    )

    # Search similar chunks
    results = vectorstore.similarity_search(
        query,
        k=3
    )

    context = ""

    for result in results:

        context += result.page_content + "\n"

    return context