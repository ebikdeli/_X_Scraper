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
