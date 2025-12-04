# server.py

from mcp.server.fastmcp import FastMCP
from pymongo import MongoClient
import litellm
from typing import List, Dict, Any

# ===== MongoDB config =====
MONGO_URI = (
    "mongodb+srv://deepak:IYnS9CGWYVkA1Zba@chatbot.3ogfnrt.mongodb.net/"
    "?retryWrites=true&w=majority&appName=ResumeATS"
)
DB_NAME = "ResumeATS"
RESUME_COLLECTION = "Resume"
JOB_COLLECTION = "jobs"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# ===== Enable LiteLLM Debugging =====
litellm._turn_on_debug()

# ===== Initialize MCP Server =====
mcp = FastMCP("mongochatbot")
mcp.memory = {
    "collection_fields": {}
}


# ===== helpers =====

def _normalize_skill_list(skills: List[str]) -> List[str]:
    out = []
    seen = set()
    for s in skills or []:
        if not isinstance(s, str):
            continue
        k = s.strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _jaccard_score(resume_skills: List[str], job_skills: List[str]) -> float:
    rs = set(_normalize_skill_list(resume_skills))
    js = set(_normalize_skill_list(job_skills))

    if not rs and not js:
        return 0.0
    if not js:
        return 0.0

    inter = rs.intersection(js)
    union = rs.union(js)
    if not union:
        return 0.0

    return round(len(inter) / len(union) * 100.0, 2)


# ===== Tool: List collections and fields =====
@mcp.tool()
def list_collections_and_fields(sample_size: int = 10) -> dict:
    """
    List all collections and their fields. Store in memory.
    """
    collection_fields = {}
    collections = db.list_collection_names()

    if not collections:
        raise ValueError("No collections found in the database")

    for collection_name in collections:
        docs = list(db[collection_name].find().limit(sample_size))
        field_set = set()
        for doc in docs:
            field_set.update(doc.keys())
        field_set.discard("_id")
        collection_fields[collection_name] = sorted(list(field_set))

    mcp.memory["collection_fields"] = collection_fields
    return {"collections_with_fields": collection_fields}


# ===== Tool 1: top matches for single job =====
@mcp.tool()
def top_matches_for_job(
    job_title: str,
    top_k: int = 3
) -> dict:
    """
    Compute top K resume matches for a given job title using skills.
    Jaccard score between job.skills and resume.skills.
    """
    jobs_col = db[JOB_COLLECTION]
    resumes_col = db[RESUME_COLLECTION]

    job_doc = jobs_col.find_one(
        {"title": {"$regex": job_title, "$options": "i"}}
    )

    if not job_doc:
        return {
            "job_title": job_title,
            "found": False,
            "message": f"No job found with title like: {job_title}",
            "matches": []
        }

    job_skills = job_doc.get("skills", [])
    job_title_resolved = job_doc.get("title", job_title)

    resume_docs = list(resumes_col.find())
    matches: List[Dict[str, Any]] = []

    for r in resume_docs:
        resume_skills = r.get("skills", [])
        filename = r.get("filename", "unknown")

        score = _jaccard_score(resume_skills, job_skills)

        matches.append({
            "filename": filename,
            "score": score,
            "resume_skills": resume_skills,
        })

    matches_sorted = sorted(matches, key=lambda x: x["score"], reverse=True)[:max(top_k, 1)]

    return {
        "job_title": job_title_resolved,
        "found": True,
        "job_skills": job_skills,
        "top_k": top_k,
        "matches": matches_sorted
    }


# ===== Tool 2: top matches for all jobs =====
@mcp.tool()
def top_matches_all_jobs(top_k_per_job: int = 3) -> dict:
    """
    For every job, compute top K resumes.
    Uses Jaccard score between job.skills and resume.skills.
    """
    jobs_col = db[JOB_COLLECTION]
    resumes_col = db[RESUME_COLLECTION]

    job_docs = list(jobs_col.find())
    resume_docs = list(resumes_col.find())

    if not job_docs:
        return {"jobs": [], "message": "No jobs found"}

    results = []

    for job in job_docs:
        job_title = job.get("title", "untitled job")
        job_skills = job.get("skills", [])

        matches = []
        for r in resume_docs:
            resume_skills = r.get("skills", [])
            filename = r.get("filename", "unknown")

            score = _jaccard_score(resume_skills, job_skills)

            matches.append({
                "filename": filename,
                "score": score,
                "resume_skills": resume_skills,
            })

        matches_sorted = sorted(matches, key=lambda x: x["score"], reverse=True)[:max(top_k_per_job, 1)]

        results.append({
            "job_title": job_title,
            "job_skills": job_skills,
            "top_k": top_k_per_job,
            "matches": matches_sorted
        })

    return {"jobs": results}


# ===== Tool: Final response rendering =====
@mcp.tool()
def final_answer(answer: str) -> str:
    return answer


# ===== Start the FastMCP server =====
if __name__ == "__main__":
    mcp.run()
