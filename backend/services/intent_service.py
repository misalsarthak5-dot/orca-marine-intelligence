import re
from enum import Enum

class OrcaIntent(str, Enum):
    CHLOROPHYLL = "chlorophyll"
    SST = "sst"
    ENVIRONMENTAL_INTELLIGENCE = "environmental_intelligence"
    FISHING_SAFETY = "fishing_safety"
    MARINE_HAZARDS = "marine_hazards"
    MARINE_CONDITIONS = "marine_conditions"
    PFZ_DISCOVERY = "pfz_discovery"
    SAFEST_ROUTE = "safest_route"
    RISK_EXPLANATION = "risk_explanation"
    AVOIDANCE = "avoidance"
    PRODUCTIVITY = "productivity"
    GENERAL_HELP = "general_help"

MARATHI_WORDS = {
    "आहे", "आहेत", "नाही", "नाहीत", "होय", "नको", "का", "कसे", "कशी", "कसा", "कुठे",
    "किती", "केव्हा", "कधी", "कशा", "जवळ", "जवळचा", "जवळचे", "उद्या", "सकाळी", "पहाटे",
    "मासेमारी", "मासेमारीसाठी", "मासेमारीस", "मासे", "सांगा", "सांग", "करा", "करावे", "होईल",
    "असतील", "लाटा", "लाटांची", "लाटांचा", "वारा", "वाऱ्याचा", "वादळ", "पाऊस", "धोका", "धोके",
    "जाऊ", "शकतो", "शकते", "शकतात", "सागरी", "हवामान", "मैल", "किलोमीटर", "च्या", "साठी",
    "मध्ये", "पासून", "वरून", "पर्यंत", "सर्वात", "संभाव्य", "क्षेत्र", "असेल", "आहात",
    "कोणते", "कोणती", "कोणता", "काही", "करणे", "योग्य", "मी", "तुम्ही", "आपण", "तेव्हा",
    "समुद्राचे", "समुद्रात", "समुद्राचा", "सागराचे", "सागरात"
}

HINDI_WORDS = {
    "है", "हैं", "नहीं", "हाँ", "क्या", "कैसे", "कैसा", "कैसी", "कहाँ", "किधर", "कितना",
    "कितनी", "कितने", "कब", "पास", "कल", "सुबह", "सवेरे", "मछली", "मत्स्य", "पकड़ना",
    "पकड़ने", "पकड़", "बताएं", "बताओ", "करो", "कीजिए", "होगा", "होगी", "होंगे", "लहरें",
    "लहरों", "लहर", "हवा", "तूफान", "बारिश", "वर्षा", "खतरा", "खतरे", "जा", "सकता",
    "सकती", "सकते", "समुद्री", "मौसम", "मील", "की", "के", "में", "से", "पर", "तक",
    "सबसे", "संभावित", "क्षेत्र", "होगा", "रहेगा", "होने", "नज़दीकी", "नजदीकी", "मुझे",
    "हूँ", "हूं", "आप", "हम", "वहाँ", "यहाँ", "समुद्र"
}

MARATHI_ROMAN = {
    "aahe", "aahet", "nahi", "nahit", "hoy", "kuthe", "kiti", "kadhi", "kasa", "kashi",
    "kase", "jawal", "jval", "zaval", "udya", "sakali", "pahate", "masemari", "mase",
    "sang", "sanga", "shakto", "shakte", "shaktat", "lata", "dhoka", "dhoke", "wara",
    "havaman", "paus", "sathi", "madhye", "pasun", "varun", "sarvat", "sambhavya",
    "kshetra", "asel", "kahi", "jogya", "yogya", "karu"
}

HINDI_ROMAN = {
    "hai", "hain", "nahin", "kya", "kaise", "kaisa", "kaisi", "kahan", "kaha", "kitna",
    "kitni", "kitne", "kab", "paas", "kal", "subah", "machli", "machhli", "pakadna",
    "pakadne", "batao", "bataye", "batayein", "hoga", "hogi", "honge", "lahrein",
    "lahre", "khatra", "khatre", "hawa", "toofan", "barish", "sakta", "sakti", "sakte",
    "mausam", "sabse", "sambhavit", "najdiki", "nazdiki", "hoon"
}

def detect_language(query: str, default_lang: str = "en") -> str:
    """
    Determines if user query is English ('en'), Hindi ('hi'), or Marathi ('mr').
    Accurately supports pure Devanagari, mixed Latin/English terms, and Romanized script.
    """
    if not query or not query.strip():
        return default_lang
    
    q = query.strip().lower()
    
    mr_score = 0
    hi_score = 0
    
    # 1. Distinct Marathi character 'ळ' (\u0933)
    if 'ळ' in q:
        mr_score += 5
        
    # 2. Tokenize words (both Devanagari and Latin)
    tokens = re.findall(r'[\u0900-\u097F]+|[a-zA-Z]+', q)
    
    for token in tokens:
        if token in MARATHI_WORDS:
            mr_score += 3
        if token in HINDI_WORDS:
            hi_score += 3
        if token in MARATHI_ROMAN:
            mr_score += 2
        if token in HINDI_ROMAN:
            hi_score += 2

    # Check Devanagari substrings
    for w in MARATHI_WORDS:
        if len(w) >= 3 and w in q:
            mr_score += 1
    for w in HINDI_WORDS:
        if len(w) >= 3 and w in q:
            hi_score += 1
            
    # Check if Devanagari script is present
    has_devanagari = bool(re.search(r'[\u0900-\u097F]', q))
    
    if mr_score > hi_score and mr_score > 0:
        return "mr"
    elif hi_score > mr_score and hi_score > 0:
        return "hi"
    elif mr_score == hi_score and mr_score > 0:
        return default_lang if default_lang in ["hi", "mr"] else "mr"
    elif has_devanagari:
        return default_lang if default_lang in ["hi", "mr"] else "hi"
    
    # Pure Latin/English without Indic tokens
    return "en"

def detect_intent(query: str) -> OrcaIntent:
    """
    Lightweight rule-based intent classifier for ORCA decision support.
    Supports English, Hindi, and Marathi keyword patterns.
    """
    q = query.lower().strip()

    # 1. Chlorophyll-a / Ocean Color Inquiry (explicit)
    if any(kw in q for kw in [
        "chlorophyll", "chlorophyll-a", "chlorophyll level", "chlorophyll concentration",
        "ocean color", "ocean-color", "क्लोरोफिल", "हरितद्रव्य"
    ]):
        return OrcaIntent.CHLOROPHYLL

    # 2. Sea Surface Temperature (SST) Inquiry (explicit)
    if any(kw in q for kw in [
        "sst", "sea surface temp", "sea surface temperature", "sea temp",
        "sea temperature", "ocean temperature", "water temp", "water temperature",
        "समुद्र सतह तापमान", "समुद्राचे तापमान", "समुद्र का तापमान", "सागरी तापमान", "पाण्याचे तापमान"
    ]):
        return OrcaIntent.SST

    # 3. Environmental Intelligence / Conditions summary Inquiry
    if any(kw in q for kw in [
        "environmental intelligence", "environmental conditions", "environmental condition",
        "environmental data", "environmental", "पर्यावरणीय स्थिति", "पर्यावरणीय", "पर्यावरण"
    ]):
        return OrcaIntent.ENVIRONMENTAL_INTELLIGENCE

    # 4. Productivity Trend Inquiry
    if any(kw in q for kw in [
        "productivity", "declined", "catch trend",
        "fish catch", "productivity trend", "उत्पादकता", "घट"
    ]):
        return OrcaIntent.PRODUCTIVITY

    # 5. Avoidance Zones Inquiry (explicit "avoid")
    if any(kw in q for kw in [
        "avoid", "areas should i avoid", "areas to avoid", "restricted area", "बचना", "दूर", "टाळा", "टाळावे"
    ]):
        return OrcaIntent.AVOIDANCE

    # 6. Marine Hazards & Environmental Alerts Inquiry
    if any(kw in q for kw in [
        "hazard", "hazards", "marine alert", "marine alerts", "any alerts", "active alerts",
        "any alert", "alert", "alerts", "heavy rain", "heavy precipitation",
        "dangerous waves", "waves dangerous", "are waves dangerous", "dangerous wave",
        "strong winds", "strong wind", "high winds", "squall", "storm alert",
        "cyclone alert", "खतरा", "धोका", "सावधान", "चेतावणी", "काही धोका", "धोका आहे का", "खतरा है"
    ]):
        return OrcaIntent.MARINE_HAZARDS

    # 7. Safest Route
    if any(kw in q for kw in [
        "route", "safest route", "safe corridor", "navigation path", "navigational route",
        "corridor", "मार्ग", "रस्ता"
    ]):
        return OrcaIntent.SAFEST_ROUTE

    # 8. PFZ Discovery (Potential Fishing Zones)
    if any(kw in q for kw in [
        "pfz", "where should i fish", "best fishing", "fishing zone", "nearest zone",
        "nearest pfz", "fish aggregation", "कहाँ मछली", "निकटतम", "मासे कुठे", "संभाव्य मासेमारी",
        "मासेमारी क्षेत्र", "संभावित मत्स्य", "मत्स्य पालन क्षेत्र", "सर्वात जवळचा", "सर्वात जवळचे",
        "नज़दीकी pfz", "सबसे नज़दीकी", "नजदीकी pfz", "कुठे आहे"
    ]):
        return OrcaIntent.PFZ_DISCOVERY

    # 9. Fishing Safety Assessment (queries asking if safe / fishing suitability)
    if any(kw in q for kw in [
        "is it safe", "safe to fish", "safe to go fishing", "can i fish", "should i fish",
        "go fishing", "fishing tomorrow", "tomorrow morning", "suitable to fish",
        "departure safe", "safe", "safety", "सुरक्षित", "सुरक्षा", "मछली पकड़ना", "मासेमारी",
        "योग्य आहे का", "जाऊ शकतो का", "जा सकता हूँ", "मासेमारीसाठी", "पकड़ने जा",
        "fishing safe", "safe आहे का", "safe hai", "fishing"
    ]):
        return OrcaIntent.FISHING_SAFETY

    # 10. Risk Explanation (check "why" patterns)
    if any(kw in q for kw in [
        "why", "explain risk", "why is it safe", "why is risk", "reason for risk",
        "why the risk", "why is fishing risk", "why is the risk", "जोखिम क्यों", "जोखीम का",
        "का बरे", "कशासाठी", "काय कारण", "कारण काय", "कारण सांगा", "कारण बताएं", "क्यों है"
    ]):
        return OrcaIntent.RISK_EXPLANATION

    # 11. Marine Conditions & Weather Telemetry
    if any(kw in q for kw in [
        "conditions", "current conditions", "marine conditions", "sea conditions",
        "weather", "weather conditions", "sea state", "ocean conditions",
        "ocean weather", "atmospheric conditions", "how are the conditions",
        "what are the conditions", "what is the weather", "how are the waves",
        "wind and wave", "wave conditions", "wind conditions", "wave", "waves",
        "wind", "winds", "swell", "sst", "sea surface temperature", "temperature",
        "tide", "tides", "precipitation", "rain", "समुद्री स्थिति", "सागरी परिस्थिती",
        "मौसम", "हवामान"
    ]):
        return OrcaIntent.MARINE_CONDITIONS

    # 12. General Help / Fallback
    if any(kw in q for kw in ["help", "what can", "features", "capabilities", "मदद", "सहायता", "काय करू शकता"]):
        return OrcaIntent.GENERAL_HELP

    return OrcaIntent.GENERAL_HELP

def extract_time_window(query: str) -> str:
    """
    Extract temporal window from the user query.
    Supported:
    - 'tomorrow morning' / 'कल सुबह' / 'उद्या सकाळी' -> 'tomorrow_morning'
    - 'tomorrow' / 'कल' / 'उद्या' -> 'tomorrow'
    - otherwise -> 'now'
    """
    q = query.lower().strip()

    # 1. Check multi-word 'tomorrow morning' before single-word 'tomorrow'
    if any(phrase in q for phrase in [
        "tomorrow morning", "tomorrow early morning", "early tomorrow morning",
        "tomorrow am", "कल सुबह", "कल सवेरे", "उद्या सकाळी", "उद्या पहाटे"
    ]):
        return "tomorrow_morning"

    # 2. Check general 'tomorrow'
    if any(phrase in q for phrase in [
        "tomorrow", "कल", "उद्या"
    ]):
        return "tomorrow"

    return "now"
