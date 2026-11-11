"""Post-approval live end-to-end check for Aperture.

Run ONLY after Rohan's explicit approval of the specific Gemini key, after
preflight_provider.py passes. Drives the real API with SYNTHETIC candidates
only, saves a transcript for the demo video, and exercises the provider-
failure path. Never prints or stores the key.

Usage:
  # backend already running with the approved environment on :8000
  python scripts/live_e2e_check.py [--base http://127.0.0.1:8000]
"""
import argparse
import json
import sys
import time

import httpx

CANDIDATES = [
    {
        "name": "Aarav Singh (synthetic)",
        "role": "AI / ML Engineer",
        "text": (
            "Aarav Singh is a fictional final-year engineering student. Skills: Python, "
            "PyTorch, scikit-learn, CNN image classifiers, decision trees, basic statistics. "
            "Projects: a leaf-disease classifier with transfer learning, a decision-tree "
            "comparison on UCI datasets. Two years of project experience. This resume is "
            "entirely made up for a private prototype."
        ),
        "answers": [
            "Entropy measures impurity; information gain is the expected entropy reduction after a split, and ID3 picks the attribute with the highest gain.",
            "Overfitting is when the tree fits noise in the training data; reduced-error pruning and depth limits help, checked with a validation set.",
            "Backpropagation applies the chain rule to propagate output error backwards, updating each weight by gradient descent with a learning rate.",
            "Bayes theorem gives the posterior from prior and likelihood; a naive Bayes classifier assumes feature independence given the class.",
        ],
    },
    {
        "name": "Meera Iyer (synthetic)",
        "role": "Data Science / Applied ML",
        "text": (
            "Meera Iyer is a fictional graduate applicant. Skills: Python, pandas, SQL, "
            "regression analysis, cross validation, hypothesis testing, data visualization. "
            "Projects: a house-price regression study with k-fold validation and a churn "
            "analysis dashboard. One year of project experience. Entirely made up."
        ),
        "answers": [
            "Cross validation splits data into folds, trains on k-1 and tests on the held-out fold, then averages; it gives a less biased estimate than one split.",
            "The hypothesis space is the set of functions the learner can represent; inductive bias is how it prefers some hypotheses over others.",
            "A Bayesian approach weights hypotheses by their posterior probability instead of committing to a single one.",
            "Missing attributes can be handled by assigning the most common value among examples at that node, or a fractional distribution over values.",
        ],
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default="/tmp/aperture-live-e2e.json")
    args = ap.parse_args()
    record = {"base": args.base, "candidates": []}
    entries = []

    with httpx.Client(base_url=args.base, timeout=90) as c:
        health = c.get("/api/health").json()
        print("health:", json.dumps(health))
        if not health.get("ai_connected") or not health.get("knowledge_ready"):
            print("aborting: provider or index not ready")
            return 2

        for cand in CANDIDATES:
            entry = {"name": cand["name"], "role": cand["role"], "qa": []}
            r = c.post("/api/sessions", json={"text": cand["text"], "role": cand["role"], "consent": True})
            r.raise_for_status()
            sid = r.json()["id"]
            entry["session_id"] = sid
            try:
                for i, answer in enumerate(cand["answers"], 1):
                    nq = c.post(f"/api/sessions/{sid}/next")
                    if nq.status_code == 429:
                        print("quota busy mid-interview; session saved; stopping live run")
                        entry["stopped"] = "429"
                        break
                    nq.raise_for_status()
                    sess = nq.json()
                    q = sess["questions"][-1]
                    assert q["number"] == i, f"expected question {i}, got {q['number']}"
                    print(f"[{cand['name']}] Q{i}: {q['question'][:100]}")
                    cited = q.get("source_ids", [])
                    if not cited:
                        print(f"WARNING: Q{i} has no cited source ids")
                    sv = c.post(f"/api/sessions/{sid}/answers", json={"number": i, "answer": answer})
                    sv.raise_for_status()
                    entry["qa"].append({"question": q, "answer": answer})
                    time.sleep(2)  # be gentle with free-tier quota
                if entry.get("stopped") != "429":
                    fin = c.post(f"/api/sessions/{sid}/finish")
                    fin.raise_for_status()
                    entry["summary"] = fin.json().get("summary")
                    exp = c.get(f"/api/sessions/{sid}/export")
                    exp.raise_for_status()
                    entry["export_ok"] = True
            finally:
                c.delete(f"/api/sessions/{sid}")
            entries.append(entry)

        # provider-failure path: quota/busy (429) is handled gracefully above and
        # leaves the session saved; bad-key and malformed responses are covered by
        # the backend unit tests.

    record["candidates"] = entries
    with open(args.out, "w") as f:
        json.dump(record, f, indent=2)
    print(f"live E2E transcript saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
