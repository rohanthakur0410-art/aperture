# Aperture: project explanation

**Status, 11 November 2026:** the interface, backend, persistence, retrieval and live generation layers are implemented and tested. On 11 November the approved free-tier provider project was verified and two complete synthetic-candidate interviews ran with real generation (grounded questions, validated citations, summaries, export, deletion), and the end-to-end demo video was recorded against the production app. This document still requires Rohan's review before any submission.

## What Aperture is

Aperture is an AI-powered, role-based candidate screening system. It reads a candidate's resume, chooses a technical role, and runs a structured four-question interview in which every question is generated against passages retrieved from a prescribed textbook. After the fourth answer it produces a learning summary tied to the same sources, plus a full transcript that can be exported as JSON.

The design goal is that no question is a template. Each question comes from a retrieval step over the textbook, conditioned on the candidate's background, the role, and the answers given so far, and every generated question must cite the exact passages it was grounded in.

## Candidate journey

1. **Background.** The candidate uploads a PDF or plain-text resume, or loads a synthetic sample. The backend extracts text, applies upload safety limits (2 MB, 10 PDF pages), and runs a deterministic parser that produces skill labels and a simple experience-level signal. The candidate can edit the text and re-parse before continuing.
2. **Role and consent.** The candidate picks AI/ML Engineer or Data Science/Applied ML. These are the roles the supplied corpus can support; a backend-engineer role is not offered because the provided source material does not cover it. A disclosure explains what data leaves the machine, and the candidate confirms.
3. **Interview.** Four questions, one at a time. For each question the candidate can open the retrieval query and the retrieved passages, with the cited ones marked. Saving an answer and generating the next question are separate actions, so a provider failure can never lose a saved answer.
4. **Results.** A cautious, study-oriented summary based on the answers and the same sources, the full transcript with evidence, JSON export, and session deletion.

## Architecture

```text
React / TypeScript (Vite, self-hosted fonts)
   | PDF or UTF-8 resume
FastAPI -> deterministic resume parser
   | reviewed skills + experience level + role
Interview service -> query construction -> local BGE query embedding
   |                                   -> persistent Qdrant cosine retrieval
   | <- page-aware textbook chunks + IDs + source URL
Gemini structured generation (approved data only)
   | validated question, rationale, cited chunk IDs, private expected points
SQLite -> question -> answer -> next question
   | four completed answers
Gemini evidence-based summary -> SQLite -> React results / JSON export
```

- **Frontend:** React 18 with TypeScript and Vite. No UI kit; the visual language (editorial serif headings, plum side rail, coral accents) is custom CSS. Self-hosted DM Sans and Instrument Serif under the OFL.
- **Backend:** FastAPI with a small service layer. All state transitions go through per-session async locks so concurrent calls cannot interleave a question boundary.
- **Persistence:** SQLite in WAL mode with parameterized queries. One row per session carries the structured profile, questions, answers and report. Raw resume text is never stored; only small derived profile signals are kept.
- **Retrieval:** local Qdrant, cosine distance, persisted on disk next to the database.

## The RAG pipeline

### Corpus

The employer's brief links Tom Mitchell's *Machine Learning* (CMU-hosted PDF) as the primary source. A setup script downloads it, checks that it is a valid PDF and verifies its hash before ingestion.

### Chunking

The PDF is split into page-aware chunks of 210 words with a 40-word overlap. A chunk never crosses a page boundary, so every chunk maps to exactly one PDF page for provenance. Catalog and front-matter pages are skipped. The current source produces 1,121 chunks; source drift can change that count.

### Embeddings

Chunks are embedded locally with BAAI/bge-small-en-v1.5 (384 dimensions) through FastEmbed/ONNX. Embedding therefore costs nothing, sends nothing to a third party, and works offline after the first model download. Query construction uses the same model on the backend.

### Retrieval

Each interview step builds a query from the role, the candidate's skill labels and experience level, the topics covered so far, and the previous answer. The query is embedded and matched against the chunk store. The full retrieved candidate set is shown in the UI, not only the winners, so the evidence base is inspectable.

### Generation and grounding validation

The provider receives the role, the derived profile signals, the retrieved passages with their IDs, and a structured-output schema. The model returns a question, a rationale, the cited chunk IDs and private expected points. The backend validates every cited ID against the retrieved set and rejects the response if any citation points outside it. Expected points stay server-side and are never sent to the client during the interview.

This design makes provenance explicit: the system can show exactly which textbook passages a question came from. It does not prove the question is factually correct; that remains the reviewer's job.

## How the resume shapes the interview

The parser is deliberately deterministic: known-skill matching plus a simple experience-level heuristic, not a full NLP resume parser. Those signals enter the retrieval query and the generation prompt, so a candidate listing deep learning projects is asked differently from a candidate listing classical statistics. Prior answers also influence later questions, which keeps the four-question arc from repeating a topic the candidate has already answered well or badly.

## Sessions and durability

Sessions are created only after the consent step and are addressed by an unguessable ID held in browser local storage. Reloading the browser restores the exact interview state from SQLite. Answer saves are idempotent: the same save twice changes nothing, and overwriting a saved answer is rejected. Deletion removes the session record entirely.

## Engineering decisions and tradeoffs

- **Local embeddings over an embedding API:** zero cost, zero data sharing, reproducible indexing. The cost is a one-time model download and a few minutes of ingestion.
- **Local Qdrant over a hosted vector DB:** no external account, persistent on disk. The cost is a filesystem lock that limits the backend to one worker.
- **SQLite over a server database:** the whole lifecycle fits in one file with transactional safety. The cost is no horizontal scaling.
- **Separate save and next endpoints:** durability before the next paid-class provider call. The cost is one more round trip per step.
- **No silent fallback:** if the provider fails or is unconfigured, the interview does not start and no canned questions appear. The cost is a hard dependency on the approved provider for generation.
- **No scoring verdicts:** the summary reports observations and study pointers, never a pass/fail, rank or hiring recommendation. Automated hiring judgments are out of scope by design.

## Interface design

The layout is a three-stage editorial flow: a plum side rail carries progress, the ivory reading surface carries content, and coral marks the single primary action on each screen. Instrument Serif sets headings; DM Sans sets body text. The goal was a screening tool that reads like a well-set document rather than a dashboard, and every state (empty, loading, failed, restored) has an explicit design rather than a spinner alone.

## Testing and verification

- Eleven backend tests cover upload safety limits, consent and role validation, disconnected-provider behavior, the full session lifecycle, export and deletion, answer idempotency and overwrite rejection, provider failure and quota errors, citation rejection, raw-resume exclusion from provider payloads, incomplete-index gating and chunk overlap. All provider calls in tests are isolated fixtures.
- A scripted-fixture browser pass completed the full journey (four answers, summary, transcript, reload recovery, export, deletion) with real local retrieval and no JS errors, at desktop and mobile widths with no horizontal overflow.
- A fresh isolated Python environment installs and passes all tests; a fresh npm install builds with zero audit findings. Dependency versions are pinned and a full lock file is included.
- Live provider generation was verified on 11 November (free tier, synthetic data only) and the real end-to-end demo video is recorded. Remaining gate: Rohan's review, then any release steps, each with explicit approval.

## Privacy and safety

Only made-up candidate details are used in this prototype. The provider never receives raw resume text; it receives derived skill labels, an experience level, candidate answers and short retrieved textbook passages. The unpaid tier of the provider's terms allows the provider to use prompts and replies for product improvement, which is why inputs are restricted to synthetic data. Resume text, source text and answers are treated as untrusted input: the generation instruction tells the model not to follow instructions embedded in them, and the model has no tools or filesystem access.

## Known limits

- Session IDs are unguessable capabilities, not authenticated accounts. Anyone holding one can read or delete that session. Acceptable for a private local prototype; a public deployment needs accounts, rate limiting and an abuse plan.
- Local Qdrant and SQLite require durable disk; an ephemeral free host would lose data on restart.
- PDF page numbers refer to the PDF file's pages, not the printed book's numbering. Similarity scores are a retrieval ranking signal, not a confidence measure.

## Contribution record

Aperture was built with substantial AI assistance under Rohan's direction and review. No claim is made that it was written unaided; he reviews and understands the implementation before anything is submitted. The textbook and embedding model remain third-party materials and are not relicensed as part of this project's code.

## References

- Employer application page: https://pgagi.in/jobs/28df1e98-f0c3-4d58-9509-d5b1a4ea9754
- Employer-linked brief: https://drive.google.com/file/d/1KazpO52Xpd0zGlFao0HWtReKx8xhCHUe/view
- Primary source: https://www.cs.cmu.edu/~tom/files/MachineLearningTomMitchell.pdf
