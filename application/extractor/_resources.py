import re


def to_english_digits(text: str) -> str:
    """
    Convert Persian and Arabic-Indic digits in a string to English digits.
    """
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    translation_table = {}

    # Persian to English
    for p, e in zip(persian_digits, english_digits):
        translation_table[ord(p)] = e

    # Arabic to English
    for a, e in zip(arabic_digits, english_digits):
        translation_table[ord(a)] = e

    return text.translate(translation_table)


def subset_dict(data_dict: dict, needed_fields: list, include_missing: bool = False, default=None) -> dict:
    """
    Create a subset of the product data dictionary based on specified fields.
    """
    if include_missing:
        return {k: data_dict.get(k, default) for k in needed_fields}
    return {k: data_dict[k] for k in needed_fields if k in data_dict}

def clean_text(text: str) -> str:
    """Clean and normalize text by removing extra whitespace and unwanted characters."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove unwanted characters (example: non-printable characters)
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text
