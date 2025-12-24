import re
from venv import logger


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


def process_price_text(price_text: str) -> int:
        """Process raw price text to extract integer price value and adjust the price value if it was Rial
        """
        try:
            price_value: int = 0
            if not price_text:
                return 0
            # convert any non-english digits
            price_text = to_english_digits(price_text)
            # remove commas and spaces
            price_text = price_text.replace(',', '').replace(' ', '')
            # extract numeric part using regex
            match = re.search(r'(\d+)', price_text)
            if match:
                price_str = match.group(1)
                price_value = int(price_str)
                # Check if the price text contains 'rial' or 'ریال' to adjust the value
                if price_value and re.search(r'(rial|ریال)', price_text, re.I):
                    price_value = price_value // 10
        except Exception as e:
            logger.error(f"\nError processing price text '{price_text}':\n{e}\n")    
        return price_value
