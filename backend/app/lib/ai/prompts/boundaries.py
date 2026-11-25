import re

OUT_OF_SCOPE_PATTERN = re.compile(
    r"\border(?:s| status)?\b|\bcheckout\b|\bpayment(?:s)?\b|\bpay\b|"
    r"\brefund(?:s)?\b|\breturn(?:s| policy)?\b|\bstore polic(?:y|ies)\b|"
    r"\bwarranty polic(?:y|ies)\b|\bshipping\b|\baccount\b|\blog ?in\b",
    re.IGNORECASE,
)

OUT_OF_SCOPE_REPLY = (
    "I can’t help with orders, checkout, payments, accounts, returns, or store policies "
    "in this version. I can help discover products and answer catalog-backed product questions."
)


def is_out_of_scope(message: str) -> bool:
    """Store policies and consequential/commercial workflows never enter product Q&A."""
    return OUT_OF_SCOPE_PATTERN.search(message) is not None
