# Assignment traceability, 9 November 2026

| Requirement | Implementation | Verification |
|---|---|---|
| React/Next.js frontend | React + TypeScript + Vite | Production bundle builds |
| Python backend | FastAPI routes, services, SQLite adapter, RAG, provider adapter | Eleven tests pass |
| Resume PDF/text, role choice | Upload limits, PDF text extraction, review step, two ML-aligned roles | Unit and browser tests |
| Resume-driven queries/difficulty | Skills and simple experience-level heuristic | Payload tests; live quality pending |
| Chunking / embeddings / vector DB | 210 words, 40 overlap, local BGE 384d, Qdrant | 1,121 indexed chunks; real retrieval sampled |
| Prescribed primary source | Employer-linked Mitchell textbook | URL and PDF verified |
| Dynamic, grounded generation | Gemini structured API, citations validated | Live-verified 11 Nov: two synthetic sessions, citations validated |
| Context-question-answer-storage trace | Query, contexts, IDs, rationale, questions and answers persisted | Lifecycle/export tests |
| Session continuity | SQLite WAL + local opaque ID | Browser reload recovery |
| Results/insights | Cautious learning summary + evidence + full transcript | Live summaries generated 11 Nov; UI verified |
| Repository / README | Private source archive + setup + architecture | Prepared; no public push authorized |
| Mandatory end-to-end video | Recorded 11 Nov against production app with live generation | frontend/live-walkthrough.mjs output |
| Doc explaining the project | docs/project-explanation.md prepared privately | Employer application form requires a pasted URL; publication gated |

## Application form fields (verified on the live page, 10 November 2026)
- Required under "Submitting Assignment": Doc Explaining the Project (URL), Demo Video (link), Code Base (GitHub repo URL).
- Also required: First/Last name, Email, Phone, Educational Institute, Resume/CV link.
- Optional: LinkedIn, Portfolio/GitHub, Cover Letter, Hosted Link.
- The form says: "To apply, please complete the assignment first and then fill out the application form."

## Remaining release gates
1. ~~Confirm authority for a specific provider credential and verify free-tier billing/quota.~~ Done 11 Nov (approved Composio-demo key, model + live call verified, free tier).
2. ~~Run actual generation and summary, including provider failure and different synthetic resumes.~~ Done 11 Nov (two synthetic profiles; failure path covered by unit tests and 429 handling).
3. ~~Record live end-to-end demo and explain architecture.~~ Done 11 Nov (live-walkthrough recording with component captions).
4. Rohan reviews the full flow, contributions and submission materials.
5. Only after explicit approval: public repository/deployment, project-explanation doc URL, and employer form submission.
6. The brief states "48 Hours from Assignment Receipt." No personal deadline was found on the job page, application form, brief, or Rohan's records; absence of records does not prove the employer tracks nothing. Conservative planning target: 11 November 2026 evening (48 hours from our 9 November inspection of the brief). This is our own planning target, not an employer-confirmed cutoff.
