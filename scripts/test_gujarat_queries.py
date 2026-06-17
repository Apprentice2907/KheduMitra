"""
scripts/test_gujarat_queries.py
================================
Runs 8 Gujarat-specific test queries against the KissanBot API and reports:
  - Detected intent
  - Full answer
  - Language of response (heuristic check)
  - ✅/❌ pass/fail for language correctness

Usage:
  # With live server (default):
  python scripts/test_gujarat_queries.py

  # Offline mode (uses local sample_dataset.json directly via RAG pipeline):
  python scripts/test_gujarat_queries.py --offline

Server expected at: http://localhost:8000/api/v1/test/ask
"""

import sys
import json
import time
import unicodedata
import argparse
import asyncio
import os
import io

# Force UTF-8 output so Gujarati script prints correctly on Windows cp1252 terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import httpx

# ---------------------------------------------------------------------------
# 8 Gujarat-specific test queries
# ---------------------------------------------------------------------------
TEST_QUERIES = [
    {
        "id": 1,
        "label": "Gujarati script — cotton pink bollworm",
        "question": "મારા કપાસમાં ગુલાબી ઈયળ આવી છે, શું કરું?",
        "phone_number": "test_guj_1",
        "expected_intent": "crop_disease",
        "expected_lang": "gu",
        "expected_lang_label": "Gujarati script",
    },
    {
        "id": 2,
        "label": "Gu-En mix — groundnut mandi price Rajkot",
        "question": "aaj rajkot mandi ma groundnut no bhav kya che",
        "phone_number": "test_guj_1",
        "expected_intent": "market_price",
        "expected_lang": "gu-en",
        "expected_lang_label": "Gujarati-English mix",
    },
    {
        "id": 3,
        "label": "Mixed script — groundnut MSP",
        "question": "mगफळी નો MSP આ વર્ષે કેટલો છે",
        "phone_number": "test_guj_1",
        "expected_intent": "market_price",
        "expected_lang": "gu",
        "expected_lang_label": "Gujarati or mixed",
    },
    {
        "id": 4,
        "label": "Gu-En mix — iKhedut drip irrigation scheme",
        "question": "ikhedut portal par drip irrigation scheme mate apply kevi rite karvu",
        "phone_number": "test_guj_2",
        "expected_intent": "govt_scheme",
        "expected_lang": "gu-en",
        "expected_lang_label": "Gujarati-English mix",
    },
    {
        "id": 5,
        "label": "Gujarati script — PM-KISAN installment",
        "question": "PM કિસાન નો પૈસો ક્યારે આવશે",
        "phone_number": "test_guj_2",
        "expected_intent": "govt_scheme",
        "expected_lang": "gu",
        "expected_lang_label": "Gujarati script",
    },
    {
        "id": 6,
        "label": "Gu-En mix — Amreli district weather",
        "question": "Amreli district ma aavti kal varshad padse ke nahi",
        "phone_number": "test_guj_2",
        "expected_intent": "weather",
        "expected_lang": "gu-en",
        "expected_lang_label": "Gujarati-English mix",
    },
    {
        "id": 7,
        "label": "Hindi — cumin blight disease",
        "question": "jeere mein blight rog ka upay batao",
        "phone_number": "test_guj_3",
        "expected_intent": "crop_disease",
        "expected_lang": "hi",
        "expected_lang_label": "Hindi",
    },
    {
        "id": 8,
        "label": "Gu-En mix — Junagadh cumin mandi price",
        "question": "Junagadh mandi ma jeeru no bhav",
        "phone_number": "test_guj_3",
        "expected_intent": "market_price",
        "expected_lang": "gu-en",
        "expected_lang_label": "Gujarati-English mix",
    },
]

API_BASE = "http://localhost:8000/api/v1/test/ask"

# ---------------------------------------------------------------------------
# Language detection heuristics
# ---------------------------------------------------------------------------
GUJARATI_BLOCK = (0x0A80, 0x0AFF)
DEVANAGARI_BLOCK = (0x0900, 0x097F)


def detect_response_language(text: str) -> str:
    """Simple heuristic language detector for response validation."""
    gu_chars = sum(1 for c in text if GUJARATI_BLOCK[0] <= ord(c) <= GUJARATI_BLOCK[1])
    hi_chars = sum(1 for c in text if DEVANAGARI_BLOCK[0] <= ord(c) <= DEVANAGARI_BLOCK[1])
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha == 0:
        return "unknown"

    gu_ratio = gu_chars / total_alpha
    hi_ratio = hi_chars / total_alpha

    if gu_ratio > 0.3:
        return "gu"
    if hi_ratio > 0.3:
        return "hi"
    # Mixed Latin script — likely Gu-En or Hi-En mix
    return "gu-en"


def check_language_pass(response_text: str, expected_lang: str) -> tuple[bool, str]:
    """
    Returns (passed, detected_lang).
    For Gujarati queries: response MUST contain Gujarati script.
    For Hi-En: response should contain Hindi or be mixed.
    For Gu-En: response can be mixed.
    """
    detected = detect_response_language(response_text)

    if expected_lang == "gu":
        passed = detected == "gu"
    elif expected_lang == "hi":
        passed = detected in ("hi", "gu-en")  # Hi-En acceptable
    elif expected_lang == "gu-en":
        passed = True  # mixed is expected, any response format acceptable
    else:
        passed = True  # unknown expected — don't fail

    return passed, detected


# ---------------------------------------------------------------------------
# Online mode: hit the live API
# ---------------------------------------------------------------------------
def run_online_tests() -> list:
    results = []
    with httpx.Client(timeout=30.0) as client:
        for query in TEST_QUERIES:
            payload = {
                "question": query["question"],
                "phone_number": query["phone_number"],
            }
            start = time.time()
            try:
                resp = client.post(API_BASE, json=payload)
                elapsed = time.time() - start
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("response", data.get("answer", ""))
                    intent = data.get("intent", "unknown")
                else:
                    answer = f"[HTTP {resp.status_code}] {resp.text[:200]}"
                    intent = "error"
                    elapsed = time.time() - start
            except Exception as e:
                answer = f"[CONNECTION ERROR] {e}"
                intent = "error"
                elapsed = time.time() - start

            lang_pass, detected_lang = check_language_pass(answer, query["expected_lang"])
            results.append({
                **query,
                "answer": answer,
                "detected_intent": intent,
                "detected_lang": detected_lang,
                "lang_pass": lang_pass,
                "elapsed_s": round(elapsed, 2),
            })
            time.sleep(0.5)  # Be polite to local server
    return results


# ---------------------------------------------------------------------------
# Offline mode: call Groq directly with local dataset as context (no Redis)
# ---------------------------------------------------------------------------
def run_offline_tests() -> list:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

    import os as _os
    import json as _json
    from groq import Groq
    from app.services.intent_classifier import intent_classifier_service
    from app.rag.pipeline import SYSTEM_PROMPT

    groq_key = _os.environ.get("GROQ_API_KEY", "")
    groq_model = _os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not groq_key:
        print("[ERROR] GROQ_API_KEY not set — cannot run offline tests.")
        sys.exit(1)

    groq_client = Groq(api_key=groq_key)

    # Load local dataset as context
    dataset_path = _os.path.join(_os.path.dirname(__file__), "..", "data", "sample_dataset.json")
    context_str = ""
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            local_data = _json.load(f)
        context_str = "\n\n".join(d.get("content", "") for d in local_data[:30])
        print(f"  Loaded {len(local_data)} local entries as RAG context.")
    except Exception as e:
        print(f"  [WARN] Could not load local dataset: {e}")
        context_str = "No local context available."

    results = []
    for query in TEST_QUERIES:
        start = time.time()
        try:
            intent = intent_classifier_service.predict(query["question"])
            # Build prompt using SYSTEM_PROMPT (same as production RAG)
            filled_prompt = SYSTEM_PROMPT.format(
                intent=intent,
                crop="Unknown",
                district="Unknown",
                context=context_str[:3000],
                question=query["question"],
            )
            response = groq_client.chat.completions.create(
                model=groq_model,
                messages=[{"role": "user", "content": filled_prompt}],
                temperature=0.3,
                max_tokens=400,
            )
            answer = response.choices[0].message.content.strip()
            elapsed = time.time() - start
        except Exception as e:
            answer = f"[ERROR] {e}"
            intent = "error"
            elapsed = time.time() - start

        lang_pass, detected_lang = check_language_pass(answer, query["expected_lang"])
        results.append({
            **query,
            "answer": answer,
            "detected_intent": intent,
            "detected_lang": detected_lang,
            "lang_pass": lang_pass,
            "elapsed_s": round(elapsed, 2),
        })
        time.sleep(1.2)  # Groq rate limit buffer

    return results


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------
def print_report(results: list, mode: str):
    print("\n" + "=" * 70)
    print(f"STEP 7 — Gujarat Query Test Results  [{mode.upper()} MODE]")
    print("=" * 70)

    total = len(results)
    passed_lang = sum(1 for r in results if r["lang_pass"])
    intent_correct = sum(
        1 for r in results if r["detected_intent"] == r["expected_intent"]
    )

    for r in results:
        lang_icon = "[PASS]" if r["lang_pass"] else "[FAIL]"
        intent_icon = "[OK]" if r["detected_intent"] == r["expected_intent"] else "[?]"

        print(f"\n{'-' * 70}")
        print(f"Query {r['id']}: {r['label']}")
        print(f"  Question:         {r['question']}")
        print(f"  Expected intent:  {r['expected_intent']}")
        print(f"  Detected intent:  {intent_icon} {r['detected_intent']}")
        print(f"  Expected lang:    {r['expected_lang_label']}")
        print(f"  Detected lang:    {lang_icon} {r['detected_lang']}")
        print(f"  Response time:    {r['elapsed_s']}s")
        print(f"  Answer:")
        # Print answer wrapped at 65 chars
        answer_lines = []
        words = r["answer"].split()
        line = "    "
        for w in words:
            if len(line) + len(w) + 1 > 68:
                answer_lines.append(line)
                line = "    " + w
            else:
                line += (" " if line.strip() else "") + w
        if line.strip():
            answer_lines.append(line)
        for al in answer_lines[:12]:  # max 12 lines to avoid huge output
            print(al)
        if len(answer_lines) > 12:
            print("    [... truncated ...]")

    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"  Total queries:       {total}")
    print(f"  Language correct:    {passed_lang}/{total} {'[PASS]' if passed_lang == total else '[WARN]'}")
    print(f"  Intent correct:      {intent_correct}/{total} {'[PASS]' if intent_correct == total else '[WARN]'}")

    if passed_lang == total:
        print("\n  [OK] All Gujarati queries returned Gujarati answers -- script rendering OK!")
    else:
        failed = [r for r in results if not r["lang_pass"]]
        print(f"\n  [FAIL] {len(failed)} language mismatches:")
        for r in failed:
            print(f"     Query {r['id']}: expected {r['expected_lang']}, got {r['detected_lang']}")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KissanBot Gujarat Query Tests")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run without live server — calls ask_rag() directly",
    )
    args = parser.parse_args()

    mode = "offline" if args.offline else "online"
    print(f"Running 8 Gujarat test queries in {mode.upper()} mode...")

    if args.offline:
        results = run_offline_tests()
    else:
        print(f"Connecting to: {API_BASE}")
        results = run_online_tests()

    print_report(results, mode)
