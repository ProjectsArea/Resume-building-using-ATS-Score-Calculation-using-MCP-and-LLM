# agent.py

import os
import tempfile

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from pymongo import MongoClient
from smolagents import ToolCallingAgent, ToolCollection, LiteLLMModel
from mcp import StdioServerParameters
import spacy
from pdf2image import convert_from_path
import pytesseract

# ===== config =====
SPACY_MODEL_PATH = "en_core_web_sm"

MONGO_URI = (
    "mongodb+srv://deepak:IYnS9CGWYVkA1Zba@chatbot.3ogfnrt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=ResumeATS"
)
DB_NAME = "ResumeATS"
RESUME_COLLECTION = "Resume"
JOB_COLLECTION = "jobs"

# ===== Flask app =====
app = Flask(__name__)
app.secret_key = "resume_ats_secret"

# ===== spaCy model =====
nlp = spacy.load(SPACY_MODEL_PATH)

# ===== Mongo =====
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
resume_col = db[RESUME_COLLECTION]
job_col = db[JOB_COLLECTION]

# ===== LLM model via LiteLLM (Ollama) =====
model = LiteLLMModel(
    model_id="ollama_chat/qwen2.5:14b",
    num_ctx=8192,
)

# ===== MCP server parameters =====
server_parameters = StdioServerParameters(
    command="uv",
    args=["run", "server.py"],
)

tool_collection = None
agent = None


# ===== helpers =====

def extract_skills(text: str):
    doc = nlp(text)
    skills = []
    for ent in doc.ents:
        if ent.label_.upper() in ["SKILL", "SKILLS"]:
            skills.append(ent.text.strip())
    seen = set()
    out = []
    for s in skills:
        k = s.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(s)
    return out


def extract_text_from_pdf_file(file_storage):
    """
    Take uploaded PDF and return OCR text.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, file_storage.filename)
        file_storage.save(temp_path)

        pages = convert_from_path(temp_path, dpi=300)
        chunks = []
        for page in pages:
            txt = pytesseract.image_to_string(page)
            chunks.append(txt)
        return "\n".join(chunks)


# ===== routes =====

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/resumes", methods=["GET", "POST"])
def resumes_page():
    if request.method == "POST":
        resume_text = request.form.get("resume_text", "").strip()
        file = request.files.get("file")

        final_text = ""

        # PDF has priority
        if file and file.filename:
            try:
                final_text = extract_text_from_pdf_file(file)
            except Exception as e:
                print("Error extracting text from PDF:", e)
                flash(f"Error reading PDF: {e}")
                return redirect(url_for("resumes_page"))
        elif resume_text:
            final_text = resume_text
        else:
            flash("Provide resume text or upload a PDF")
            return redirect(url_for("resumes_page"))

        if not final_text.strip():
            flash("No text found in resume")
            return redirect(url_for("resumes_page"))

        skills = extract_skills(final_text)

        doc = {
            "filename": file.filename if file and file.filename else "manual",
            "text": final_text,
            "skills": skills,
            "skill_count": len(skills),
        }
        resume_col.insert_one(doc)
        flash("Resume saved to database")
        return redirect(url_for("resumes_page"))

    all_resumes = list(resume_col.find())
    return render_template("resumes.html", resumes=all_resumes)


@app.route("/jobs", methods=["GET", "POST"])
def jobs_page():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        job_text = request.form.get("job_text", "").strip()

        if not title or not job_text:
            flash("Job title and description are required")
            return redirect(url_for("jobs_page"))

        skills = extract_skills(job_text)

        doc = {
            "title": title,
            "text": job_text,
            "skills": skills,
            "skill_count": len(skills),
        }
        job_col.insert_one(doc)
        flash("Job saved to database")
        return redirect(url_for("jobs_page"))

    all_jobs = list(job_col.find())
    return render_template("jobs.html", jobs=all_jobs)


@app.route("/find_match", methods=["GET", "POST"])
def find_match():
    jobs = list(job_col.find())
    selected_job_id = None
    llm_answer = None

    if request.method == "POST":
        selected_job_id = request.form.get("job_id", "")

        job_doc = None
        for j in jobs:
            if str(j["_id"]) == selected_job_id:
                job_doc = j
                break

        if not job_doc:
            flash("Selected job not found")
        else:
            job_title = job_doc.get("title", "")
            prompt = (
                f"For the job titled '{job_title}', "
                f"use the tool 'top_matches_for_job' with job_title='{job_title}' "
                "and top_k=5. Then answer with a clear list of resumes, "
                "each with match score and short reason based on overlapping skills."
            )
            llm_answer = str(agent.run(prompt))

    return render_template(
        "find_match.html",
        jobs=jobs,
        selected_job_id=selected_job_id,
        llm_answer=llm_answer,
    )


@app.route("/api/top_matches", methods=["GET"])
def api_top_matches():
    prompt = (
        "Use the tool 'top_matches_all_jobs' with top_k_per_job=3 and "
        "return a concise text summary of best resumes for each job."
    )
    answer = str(agent.run(prompt))
    return jsonify({"answer": answer})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    with ToolCollection.from_mcp(
        server_parameters,
        trust_remote_code=True
    ) as tc:
        tool_collection = tc
        agent = ToolCallingAgent(
            tools=tool_collection.tools,
            model=model,
            max_steps=6,
            description=(
                "You are an ATS assistant. "
                "Use tools to read resumes and jobs from MongoDB and compute matches."
            ),
        )

        app.run(host="0.0.0.0", port=8000, debug=True)
