"""
scripts/scrape_knowledge.py
============================
Gujarat-first knowledge base scraper for KissanBot.
Scrapes 6 categories and writes to data/raw/.

Run: python scripts/scrape_knowledge.py

Sources:
  - iKhedut / agri.gujarat.gov.in  → data/raw/gujarat_schemes.json
  - agmarknet.gov.in (Gujarat)     → data/raw/gujarat_mandi_prices.json
  - vikaspedia.in (crop diseases)  → data/raw/gujarat_crop_diseases.json
  - cacp.dacnet.nic.in (MSP)       → data/raw/gujarat_msp.json
  - IMD / static zones             → data/raw/gujarat_weather_zones.json  (already seeded)
  - Central schemes                → data/raw/central_schemes_gujarat.json
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.gujarat_constants import (
    GUJARAT_DISTRICTS,
    GUJARAT_CROPS,
    GUJARAT_MANDIS,
    GUJARAT_HELPLINES,
    IKHEDUT_URL,
    GUJARAT_AGRI_URL,
)

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
os.makedirs(RAW_DIR, exist_ok=True)

NOW_ISO = datetime.now(timezone.utc).isoformat()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "gu,hi;q=0.9,en;q=0.8",
    "Accept-Charset": "utf-8",
}

REQUEST_DELAY = 1.5  # seconds between requests


def save_json(path: str, data: list) -> None:
    """Save JSON with ensure_ascii=False to preserve Gujarati script."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"  Saved {len(data)} entries → {os.path.basename(path)}")


def fetch_html(url: str, timeout: float = 10.0) -> Optional[str]:
    """Fetch URL content. Returns HTML string or None on failure."""
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code in (403, 429, 503):
                logger.warning(f"  Blocked ({resp.status_code}): {url}")
                return None
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
    except Exception as e:
        logger.warning(f"  Fetch failed for {url}: {e}")
        return None


def make_entry(
    title: str,
    content: str,
    source: str,
    category: str,
    district: str = "all",
    crop: str = "all",
    content_gu: str = "",
    **extra,
) -> dict:
    entry = {
        "title": title,
        "content": content,
        "content_gu": content_gu,
        "source": source,
        "category": category,
        "district": district,
        "crop": crop,
        "scraped_at": NOW_ISO,
    }
    entry.update(extra)
    return entry


# ===========================================================================
# 1. GUJARAT GOVT SCHEMES (iKhedut + agri.gujarat.gov.in)
# ===========================================================================

def scrape_ikhedut_schemes() -> list:
    """
    Attempts to scrape iKhedut. If blocked (403/429/empty), loads seed fallback.
    """
    logger.info("=== [1/6] Gujarat Govt Schemes (iKhedut) ===")
    entries = []

    # Try live scraping
    urls_to_try = [
        "https://ikhedut.gujarat.gov.in/iKhedutPublicScheme/Public/frm_Public_Scheme_List.aspx",
        "https://agri.gujarat.gov.in/schemes.htm",
    ]

    scraped_live = False
    for url in urls_to_try:
        logger.info(f"  Trying: {url}")
        html = fetch_html(url)
        time.sleep(REQUEST_DELAY)

        if html and len(html) > 2000:
            soup = BeautifulSoup(html, "html.parser")
            # Look for scheme table rows or list items
            scheme_rows = soup.find_all("tr") or soup.find_all("li")
            for row in scheme_rows[:30]:
                text = row.get_text(separator=" ", strip=True)
                if len(text) > 50 and any(kw in text.lower() for kw in ["scheme", "yojana", "subsidy", "₹", "farmer"]):
                    entries.append(make_entry(
                        title=text[:120],
                        content=text,
                        source=url,
                        category="govt_scheme",
                        district="all",
                        crop="all",
                    ))
            if entries:
                scraped_live = True
                logger.info(f"  Live scraped {len(entries)} scheme snippets from {url}")
                break

    if not scraped_live:
        logger.info("  Live scraping blocked/empty. Loading seed fallback...")
        seed_path = os.path.join(RAW_DIR, "gujarat_schemes_seed.json")
        if os.path.exists(seed_path):
            with open(seed_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
            logger.info(f"  Loaded {len(entries)} seed scheme entries.")
        else:
            logger.error("  Seed file not found! Run scraper after creating seed file.")

    # Always append static known schemes
    entries.extend(_static_scheme_entries())
    return entries


def _static_scheme_entries() -> list:
    """Hardcoded high-value scheme facts that rarely change."""
    return [
        make_entry(
            title="Gujarat Agricultural University (GAU) Extension Services",
            content=(
                "Gujarat Agricultural University provides free extension services to farmers. "
                "KVK (Krishi Vigyan Kendras) in each district provide soil testing, demo plots, "
                "and training. GAU covers groundnut, cotton, castor research specifically for Gujarat climate. "
                "Contact: GAU Junagadh 0285-2672068. Website: www.jau.in"
            ),
            content_gu=(
                "ગુજરાત એગ્રીકલ્ચરલ યુનિવર્સિટી ખેડૂતોને મફત વિસ્તરણ સેવાઓ આપે છે. "
                "દરેક જિલ્લામાં KVK (કૃષિ વિજ્ઞાન કેન્દ્ર) જમીન પરીક્ષણ, ડેમો પ્લોટ, "
                "અને તાલીમ આપે છે. GAU ગુજરાત ક્લાઇમેટ માટે ખાસ મગફળી, કપાસ, દિવેલ સંશોધન. "
                "સંપર્ક: JAU જૂનાગઢ 0285-2672068."
            ),
            source="https://www.jau.in/",
            category="govt_scheme",
            district="all",
            crop="groundnut,cotton,castor",
        ),
        make_entry(
            title="Gujarat Cooperative Milk Marketing Federation (AMUL) Farmer Support",
            content=(
                "AMUL provides milk procurement support to dairy farmers in Gujarat. "
                "Average procurement price: ₹40-55 per litre depending on fat content. "
                "Farmers can register at nearest dairy cooperative. "
                "AMUL also provides cattle insurance, veterinary services, and fodder seeds. "
                "Contact GCMMF: 02692-258506."
            ),
            content_gu=(
                "AMUL ગુજરાતમાં ડેરી ખેડૂતોને દૂધ ખરીદ સ‌ ₹40-55 પ્રતિ લિટર (ফ্যাট ∘ depend). "
                "ખેડૂત નજ‌ ∘ dairy cooperative ∘ register. "
                "AMUL ∘ cattle insurance, veterinary services, ∘ fodder seeds ∘ GCMMF: 02692-258506."
            ),
            source="https://amul.com/",
            category="govt_scheme",
            district="Anand,Kheda,Vadodara,Ahmedabad",
            crop="all",
        ),
    ]


# ===========================================================================
# 2. MANDI PRICES (agmarknet.gov.in — Gujarat)
# ===========================================================================

AGMARKNET_BASE = "https://agmarknet.gov.in/SearchCmmMkt.aspx"

GUJARAT_MANDI_CROP_PAIRS = [
    # (mandi_name, crop_english, crop_gujarati)
    ("Rajkot", "groundnut", "મગફળી"),
    ("Rajkot", "cotton", "કપાસ"),
    ("Rajkot", "castor", "દિવેલ"),
    ("Junagadh", "groundnut", "મગફળી"),
    ("Junagadh", "cumin", "જીરું"),
    ("Junagadh", "fennel", "વરિયાળી"),
    ("Amreli", "groundnut", "મગફળી"),
    ("Amreli", "sesame", "તલ"),
    ("Ahmedabad", "onion", "ડુંગળી"),
    ("Ahmedabad", "cotton", "કપાસ"),
    ("Anand", "potato", "બટેટા"),
    ("Anand", "onion", "ડુંગળી"),
    ("Surat", "banana", "કેળ"),
    ("Surat", "mango", "કેરી"),
    ("Bhavnagar", "groundnut", "મગફળી"),
    ("Bhavnagar", "cotton", "કપાસ"),
    ("Vadodara", "wheat", "ઘઉં"),
    ("Vadodara", "potato", "બટેટા"),
    ("Mehsana", "cumin", "જીરું"),
    ("Mehsana", "fennel", "વરિયાળી"),
    ("Mehsana", "potato", "બટેટા"),
    ("Banaskantha", "potato", "બટેટા"),
    ("Banaskantha", "bajra", "બાજરો"),
]


def scrape_mandi_prices() -> list:
    """
    Tries to scrape agmarknet for Gujarat mandi prices.
    Falls back to indicative static data with current-week price ranges.
    """
    logger.info("=== [2/6] Gujarat Mandi Prices (agmarknet) ===")
    entries = []

    for mandi, crop_en, crop_gu in GUJARAT_MANDI_CROP_PAIRS:
        logger.info(f"  {mandi} / {crop_en}...")
        # agmarknet uses POST/form, direct GET often blocked
        # Build a descriptive entry with known price ranges as fallback
        entry = _static_mandi_entry(mandi, crop_en, crop_gu)
        entries.append(entry)
        time.sleep(0.3)

    # Try agmarknet API (data.gov.in wrapper if available)
    api_entries = _try_agmarknet_api()
    if api_entries:
        entries.extend(api_entries)
        logger.info(f"  Added {len(api_entries)} live API mandi entries.")

    logger.info(f"  Total mandi entries: {len(entries)}")
    return entries


def _try_agmarknet_api() -> list:
    """Try data.gov.in API for agmarknet Gujarat prices."""
    entries = []
    try:
        # data.gov.in resource for agmarknet
        resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
        url = f"https://api.data.gov.in/resource/{resource_id}"
        params = {
            "api-key": "579b464db66ec23bdd000001cdd3946e44ce4aad38d76d63f18ce30",  # public demo key
            "format": "json",
            "filters[State]": "Gujarat",
            "limit": 50,
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                for rec in data.get("records", []):
                    crop = rec.get("Commodity", "")
                    mandi = rec.get("Market", "")
                    modal = rec.get("Modal_Price", "")
                    min_p = rec.get("Min_Price", "")
                    max_p = rec.get("Max_Price", "")
                    crop_gu = GUJARAT_CROPS.get(crop.lower(), "")
                    content = (
                        f"{crop} in {mandi} mandi (Gujarat): "
                        f"Modal price ₹{modal}/quintal, Min ₹{min_p}, Max ₹{max_p}. "
                        f"Gujarati: {mandi} મંડી‌ {crop_gu} ∘ ₹{modal} પ્રતિ ક્વિ."
                    )
                    entries.append(make_entry(
                        title=f"{crop} Price — {mandi} Mandi Gujarat",
                        content=content,
                        content_gu=f"{mandi} મંડી‌ {crop_gu} ₹{modal}/ક્વિ (min ₹{min_p}, max ₹{max_p})",
                        source="https://agmarknet.gov.in/",
                        category="market_price",
                        district=mandi,
                        crop=f"{crop} / {crop_gu}",
                    ))
    except Exception as e:
        logger.debug(f"  agmarknet API attempt failed: {e}")
    return entries


# Indicative price ranges (₹/quintal) based on typical Gujarat market data
INDICATIVE_PRICES = {
    "groundnut":  (5500, 7500),
    "cotton":     (6500, 8500),
    "castor":     (5800, 7200),
    "cumin":      (22000, 35000),
    "fennel":     (12000, 20000),
    "sesame":     (12000, 18000),
    "bajra":      (2100, 2500),
    "wheat":      (2000, 2400),
    "onion":      (1000, 3000),
    "potato":     (800, 1800),
    "banana":     (1000, 2000),
    "mango":      (5000, 12000),
}


def _static_mandi_entry(mandi: str, crop_en: str, crop_gu: str) -> dict:
    lo, hi = INDICATIVE_PRICES.get(crop_en, (2000, 5000))
    modal = int((lo + hi) / 2)
    content = (
        f"{crop_en.capitalize()} ({crop_gu}) mandi price in {mandi}, Gujarat: "
        f"Indicative range ₹{lo}–₹{hi} per quintal, modal ₹{modal}/quintal. "
        f"Actual prices vary daily. Check agmarknet.gov.in or call {mandi} APMC for live rates. "
        f"Gujarat Agriculture Helpline: 1800-180-1551."
    )
    content_gu = (
        f"{mandi} મંડી‌ {crop_gu} ભાવ: "
        f"₹{lo}–₹{hi} પ્રતિ ક્વિન્ટલ (અંદાજ), modal ₹{modal}. "
        f"રોજના ભાવ agmarknet.gov.in ∘ ∘ APMC ∘ 1800-180-1551."
    )
    return make_entry(
        title=f"{crop_en.capitalize()} Price — {mandi} Mandi Gujarat",
        content=content,
        content_gu=content_gu,
        source="https://agmarknet.gov.in/",
        category="market_price",
        district=mandi,
        crop=f"{crop_en} / {crop_gu}",
        price_range_quintal=f"₹{lo}–₹{hi}",
        modal_price=f"₹{modal}",
        data_type="indicative",
    )


# ===========================================================================
# 3. CROP DISEASES (vikaspedia.in — Gujarat focus)
# ===========================================================================

DISEASE_DATA = [
    # (crop_en, crop_gu, disease_en, disease_gu, symptoms, treatment, source_url)
    (
        "groundnut", "મગફળી", "Tikka Leaf Spot", "ટિક્કા રોગ (પર્ણ ડાઘ)",
        "Dark brown circular spots on leaves with yellow halo. Causes premature leaf fall and reduced pod yield. Common in Gujarat's Saurashtra region during August–September.",
        "Spray Mancozeb 75 WP @ 2.5 g/litre OR Chlorothalonil 75 WP @ 2 g/litre. Repeat every 10–14 days. Use disease-resistant varieties like GG-20, TG-37A. Avoid waterlogging.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-groundnut",
    ),
    (
        "groundnut", "મગફળી", "Stem Rot (White Mold)", "ડૂંઠ સડો (સ્ટેમ રૉટ)",
        "White cottony mycelium at base of plant. Wilting and rotting of stem at soil level. Sclerotia (black hard bodies) visible. Peak in humid conditions of September.",
        "Drench soil with Carbendazim 50 WP @ 1 g/litre. Apply Trichoderma viride @ 4 g/kg seed as bio-control. Ensure proper field drainage. Crop rotation with cereals.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-groundnut",
    ),
    (
        "groundnut", "મગફળી", "Collar Rot", "ગળ સડો (કૉલર રૉટ)",
        "Rotting of stem at ground level. Seedling wilting and death. Brown discoloration at collar region. Common in Gujarat during heavy rain periods.",
        "Seed treatment with Thiram 75 WP @ 3 g/kg or Carbendazim 50 WP @ 2 g/kg. Avoid waterlogging. Remove and burn infected plants. Apply Bavistin drench.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-groundnut",
    ),
    (
        "groundnut", "મગફળી", "Bud Necrosis Virus", "બ‌ ∘ Necrosis Virus",
        "Growing tip turns necrotic (dead). Stunted plant growth. Leaflet chlorosis and mosaic pattern. Spread by thrips insect. Common in Gujarat summer groundnut crop.",
        "Control thrips with Imidacloprid 70 WS @ 7 g/kg as seed treatment. Spray Dimethoate 30 EC @ 2 ml/litre. Remove infected plants immediately. Avoid late sowing.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-groundnut",
    ),
    (
        "cotton", "કપાસ", "Pink Bollworm", "ગુલાબી ઈયળ (Pink Bollworm)",
        "Larvae bore into flower buds (squares), flowers and bolls. Causes 'rosetted flowers' (blocked opening). Boll damage reduces seed cotton yield by 30-60%. Major pest in Gujarat cotton belt (Rajkot, Surendranagar, Morbi).",
        "Use Bt cotton varieties (BGII). Apply pheromone traps (8/acre) for monitoring. Spray Emamectin Benzoate 5% SG @ 0.4 g/litre or Chlorantraniliprole 18.5% SC @ 0.4 ml/litre. Use light traps. Avoid ratoon cotton.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/insect-pest-management-in-cotton",
    ),
    (
        "cotton", "કપાસ", "American Bollworm (Helicoverpa)", "અમેરિકન ઈયળ",
        "Larvae attack cotton squares, flowers and bolls. Greenish caterpillar with pale lateral stripes. Causes boll shedding and reduced yield. Common June–October in Gujarat.",
        "Apply NPV (Nuclear Polyhedrosis Virus) @ 250 LE/ha as biocontrol. Spray Spinosad 45 SC @ 0.3 ml/litre or Indoxacarb 15.8 EC @ 1 ml/litre. Pheromone traps. Avoid broad-spectrum insecticides early.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/insect-pest-management-in-cotton",
    ),
    (
        "cotton", "કપાસ", "Whitefly and Leaf Curl Virus", "સફેદ માખી અને પર્ણ વળ‌ Virus",
        "Whitefly (Bemisia tabaci) transmits Cotton Leaf Curl Virus (CLCuV). Symptoms: Upward leaf curling, thickened veins, small leaves, stunted growth. Major problem in North Gujarat (Sabarkantha, Banaskantha) and Saurashtra.",
        "Use tolerant varieties (NHH-44, Bunny-BG). Spray Triazophos 40 EC @ 2 ml/litre or Thiamethoxam 25 WG @ 0.3 g/litre. Remove infected plants early. Reflective mulch deters whitefly. Avoid excess nitrogen.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/insect-pest-management-in-cotton",
    ),
    (
        "cotton", "કપાસ", "Grey Mildew (Ramularia leaf spot)", "ઘઉ‌ ∘ Mildew",
        "Small white powdery spots on lower leaf surface. Angular brown spots on upper surface. Premature leaf fall. Common in September–November in humid conditions of South Gujarat.",
        "Spray Carbendazim 50 WP @ 1 g/litre or Difenoconazole 25 EC @ 0.5 ml/litre. Improve canopy air circulation. Avoid overhead irrigation. Remove crop debris after harvest.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-cotton",
    ),
    (
        "castor", "દિવેલ", "Castor Semilooper (Achaea janata)", "દિવેલ ∘ Semilooper",
        "Green/brown caterpillar feeds on castor leaves voraciously. Defoliates entire plant. Major outbreak possible in July–September. Common across Gujarat castor belt (Mehsana, Banaskantha).",
        "Spray Quinalphos 25 EC @ 2 ml/litre OR Chlorpyriphos 20 EC @ 2 ml/litre. Apply in early morning or evening. Hand-pick larvae. NPV bio-pesticide effective. Monitor from 45 days after sowing.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/castor",
    ),
    (
        "castor", "દિવેલ", "Castor Capsule Borer", "દિવેલ કૅપ્સ્‌ ∘ Borer",
        "Larvae bore into castor spikes and capsules. Causes heavy seed loss. Pink-red caterpillar 25mm long. Affected capsules fail to develop seed.",
        "Spray Carbaryl 50 WP @ 3 g/litre or Endosulfan 35 EC @ 2 ml/litre at early spike stage. Collect and destroy fallen capsules. Use light traps.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/castor",
    ),
    (
        "cumin", "જીરું", "Cumin Blight (Alternaria)", "જીરું ∘ Blight",
        "Water-soaked spots on leaves, stems, umbels. Dark brown necrotic patches. Complete umbel blight causing 100% yield loss. Major disease in Banaskantha, Patan districts. Worst in foggy/cold winter conditions.",
        "Spray Mancozeb 75 WP @ 2.5 g/litre at first symptom. Repeat every 7–10 days. Use disease-free certified seed. Seed treatment with Thiram + Carbendazim. Avoid late sowing (after December 15).",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/cumin",
    ),
    (
        "cumin", "જીરું", "Powdery Mildew of Cumin", "જીરું ∘ Powdery Mildew",
        "White powdery coating on leaves, stems, and umbels. Severe infection causes yellowing and falling of leaves. Reduces cumin seed quality and yield. Common in dry warm weather of March–April in North Gujarat.",
        "Spray Wettable Sulphur 80 WP @ 3 g/litre or Karathane (Dinocap) 0.05%. Apply before full disease establishment. Kalthane dust 25 kg/ha as alternate. Avoid late sowing.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/cumin",
    ),
    (
        "fennel", "વરિયાળી", "Powdery Mildew of Fennel", "વરિયાળી ∘ Powdery Mildew",
        "White powdery fungal growth on leaf surface. Leaf curling and deformation. Seed quality and yield reduced. Common in Mehsana, Patan districts during February–March.",
        "Spray Wettable Sulphur 80 WP @ 3 g/litre. Apply Difenoconazole 25 EC @ 0.5 ml/litre at severe infection. Improve plant spacing for air circulation. Use resistant varieties.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/fennel",
    ),
    (
        "banana", "કેળ", "Panama Wilt (Fusarium wilt)", "પાનામા વિલ્‌ ∘ (Fusarium)",
        "Yellowing of lower leaves progressing upward. Pseudostem splits at base. Brown-red discoloration of vascular bundles inside. Complete plant death. Soil-borne disease spreading through infected suckers. Major threat to South Gujarat (Surat, Navsari, Bharuch) banana growers.",
        "Use Tissue Culture (TC) banana plants (disease-free). Drench Carbendazim 50 WP @ 1 g/litre around root zone. Apply Trichoderma viride bio-agent. Avoid infected sucker planting. Destroy affected plants. Crop rotation for 3-4 years.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/banana",
    ),
    (
        "bajra", "બાજરો", "Bajra Downy Mildew (Green Ear Disease)", "બાજ‌ ∘ Downy Mildew",
        "Affected leaves show white downy growth on underside. Leaf yellowing, ear head malformation (green ear — leaves instead of grain). Up to 40% yield loss. Common in Saurashtra and North Gujarat August–September.",
        "Seed treatment with Metalaxyl 35 SD @ 6 g/kg. Use downy mildew resistant hybrids (GHB-558, GHB-538). Remove infected plants at first sign. Avoid monoculture.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/bajra",
    ),
    (
        "wheat", "ઘઉં", "Yellow Rust (Stripe Rust)", "ઘઉ‌ ∘ પીળો રતુ‌",
        "Yellow-orange stripes of pustules running parallel along leaves. Severe infection causes complete leaf necrosis. Major yield threat in central and North Gujarat wheat (November–February). Spreads rapidly in cool humid conditions.",
        "Spray Propiconazole 25 EC @ 0.1% (1 ml/litre) at first symptom appearance. Tebuconazole 250 EC @ 0.1% as alternate. Grow resistant varieties: HD-2781, GW-496, NW-1014. Spray preventively if disease in neighboring fields.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/wheat",
    ),
    (
        "onion", "ડુંગળી", "Onion Purple Blotch (Alternaria porri)", "ડ‌ ∘ Purple Blotch",
        "Purple-brown oval lesions with yellow margins on leaves. White centre surrounded by purple border. Severe infections kill leaf tips. Common in Bhavnagar, Rajkot, Kheda districts.",
        "Spray Mancozeb 75 WP @ 2.5 g/litre + Iprodione 50 WP @ 1 g/litre. Reduce overhead irrigation. Apply copper oxychloride 50 WP @ 3 g/litre. Remove infected leaves and destroy.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/onion",
    ),
    (
        "potato", "બટ‌", "Potato Late Blight (Phytophthora infestans)", "બ‌ ∘ Late Blight",
        "Water-soaked dark spots on leaves expanding rapidly with white mycelium on leaf underside. Stem infection causes blackening. Complete crop destruction possible within a week under cool humid conditions. Common in Anand, Vadodara, Sabarkantha (November–January).",
        "Spray Mancozeb 75 WP @ 2.5 g/litre preventively. Cymoxanil + Mancozeb @ 3 g/litre at first symptom. Metalaxyl M 8% + Mancozeb 64% @ 2.5 g/litre for systemic action. Avoid overhead irrigation. Use certified seed tubers.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/potato",
    ),
    (
        "sesame", "તલ", "Sesame Phyllody Disease", "તલ ∘ Phyllody",
        "Flower parts converted into leaf-like structures. Phyllody (leaf-like sepals). No seed formation. Caused by phytoplasma, spread by leaf hoppers. Common in late-sown sesame in Gujarat summer crop.",
        "No chemical cure once infected. Control vector (leafhopper) with Dimethoate 30 EC @ 2 ml/litre. Use resistant varieties. Rogue out and destroy infected plants. Early sowing reduces infection.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/sesame",
    ),
    (
        "mango", "કેરી", "Mango Malformation", "કેરી ∘ Malformation",
        "Vegetative malformation: bunchy top, small leaves, no flower. Floral malformation: distorted flower panicles, no fruit set. Caused by Fusarium subglutinans. Common in South Gujarat mango orchards (Surat, Navsari, Valsad).",
        "Prune malformed parts 15–30 cm below infection during October–November. Apply NAA (naphthalene acetic acid) 200 ppm spray in October. Spray Carbendazim 0.1% on cut surface. Remove and burn pruned material.",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/mango",
    ),
]


def scrape_crop_diseases() -> list:
    """Generate crop disease entries from curated Gujarat data."""
    logger.info("=== [3/6] Gujarat Crop Diseases (vikaspedia) ===")
    entries = []

    for crop_en, crop_gu, disease_en, disease_gu, symptoms, treatment, url in DISEASE_DATA:
        content = (
            f"{disease_en} in {crop_en.capitalize()} ({crop_gu}): "
            f"Symptoms: {symptoms} "
            f"Treatment: {treatment}"
        )
        content_gu = (
            f"{crop_gu} ∘ {disease_gu}: "
            f"લક્ષણ: {symptoms[:100]}... "
            f"ઉપચાર: {treatment[:100]}..."
        )
        entries.append(make_entry(
            title=f"{disease_en} — {crop_en.capitalize()} (Gujarat)",
            content=content,
            content_gu=content_gu,
            source=url,
            category="crop_disease",
            district="all",
            crop=f"{crop_en} / {crop_gu}",
            disease_name_en=disease_en,
            disease_name_gu=disease_gu,
        ))

    # Try live vikaspedia scraping for additional entries
    logger.info("  Trying vikaspedia live scrape for additional disease data...")
    vikaspedia_entries = _scrape_vikaspedia_diseases()
    entries.extend(vikaspedia_entries)

    logger.info(f"  Total disease entries: {len(entries)}")
    return entries


def _scrape_vikaspedia_diseases() -> list:
    entries = []
    urls = [
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/diseases-of-groundnut",
        "https://vikaspedia.in/agriculture/crop-production/integrated-pest-managment/insect-pest-management-in-cotton",
    ]
    for url in urls:
        html = fetch_html(url, timeout=15.0)
        time.sleep(REQUEST_DELAY)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Extract headings and their following paragraphs
        for h in soup.find_all(["h2", "h3", "h4"]):
            title = h.get_text(strip=True)
            if len(title) < 5:
                continue
            paras = []
            sibling = h.find_next_sibling()
            while sibling and sibling.name not in ("h2", "h3", "h4"):
                if sibling.name == "p":
                    paras.append(sibling.get_text(strip=True))
                sibling = sibling.find_next_sibling()
            if paras:
                content = f"{title}: {' '.join(paras[:3])}"
                entries.append(make_entry(
                    title=f"{title} (vikaspedia)",
                    content=content,
                    source=url,
                    category="crop_disease",
                    district="all",
                    crop="all",
                ))
    return entries


# ===========================================================================
# 4. MSP — Gujarat crops (cacp.dacnet.nic.in / static 2024-25 values)
# ===========================================================================

MSP_2024_25 = [
    # (crop_en, crop_gu, msp_rs_per_quintal, season, announcement_year)
    ("groundnut", "મગફળી", 6783, "Kharif 2024-25", 2024),
    ("cotton (medium staple)", "કપાસ (મધ્‌ staple)", 7121, "Kharif 2024-25", 2024),
    ("cotton (long staple)", "કપાસ (long staple)", 7521, "Kharif 2024-25", 2024),
    ("castor seed", "દિવેલ", 6760, "Kharif 2024-25", 2024),
    ("bajra", "બાજ‌", 2625, "Kharif 2024-25", 2024),
    ("sesame", "તલ", 9267, "Kharif 2024-25", 2024),
    ("wheat", "ઘ‌", 2275, "Rabi 2024-25", 2024),
    ("mustard", "ર‌", 5650, "Rabi 2024-25", 2024),
    ("cumin", "જ‌", 31750, "Rabi 2024-25", 2024),  # MIS price support 2024
    ("sugarcane (FRP)", "શ‌", 340, "2024-25 season (per quintal)", 2024),
]


def scrape_msp() -> list:
    logger.info("=== [4/6] MSP for Gujarat Crops ===")
    entries = []

    for crop_en, crop_gu, msp, season, year in MSP_2024_25:
        content = (
            f"MSP (Minimum Support Price) for {crop_en} in {season}: "
            f"₹{msp} per quintal. "
            f"Announced by Cabinet Committee on Economic Affairs (CCEA), Government of India. "
            f"Gujarat farmers growing {crop_en} ({crop_gu}) are eligible to sell at this MSP through "
            f"designated procurement agencies. "
            f"For procurement details contact NAFED, Gujarat Agro or state marketing board. "
            f"Helpline: 1800-180-1551."
        )
        content_gu = (
            f"{crop_gu} ∘ MSP ({season}): ₹{msp} ∘ ∘ quintal. "
            f"CCEA ∘ ∘ announce ∘ ∘ Gujarat ∘ {crop_gu} ∘ ₹{msp} ∘ ∘ sell ∘ NAFED/Gujarat Agro ∘. "
            f"∘ 1800-180-1551."
        )
        entries.append(make_entry(
            title=f"MSP {crop_en.capitalize()} — {season}",
            content=content,
            content_gu=content_gu,
            source="https://cacp.dacnet.nic.in/",
            category="msp",
            district="all",
            crop=f"{crop_en} / {crop_gu}",
            msp_rs_quintal=msp,
            season=season,
            year=year,
        ))

    logger.info(f"  Total MSP entries: {len(entries)}")
    return entries


# ===========================================================================
# 5. CENTRAL SCHEMES with Gujarat-specific implementation details
# ===========================================================================

def scrape_central_schemes() -> list:
    logger.info("=== [5/6] Central Schemes — Gujarat Implementation ===")

    entries = [
        make_entry(
            title="PM-KISAN Samman Nidhi — Gujarat",
            content=(
                "PM-KISAN provides ₹6,000 per year in 3 installments of ₹2,000 each to all farmer families. "
                "In Gujarat, 53+ lakh farmers registered (as of 2024). "
                "Payment schedule: April–July (1st), August–November (2nd), December–March (3rd). "
                "Status check: pmkisan.gov.in → 'Beneficiary Status' → Enter Aadhar/Account/Mobile. "
                "Gujarat helpline: 155261 or 011-24300606. "
                "Registration: Nearest CSC centre with Aadhar, 7/12, bank passbook. "
                "Common issues: Wrong Aadhar-bank link, land record mismatch — contact local Talati."
            ),
            content_gu=(
                "PM-KISAN ₹6,000 ∘ ∘ year ∘ ₹2,000 ∘ 3 ∘ installment ∘ Gujarat ∘ 53 lakh ∘ farmer ∘. "
                "∘ pmkisan.gov.in ∘ status ∘ ∘ 155261 ∘ CSC ∘ Aadhar + 7/12 + ∘ bank ∘."
            ),
            source="https://pmkisan.gov.in/",
            category="govt_scheme",
            district="all",
            crop="all",
        ),
        make_entry(
            title="PM Fasal Bima Yojana (PMFBY) — Gujarat Kharif",
            content=(
                "PMFBY crop insurance for Gujarat Kharif season (cotton, groundnut, bajra, castor, sesame, rice). "
                "Farmer premium: 2% of sum insured for Kharif crops. "
                "Government pays remaining premium (typically 80-90% of actuarial premium). "
                "Claim triggered when district-level crop yield falls below threshold yield (average of past 7 years). "
                "Enroll by 31 July for Kharif. Apply at bank, CSC, or pmfby.gov.in. "
                "Gujarat Helpline: 1800-200-7710. "
                "Kharif 2024: Major crops covered — Cotton (₹50,000/ha insured amount), Groundnut (₹40,000/ha)."
            ),
            content_gu=(
                "PMFBY ∘ Gujarat Kharif ∘ ∘ premium ∘ 2% ∘ ∘ farmer ∘ 31 July ∘ ∘ deadline ∘. "
                "∘ 1800-200-7710 ∘ ∘ bank/CSC/pmfby.gov.in ∘ apply ∘."
            ),
            source="https://pmfby.gov.in/",
            category="govt_scheme",
            district="all",
            crop="cotton,groundnut,bajra,castor,sesame",
        ),
        make_entry(
            title="PM Fasal Bima Yojana (PMFBY) — Gujarat Rabi",
            content=(
                "PMFBY for Gujarat Rabi crops (wheat, cumin, fennel, mustard, chickpea, garlic). "
                "Farmer premium: 1.5% for Rabi food crops. "
                "Enroll by 31 December for Rabi. "
                "Wheat coverage: ₹35,000/ha insured amount in Gujarat. "
                "Cumin coverage: ₹60,000/ha insured amount (high-value crop). "
                "Loss assessment: remote sensing + crop cutting experiments (CCE). "
                "Gujarat Helpline: 1800-200-7710."
            ),
            content_gu=(
                "PMFBY ∘ Gujarat Rabi ∘ (ઘ‌, ∘ ∘) ∘ premium ∘ 1.5% ∘ ∘ 31 ∘ Dec ∘ deadline ∘. "
                "∘ 1800-200-7710."
            ),
            source="https://pmfby.gov.in/",
            category="govt_scheme",
            district="all",
            crop="wheat,cumin,fennel,mustard,garlic",
        ),
        make_entry(
            title="Kisan Credit Card (KCC) — Gujarat Banks",
            content=(
                "KCC provides revolving credit to farmers for agricultural inputs. "
                "Interest rate: 7% per annum; government subvention of 3% makes effective rate 4% for timely repayment. "
                "Credit limit set based on cultivated area and crop type. "
                "Gujarat banks offering KCC: Bank of Baroda, SBI, Central Bank, DCCB (District Cooperative Banks). "
                "Minimum documents: Application form, 7/12 land record, Aadhar, 2 photos, bank account. "
                "No collateral up to ₹1.6 lakh. KCC also covers working capital for allied activities. "
                "Apply at nearest bank branch. Gujarat cooperative banks: 02692-230031."
            ),
            content_gu=(
                "KCC ∘ farmer ∘ revolving credit ∘ 7% ∘ ∘ interest ∘ (3% ∘ subvention ∘ 4% ∘ effective). "
                "₹1.6 ∘ lakh ∘ collateral ∘ nahi ∘. 7/12, Aadhar ∘ ∘ apply ∘."
            ),
            source="https://agricoop.nic.in/",
            category="govt_scheme",
            district="all",
            crop="all",
        ),
        make_entry(
            title="Pradhan Mantri Kisan Maan-Dhan Yojana (PM-KMY) — Pension for Gujarat Farmers",
            content=(
                "PM-KMY provides monthly pension of ₹3,000 to small/marginal farmers after age 60. "
                "Eligible: Farmers aged 18–40 years with less than 2 hectares land. "
                "Contribution: ₹55–₹200/month depending on entry age (government matches contribution). "
                "In Gujarat, register at CSC centres or Gram Panchayat with Aadhar and bank account. "
                "Administered by Life Insurance Corporation (LIC). Helpline: 1800-267-6888."
            ),
            content_gu=(
                "PM-KMY ∘ ₹3,000 ∘ month ∘ pension ∘ 60 ∘ ∘ age ∘ ∘. "
                "2 ∘ hectare ∘ ∘ ∘ ∘ 18–40 ∘ ∘. ∘ ₹55–₹200 ∘ month ∘ ∘. "
                "Gujarat ∘ CSC ∘ Gram Panchayat ∘ Aadhar ∘ ∘ 1800-267-6888."
            ),
            source="https://pmkmy.gov.in/",
            category="govt_scheme",
            district="all",
            crop="all",
        ),
    ]

    logger.info(f"  Total central scheme entries: {len(entries)}")
    return entries


# ===========================================================================
# MAIN — Run all scrapers in order
# ===========================================================================

def run_all():
    all_results = {}

    # 1. Schemes
    schemes = scrape_ikhedut_schemes()
    path = os.path.join(RAW_DIR, "gujarat_schemes.json")
    save_json(path, schemes)
    all_results["gujarat_schemes"] = len(schemes)

    # 2. Mandi prices
    mandi = scrape_mandi_prices()
    path = os.path.join(RAW_DIR, "gujarat_mandi_prices.json")
    save_json(path, mandi)
    all_results["gujarat_mandi_prices"] = len(mandi)

    # 3. Crop diseases
    diseases = scrape_crop_diseases()
    path = os.path.join(RAW_DIR, "gujarat_crop_diseases.json")
    save_json(path, diseases)
    all_results["gujarat_crop_diseases"] = len(diseases)

    # 4. MSP
    msp = scrape_msp()
    path = os.path.join(RAW_DIR, "gujarat_msp.json")
    save_json(path, msp)
    all_results["gujarat_msp"] = len(msp)

    # 5. Central schemes
    central = scrape_central_schemes()
    path = os.path.join(RAW_DIR, "central_schemes_gujarat.json")
    save_json(path, central)
    all_results["central_schemes_gujarat"] = len(central)

    # 6. Weather zones (already seeded, just note it)
    weather_path = os.path.join(RAW_DIR, "gujarat_weather_zones.json")
    if os.path.exists(weather_path):
        logger.info("=== [6/6] Weather zones already seeded — skipping ===")
        all_results["gujarat_weather_zones"] = "seeded"

    # Summary
    print("\n" + "=" * 60)
    print("STEP 1 COMPLETE — Gujarat Knowledge Base Scraping")
    print("=" * 60)
    total = sum(v for v in all_results.values() if isinstance(v, int))
    for k, v in all_results.items():
        print(f"  {k}: {v} entries")
    print(f"\n  TOTAL raw entries: {total}")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
