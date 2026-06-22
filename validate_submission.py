"""
Lyle Intelligence — Submission CSV Validator
Checks the hackathon-required format and constraints.

Usage:
    python validate_submission.py submission.csv
"""

import sys
import csv


def validate(path: str) -> bool:
    errors: list[str] = []

    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # CHECK 1 — Required columns
        required = {"candidate_id", "rank", "score", "reasoning"}
        if reader.fieldnames is None:
            errors.append("FAIL: CSV has no header row")
            _report(errors)
            return False
        missing = required - set(reader.fieldnames)
        if missing:
            errors.append(f"FAIL: Missing columns: {missing}")

        rows = list(reader)

    # CHECK 2 — Row count
    if len(rows) == 0:
        errors.append("FAIL: CSV has 0 data rows")
    elif len(rows) > 100:
        errors.append(f"FAIL: {len(rows)} rows — max 100 allowed")

    # CHECK 3 — Ranks are 1..N sequential
    ranks = []
    for i, row in enumerate(rows):
        try:
            r = int(row["rank"])
            ranks.append(r)
        except (ValueError, KeyError):
            errors.append(f"FAIL: Row {i + 1} has invalid rank: {row.get('rank')}")

    expected = list(range(1, len(rows) + 1))
    if ranks != expected:
        errors.append(f"FAIL: Ranks are not sequential 1..{len(rows)}")

    # CHECK 4 — Scores are valid floats, non-negative, descending
    scores = []
    for i, row in enumerate(rows):
        try:
            s = float(row["score"])
            if s < 0:
                errors.append(f"FAIL: Row {i + 1} has negative score: {s}")
            scores.append(s)
        except (ValueError, KeyError):
            errors.append(f"FAIL: Row {i + 1} has invalid score: {row.get('score')}")

    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errors.append(
                f"FAIL: Scores not descending at rank {i + 1} → {i + 2}: "
                f"{scores[i]} < {scores[i + 1]}"
            )
            break  # one violation is enough

    # CHECK 5 — No duplicate candidate_ids
    ids = [row.get("candidate_id", "") for row in rows]
    dupes = set(x for x in ids if ids.count(x) > 1)
    if dupes:
        errors.append(f"FAIL: Duplicate candidate_ids: {dupes}")

    # CHECK 6 — Reasoning present and ≤300 chars
    for i, row in enumerate(rows):
        reasoning = row.get("reasoning", "")
        if not reasoning.strip():
            errors.append(f"FAIL: Row {i + 1} (rank {row.get('rank')}) has empty reasoning")
        if len(reasoning) > 300:
            errors.append(
                f"WARN: Row {i + 1} reasoning is {len(reasoning)} chars (>300, may be truncated)"
            )

    _report(errors)
    return len([e for e in errors if e.startswith("FAIL")]) == 0


def _report(errors: list[str]):
    if not errors:
        print("✅ PASS — submission CSV is valid")
    else:
        fails = [e for e in errors if e.startswith("FAIL")]
        warns = [e for e in errors if e.startswith("WARN")]
        for e in errors:
            print(f"  {e}")
        if fails:
            print(f"\n❌ INVALID — {len(fails)} error(s), {len(warns)} warning(s)")
        else:
            print(f"\n✅ PASS with {len(warns)} warning(s)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_submission.py <submission.csv>")
        sys.exit(1)
    ok = validate(sys.argv[1])
    sys.exit(0 if ok else 1)
