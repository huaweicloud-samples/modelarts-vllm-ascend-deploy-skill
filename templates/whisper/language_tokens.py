"""Sunbird Whisper language token ids (Transformers). Do not use faster-whisper remaps here."""

# Existing Whisper language codes + overwritten unused slots (model card).
LANGUAGE_TOKENS = {
    "eng": 50259, "fra": 50265, "swa": 50318, "sna": 50324, "yor": 50325, "som": 50326,
    "afr": 50327, "amh": 50334, "mlg": 50349, "lin": 50353, "hau": 50354,
    "ach": 50357, "aka": 50356, "bam": 50355, "bem": 50352, "ber": 50351,
    "cgg": 50350, "dag": 50348, "dga": 50347, "ewe": 50346, "ful": 50345,
    "ibo": 50344, "kab": 50343, "kau": 50342, "kik": 50341, "kin": 50340,
    "kln": 50339, "koo": 50338, "kpo": 50337, "led": 50336, "lgg": 50335,
    "lth": 50333, "lug": 50332, "luo": 50331, "luy": 50330, "myx": 50329,
    "nbl": 50328, "nya": 50323, "nyn": 50322, "orm": 50321, "pcm": 50320,
    "ruc": 50319, "rwm": 50317, "sot": 50316, "teo": 50315, "tsn": 50314,
    "ttj": 50313, "wol": 50312, "xho": 50311, "xog": 50310, "zul": 50309,
}

# ISO-639-1 / common aliases → Sunbird code
ALIASES = {
    "en": "eng", "fr": "fra", "sw": "swa", "af": "afr", "zu": "zul", "xh": "xho",
    "st": "sot", "tn": "tsn", "english": "eng", "french": "fra", "swahili": "swa",
    "afrikaans": "afr", "zulu": "zul", "xhosa": "xho",
}
