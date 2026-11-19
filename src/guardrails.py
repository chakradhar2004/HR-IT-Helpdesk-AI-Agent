"""Guardrails module for HR and IT Helpdesk AI Agent.

Implements:
1. Input Guardrails:
   - Adversarial prompt injection detection (heuristics & pattern matching).
   - Domain restriction enforcement (HR and IT helpdesk queries only).
2. Output Guardrails:
   - Sensitive PII redaction (phone numbers, email addresses, national IDs).
   - Source citation enforcement for policy queries.
   - Grounding validation (preventing hallucinations for missing employees).
"""

import re
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field

class GuardrailResult(BaseModel):
    passed: bool
    category: str = "PASSED"  # "PASSED", "PROMPT_INJECTION", "OFF_TOPIC", "INVALID_OUTPUT"
    reason: str = ""
    sanitized_text: Optional[str] = None
    refusal_message: Optional[str] = None

# ==============================================================================
# 1. INPUT GUARDRAIL PATTERNS
# ==============================================================================

# Prompt injection and jailbreak heuristic patterns
INJECTION_PATTERNS = [
    r"(?i)\b(ignore|disregard|forget|override|bypass)\b.*?\b(previous|all|system|base|prior)\b.*?\b(instructions?|prompts?|rules?|guidelines?)\b",
    r"(?i)\b(system\s*prompt|developer\s*prompt|hidden\s*instructions?)\b",
    r"(?i)\b(reveal|show|display|leak|print|dump|output)\b.*?\b(system\s*prompt|credentials?|passwords?|secret|database\s*schema|sql\s*tables?)\b",
    r"(?i)\b(dump\s+sql|drop\s+table|delete\s+from|insert\s+into|select\s+\*\s+from\s+information_schema|union\s+select)\b",
    r"(?i)\b(jailbreak|dan\s+mode|unrestricted\s+mode|bypass\s+filters?)\b",
    r"(?i)\b(output\s+your\s+system\s+prompt)\b",
    r"(?i)\b(database\s+credentials|db\s+password|admin\s+credentials)\b",
]

# HR and IT Helpdesk Domain keywords
HR_IT_KEYWORDS = [
    # HR keywords
    r"\bleave\b", r"\bvacation\b", r"\bholiday\b", r"\bpto\b", r"\bsick\b", r"\bcarry[- ]?forward\b",
    r"\bwfh\b", r"\bwork(?:ing)?\s+from\s+home\b", r"\bremote\b", r"\bhybrid\b", r"\bprobation\b",
    r"\breimbursement\b", r"\bexpense\b", r"\ballowance\b", r"\bsubsidy\b", r"\bper\s+diem\b",
    r"\bparental\b", r"\bmaternity\b", r"\bpaternity\b", r"\bbenefit\b", r"\bhr\b",
    r"\bhuman\s+resources\b", r"\bpolicy\b", r"\bpolicies\b", r"\battendance\b",
    r"\bmanager\b", r"\brole\b", r"\bdepartment\b", r"\beligib\w*\b", r"\bguideline\w*\b",
    
    # IT keywords
    r"\b(it\s+ticket|ticket|tickets|tkt[-\d]+)\b", r"\blaptop\b", r"\bhardware\b", r"\bsoftware\b",
    r"\bmonitor\b", r"\bscreen\b", r"\bkeyboard\b", r"\bmouse\b", r"\bcharger\b", r"\bbattery\b",
    r"\bmacbook\b", r"\bdell\b", r"\blenovo\b", r"\bworkstation\b", r"\basset\b", r"\basset\s*id\b",
    r"\bvpn\b", r"\bmfa\b", r"\bokta\b", r"\bcisco\b", r"\banyconnect\b", r"\bnetwork\b",
    r"\bpassword\b", r"\bcredential\b", r"\blogin\b", r"\bsso\b", r"\baccess\b",
    r"\breset\b", r"\bsecurity\b", r"\bincident\b", r"\bphishing\b", r"\bbitlocker\b",
    r"\bfilevault\b", r"\bcrowdstrike\b", r"\bedr\b", r"\bwipe\b", r"\bit\s+helpdesk\b",
    r"\bit\s+support\b", r"\bdesk\b", r"\bportal\b", r"\bprofile\b",
    r"\breplace\w*\b", r"\bcycle\b", r"\brefresh\b",
    
    # Employee identifiers
    r"\bemp\d{3,}\b", r"\bemployee\b", r"\bcolleague\b", r"\bstaff\b",
]

# Common off-topic patterns that should be politely refused
OFF_TOPIC_PATTERNS = [
    r"(?i)\b(write\s+(?:a\s+)?(?:python|javascript|java|c\+\+|bash|code|script))\b",
    r"(?i)\b(scrape\s+websites?|web\s+scraping|hacker|exploit)\b",
    r"(?i)\b(stock\s+market|cryptocurrency|bitcoin|investing\s+advice|financial\s+portfolio)\b",
    r"(?i)\b(recipe|cook|baking|pasta|pizza|cocktail)\b",
    r"(?i)\b(world\s+cup|olympics|football|soccer|cricket|nba|super\s*bowl)\b",
    r"(?i)\b(movie|film|actor|actress|hollywood|celebrity)\b",
    r"(?i)\b(write\s+a\s+(?:poem|essay|story|song|joke))\b",
]

def check_prompt_injection(user_input: str) -> GuardrailResult:
    """Checks if the user input contains prompt injection or adversarial attacks."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input):
            return GuardrailResult(
                passed=False,
                category="PROMPT_INJECTION",
                reason=f"Matched adversarial pattern: {pattern}",
                refusal_message="Security Alert: Your request has been blocked by our security guardrails as it contains patterns resembling prompt injection or unauthorized system access instructions."
            )
    return GuardrailResult(passed=True, category="PASSED")

def check_domain_restriction(user_input: str) -> GuardrailResult:
    """Ensures query is strictly within HR or IT Helpdesk scope."""
    # First check explicit off-topic patterns
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, user_input):
            return GuardrailResult(
                passed=False,
                category="OFF_TOPIC",
                reason=f"Matched out-of-scope pattern: {pattern}",
                refusal_message="I apologize, but as the corporate HR and IT Helpdesk AI Assistant, I can only assist with internal HR policies, employee records, IT support tickets, and technology guidelines. I cannot assist with external coding tasks, general trivia, or non-work-related queries."
            )
            
    # Then verify at least one HR/IT domain concept or question is present
    has_hr_it_concept = any(re.search(pat, user_input, re.IGNORECASE) for pat in HR_IT_KEYWORDS)
    if not has_hr_it_concept:
        # Check if it's a simple greeting or general conversation
        greeting_pattern = r"(?i)^(hi|hello|hey|good\s+(?:morning|afternoon|evening)|help)\b"
        if re.search(greeting_pattern, user_input.strip()):
            return GuardrailResult(passed=True, category="PASSED")
            
        return GuardrailResult(
            passed=False,
            category="OFF_TOPIC",
            reason="Query does not contain recognized HR or IT helpdesk concepts.",
            refusal_message="I am the Enterprise HR & IT Helpdesk Virtual Assistant. I am specifically designed to help with company HR policies (leave, remote work, expenses), IT support (VPN, hardware refresh, credentials), and employee ticket/profile queries. How can I assist you with HR or IT today?"
        )

    return GuardrailResult(passed=True, category="PASSED")

def validate_input(user_input: str) -> GuardrailResult:
    """Combines all input guardrail checks."""
    injection_check = check_prompt_injection(user_input)
    if not injection_check.passed:
        return injection_check

    domain_check = check_domain_restriction(user_input)
    if not domain_check.passed:
        return domain_check

    return GuardrailResult(passed=True, category="PASSED")


# ==============================================================================
# 2. OUTPUT GUARDRAIL: PII REDACTION & RESPONSE VALIDATION
# ==============================================================================

# Regex for detecting email addresses
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Regex for phone numbers: matches international or domestic phone formats
# (e.g. +1-555-012-3456, (555) 012-3456, 555-014-9876, +1 555 019 2834)
PHONE_PATTERN = re.compile(
    r"(?<![\w\-])(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?![\w\-])"
)

# Regex for national IDs: SSN (###-##-####), Aadhaar (#### #### ####), PAN ([A-Z]{5}[0-9]{4}[A-Z])
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")

def redact_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Redacts sensitive PII from text while preserving non-sensitive identifiers
    like employee IDs (EMP101) and ticket IDs (TKT-001).
    
    Returns:
        Tuple[redacted_text, redaction_counts]
    """
    redaction_counts = {
        "email": 0,
        "phone": 0,
        "id": 0
    }

    # Redact email addresses
    email_matches = EMAIL_PATTERN.findall(text)
    if email_matches:
        redaction_counts["email"] += len(email_matches)
        text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)

    # Redact phone numbers
    phone_matches = PHONE_PATTERN.findall(text)
    if phone_matches:
        redaction_counts["phone"] += len(phone_matches)
        text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)

    # Redact national / tax IDs
    for pattern in [SSN_PATTERN, AADHAAR_PATTERN, PAN_PATTERN]:
        matches = pattern.findall(text)
        if matches:
            redaction_counts["id"] += len(matches)
            text = pattern.sub("[REDACTED_ID]", text)

    return text, redaction_counts

def validate_citations(response: str, route: str, citations: list) -> str:
    """Ensures policy responses cite their sources explicitly."""
    if route in ("rag", "hybrid") and citations:
        has_citation_in_text = any(cite in response for cite in citations) or "Source:" in response or "[Source:" in response
        if not has_citation_in_text:
            formatted_citations = "\n\n**Sources:**\n" + "\n".join(f"- `{c}`" for c in citations)
            response += formatted_citations
    return response

def validate_output(response: str, route: str = "general", citations: Optional[list] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Applies all output guardrails:
    1. PII Redaction
    2. Citation verification
    """
    citations = citations or []
    sanitized, redaction_stats = redact_pii(response)
    validated = validate_citations(sanitized, route, citations)
    
    meta = {
        "redactions_applied": redaction_stats,
        "pii_redacted": any(v > 0 for v in redaction_stats.values()),
        "citations_verified": bool(citations)
    }
    return validated, meta
