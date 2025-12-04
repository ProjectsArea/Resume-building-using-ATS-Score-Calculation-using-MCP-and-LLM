# resume_skill_extract.py

import os
import tempfile

from flask import Flask, request, jsonify
import spacy
from pdf2image import convert_from_path
import pytesseract
from pymongo import MongoClient
from bson import ObjectId

# Path to your saved spaCy model
SPACY_MODEL_PATH = "/home/deepak/resume kaggle/spacy_model"

# MongoDB config
MONGO_URI = "mongodb+srv://deepak:IYnS9CGWYVkA1Zba@chatbot.3ogfnrt.mongodb.net/?retryWrites=true&w=majority&appName=ResumeATS"
DB_NAME = "ResumeATS"
COLLECTION_NAME = "Resume"

print("Loading spaCy model from:", SPACY_MODEL_PATH)
nlp = spacy.load(SPACY_MODEL_PATH)

# Mongo client
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[DB_NAME]
resume_collection = mongo_db[COLLECTION_NAME]

app = Flask(__name__)


def extract_text_from_pdf(pdf_path):
    """
    Convert each page of the PDF to image and run OCR.
    Returns full text as a single string.
    """
    print(f"OCR on PDF: {pdf_path}")
    pages = convert_from_path(pdf_path, dpi=300)
    text_chunks = []

    for idx, page in enumerate(pages):
        page_text = pytesseract.image_to_string(page)
        print(f"Page {idx + 1} length: {len(page_text)}")
        text_chunks.append(page_text)

    full_text = "\n".join(text_chunks)
    return full_text


def unique_ordered(seq):
    """
    Unique list while keeping original order.
    """
    seen = set()
    out = []
    for item in seq:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def extract_skills_from_text(text, nlp_model):
    """
    Use spaCy model to extract skills entities.
    Assumes EntityRuler or NER labels skills as SKILL or similar.
    """
    doc = nlp_model(text)
    raw_skills = []

    for ent in doc.ents:
        if ent.label_.upper() in ["SKILL", "SKILLS"]:
            raw_skills.append(ent.text)

    skills = unique_ordered(raw_skills)
    return skills


@app.route("/extract_skills", methods=["POST"])
def extract_skills_endpoint():
    """
    API endpoint.
    Accepts multipart form-data with field name 'file'.
    Returns JSON with extracted skills.
    Also saves resume text and skills into MongoDB collection 'Resume'.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, file.filename)
        file.save(temp_path)

        try:
            # Step 1: OCR from PDF
            resume_text = extract_text_from_pdf(temp_path)

            if not resume_text.strip():
                return jsonify({"error": "No text found in PDF after OCR"}), 422

            # Step 2: Extract skills with spaCy model
            skills = extract_skills_from_text(resume_text, nlp)

            # Step 3: Save into MongoDB
            doc = {
                "filename": file.filename,
                "skills": skills,
                "skill_count": len(skills),
                "text": resume_text,
            }
            insert_result = resume_collection.insert_one(doc)

            return jsonify({
                "skills": skills,
                "skill_count": len(skills),
                "text_length": len(resume_text),
                "mongo_id": str(insert_result.inserted_id)
            })
        except Exception as e:
            print("Error:", str(e))
            return jsonify({"error": "Processing failed", "details": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
