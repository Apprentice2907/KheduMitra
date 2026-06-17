"""
ml/train_intent_classifier.py
==============================
Trains a TF-IDF + LinearSVC intent classifier for KissanBot (Gujarat-first).

Intents: crop_disease | market_price | govt_scheme | weather

Training data:
  - Original generic Hindi/English examples (~2,400 augmented)
  - NEW: 600+ Gujarat-specific examples:
      * Gujarati script (pure Gujarati)
      * Gu-En mix (Gujarati-English)
      * Hi-En mix (Hindi-English)
      * Programmatic generation: 33 districts × 4 intents × major crops

Output: models/intent_classifier.pkl

Run: python ml/train_intent_classifier.py
"""

import os
import sys
import pickle
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.gujarat_constants import (
    GUJARAT_DISTRICTS,
    GUJARAT_CROPS,
    GUJARAT_MANDIS,
)

# ---------------------------------------------------------------------------
# Original generic training data (unchanged from before)
# ---------------------------------------------------------------------------

def generate_generic_training_data():
    """Original generic Hindi/English dataset (~2,400 examples via augmentation)."""
    examples = {
        "crop_disease": [
            "meri fasal mein disease hai",
            "cotton leaves are curling",
            "kapaas ke patte mod rahe hain",
            "wheat has yellow spots",
            "gehu me pila ratua lag gaya hai",
            "what to spray for whitefly",
            "safed makhi ki dawai batao",
            "crop is turning yellow",
            "fasal sukh rahi hai",
            "patton par dhabbe hain",
            "leaves have brown spots",
            "disease in tomato plant",
            "tamatar me keeda lag gaya",
            "pesticide for fungus",
            "fungicide for yellow rust",
        ],
        "market_price": [
            "mandi bhav kya hai",
            "what is the price of cotton",
            "aaj ka kapaas ka rate",
            "wheat price in punjab",
            "gehu ka kya bhav chal raha hai",
            "how much is soybean selling for",
            "soybean ka mandi rate",
            "onion price nasik",
            "pyaz ka bhav batao",
            "market price for tomato",
            "tamatar mandi bhav",
            "rate of mustard today",
            "sarson ka price kya hai",
            "is it a good time to sell wheat",
            "bhav kab badhega",
        ],
        "govt_scheme": [
            "kya PM-KISAN ka paisa aaya",
            "pm kisan installment status",
            "mera registration number hai",
            "how to apply for pmfby",
            "fasal bima yojana kya hai",
            "crop insurance details",
            "subsidy for tractor",
            "tractor ki subsidy kaise milegi",
            "kisan credit card apply",
            "kcc loan kaise le",
            "government schemes for farmers",
            "sarkari yojana batao",
            "when will 14th installment come",
            "mera kisan samman nidhi ka paisa nahi aaya",
            "eligibility for pm kisan",
        ],
        "weather": [
            "aaj ka mausam kaisa hai",
            "weather forecast for tomorrow",
            "kal barish hogi kya",
            "will it rain today",
            "pune district weather",
            "pune ka mausam batao",
            "temperature kya hai",
            "kitni dhoop niklegi",
            "is there a storm warning",
            "toofan aane wala hai kya",
            "humidity in nashik",
            "nashik me barish kab hogi",
            "when will monsoon arrive",
            "monsoon kab aayega",
            "weather updates for next 3 days",
        ],
    }

    fillers_prefix = ["mujhe batao ", "please tell me ", "kya aap jante hain ", "sir ", "hello ", ""]
    fillers_suffix = [" please", " ji", " yaar", " abhi", ""]

    X, y = [], []
    for intent, sentences in examples.items():
        for _ in range(40):  # 40 × 15 ≈ 600 per class
            for sentence in sentences:
                prefix = random.choice(fillers_prefix)
                suffix = random.choice(fillers_suffix)
                X.append(f"{prefix}{sentence}{suffix}".strip().lower())
                y.append(intent)
    return X, y


# ---------------------------------------------------------------------------
# Gujarat-specific training data
# ---------------------------------------------------------------------------

# Seed examples manually crafted (Gujarati script + Gu-En + Hi-En)
GUJARAT_SEED: dict[str, list[str]] = {
    "crop_disease": [
        # Gujarati script
        "મારા ઘઉ‌ ∘ ∘ ∘ ∘",
        "ક‌ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "મ‌ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        # Gujarati-English mix
        "cotton ma bollworm nu shu karvu",
        "groundnut ma tikka disease no upay",
        "castor ma semilooper keeda che",
        "kapas na pana vali javay che",
        "magfali ma stem rot kevi rite rokvu",
        "cumin ma blight disease no ilaj",
        "banana ma panama wilt che shu karvu",
        "bajra ma downy mildew nu upchar",
        "diveli ma capsule borer nu spray",
        "onion ma purple blotch nu dava",
        "wheat ma yellow rust spread thashe",
        "tal na paka te pahela keeda lage",
        # Hindi-English mix
        "groundnut mein tikka disease ka ilaj",
        "kapas mein pink bollworm ka upay batao",
        "jeere mein blight rog ka upay",
        "castor mein semilooper ka spray",
        "gehun mein pila ratua lag gaya",
        "kele mein panama wilt ka ilaj",
        "bajra mein downy mildew kya kare",
        "onion mein purple blotch ka dawai",
    ],
    "market_price": [
        # Gujarati script
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        # Gujarati-English mix
        "aaj rajkot mandi ma groundnut no bhav",
        "junagadh mandi ma jeeru no rate kya che",
        "amreli ma magfali no bhav ketlo che",
        "surat mandi ma kela no bhav",
        "anand mandi ma batata no rate",
        "ahmedabad ma kapas no aajno bhav",
        "rajkot mandi ma castor no bhav",
        "gondal mandi ma magfali rate",
        "unjha ma jeeru no aaj no bhav",
        "mehsana ma variyali no rate",
        "bhavnagar ma tal no mandi bhav",
        "vadodara ma ghau no rate",
        "rajkot mandi ma MSP kya che",
        # Hindi-English mix
        "Rajkot mandi mein groundnut ka aaj ka bhav",
        "junagadh mandi mein jeera ka rate",
        "amreli mein castor ka mandi bhav",
        "surat mandi mein kela ka price",
        "anand mein potato ka aaj ka rate",
        "ahmedabad mandi mein cotton ka bhav",
        "unjha mein jeere ka MSP kitna hai",
    ],
    "govt_scheme": [
        # Gujarati script
        "∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "iKhedut portal par ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘",
        "PM ∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "પીએમ કિસાન યોજના",
        "કિસાન સન્માન નિધિ",
        "સરકાર ની મદદ ક્યારે મળશે",
        "પીએમ કિસાન નો હપ્તો",
        "ખેડૂત સહાય યોજના",
        "સબસિડી માટે અરજી",
        "iKhedut પોર્ટલ પર નોંધણી",
        "ટ્રેક્ટર સબસિડી સહાય",
        "સરકાર ની યોજના",
        "કિસાન યોજના ના પૈસા",
        "પીએમ કિસાન સન્માન નિધિ ના 2000 રૂપિયા",
        "અનુદાન ક્યારે મળશે",
        "સરકારી સહાય",
        "પીએમ કિસાન પૈસા ક્યારે આવશે",
        "કિસાન યોજના નું ફોર્મ",
        "ખેતી માટે સબસિડી",
        "પીએમ કિસાન 14મો હપ્તો",
        "સરકાર ની સબસિડી",
        "સન્માન નિધિ યોજના લાભ",
        # New Gu-En mix specifically for PM-KISAN and schemes
        "pm kisan no hapto",
        "sarkar ni sahay",
        "kisan yojana na paisa",
        "pm kisan samman nidhi no labh",
        "ikhedut par subsidy",
        "sarkar ni madad kyare malse",
        "anudan mate apply kevi rite karvu",
        "pm kisan yojana status check",
        "kisan samman nidhi gujarat",
        "tractor mate sarkar ni sahay",
        "pm kisan paisa account ma nathi aavya",
        "ikhedut portal par kisan yojana form",
        "sarkar ni drip irrigation subsidy",
        "pm kisan 2000 rupees kyare aavse",
        "gujarat sarkar ni khedut yojana",
        "khedut sahay yojana details",
        "subsidy mate ikhedut portal",
        "sarkar ni anudan yojana",
        "pm kisan no 15mo hapto",
        "samman nidhi yojana helpline",
        "pm kisan list ma nam che ke nahi",
        "sarkar ni madad joiye che",
        "kisan yojana registration kevi rite karvu",
        "ikhedut subsidy status",
        "khedut yojana 2024",
        "sarkar ni yojana no labh levu che",
        "pm kisan samman nidhi gujarat portal",
        "pm kisan sahay",
        # Gujarati-English mix
        "ikhedut portal par drip irrigation subsidy mate apply kevi rite karvu",
        "PM kisan no paiso kyare aavse",
        "fasal bima mate registration kevi rite karvu",
        "kisan credit card mate shu document joiye",
        "tractor subsidy mate apply kevi rite karvu",
        "soil health card kyathi malavvu",
        "ikhedut par kankrit scheme list jovu",
        "mukhyamantri kisan sahay yojana no labh kevi rite lavvu",
        "pm kisan samman nidhi Gujarat helpline number",
        "PMFBY kharif deadline kyari che",
        "KCC interest rate kya che Gujarat ma",
        # Hindi-English mix
        "ikhedut portal par drip irrigation ke liye apply karna hai",
        "pm kisan ka paisa kab aayega",
        "Gujarat mein fasal bima ka premium kitna hai",
        "kisan credit card ke liye document kya chahiye",
        "tractor subsidy Gujarat mein kitni milti hai",
        "soil health card kaise milega Gujarat mein",
        "pm kisan mein registration kaise kare",
    ],
    "weather": [
        # Gujarati script
        "∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘",
        "∘ ∘ ∘ ∘ ∘ ∘ ∘",
        # Gujarati-English mix
        "Amreli district ma kal varshad padse ke nahi",
        "Rajkot ma aaj mausam kaevo che",
        "Saurashtra ma monsoon kyare avse",
        "Junagadh ma kal rain forecast",
        "Surat ma flood nu risk che ke nahi",
        "Kutch ma aaj temperature ketlu che",
        "Bhavnagar ma cyclone warning che ke",
        "Mehsana ma kal hava pani",
        "Anand ma fog alert che ke",
        # Hindi-English mix
        "Amreli mein kal barish padegi kya",
        "Rajkot mein aaj mausam kaisa hai",
        "Saurashtra mein monsoon kab aayega",
        "Junagadh mein 3 din ka weather forecast",
        "Gujarat mein barish ki sambhavna",
        "Kutch district weather forecast tomorrow",
    ],
}


def generate_gujarat_programmatic_data() -> tuple[list, list]:
    """
    Programmatically generate 600+ Gujarat-specific examples.
    Covers 33 districts × 4 intents × major crops with template filling.
    """
    X, y = [], []
    crops_en = list(GUJARAT_CROPS.keys())
    crops_gu = list(GUJARAT_CROPS.values())
    mandis = list(GUJARAT_MANDIS.keys())

    # ----------------------------------------------------------------
    # Templates (use {district}, {crop_en}, {crop_gu}, {mandi} as slots)
    # ----------------------------------------------------------------
    disease_templates = [
        "mara {crop_en} ma keeda laga che",
        "{crop_en} na pana par dabbe pad gaya",
        "{district} district ma {crop_en} ma bimari",
        "{crop_en} no pako kharab thai gayo",
        "mara {crop_en} ma {crop_en} fungus che",
        "{crop_gu} ∘ ∘ ∘ ∘ ∘ {district}",
        "{crop_en} mein disease hai {district} mein",
        "{crop_en} ka keeda {district} mein lag gaya",
        "shu spray karvanu {crop_en} ma {district}",
        "{crop_en} leaves turning yellow in {district} Gujarat",
    ]

    price_templates = [
        "aaj {mandi} mandi ma {crop_en} no bhav",
        "{mandi} ma {crop_gu} no rate ketlo che",
        "{crop_en} ka {mandi} mandi mein aaj ka rate",
        "Gujarat {mandi} mein {crop_en} ka bhav",
        "{mandi} APMC {crop_en} price today",
        "{mandi} mandi {crop_en} rate",
        "aaj {crop_en} no mandi bhav {district} Gujarat",
        "{crop_gu} ∘ ∘ {mandi} ∘ ∘",
        "{crop_en} MSP 2024 Gujarat kya hai",
        "{district} mein {crop_en} bechna hai rate kya hai",
    ]

    scheme_templates = [
        "{district} ma ikhedut portal par {crop_en} subsidy",
        "Gujarat {district} ma pm kisan installment",
        "{crop_en} ke liye {district} mein subsidy kya hai",
        "ikhedut par {crop_en} mate apply {district}",
        "{district} ma fasal bima {crop_en} ka",
        "Gujarat mein {crop_en} farmers ke liye scheme",
        "{crop_en} seed subsidy Gujarat 2024",
        "{district} district ma kisan credit card",
        "Gujarat {district} {crop_en} growers helpline",
        "pm kisan status {district} Gujarat",
    ]

    weather_templates = [
        "{district} ma aavti kal varshad padse",
        "{district} district mein kal barish hogi kya",
        "Gujarat {district} weather forecast tomorrow",
        "{district} ma monsoon status",
        "{district} mein aaj temperature kitna hai",
        "{district} ma cyclone warning che ke nahi",
        "Saurashtra {district} mausam",
        "Gujarat {district} ma vatar kevo che",
        "{district} rain forecast 3 days",
        "Gujarat {district} ma aaj no mausam",
    ]

    templates_by_intent = {
        "crop_disease": disease_templates,
        "market_price": price_templates,
        "govt_scheme": scheme_templates,
        "weather": weather_templates,
    }

    random.seed(42)
    for intent, templates in templates_by_intent.items():
        for district in GUJARAT_DISTRICTS:
            for _ in range(5):  # 5 samples per district per intent ≈ 33 × 5 × 4 = 660
                tmpl = random.choice(templates)
                crop_idx = random.randint(0, len(crops_en) - 1)
                mandi = random.choice(mandis)
                text = tmpl.format(
                    district=district,
                    crop_en=crops_en[crop_idx],
                    crop_gu=crops_gu[crop_idx],
                    mandi=mandi,
                )
                X.append(text.lower())
                y.append(intent)

    return X, y


def generate_gujarat_seed_data() -> tuple[list, list]:
    """Add seed manual examples with augmentation."""
    X, y = [], []
    fillers = ["", "bhai ", "sir ", "ji ", "please "]
    suffixes = ["", " please", " batao", " jaldi", " important"]

    for intent, sentences in GUJARAT_SEED.items():
        for _ in range(8):  # augment 8× each seed
            for sent in sentences:
                pre = random.choice(fillers)
                suf = random.choice(suffixes)
                X.append(f"{pre}{sent}{suf}".strip().lower())
                y.append(intent)
    return X, y


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Gujarat-First Intent Classifier Training")
    print("=" * 60)

    random.seed(42)

    print("\n[1/4] Generating generic training data...")
    X_gen, y_gen = generate_generic_training_data()
    print(f"  Generic examples: {len(X_gen)}")

    print("[2/4] Generating Gujarat seed examples...")
    X_seed, y_seed = generate_gujarat_seed_data()
    print(f"  Gujarat seed (augmented): {len(X_seed)}")

    print("[3/4] Generating Gujarat programmatic examples...")
    X_prog, y_prog = generate_gujarat_programmatic_data()
    print(f"  Gujarat programmatic: {len(X_prog)}")

    # Combine all
    X = X_gen + X_seed + X_prog
    y = y_gen + y_seed + y_prog
    print(f"\n  TOTAL training examples: {len(X)}")

    # Intent distribution
    from collections import Counter
    dist = Counter(y)
    for intent, count in sorted(dist.items()):
        print(f"    {intent}: {count}")

    print("\n[4/4] Training TF-IDF + LinearSVC pipeline...")
    pipeline = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 3),         # trigrams for Hinglish/Gujarati mix
            analyzer="char_wb",          # character-level for script agnosticism
            min_df=2,
            max_features=50000,
        ),
        LinearSVC(C=1.0, max_iter=2000),
    )
    pipeline.fit(X, y)

    accuracy = pipeline.score(X, y)
    print(f"  Training accuracy: {accuracy * 100:.2f}%")

    os.makedirs("models", exist_ok=True)
    model_path = "models/intent_classifier.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"\n  Model saved -> {model_path}")

    # Quick sanity check on Gujarat queries
    print("\n--- Gujarat Query Sanity Check ---")
    test_queries = [
        ("kapas ma bollworm che", "crop_disease"),
        ("aaj rajkot mandi ma groundnut no bhav", "market_price"),
        ("ikhedut portal par drip subsidy", "govt_scheme"),
        ("Amreli ma kal varshad padse", "weather"),
        ("jeere mein blight rog ka upay", "crop_disease"),
        ("Junagadh mandi ma jeeru no rate", "market_price"),
        ("pm kisan ka paisa kab aayega", "govt_scheme"),
        ("Gujarat monsoon forecast", "weather"),
        ("PM કિસાન નો પૈસો ક્યારે આવશે", "govt_scheme"),
        ("ikhedut portal par apply kevi rite karvu", "govt_scheme"),
        ("sarkar ni drip irrigation subsidy male che", "govt_scheme"),
    ]
    all_pass = True
    for query, expected in test_queries:
        predicted = pipeline.predict([query.lower()])[0]
        status = "[PASS]" if predicted == expected else "[FAIL]"
        if predicted != expected:
            all_pass = False
        print(f"  {status} '{query}' -> {predicted} (expected: {expected})")

    print("\n" + "=" * 60)
    if all_pass:
        print("ALL SANITY CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED -- review training data")
    print("=" * 60)



if __name__ == "__main__":
    main()
