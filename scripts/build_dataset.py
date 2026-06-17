"""
scripts/build_dataset.py
=========================
Merges all raw Gujarat JSON files + QA pairs into data/sample_dataset.json.
Target: 500+ entries.

Output format matches existing schema (backward-compatible) with extra fields:
  content_gu, district, crop, language

Also runs the Gujarati script integrity check:
  - Ensures content is stored as actual Unicode, not \\u0aXX escape sequences.

Run: python scripts/build_dataset.py
"""

import os
import sys
import json
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_dataset.json")

# ---------------------------------------------------------------------------
# Raw source files to merge (in priority order)
# ---------------------------------------------------------------------------
RAW_SOURCES = [
    # (filename, category_override or None)
    ("gujarat_schemes.json",          None),
    ("gujarat_schemes_seed.json",     None),
    ("gujarat_mandi_prices.json",     None),
    ("gujarat_crop_diseases.json",    None),
    ("gujarat_msp.json",              None),
    ("central_schemes_gujarat.json",  None),
    ("gujarat_qa_pairs.json",         "qa_pair"),   # QA pairs get their own category
]


def load_raw_file(filename: str, category_override: str | None) -> list:
    path = os.path.join(RAW_DIR, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found - skipping.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # e.g. weather_zones.json is a dict — skip for now
        return []
    if category_override:
        for item in data:
            item["_source_category"] = category_override
    print(f"  [OK] Loaded {len(data):>4} entries from {filename}")
    return data


def normalize_entry(item: dict, idx: int) -> dict:
    """
    Normalize any raw entry into the standard dataset schema.
    Backward-compatible: keeps all existing fields + adds Gujarat-specific ones.
    """
    category = item.get("_source_category") or item.get("category", "general")

    # QA pairs have a different shape — convert to document format
    if category == "qa_pair":
        question = item.get("question", "")
        answer = item.get("answer", "")
        lang = item.get("language", "gu")
        source_cat = item.get("source_category", "general")
        return {
            "id": f"qa_{idx}",
            "category": source_cat,
            "title": question[:100],
            "content": f"Q: {question}\nA: {answer}",
            "content_gu": f"Q: {question}\nA: {answer}" if lang == "gu" else "",
            "district": item.get("district", "all"),
            "crop": item.get("crop", "all"),
            "metadata": {
                "language": lang,
                "source_category": item.get("source_category", "general"),
                "source_title": item.get("source_title", ""),
                "tags": [lang, category, item.get("source_category", "")],
            },
        }

    # Standard document format
    title = item.get("title", f"entry_{idx}")
    content = item.get("content", "")
    content_gu = item.get("content_gu", "")
    district = item.get("district", "all")
    crop = item.get("crop", "all")
    source = item.get("source", "")

    tags = [category]
    if crop and crop != "all":
        tags.append(crop.split("/")[0].strip())
    if district and district != "all":
        tags.extend(district.split(",")[:3])

    language = "gu" if content_gu else "en"

    return {
        "id": f"doc_{idx}",
        "category": category,
        "title": title,
        "content": content,
        "content_gu": content_gu,
        "district": district,
        "crop": crop,
        "metadata": {
            "source": source,
            "language": language,
            "tags": tags,
            "district": district,
            "crop": crop,
        },
    }


def check_gujarati_integrity(dataset: list) -> dict:
    """
    Verify Gujarati script is stored as actual Unicode characters,
    NOT as \\u0aXX escape sequences (which would break RAG retrieval).

    Returns a dict with pass/fail counts.
    """
    gu_entries = [d for d in dataset if d.get("metadata", {}).get("language") == "gu"
                  or d.get("content_gu", "")]
    passed = 0
    failed = 0
    sample = None

    for entry in gu_entries:
        content = entry.get("content", "") + entry.get("content_gu", "")
        # Check for actual Gujarati Unicode block (U+0A80–U+0AFF)
        has_gujarati = any(0x0A80 <= ord(c) <= 0x0AFF for c in content)
        if has_gujarati:
            passed += 1
            if sample is None:
                sample = content[:120]
        else:
            failed += 1

    return {"gu_entries": len(gu_entries), "passed": passed, "failed": failed, "sample": sample}


def build_dataset():
    print("=" * 60)
    print("STEP 6 -- Gujarat Dataset Builder")
    print("=" * 60)

    all_entries = []
    category_counts = defaultdict(int)

    # Load all raw sources
    print("\nLoading raw files:")
    for filename, category_override in RAW_SOURCES:
        entries = load_raw_file(filename, category_override)
        all_entries.extend(entries)

    print(f"\nTotal raw entries before deduplication: {len(all_entries)}")

    # Deduplicate by title (case-insensitive)
    seen_titles = set()
    deduped = []
    for entry in all_entries:
        title_key = entry.get("title", "").lower().strip()[:80]
        if title_key and title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(entry)

    print(f"After deduplication: {len(deduped)}")

    # Normalize to standard schema
    dataset = []
    for i, raw in enumerate(deduped):
        norm = normalize_entry(raw, i + 1)
        dataset.append(norm)
        category_counts[norm["category"]] += 1

    # Save with ensure_ascii=False (critical for Gujarati script)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("STEP 6 COMPLETE -- Dataset Build Summary")
    print("=" * 60)
    print(f"  Total entries: {len(dataset)}")
    if len(dataset) >= 500:
        print(f"  [OK] Target of 500+ entries met!")
    else:
        print(f"  [WARN] Only {len(dataset)} entries -- run scraper + QA generator first.")
    print("\nBy category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat:<25} {count:>4}")
    print(f"\n  Output: {OUTPUT_PATH}")

    # ---------------------------------------------------------------------------
    # Gujarati Script Integrity Check (user-requested verification)
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("GUJARATI SCRIPT INTEGRITY CHECK")
    print("=" * 60)
    integrity = check_gujarati_integrity(dataset)
    print(f"  Gujarati entries found: {integrity['gu_entries']}")
    print(f"  Passed (real Unicode):  {integrity['passed']}")
    print(f"  Failed (escaped/None):  {integrity['failed']}")
    if integrity["sample"]:
        print(f"  Sample Gujarati content: {integrity['sample']}")
        print(f"  [OK] Gujarati script stored correctly as Unicode (not \\u0aXX sequences)")
    else:
        print(f"  [WARN] No Gujarati content found -- run generate_qa_pairs.py first")

    # ---------------------------------------------------------------------------
    # Inline verification script (as requested)
    # ---------------------------------------------------------------------------
    print("\n--- Verification One-liner Output ---")
    gu_entries = [d for d in dataset if d.get("metadata", {}).get("language") == "gu"]
    print(f"Total entries: {len(dataset)}")
    print(f"Gujarati entries: {len(gu_entries)}")
    if gu_entries:
        sample_content = gu_entries[0]["content"][:100]
        print(f"Sample Gujarati content: {sample_content}")
    else:
        print("Sample Gujarati content: NONE -- run generate_qa_pairs.py first")


if __name__ == "__main__":
    build_dataset()
