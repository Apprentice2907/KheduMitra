"""
gujarat_constants.py
====================
Single source of truth for all Gujarat-specific constants used throughout KissanBot.
Never hardcode district names, crop names, or helplines elsewhere — import from here.
"""

# ---------------------------------------------------------------------------
# All 33 Gujarat Districts grouped by agro-climatic zone
# ---------------------------------------------------------------------------
GUJARAT_DISTRICTS_BY_ZONE = {
    "saurashtra": [
        "Rajkot", "Junagadh", "Amreli", "Bhavnagar", "Jamnagar",
        "Porbandar", "Morbi", "Gir Somnath", "Devbhumi Dwarka", "Botad",
    ],
    "north_gujarat": [
        "Mehsana", "Patan", "Banaskantha", "Sabarkantha", "Gandhinagar", "Aravalli",
    ],
    "central_gujarat": [
        "Ahmedabad", "Anand", "Kheda", "Vadodara", "Panchmahal",
        "Dahod", "Mahisagar", "Chhota Udaipur",
    ],
    "south_gujarat": [
        "Surat", "Navsari", "Valsad", "Bharuch", "Narmada",
        "Tapi", "Dang",
    ],
    "kutch": [
        "Kutch",
    ],
}

# Flat list of all 33 districts (canonical, used for iteration)
GUJARAT_DISTRICTS: list[str] = [
    d for zone_districts in GUJARAT_DISTRICTS_BY_ZONE.values() for d in zone_districts
]

# ---------------------------------------------------------------------------
# Gujarat key crops: English name → Gujarati name
# ---------------------------------------------------------------------------
GUJARAT_CROPS: dict[str, str] = {
    "groundnut":  "મગફળી",
    "cotton":     "કપાસ",
    "castor":     "દિવેલ",
    "cumin":      "જીરું",
    "fennel":     "વરિયાળી",
    "sesame":     "તલ",
    "bajra":      "બાજરો",
    "wheat":      "ઘઉં",
    "onion":      "ડુંગળી",
    "potato":     "બટેટા",
    "banana":     "કેળ",
    "mango":      "કેરી",
    "turmeric":   "હળદર",
    "tobacco":    "તમાકુ",
    "sugarcane":  "શેરડી",
    "garlic":     "લસણ",
    "chickpea":   "ચણા",
    "mustard":    "રાઈ",
    "soybean":    "સોયાબીન",
    "rice":       "ડાંગર",
}

# Gujarati name → English name (reverse lookup)
GUJARAT_CROPS_GU_TO_EN: dict[str, str] = {v: k for k, v in GUJARAT_CROPS.items()}

# ---------------------------------------------------------------------------
# Key mandis in Gujarat with their district
# ---------------------------------------------------------------------------
GUJARAT_MANDIS: dict[str, str] = {
    "Rajkot":    "Rajkot",
    "Junagadh":  "Junagadh",
    "Amreli":    "Amreli",
    "Surat":     "Surat",
    "Ahmedabad": "Ahmedabad",
    "Anand":     "Anand",
    "Bhavnagar": "Bhavnagar",
    "Vadodara":  "Vadodara",
    "Gondal":    "Rajkot",      # sub-mandi under Rajkot district
    "Dhari":     "Amreli",
    "Unjha":     "Mehsana",     # largest cumin/fennel mandi in Asia
}

# ---------------------------------------------------------------------------
# Important helplines for Gujarat farmers
# ---------------------------------------------------------------------------
GUJARAT_HELPLINES: dict[str, str] = {
    "gujarat_agriculture_dept":   "1800-180-1551",
    "ikhedut_helpline":           "1800-233-3155",
    "pm_kisan_helpline":          "155261",
    "pm_kisan_alt":               "011-24300606",
    "kisan_call_centre":          "1800-180-1551",
    "weather_sms_service":        "7738299899",
    "soil_health_card":           "1800-180-1551",
    "pmfby_helpline":             "1800-200-7710",
}

# ---------------------------------------------------------------------------
# iKhedut portal URL and Gujarat Agriculture Dept URL
# ---------------------------------------------------------------------------
IKHEDUT_URL = "https://ikhedut.gujarat.gov.in/"
GUJARAT_AGRI_URL = "https://agri.gujarat.gov.in/"

# ---------------------------------------------------------------------------
# Crop diseases specific to Gujarat (crop → list of major diseases)
# ---------------------------------------------------------------------------
GUJARAT_CROP_DISEASES: dict[str, list[str]] = {
    "groundnut":  ["tikka_leaf_spot", "stem_rot", "collar_rot", "aflatoxin", "bud_necrosis"],
    "cotton":     ["pink_bollworm", "american_bollworm", "whitefly_leaf_curl", "grey_mildew", "bacterial_blight"],
    "castor":     ["semilooper", "capsule_borer", "wilt", "grey_mould"],
    "cumin":      ["blight", "powdery_mildew", "wilt", "aphid"],
    "fennel":     ["powdery_mildew", "stem_canker", "aphid"],
    "bajra":      ["downy_mildew", "ergot", "smut", "stem_borer"],
    "wheat":      ["yellow_rust", "stem_rust", "karnal_bunt", "loose_smut"],
    "banana":     ["panama_wilt", "sigatoka", "bunchy_top"],
    "onion":      ["purple_blotch", "stemphylium_blight", "thrips"],
    "potato":     ["late_blight", "early_blight", "black_scurf"],
}

# ---------------------------------------------------------------------------
# Gujarat farming seasons
# ---------------------------------------------------------------------------
GUJARAT_SEASONS: dict[str, dict] = {
    "kharif": {
        "gujarati": "ખરીફ",
        "months": "June–October",
        "main_crops": ["cotton", "groundnut", "bajra", "castor", "rice"],
    },
    "rabi": {
        "gujarati": "રવિ",
        "months": "November–March",
        "main_crops": ["wheat", "cumin", "fennel", "garlic", "mustard"],
    },
    "summer": {
        "gujarati": "ઉનાળુ",
        "months": "March–June",
        "main_crops": ["groundnut", "sesame", "onion", "potato"],
    },
}

# ---------------------------------------------------------------------------
# MSP (indicative, to be updated each year from CACP)
# ---------------------------------------------------------------------------
GUJARAT_MSP_CROPS: list[str] = [
    "groundnut", "cotton", "castor", "bajra", "wheat", "cumin", "sesame",
    "mustard", "sugarcane", "rice",
]
