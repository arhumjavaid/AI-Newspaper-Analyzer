"""Hand-built domain lexicons for the NLP engine.

All entries come from domain knowledge of Pakistani power-sector reporting, written
before looking at the evaluation errors, so the evaluation stays honest.
"""
from __future__ import annotations

# --- Domain sentiment lexicon (added to VADER) --------------------------------------
# VADER was built for social media. It has no entry for "load-shedding" or
# "overbilling", and it scores "fine" as POSITIVE (as in "I'm fine"), although in
# this domain "NEPRA fines KE" is bad news. Valences use VADER's -4..+4 scale.
DOMAIN_VALENCE: dict[str, float] = {
    # supply failures
    "load-shedding": -2.0, "loadshedding": -2.0, "loadshed": -2.0, "outage": -1.8,
    "outages": -1.8, "breakdown": -1.8, "blackout": -2.2, "tripping": -1.2,
    "tripped": -1.2, "unannounced": -1.5, "shortfall": -1.3, "disrupted": -1.5,
    # billing grievances
    "overbilling": -2.5, "over-billing": -2.5, "overcharging": -2.5,
    "inflated": -1.8, "exorbitant": -2.2, "excessive": -1.5,
    # safety
    "electrocuted": -3.0, "electrocution": -3.0, "electrocutions": -3.0,
    # regulatory action
    "fine": -1.5, "fined": -2.0, "fines": -1.5, "penalty": -2.0, "show-cause": -1.8,
    # protest
    "protest": -1.5, "protests": -1.5, "protested": -1.5, "sit-in": -1.5,
    "ransacked": -2.5,
    # service improvements
    "restored": 1.8, "restoration": 1.5, "uninterrupted": 1.8, "exempted": 0.8,
    "exempt": 0.8, "relief": 1.5, "facilitation": 1.2, "facilitated": 1.2,
    "upgrade": 1.2, "efficiency": 1.0, "renewable": 1.0, "milestone": 1.8,
}

# --- Topic lexicon --------------------------------------------------------------------
# Matched as lowercase substrings, so "electrocut" covers electrocuted/electrocution.
TOPIC_CUES: dict[str, list[str]] = {
    "load-shedding": ["load-shed", "loadshed", "load shed", "outage", "power cut",
                      "breakdown", "blackout", "tripp", "power interruption"],
    "tariff": ["tariff", "per unit", "fuel charge", "fuel cost adjustment", "fca",
               "fuel price adjustment", "myt", "base rate"],
    "billing": ["bill", "overbill", "over-bill", "overcharg", "inflated", "instalment",
                "installment", "supplementary"],
    "safety": ["electrocut", "electric shock", "safety", "earthing", "grounded"],
    "investment": ["invest", "grid station", "power plant", "megawatt", " mw ",
                   "transmission", "financing", "solar", "project"],
    "theft": ["theft", "kunda", "illegal connection", "illegal wiring", "hooked"],
    "protest": ["protest", "sit-in", "demonstration", "rally", "agitation"],
    "regulation": ["nepra", "regulator", "hearing", "penalty", "show-cause", "fined"],
    "corporate": ["ceo", "chief executive", "board of directors", "shareholder",
                  "stock exchange", "psx", "profit", "loss after tax", "financial results"],
    "csr": ["award", "csr", "rebate", "philanthrop", "community", "women"],
}

# --- Tone cues --------------------------------------------------------------------------
# Sarcasm and taunts need world knowledge and are left to the LLM benchmark.
TONE_CUES: dict[str, list[str]] = {
    "accusatory": ["blame", "accus", "negligen", "failed", "failure", "mafia", "plunder",
                   "exploit", "extortion", "highhanded", "flouting", "fraudulent"],
    "alarmist": ["crisis", "chaos", "alarming", "misery", "torment", "nightmare",
                 "severe", "staggering", "worst", "tragic"],
    "praise": ["award", "commend", "welcome", "milestone", "success", "achiev",
               "honour", "honor", "prestigious", "pioneering", "record time"],
}

# --- Gazetteer for named-entity correction ---------------------------------------------
# NLTK's NE chunker was trained on US news. It misses or mislabels Karachi
# localities and Pakistani institutions, so a gazetteer catches the common ones.
GAZETTEER_LOCATIONS = [
    "Karachi", "Sindh", "Islamabad", "Lahore", "Lyari", "Korangi", "Malir", "Orangi",
    "Orangi Town", "Gulshan-e-Iqbal", "Gulshan-i-Iqbal", "Gulistan-e-Jauhar",
    "Gulistan-i-Jauhar", "Clifton", "DHA", "Defence", "Saddar", "Nazimabad",
    "North Nazimabad", "North Karachi", "Landhi", "Surjani Town", "Baldia", "SITE",
    "Keamari", "Kemari", "Gadap", "Bin Qasim", "Port Qasim", "Shah Faisal Colony",
    "Liaquatabad", "Federal B Area", "PECHS", "Bahadurabad", "Gizri", "Jamshoro",
    "Shahrah-e-Faisal", "Sharea Faisal", "Shara-e-Faisal", "Mauripur", "Gulshan-e-Hadeed",
    "Gulshan-e-Maymar", "Gulshan-i-Maymar", "Scheme 33", "Hub", "Uthal", "Thar", "Gharo",
]
# Pattern rule: Karachi place names usually end in one of these words or suffixes
# ("Sohrab Goth", "Lyari Expressway", "Liaquatabad"), whatever NLTK labelled them.
LOCATION_SUFFIXES = (
    " goth", " town", " colony", " expressway", " road", " chowrangi", " nagar",
    " market", " block", " sector", " society", " city", " bazar", " bazaar", "abad",
)

GAZETTEER_ORGANISATIONS = [
    "NEPRA", "Nepra", "NTDC", "CPPA", "SSGC", "KWSB", "KMC", "Power Division",
    "Ministry of Energy", "Sindh government", "Government of Sindh", "Sindh Assembly",
    "National Assembly", "Federal Ombudsman", "Jamaat-e-Islami", "Jamaat-i-Islami",
    "PTI", "Pakistan Tehreek-e-Insaf", "MQM-P", "PPP", "Pakistan Peoples Party", "PSX",
    "Pakistan Stock Exchange", "World Bank", "Pakistan LNG Limited", "PSO",
    "Faysal Bank", "Shanghai Electric", "KES Power", "Oursun", "PowerChina",
]
