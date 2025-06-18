from flask import Blueprint, request, jsonify
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.helpers import from_chain
from utils.db import get_mongo_collection
from pprint import pprint

chat_blueprint = Blueprint("chat", __name__)

# Load embedding model
embedding = HuggingFaceEmbeddings()

# === Store vectorstores per session ===
session_vectorstores = {}

def build_vectorstore_for_session(session_id):
    """Build a FAISS vectorstore for a specific session_id"""
    collection = get_mongo_collection()
    docs = []
    raw_candidates = []  # To store structured data for API response

    for candidate in collection.find({"session_id": session_id}):
        pprint(candidate)
        content = f"""
        Name: {candidate.get("name")}
        Email: {candidate.get("mail")}
        LinkedIn: {candidate.get("linkedin")}
        Education: {candidate.get("education")}
        Work Experience: {candidate.get("work_experience")}
        Skills: {', '.join(candidate.get("skills", []))}
        """
        docs.append(Document(page_content=content, metadata={"file_name": candidate.get("file_name")}))

        raw_candidates.append({
            "name": candidate.get("name"),
            "mail": candidate.get("mail"),
            "linkedin": candidate.get("linkedin"),
            "education": candidate.get("education"),
            "work_experience": candidate.get("work_experience"),
            "skills": candidate.get("skills", []),
            "file_name": candidate.get("file_name")
        })

    if docs:
        vectorstore = FAISS.from_documents(docs, embedding)
        session_vectorstores[session_id] = vectorstore
        return raw_candidates  # Return structured JSON data
    return []

# === Route to return resume data and trigger LLM embedding ===
@chat_blueprint.route("/result/<session_id>", methods=["GET"])
def result_for_session(session_id):
    try:
        candidates = build_vectorstore_for_session(session_id)

        if not candidates:
            return jsonify({"error": "No resumes found for this session"}), 404

        return jsonify(candidates)
    except Exception as e:
        print("Exception hit:", e)
        return jsonify({"error": str(e)}), 500

# === Chat route using session-specific vectorstore ===
@chat_blueprint.route("/chat/<session_id>", methods=["POST"])
def chat_with_session(session_id):
    data = request.get_json()
    query = data.get("query")

    if not query:
        return jsonify({"error": "Missing query"}), 400

    vectorstore = session_vectorstores.get(session_id)
    if not vectorstore:
        return jsonify({"error": "Session vectorstore not found"}), 404

    try:
        # qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=vectorstore.as_retriever())
        qa_chain = from_chain(vectorstore)
        answer = qa_chain.run(query)
        return jsonify({"response": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


