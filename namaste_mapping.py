"""
NAMASTE & ICD-11 TM2 Mapping Engine with AI Priority Triage & Summary Generation
"""

RED_FLAG_TERMS = [
    "chest pain", "breathlessness", "dyspnea", "paralysis", "unconscious",
    "unconsciousness", "seizure", "severe bleeding", "hemorrhage",
    "anaphylaxis", "high fever", "acute abdomen", "organ failure",
    "suicidal", "cyanosis", "stroke", "cardiac", "shock"
]

NAMASTE_DICTIONARY = {
    "fever": ("AYU-001 (Jwara)", "TM2-JWA-01"),
    "jwara": ("AYU-001 (Jwara)", "TM2-JWA-01"),
    "cough": ("AYU-002 (Kasa)", "TM2-KAS-02"),
    "kasa": ("AYU-002 (Kasa)", "TM2-KAS-02"),
    "breathlessness": ("AYU-003 (Shwasa)", "TM2-SHW-03"),
    "shwasa": ("AYU-003 (Shwasa)", "TM2-SHW-03"),
    "joint pain": ("AYU-004 (Amavata)", "TM2-AMA-04"),
    "amavata": ("AYU-004 (Amavata)", "TM2-AMA-04"),
    "skin rash": ("AYU-005 (Kushta)", "TM2-KUS-05"),
    "kushta": ("AYU-005 (Kushta)", "TM2-KUS-05"),
    "headache": ("AYU-006 (Shiroroga)", "TM2-SHI-06"),
    "indigestion": ("AYU-007 (Agnimandya)", "TM2-AGN-07"),
    "agnimandya": ("AYU-007 (Agnimandya)", "TM2-AGN-07"),
    "chest pain": ("AYU-008 (Hridroga)", "TM2-HRI-08"),
    "paralysis": ("AYU-009 (Pakshaghata)", "TM2-PAK-09"),
    "diabetes": ("AYU-010 (Prameha)", "TM2-PRA-10"),
    "prameha": ("AYU-010 (Prameha)", "TM2-PRA-10"),
}

def extract_and_map(case_text_or_answers):
    """
    Extracts NAMASTE and ICD-11 TM2 codes from case history text or structured answers.
    Returns: (namaste_codes, icd11_tm2_codes, referral_flag)
    """
    text = ""
    if isinstance(case_text_or_answers, dict):
        text = " ".join([str(v) for v in case_text_or_answers.values()]).lower()
    else:
        text = str(case_text_or_answers).lower()

    found_namaste = []
    found_icd11 = []
    referral_flag = False

    # Check Red Flags
    for flag in RED_FLAG_TERMS:
        if flag in text:
            referral_flag = True
            break

    # Map Terms
    for keyword, (namaste_code, icd_code) in NAMASTE_DICTIONARY.items():
        if keyword in text:
            if namaste_code not in found_namaste:
                found_namaste.append(namaste_code)
            if icd_code not in found_icd11:
                found_icd11.append(icd_code)

    if not found_namaste:
        found_namaste.append("AYU-GEN-00 (General Ayush Case)")
        found_icd11.append("TM2-GEN-00")

    return ", ".join(found_namaste), ", ".join(found_icd11), referral_flag

def build_ai_summary(ayush_system, structured_answers, namaste_codes="", icd11_tm2_codes=""):
    """
    Generates a structured clinical summary based on Ayush case data.
    """
    if isinstance(structured_answers, dict):
        complaints = structured_answers.get("chief_complaints", structured_answers.get("symptoms", "Not specified"))
        duration = structured_answers.get("duration", "Recent")
        notes = ", ".join([f"{k}: {v}" for k, v in structured_answers.items() if k not in ["chief_complaints", "duration"]])
    else:
        complaints = str(structured_answers)
        duration = "N/A"
        notes = "N/A"

    summary = (
        f"[{ayush_system.upper()} CLINICAL SUMMARY]\n"
        f"Primary Complaints: {complaints} (Duration: {duration})\n"
        f"Clinical Details: {notes}\n"
        f"NAMASTE Classification: {namaste_codes or 'Pending'}\n"
        f"ICD-11 TM2 Code: {icd11_tm2_codes or 'Pending'}"
    )
    return summary

def assess_priority(case_record_or_answers, citizen_history=None, citizen_age=None):
    """
    Assesses patient case priority.
    Returns: 'urgent', 'review_required', or 'routine'
    """
    text = ""
    if hasattr(case_record_or_answers, "structured_answers"):
        answers = case_record_or_answers.structured_answers or ""
        text = str(answers).lower() + " " + str(getattr(case_record_or_answers, "ai_summary", "")).lower()
    elif isinstance(case_record_or_answers, dict):
        text = " ".join([str(v) for v in case_record_or_answers.values()]).lower()
    else:
        text = str(case_record_or_answers).lower()

    # Rule 1: Red Flag match -> Urgent
    for term in RED_FLAG_TERMS:
        if term in text:
            return "urgent"

    # Rule 2: Vulnerable Age with multiple symptoms -> Review Required / Urgent
    if citizen_age is not None and (citizen_age < 5 or citizen_age > 65):
        if len(text.split()) > 10:
            return "review_required"

    # Rule 3: Previous urgent cases in history -> Review Required
    if citizen_history:
        urgent_count = sum(1 for c in citizen_history if getattr(c, "priority", "") == "urgent" or getattr(c, "referral_flag", False))
        if urgent_count >= 1:
            return "review_required"

    # Moderate indicators
    moderate_indicators = ["fever", "pain", "swelling", "vomiting", "diarrhea", "infection"]
    matched_mod = sum(1 for mod in moderate_indicators if mod in text)
    if matched_mod >= 2:
        return "review_required"

    return "routine"

def get_detailed_risk_analysis(case_text_or_answers, citizen_age=None, severity=None):
    """
    Analyzes case details for high risk & red flags.
    Returns a dict with risk_level, red_flags, risk_score, and triage_badge_color.
    """
    text = ""
    if isinstance(case_text_or_answers, dict):
        text = " ".join([str(v) for v in case_text_or_answers.values()]).lower()
    else:
        text = str(case_text_or_answers).lower()

    red_flags = []
    
    # Check Red Flags
    for flag in RED_FLAG_TERMS:
        if flag in text:
            red_flags.append(f"CRITICAL RED-FLAG: '{flag.title()}' detected in patient assessment.")

    if severity and str(severity).lower() in ['severe', 'critical']:
        red_flags.append(f"HIGH SEVERITY ALERT: Patient state evaluated as '{severity.upper()}'.")

    if citizen_age is not None:
        try:
            age = int(citizen_age)
            if age < 5:
                red_flags.append("PEDIATRIC WARNING: High-risk patient age (<5 years).")
            elif age > 65:
                red_flags.append("GERIATRIC WARNING: Vulnerable senior patient age (>65 years).")
        except (ValueError, TypeError):
            pass

    if len(red_flags) >= 2 or (severity and str(severity).lower() == 'critical'):
        risk_level = "CRITICAL / URGENT"
        risk_score = 9
        badge_color = "rose"
    elif len(red_flags) == 1 or (severity and str(severity).lower() == 'severe'):
        risk_level = "HIGH RISK"
        risk_score = 7
        badge_color = "amber"
    elif "fever" in text or "pain" in text or (severity and str(severity).lower() == 'moderate'):
        risk_level = "MODERATE RISK"
        risk_score = 4
        badge_color = "yellow"
    else:
        risk_level = "ROUTINE Intake"
        risk_score = 2
        badge_color = "emerald"

    if not red_flags:
        red_flags.append("No immediate critical red flags detected. Standard clinical triage applies.")

    return {
        "risk_level": risk_level,
        "red_flags": red_flags,
        "risk_score": risk_score,
        "badge_color": badge_color
    }

