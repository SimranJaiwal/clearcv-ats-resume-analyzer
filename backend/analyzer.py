import re
from collections import Counter
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

SKILL_GROUPS = {
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sql server", "sqlite", "oracle sql"],
    "Python": ["python", "pandas", "numpy", "scikit-learn", "sklearn"],
    "Excel": ["excel", "microsoft excel", "pivot table", "vlookup", "xlookup"],
    "Power BI": ["power bi", "powerbi", "dax", "power query"],
    "Tableau": ["tableau"],
    "ETL": ["etl", "extract transform load", "data pipeline", "data pipelines"],
    "Data validation": ["data validation", "data quality", "quality checks", "data cleansing", "data cleaning"],
    "Data visualization": ["data visualization", "data visualisation", "dashboard", "dashboards", "reporting"],
    "Statistics": ["statistics", "statistical analysis", "hypothesis testing", "regression"],
    "Machine learning": ["machine learning", "classification", "clustering", "model evaluation"],
    "Java": ["java", "core java", "spring boot", "hibernate"],
    "JavaScript": ["javascript", "js", "typescript"],
    "HTML/CSS": ["html", "html5", "css", "css3", "responsive design"],
    "Communication": ["communication", "stakeholder management", "presentation", "cross-functional"],
    "Problem solving": ["problem solving", "troubleshooting", "root cause analysis"],
    "Cloud": ["aws", "azure", "gcp", "cloud computing"],
    "Git": ["git", "github", "version control"],
    "APIs": ["api", "apis", "rest api", "restful"],
    "Database design": ["database design", "dbms", "normalization", "database management"],
}

SECTION_PATTERNS = {
    "Summary / Objective": [r"\bsummary\b", r"\bobjective\b", r"\bprofile\b", r"\babout me\b"],
    "Experience": [r"\bexperience\b", r"\bemployment\b", r"\bwork history\b", r"\binternship\b"],
    "Education": [r"\beducation\b", r"\bacademic\b", r"\bqualification\b"],
    "Skills": [r"\bskills\b", r"\btechnical skills\b", r"\bcore competencies\b"],
    "Projects": [r"\bprojects\b", r"\bacademic projects\b", r"\bpersonal projects\b"],
    "Certifications": [r"\bcertifications?\b", r"\bcourses\b", r"\blicenses\b"],
}

def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def contains_term(text: str, term: str) -> bool:
    # Match phrases robustly without treating a substring as a word (e.g. "java" in "javascript").
    pattern = r"(?<![a-z0-9+#])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9+#])"
    return re.search(pattern, text.lower()) is not None

def extract_requirements(jd: str):
    lower = jd.lower()
    requirements = []
    for skill, terms in SKILL_GROUPS.items():
        found = [term for term in terms if contains_term(lower, term)]
        if found:
            requirements.append({
                "skill": skill,
                "terms_found_in_jd": found,
                "priority": "required" if re.search(
                    r"(required|must have|mandatory|essential|minimum|strong proficiency|proficient in|shall have).{0,100}" +
                    r"(?:" + "|".join(re.escape(t) for t in found) + r")", lower
                ) else "preferred"
            })
    # Explicit degree / experience signals, useful beyond technical skills.
    for label, patterns in [
        ("Years of experience", [r"\b\d+\+?\s*(?:years?|yrs?)\b"]),
        ("Degree / education", [r"\b(bachelor'?s?|b\.?tech|b\.?e\.?|master'?s?|mba|degree|diploma)\b"]),
        ("Certifications", [r"\b(certification|certified|certificate)\b"]),
    ]:
        if any(re.search(p, lower) for p in patterns):
            requirements.append({"skill": label, "terms_found_in_jd": [m.group(0) for p in patterns for m in re.finditer(p, lower)][:5], "priority": "required" if re.search(r"\b(required|mandatory|must have)\b", lower) else "preferred"})
    return requirements

def analyze_resume(resume_text: str, jd_text: str, filename: str):
    resume = clean_text(resume_text)
    jd = clean_text(jd_text)
    resume_lower, jd_lower = resume.lower(), jd.lower()

    requirements = extract_requirements(jd)
    for item in requirements:
        skill = item["skill"]
        terms = SKILL_GROUPS.get(skill, item["terms_found_in_jd"])
        item["matched"] = any(contains_term(resume_lower, t) for t in terms)
        item["resume_evidence"] = next((t for t in terms if contains_term(resume_lower, t)), None)
        item["status"] = "matched" if item["matched"] else "not_found"
        item["recommendation"] = (
            "Keep this evidence visible in your Skills, Experience, or Projects section."
            if item["matched"] else
            "If you genuinely have this skill or qualification, add a specific example in the relevant section. Do not add it just to match the JD."
        )

    required = [x for x in requirements if x["priority"] == "required"]
    preferred = [x for x in requirements if x["priority"] == "preferred"]
    required_score = round(100 * sum(x["matched"] for x in required) / len(required)) if required else None
    preferred_score = round(100 * sum(x["matched"] for x in preferred) / len(preferred)) if preferred else None
    all_score = round(100 * sum(x["matched"] for x in requirements) / len(requirements)) if requirements else 0

    sections = {}
    for label, patterns in SECTION_PATTERNS.items():
        sections[label] = any(re.search(p, resume_lower) for p in patterns)

    bullets = [line.strip(" •\t-") for line in resume.splitlines() if re.match(r"^\s*(?:[-•*]|\d+[.)])\s+", line)]
    metric_bullets = [b for b in bullets if re.search(r"\b\d+(?:\.\d+)?\s*%?\b|\b\d+\s*(?:users|customers|projects|records|hours|days|weeks|months)\b", b, re.I)]
    action_verbs = ["built", "developed", "created", "analyzed", "analysed", "improved", "reduced", "increased", "automated", "implemented", "designed", "delivered", "optimized", "optimised", "validated", "managed", "led"]
    action_bullets = [b for b in bullets if any(re.match(r"(?i)^" + v + r"\b", b) for v in action_verbs)]

    review = []
    def add_review(area, status, finding, suggestion, priority="Medium"):
        review.append({"area": area, "status": status, "finding": finding, "suggestion": suggestion, "priority": priority})

    add_review("Role alignment", "Positive" if all_score >= 60 else "Needs attention",
        f"{all_score}% of the detected JD requirements were found in the resume." if requirements else "No supported skill requirements were detected automatically from this JD.",
        "Prioritize mandatory requirements and show evidence in projects or experience." if all_score < 80 else "Keep the strongest role-relevant evidence near the top.")
    for section in ["Summary / Objective", "Skills", "Experience", "Education", "Projects"]:
        if sections.get(section):
            add_review(section, "Found", f"A section resembling '{section}' was detected.", "Ensure this section is relevant to the target role.")
        else:
            add_review(section, "Not detected", f"No clear '{section}' heading was detected.", f"Add a clearly labeled {section.lower()} section if it is relevant to your background.", "High" if section in ["Skills", "Experience", "Education"] else "Medium")

    if bullets:
        ratio = round(100 * len(metric_bullets) / len(bullets))
        add_review("Achievement evidence", "Good" if ratio >= 30 else "Improve",
            f"{len(metric_bullets)} of {len(bullets)} detected bullet points include a number or measurable indicator ({ratio}%).",
            "Where accurate, add scope or outcomes such as records analyzed, time saved, error reduction, users served, or project count." if ratio < 30 else "Check that metrics are accurate and explain the impact.")
        add_review("Action-oriented writing", "Good" if len(action_bullets) >= max(1, len(bullets)//3) else "Improve",
            f"{len(action_bullets)} bullet points begin with a recognized action verb.",
            "Start bullets with precise verbs and explain what you did, how you did it, and the result.")
    else:
        add_review("Achievement evidence", "Not assessed",
            "No standard bullet points were detected; the resume may use a different layout.",
            "Use concise bullets for responsibilities and achievements so recruiters can scan the document.")

    word_count = len(re.findall(r"\b[\w+#.-]+\b", resume))
    if word_count < 150:
        add_review("Resume detail", "Check", f"Only about {word_count} words were extracted.", "Confirm the full resume text was extracted; scanned PDFs or complex layouts may not parse correctly.", "High")
    elif word_count > 1100:
        add_review("Conciseness", "Check", f"About {word_count} words were extracted.", "Consider removing repetition and keeping the most relevant content prominent.")
    else:
        add_review("Resume detail", "Reasonable", f"About {word_count} words were extracted.", "Keep content targeted and easy to scan.")

    if not re.search(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", resume):
        add_review("Contact details", "Check", "No email address was detected in extracted text.", "Confirm contact details are present and readable in the document.")
    if not re.search(r"\b(?:linkedin\.com|github\.com|geeksforgeeks\.org|leetcode\.com)\b", resume_lower):
        add_review("Professional links", "Optional", "No common professional profile or portfolio link was detected.", "Add a relevant LinkedIn, GitHub, portfolio, or coding profile if useful for the role.")

    # Explainable heuristic: keyword coverage 70%, resume structure/readability 30%.
    section_score = round(100 * sum(sections.values()) / len(sections))
    readability_score = min(100, round((section_score * 0.65) + (min(word_count, 700) / 700 * 35)))
    overall = round(all_score * 0.7 + readability_score * 0.3) if requirements else readability_score

    jd_words = re.findall(r"[a-zA-Z][a-zA-Z+#.-]{2,}", jd_lower)
    common = [w for w, _ in Counter(w for w in jd_words if w not in ENGLISH_STOP_WORDS).most_common(18)]
    common = [w for w in common if not any(contains_term(resume_lower, term) for term in [w])][:12]

    return {
        "filename": filename,
        "overall_score": overall,
        "jd_match_score": all_score,
        "required_match_score": required_score,
        "preferred_match_score": preferred_score,
        "score_note": "Heuristic estimate based on detected JD requirements and resume structure; not an actual employer ATS score or a hiring prediction.",
        "summary": {
            "requirements_detected": len(requirements),
            "matched_requirements": sum(x["matched"] for x in requirements),
            "missing_requirements": sum(not x["matched"] for x in requirements),
            "required_detected": len(required),
            "required_matched": sum(x["matched"] for x in required),
            "preferred_detected": len(preferred),
            "preferred_matched": sum(x["matched"] for x in preferred),
            "word_count": word_count,
            "bullet_count": len(bullets),
        },
        "requirements": requirements,
        "sections": sections,
        "review": review,
        "potential_jd_terms_to_review": common,
    }
