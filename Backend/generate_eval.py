"""
generate_eval.py — Auto-generate evaluations.csv from answers.csv.

Usage:
    python generate_eval.py

Reads:  measurements/answers.csv
Writes: measurements/evaluations.csv  (overwrites existing)

Auto-filled columns:
    timestamp, scenario, query, answer, sources_returned,
    sources_expected, recall_at_k

Manually fill after opening in Excel:
    answer_quality   — 1 (refusal) | 2 (poor) | 3 (partial) | 4 (grounded)
    answer_grounding — Grounded | Partial | Refusal | Hallucination
    notes            — optional free text
"""

import csv
import os

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
MEASUREMENTS_DIR = os.path.join(BASE_DIR, "measurements")
ANSWERS_FILE     = os.path.join(MEASUREMENTS_DIR, "answers.csv")
EVAL_FILE        = os.path.join(MEASUREMENTS_DIR, "evaluations.csv")

# ── Ground-truth expected sources per question ────────────────────────────────
# Add new questions here as you run more scenarios.
# Sources must match the exact filenames returned by the /search endpoint.
EXPECTED_SOURCES = {
    # ── RQ1 cross-document synthesis ──
    "How do different generations perceive integration between agricultural paradigms and their connections with the food system?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf",
         "1-s2.0-S0950329325003283-main.pdf"],

    "What are the generational challenges and differences in understanding agricultural paradigms and food systems ?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    # ── Single-document factual ──
    "What is the overall mean perception score of farming as a profession among agriculture students?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf"],

    "What factors predict willingness to pay for plant-based milk alternatives among Italian Gen Z consumers?":
        ["1-s2.0-S0950329325003283-main.pdf"],

    "What is the mean score for farming convenience as perceived by Gen Z students in the study?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf"],

    "What entrepreneurial factors motivate Indonesian millennials to consider careers in the agricultural sector?":
        ["Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    "What eating behavior clusters were identified among Greek university students?":
        ["nutrients-18-00758.pdf"],

    "How does emotional regulation and eating behavior relate to sustainable food choices in Gen Z?":
        ["nutrients-18-00758.pdf"],

    # ── Cross-document synthesis ──
    "How do different generations perceive farming as a career and what factors drive their attitudes?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    "What challenges prevent young people from entering the agricultural sector?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    "How does Generation Z relate to food systems and agricultural production?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "1-s2.0-S0950329325003283-main.pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    "What role does social prestige play in shaping career choices toward or away from farming?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf"],

    "How does technology influence youth attitudes toward agriculture and food systems?":
        ["Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf",
         "Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf"],

    "How do younger and older generations differ in their relationship with agricultural production and food consumption ?":
        ["Artikel+Ratna+dkk+2025+(final+author)+(CE).pdf",
         "Suwanan_2023_IOP_Conf._Ser.__Earth_Environ._Sci._1246_012037.pdf",
         "1-s2.0-S0950329325003283-main.pdf"],

    "What sustainable food behaviors are observed among younger generations and how do they connect to agricultural systems ?":
        ["nutrients-18-00758.pdf",
         "1-s2.0-S0950329325003283-main.pdf"],
}

ANSWER_QUALITY_GUIDE = (
    "1 = Refusal or no answer  |  "
    "2 = Incorrect / hallucinated  |  "
    "3 = Partially correct  |  "
    "4 = Fully grounded and accurate"
)

GROUNDING_GUIDE = "Grounded | Partial | Refusal | Hallucination"


def compute_recall(sources_returned: list[str], sources_expected: list[str]) -> float | str:
    if not sources_expected:
        return "N/A"
    returned_set = set(sources_returned)
    expected_set = set(sources_expected)
    return round(len(returned_set & expected_set) / len(expected_set), 3)


def main():
    if not os.path.exists(ANSWERS_FILE):
        print(f"ERROR: {ANSWERS_FILE} not found. Run some queries first.")
        return

    with open(ANSWERS_FILE, encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))

    # Skip header row if present
    if rows and rows[0][0] == "timestamp":
        rows = rows[1:]

    eval_rows = []
    skipped = 0

    for row in rows:
        if len(row) < 6:
            skipped += 1
            continue

        timestamp       = row[0]
        scenario        = row[1]
        query           = row[2]
        answer          = row[3]
        sources_str     = row[4]
        result_count    = row[5]

        sources_returned = [s.strip() for s in sources_str.split("|") if s.strip()]
        sources_expected = EXPECTED_SOURCES.get(query, [])
        recall           = compute_recall(sources_returned, sources_expected)

        eval_rows.append([
            timestamp,
            scenario,
            query,
            answer,                         # included so you can read while scoring
            "|".join(sources_returned),
            "|".join(sources_expected),
            recall,
            "",                             # answer_quality  — fill manually
            "",                             # answer_grounding — fill manually
            "",                             # notes — optional
        ])

    with open(EVAL_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "scenario", "query", "answer",
            "sources_returned", "sources_expected", "recall_at_k",
            f"answer_quality ({ANSWER_QUALITY_GUIDE})",
            f"answer_grounding ({GROUNDING_GUIDE})",
            "notes",
        ])
        writer.writerows(eval_rows)

    print(f"Generated {EVAL_FILE}")
    print(f"  Rows written : {len(eval_rows)}")
    print(f"  Rows skipped : {skipped}")
    print(f"  Recall summary:")
    for row in eval_rows:
        q   = row[2][:60]
        rec = row[6]
        print(f"    [{row[1]}] recall={rec}  {q}")
    print()
    print("Open evaluations.csv in Excel and fill in the two blank columns:")
    print(f"  answer_quality   → {ANSWER_QUALITY_GUIDE}")
    print(f"  answer_grounding → {GROUNDING_GUIDE}")


if __name__ == "__main__":
    main()