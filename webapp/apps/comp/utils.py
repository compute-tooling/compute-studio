import difflib
from typing import Tuple


def json_int_key_encode(rename_dict):
    """
    Recursively rename integer value keys if they are casted to strings
    via JSON encoding

    returns: dict with new keys
    """
    if isinstance(rename_dict, dict):
        for k in list(rename_dict.keys()):
            if hasattr(k, "isdigit") and k.isdigit():
                new_label = int(k)
            else:
                new_label = k
            rename_dict[new_label] = json_int_key_encode(rename_dict.pop(k))
    return rename_dict
