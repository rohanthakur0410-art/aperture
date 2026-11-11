# Aperture
## A little context. A better conversation.

A private PGAGI take-home build: a resume-aware technical interview grounded in Tom Mitchell's *Machine Learning*. The interface follows a candidate from background review to four questions and a source-linked learning summary.

**Status, 11 November 2026:** React UI, FastAPI lifecycle, SQLite persistence, local BGE/Qdrant retrieval and live Gemini generation are implemented and tested. On 11 November the approved free-tier Gemini project was verified (model available, live call succeeded) and two full synthetic-candidate interviews ran end to end with real generation: four grounded questions each, citations validated, evidence-based summaries, JSON export and deletion. The genuine end-to-end demo video was recorded against the production app (`frontend/live-walkthrough.mjs`); the scripted fixture remains for isolated UI testing only and is never the production entrypoint. Nothing has been publicly deployed, pushed or submitted.

## Run locally
Requires Python 3.10+ and Node.js 22.12+.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ..
python scripts/download_corpus.py
cd backend
python -m app.ingest
```

The first ingestion downloads the local embedding model (BGE-small-en-v1.5) and indexes the employer-linked textbook. This can take several minutes. No embedding API key or paid service is needed. An interrupted index resumes from its checkpoint and is not exposed as ready until complete.

Once the specific Gemini project has been approved for this work and confirmed to be free-tier, set `GEMINI_API_KEY` securely as an environment variable. Never place it in source, chat, screenshots or a browser bundle. Configure `GEMINI_MODEL` to a currently available model with free standard requests. The prepared default is `gemini-3.5-flash-lite`; availability and quota must be verified on that project before claiming support. No paid fallback is implemented.

```sh
# from backend, with the approved environment already set
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. For frontend development, run `npm run dev` in `frontend`; Vite proxies `/api` to the backend. Use **one backend worker** because the local Qdrant instance owns a filesystem lock.

## First run
1. Click **Try a synthetic candidate**, or upload a synthetic PDF/text resume.
2. Review the extracted skills. Edit the text and click **Read background** if needed.
3. Choose AI/ML Engineer or Data Science/Applied ML. These roles match the supplied ML corpus; a backend-engineer role is not falsely offered without suitable materials.
4. Read the provider disclosure and confirm made-up candidate data.
5. Start. The resume's skills and experience level shape retrieval and question generation.
6. Open **Read retrieved passages** or the retrieval query to inspect evidence. PDF page numbers refer to the PDF file, not printed book numbering. Similarity is a retrieval ranking signal, not confidence.
7. Save each answer and continue. Saving and generating the next question are separate steps so failures cannot lose an answer.
8. Read the summary, inspect the transcript and export JSON. Delete the session when no longer needed.

Without a configured key, the app still permits resume preparation, but the interview button is disabled. It never silently replaces a failed live model with canned questions.

## Architecture

```text
React / TypeScript (self-hosted DM Sans + Instrument Serif fonts)
   | PDF or UTF-8 resume (max 2 MB, max 10 PDF pages)
FastAPI routes -> deterministic resume skill parser
   | reviewed skills + experience level + selected role
Interview service -> query construction -> BGE local query embedding
   |                                 -> persistent Qdrant cosine retrieval
   | <- page-aware textbook chunks + IDs + source URL
Gemini structured generation (approved synthetic data only)
   | validated question, rationale, cited chunk IDs, private expected points
SQLite -> question -> candidate answer -> next question
   | four completed answers
Gemini evidence-based summary -> SQLite -> React results / JSON export
```

### Key decisions
- **Local embeddings:** 384-dimensional BAAI/BGE-small-en-v1.5 via FastEmbed/ONNX. Keeps embedding costs at zero and resume query construction on the backend.
- **Page-aware chunks:** 210-word windows with 40-word overlap. Each chunk stays inside one PDF page, balancing context and precise provenance. Page breaks can interrupt concepts; overlap does not cross page boundaries.
- **Qdrant local:** persistent cosine vector search without a hosted database account. The current source produces 1,121 chunks after catalog/front matter is skipped. Source PDF/hash drift can change that count.
- **SQLite:** persistent session records with WAL and parameterized queries. Sessions contain structured profiles, questions, answers and generated reports. Raw resumes are not stored; small project-signal snippets extracted locally are stored in the profile but not sent to Gemini.
- **Separate save/next calls:** answer durability before the next provider request. Repeated identical saves are idempotent and overwrites are rejected.
- **Resume influence:** deterministic known-skill matches and a simple experience-level heuristic affect the query and model prompt; prior answers influence later questions. This is not a full NLP resume parser.
- **Explicit source tracing:** each generated question cites IDs validated against its retrieved chunk set. The UI shows all retrieved candidates and marks those cited. This proves provenance, not factual correctness or entailment.
- **Human review:** no pass/fail, suitability rank, personality inference or automated hiring recommendation. Summaries are study-oriented AI observations.

## API
- `GET /api/health`: live-key configuration and index readiness (a configured key is not proof a provider call works).
- `POST /api/resume/upload`: PDF/text extraction and profile.
- `POST /api/resume/parse`: text profile.
- `POST /api/sessions`: create a capability-addressed session after consent.
- `GET /api/sessions/{id}`: resume a saved session.
- `POST /api/sessions/{id}/next`: retrieve context and generate one question.
- `POST /api/sessions/{id}/answers`: save current numbered answer.
- `POST /api/sessions/{id}/finish`: generate summary after four answers.
- `GET /api/sessions/{id}/export`: structured JSON export.
- `DELETE /api/sessions/{id}`: delete the session.
- `GET /docs`: native OpenAPI documentation.

## Tests and verification
```sh
cd backend
python -m pytest -q
```
Eleven backend tests cover file safety limits, consent and role validation, disconnected AI, full database lifecycle, export/deletion, answer validation and idempotency, provider/quota failure, citation rejection, raw-resume exclusion, incomplete-index gating and chunk overlap. All model calls in unit tests are isolated fixtures.

On 11 November a live browser pass recorded the mandatory end-to-end video against the production app with real Gemini generation: four answers, summary, transcript, export, reload recovery and deletion, with no browser JS errors. Earlier scripted-fixture passes (four answers, summary, transcript, deletion, reload recovery; real local retrieval; no JS errors; no horizontal overflow at 390px/320px) covered UI states only.

For isolated UI review, `tests/ui_fixture.py` supplies scripted responses and must NEVER be used as the production entrypoint. Run the portable review scripts from `frontend` with `PYTHON` pointing to the chosen Python interpreter and optional `ARTIFACT_DIR` for outputs. The walkthrough uses explicit pacing waits for a human viewer, not backend-readiness waits.

## Data, safety and deployment limits
- Only made-up candidate details are approved for this prototype. Real resumes/candidate answers are not approved inputs.
- Gemini unpaid-service terms permit Google to use prompts/replies for product improvement and human review. The application sends derived skill labels, experience level, answers and short retrieved textbook context, not raw resume text. Answers themselves can contain personal information; use synthetic answers only.
- Treat resume text, source text and candidate answers as untrusted data. The generation instruction tells the model not to follow embedded instructions. The model has no tools or filesystem access. This reduces risk, not a prompt-injection guarantee.
- The upload framework may spool larger uploads to temporary disk; the upload is closed after reading and is not retained as a project file. Text extraction runs in memory. Resume text is held in browser memory during setup. Browser local storage retains only the opaque session ID. SQLite retains the structured profile and interview until deletion. OS/provider behavior is outside the app's retention promise.
- Session URLs are unguessable capabilities, not authenticated accounts. Anyone with a session ID can access/delete it. This is acceptable only for the current private local prototype; do not put real candidate data on a public demo.
- No public rate limiting/account system has been added. Public deployment requires an abuse/credential plan, approval, a production process manager and appropriate persistent storage.
- Local Qdrant and SQLite need durable storage. A free host with an ephemeral filesystem will lose data on restarts and is not an equivalent deployment. No existing project services were changed.
- Dependency versions were pinned to the tested environment. `requirements.lock.txt` captures the full installed environment. A fresh isolated Python install passes all 11 tests; a fresh npm install builds successfully with zero npm audit findings. A broader security review remains before external release.

## Assignment and contribution record
- Employer application: https://pgagi.in/jobs/28df1e98-f0c3-4d58-9509-d5b1a4ea9754
- Employer-linked brief: https://drive.google.com/file/d/1KazpO52Xpd0zGlFao0HWtReKx8xhCHUe/view
- Exact duration wording: **48 Hours from Assignment Receipt**. No personal deadline has been confirmed on the job page, application form, brief, or Rohan's records. Conservative internal planning target: 11 November 2026 evening (48 hours from our 9 November brief inspection); not an employer-confirmed cutoff.
- The live application form (verified 10 November 2026) requires three assignment links: a doc explaining the project (URL), a demo video (link) and the GitHub repository URL. `docs/project-explanation.md` prepares the first; it stays private until release approval, and no README URL is assumed accepted.
- The reviewed eight-page brief contains no AI-assistance ban. That does not establish any separate employer policy not present in the brief.
- Implementation was produced with substantial AI assistance, based on Rohan's direction and review. No claim is made that he wrote it unaided. He should understand and review the implementation before submitting it.
- The mandatory employer demo must be re-recorded against the real, tested provider integration after approval. The present design-review video is not that deliverable.
- The textbook and model are third-party materials. They are not relicensed as this project's code. Full textbook PDF, model weights, extracted chunks and vector data are deliberately excluded from the source archive. The setup script downloads the employer-linked source for local use.
