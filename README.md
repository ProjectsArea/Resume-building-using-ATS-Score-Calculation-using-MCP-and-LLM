Below is a ready-to-use `README.md` for your GitHub repo based on your folder structure and tech stack.

***

# Resume Builder with ATS Score using MCP Server & LLMs

Intelligent **resume–job matching and ATS score assistant** built with:  

- A **web-based resume builder/ingestion UI**  
- **Skill extraction** using spaCy and custom patterns  
- **ATS score calculation** via Jaccard similarity on skills  
- A **Model Context Protocol (MCP) server** exposing matching tools  
- A **tool-calling LLM agent** that explains scores and recommends improvements  

This project helps candidates understand how ATS-like systems view their resumes and helps recruiters quickly see the best matches for each job.

***

## ✨ Features

- Upload or paste resumes (text or PDF; PDFs are processed with OCR).  
- Create and store job descriptions from the UI.  
- Extract skills from both resumes and jobs using spaCy + custom patterns.  
- Compute ATS scores based on skill overlap (Jaccard similarity).  
- MCP server tools to:  
  - List collections and fields in MongoDB  
  - Get top matching resumes for a given job  
  - Get top matches for all jobs  
- LLM-based ATS assistant that:  
  - Calls MCP tools  
  - Returns ranked resumes with scores  
  - Explains why a resume scores high/low and how to improve it.  

***

## 📂 Project Structure

```text
.
├── agent.py                  # Flask app + LLM agent + routes
├── server.py                 # MCP server exposing MongoDB + scoring tools
├── job_skill_extraction.py   # Job description skill extraction utilities
├── resume_skill_extract.py   # Resume skill extraction utilities
├── jz_skill_patterns.jsonl   # Skill patterns (JSONL) for spaCy / pattern-matching
├── uploaded_patterns.jsonl   # Additional uploaded skill patterns
├── pyproject.toml            # Project dependencies & config (uv / poetry-style)
├── uv.lock                   # Lockfile for reproducible installs
├── data/                     # Sample resumes / jobs / test data
├── spacy_model/              # Local spaCy model directory
├── static/                   # CSS, JS, images
├── templates/                # HTML templates (home, resumes, jobs, match views)
└── __pycache__/              # Python bytecode cache (ignored in Git)
```

***

## 🧠 Architecture & Workflow

### 1. Data Ingestion

- **Resumes**  
  - User can paste resume text or upload a PDF.  
  - For PDFs, pages are converted to images and passed through OCR to extract text.  
  - Extracted text is cleaned and stored along with metadata.

- **Job Descriptions**  
  - User provides a job title and detailed description via a form.  
  - Job text is similarly processed for skill extraction.

### 2. Skill Extraction

- **spaCy model** (stored under `spacy_model/`) is used to detect skills.  
- Custom patterns from `jz_skill_patterns.jsonl` and `uploaded_patterns.jsonl` improve recognition of domain-specific skills.  
- Extracted skills are normalized (lowercased, deduplicated) and saved with each resume and job in MongoDB.

### 3. ATS Score Calculation

- The MCP server (`server.py`) connects to MongoDB and exposes tools that:  
  - Read resumes and jobs.  
  - Compute **Jaccard similarity** between job skills and resume skills:  
    - Score = intersection / union × 100 (percentage overlap).  
  - Return top-k resumes for a job, or top-k resumes for each job.

### 4. MCP Server

- Implements tools such as:  
  - **list_collections_and_fields** – discover DB schema.  
  - **top_matches_for_job** – given a job title, compute best resumes based on skill overlap.  
  - **top_matches_all_jobs** – compute best resumes for all jobs at once.  
  - **final_answer** – helper for final text responses.

### 5. LLM Agent + Web UI

- `agent.py` starts:  
  - A **Flask web server** (frontend).  
  - A **tool-calling LLM agent** configured as an ATS assistant.  
- The agent:  
  - Calls MCP tools to fetch matches and scores.  
  - Generates human-readable explanations (e.g., “This resume scores 80% because it matches X, Y, Z but misses A and B.”).  
- Flask routes and templates:  
  - `/` – Home page.  
  - `/resumes` – Upload or paste resumes, view stored resumes.  
  - `/jobs` – Add/view job descriptions.  
  - `/find_match` – Select a job and see top matching resumes with LLM explanation.  
  - `/api/top_matches` – JSON API summarizing top matches for all jobs.

***

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>
```

### 2. Create & Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# or
.\.venv\Scripts\activate       # Windows
```

### 3. Install Dependencies

If you are using `uv` / `pyproject.toml`:

```bash
uv sync
```

Or with `pip` (if you add a `requirements.txt`):

```bash
pip install -r requirements.txt
```

Make sure to also install:

- spaCy and the required English model  
- Tesseract OCR (system package)  

Example:

```bash
pip install spacy pymongo pdf2image pytesseract litellm fastmcp smolagents flask
python -m spacy download en_core_web_sm
```

Also configure Tesseract on your system (install and add to PATH).

***

## 🚀 How to Run

1. **Start the MCP Server**

   In one terminal:

   ```bash
   source .venv/bin/activate   # or equivalent
   python server.py
   ```

2. **Start the Web + Agent App**

   In another terminal:

   ```bash
   source .venv/bin/activate   # or equivalent
   python agent.py
   ```

3. **Open the Web UI**

   Visit:

   ```text
   http://localhost:8000
   ```

   (or the port configured in `agent.py`).

4. **Workflow**

   - Go to **Jobs** page → add job title + description.  
   - Go to **Resumes** page → paste resume text or upload PDF.  
   - Go to **Find Match** → select a job → view:  
     - Top matching resumes (by ATS score).  
     - LLM-generated explanation and improvement tips.

***

## 🧪 Example Usage

- Add job: *“Python Backend Developer”* with skills like Python, Flask, REST, MongoDB.  
- Upload a resume with Python + REST + SQL but missing MongoDB.  
- The system might:  
  - Show a score around 60–80% depending on overlap.  
  - Explain that the resume is strong on Python and REST but missing explicit mention of MongoDB and suggesting adding relevant projects.

***

## 📊 Future Improvements

- Add semantic similarity (e.g., embedding-based) on top of skill overlap.  
- UI improvements to behave like a full “resume builder” (sections, templates, PDF export).  
- Role-based view (recruiter vs candidate dashboards).  
- Caching and indexing to scale to large numbers of resumes and jobs.  

***

## 📝 License

Specify your license, for example:

```text
MIT License
```

***

## 🙌 Acknowledgements

- spaCy for NLP and skill extraction.  
- Tesseract OCR and pdf2image for PDF text extraction.  
- MongoDB for flexible document storage.  
- MCP and tool-calling LLM frameworks for enabling controllable, explainable ATS assistance.
