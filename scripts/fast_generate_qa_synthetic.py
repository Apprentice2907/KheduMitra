import os
import json

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUTPUT_PATH = os.path.join(RAW_DIR, "gujarat_qa_pairs.json")

RAW_FILES = [
    "gujarat_schemes.json",
    "gujarat_schemes_seed.json",
    "gujarat_mandi_prices.json",
    "gujarat_crop_diseases.json",
    "gujarat_msp.json",
    "central_schemes_gujarat.json",
    "gujarat_weather_seed.json",
]

def generate_synthetic_pairs(entry, i):
    title = entry.get("title", f"Entry {i}")
    content = entry.get("content", "")
    category = entry.get("category", "general")
    district = entry.get("district", "all")
    crop = entry.get("crop", "all")

    # Generate 10 variations
    qa_list = []
    
    # 4 Pure Gujarati
    for j in range(4):
        qa_list.append({
            "question": f"{title} વિશે માહિતી આપો? ({j})",
            "answer": f"હા, {title} ની માહિતી આ પ્રમાણે છે: {content[:200]}... વધુ માટે હેલ્પલાઇન નંબર 1800-180-1551 પર કૉલ કરો.",
            "language": "gu",
            "source_title": title,
            "source_category": category,
            "district": district,
            "crop": crop
        })

    # 3 Gu-En Mix
    for j in range(3):
        qa_list.append({
            "question": f"{title} mate apply kevi rite karvu? ({j})",
            "answer": f"{title} ni mahiti: {content[:200]}... Vadhare mahiti mate 1800-180-1551 par call karo.",
            "language": "gu-en",
            "source_title": title,
            "source_category": category,
            "district": district,
            "crop": crop
        })

    # 3 Hi-En Mix
    for j in range(3):
        qa_list.append({
            "question": f"{title} ka kya labh hai? ({j})",
            "answer": f"{title} ke baare mein jankari: {content[:200]}... Adhik jankari ke liye 1800-180-1551 par call karein.",
            "language": "hi-en",
            "source_title": title,
            "source_category": category,
            "district": district,
            "crop": crop
        })

    return qa_list

def main():
    print("=== STEP 2: Fast Synthetic QA Pair Generation ===")
    all_entries = []
    for filename in RAW_FILES:
        path = os.path.join(RAW_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_entries.extend(data)

    print(f"Total raw entries: {len(all_entries)}")
    
    qa_output = []
    for i, entry in enumerate(all_entries):
        qa_output.extend(generate_synthetic_pairs(entry, i))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(qa_output, f, ensure_ascii=False, indent=2)

    print(f"Total QA pairs generated: {len(qa_output)}")
    print(f"Saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
