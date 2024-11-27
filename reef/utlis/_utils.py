import urllib.parse
from typing import List, Tuple, Dict


def _add_params_to_url(url: str, params: List[Tuple[str, str]]) -> str:
    if len(params) == 0:
        return url
    params_chunks = [
        f"{name}={urllib.parse.quote_plus(value)}" for name, value in params
    ]
    parameters_string = "&".join(params_chunks)
    return f"{url}?{parameters_string}"

def class_colors_to_hex(class_mapping: Dict[str, str]) -> Dict[str, str]:
    return {k: f"#{format(hash(k) % 0xFFFFFF, '06x')}" for k in class_mapping.values()}

