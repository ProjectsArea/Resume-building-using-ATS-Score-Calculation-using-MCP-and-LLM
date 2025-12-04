# job_skill_extraction.py

from flask import Flask, request, jsonify
import spacy
from pymongo import MongoClient

# Path to your saved spaCy model
SPACY_MODEL_PATH = "/home/deepak/resume kaggle/spacy_model"

# MongoDB config
MONGO_URI = "mongodb+srv://deepak:IYnS9CGWYVkA1Zba@chatbot.3ogfnrt.mongodb.net/?retryWrites=true&w=majority&appName=ResumeATS"
DB_NAME = "ResumeATS"
COLLECTION_NAME = "jobs"

print("Loading spaCy model from:", SPACY_MODEL_PATH)
nlp = spacy.load(SPACY_MODEL_PATH)

# Mongo client
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[DB_NAME]
jobs_collection = mongo_db[COLLECTION_NAME]

app = Flask(__name__)


def unique_ordered(seq):
    """Unique list keeping order."""
    seen = set()
    out = []
    for item in seq:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def extract_skills_from_text(text, nlp_model):
    """Use spaCy model to extract skill entities."""
    doc = nlp_model(text)
    raw_skills = []

    for ent in doc.ents:
        if ent.label_.upper() in ["SKILL", "SKILLS"]:
            raw_skills.append(ent.text)

    skills = unique_ordered(raw_skills)
    return skills


@app.route("/extract_job_skills", methods=["POST"])
def extract_job_skills_endpoint():
    """
    Accepts JSON: {"text": "...job description..."}
    Returns skills and saves to MongoDB "jobs" collection.
    """
    data = request.get_json(silent=True)

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in JSON body"}), 400

    job_text = data["text"]
    if not isinstance(job_text, str) or not job_text.strip():
        return jsonify({"error": "Text field is empty or invalid"}), 400

    try:
        # 1 extract skills
        skills = extract_skills_from_text(job_text, nlp)

        # 2 save to MongoDB
        doc = {
            "text": job_text,
            "skills": skills,
            "skill_count": len(skills),
            "text_length": len(job_text),
            "source": "job_description",
        }
        insert_result = jobs_collection.insert_one(doc)

        return jsonify({
            "skills": skills,
            "skill_count": len(skills),
            "text_length": len(job_text),
            "mongo_id": str(insert_result.inserted_id)
        })
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": "Processing failed", "details": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
