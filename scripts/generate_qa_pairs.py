"""
scripts/generate_qa_pairs.py
=============================
Gujarati-first QA pair generator for KissanBot.
Reads all raw Gujarat JSON files and calls Groq LLM to generate 7 QA pairs per entry.

Language distribution per entry:
  - 3 questions in Gujarati script (ગુજરાતી)
  - 2 questions in Gujarati-English mix (Gu-En)
  - 2 questions in Hindi-English mix (Hi-En)

Groq retry logic:
  - If Groq returns 429 (rate limit), wait 60 seconds and retry up to 3 times.
  - After 3 retries, skip the entry and log a warning.

Output: data/raw/gujarat_qa_pairs.json

Run: python scripts/generate_qa_pairs.py
"""

import os
import sys
import json
import time
import logging
from typing import Optional

from groq import Groq, RateLimitError

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_PATH = os.path.join(RAW_DIR, "gujarat_qa_pairs.json")

# Raw input files (output of scrape_knowledge.py)
RAW_FILES = [
    "gujarat_schemes.json",
    "gujarat_schemes_seed.json",
    "gujarat_mandi_prices.json",
    "gujarat_crop_diseases.json",
    "gujarat_msp.json",
    "central_schemes_gujarat.json",
    "gujarat_weather_seed.json",
]

# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set in .env — QA generation will fail.")
    sys.exit(1)

client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------------------------
# Retry constants
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
RETRY_WAIT_SECONDS = 60
BETWEEN_CALL_DELAY = 1.2  # seconds between successful calls (avoid burst)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
QA_SYSTEM_PROMPT = """You are an agricultural expert assistant for Gujarati farmers in Gujarat, India.
You generate realistic question-answer pairs that a Gujarat farmer might ask via phone or WhatsApp.

Language rules:
- 4 questions must be in pure Gujarati script (ગુજરાતી)
- 3 questions must be in Gujarati-English mix (e.g., "cotton ma bollworm nu shu karvu?")
- 3 questions must be in Hindi-English mix (e.g., "groundnut mein tikka disease ka ilaj")

Answer rules:
- For Gujarati questions: answer fully in Gujarati script
- For Gu-En mix: answer in Gujarati-English mix
- For Hi-En mix: answer in Hindi-English mix
- Always include specific ₹ amounts, district names, Gujarat mandi names
- Keep answers concise (2-4 sentences) — they will be read aloud on phone

Return ONLY a valid JSON array. No preamble, no markdown, no code fences, just the array:
[
  {"question": "...", "answer": "...", "language": "gu"},
  {"question": "...", "answer": "...", "language": "gu"},
  {"question": "...", "answer": "...", "language": "gu"},
  {"question": "...", "answer": "...", "language": "gu"},
  {"question": "...", "answer": "...", "language": "gu-en"},
  {"question": "...", "answer": "...", "language": "gu-en"},
  {"question": "...", "answer": "...", "language": "gu-en"},
  {"question": "...", "answer": "...", "language": "hi-en"},
  {"question": "...", "answer": "...", "language": "hi-en"},
  {"question": "...", "answer": "...", "language": "hi-en"}
]"""


def call_groq_with_retry(content: str, entry_title: str) -> Optional[list]:
    """
    Call Groq API to generate 7 QA pairs from the given content.
    Retries up to MAX_RETRIES times on 429 (rate limit), waiting RETRY_WAIT_SECONDS each time.
    Returns parsed list of QA dicts, or None if all retries exhausted.
    """
    user_message = f"Given this agricultural information about Gujarat:\n\n{content[:1500]}\n\nGenerate 10 QA pairs as specified."

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": QA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=2500,
            )
            raw_text = response.choices[0].message.content.strip()

            # Strip markdown code fences if Groq wraps in ```json ... ```
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(
                    line for line in lines if not line.startswith("```")
                ).strip()

            qa_pairs = json.loads(raw_text)
            if isinstance(qa_pairs, list) and len(qa_pairs) > 0:
                return qa_pairs
            else:
                logger.warning(f"  Unexpected format for '{entry_title}'. Skipping.")
                return None

        except RateLimitError:
            if attempt < MAX_RETRIES:
                logger.warning(
                    f"  Groq 429 rate limit on attempt {attempt}/{MAX_RETRIES} "
                    f"for '{entry_title}'. Waiting {RETRY_WAIT_SECONDS}s..."
                )
                time.sleep(RETRY_WAIT_SECONDS)
            else:
                logger.error(
                    f"  Groq 429 — exhausted {MAX_RETRIES} retries for '{entry_title}'. Skipping."
                )
                return None

        except json.JSONDecodeError as e:
            logger.warning(f"  JSON parse error for '{entry_title}': {e}. Skipping.")
            return None

        except Exception as e:
            logger.error(f"  Groq API error for '{entry_title}': {e}. Skipping.")
            return None

    return None


def load_raw_entries() -> list:
    """Load all raw scrape files and combine into a single list."""
    all_entries = []
    for filename in RAW_FILES:
        path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"  Raw file not found: {filename} — skipping.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle both list and dict (weather_zones is a dict)
        if isinstance(data, list):
            all_entries.extend(data)
            logger.info(f"  Loaded {len(data)} entries from {filename}")
        else:
            logger.info(f"  Skipping non-list file: {filename}")
    return all_entries


def generate_qa_pairs():
    logger.info("=== STEP 2: Gujarati QA Pair Generation ===")
    entries = load_raw_entries()
    logger.info(f"Total raw entries to process: {len(entries)}")

    qa_output = []   # flat list of all QA pairs with source metadata
    skipped = 0
    processed = 0

    for i, entry in enumerate(entries):
        title = entry.get("title", f"entry_{i}")
        content = entry.get("content", "")
        category = entry.get("category", "general")
        district = entry.get("district", "all")
        crop = entry.get("crop", "all")

        if len(content.strip()) < 50:
            logger.debug(f"  Skipping short entry: {title}")
            skipped += 1
            continue

        logger.info(f"  [{i+1}/{len(entries)}] Generating QA for: {title[:60]}...")
        qa_pairs = call_groq_with_retry(content, title)

        if qa_pairs:
            for qa in qa_pairs:
                qa_output.append({
                    "question": qa.get("question", ""),
                    "answer": qa.get("answer", ""),
                    "language": qa.get("language", "gu"),
                    "source_title": title,
                    "source_category": category,
                    "district": district,
                    "crop": crop,
                })
            processed += 1
        else:
            skipped += 1

        # Polite delay between calls
        time.sleep(BETWEEN_CALL_DELAY)

        # Save checkpoint every 20 entries (in case of crash)
        if (i + 1) % 20 == 0:
            _save_checkpoint(qa_output, i + 1)

    # Final save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(qa_output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("STEP 2 COMPLETE — Gujarati QA Pair Generation")
    print("=" * 60)
    print(f"  Entries processed:  {processed}")
    print(f"  Entries skipped:    {skipped}")
    print(f"  Total QA pairs:     {len(qa_output)}")
    print(f"  Output:             {OUTPUT_PATH}")
    print("=" * 60)

    # Language breakdown
    lang_counts = {}
    for qa in qa_output:
        lang = qa.get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    print("\nLanguage breakdown:")
    for lang, count in sorted(lang_counts.items()):
        print(f"  {lang}: {count} QA pairs")


def _save_checkpoint(qa_output: list, idx: int):
    checkpoint_path = OUTPUT_PATH.replace(".json", f"_checkpoint_{idx}.json")
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(qa_output, f, ensure_ascii=False, indent=2)
    logger.info(f"  Checkpoint saved ({idx} entries processed): {os.path.basename(checkpoint_path)}")


if __name__ == "__main__":
    generate_qa_pairs()
