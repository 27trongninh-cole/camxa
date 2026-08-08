"""
Fixed edit logic for the two known .pkg files.
These functions are intentionally isolated from pkg_codec so that if the
underlying source .pkg files get updated later, only the file paths in
config.py need to change -- the transform logic here stays valid as long
as the target XML structure (Back.xml / P2E1.xml) is unchanged.
"""
from pathlib import Path
import re

import pkg_codec as pc

DATA_DIR = Path(__file__).parent / "data"

COMMON_PKG_PATH = DATA_DIR / "CommonActions.pkg.bytes"
ACTOR530_PKG_PATH = DATA_DIR / "Actor_530_Actions.pkg.bytes"
BACK_SNIPPET_PATH = DATA_DIR / "back_insert_snippet.xml"

BACK_XML_ENTRY = "commonresource/Back.xml"
P2E1_XML_ENTRY = "530_Dirak/skill/P2E1.xml"

HEIGHT_RATE_MIN = 1.0
HEIGHT_RATE_MAX = 5.0


def _read_snippet() -> bytes:
    return BACK_SNIPPET_PATH.read_bytes()


def transform_back_xml(decoded: bytes, insert_enabled: bool) -> bytes:
    """Insert the fixed Track snippet right before the (single) </Action> tag."""
    if not insert_enabled:
        return decoded

    snippet = _read_snippet()

    marker = b"</Action>"
    count = decoded.count(marker)
    if count != 1:
        raise ValueError(
            f"Expected exactly one </Action> tag in Back.xml, found {count}"
        )

    idx = decoded.index(marker)
    # Insert snippet + CRLF before the closing tag, matching surrounding style.
    new_decoded = decoded[:idx] + snippet + b"\r\n" + decoded[idx:]
    return new_decoded


def transform_p2e1_xml(decoded: bytes, height_rate: float) -> bytes:
    """
    Set leftTimeSlerpBack to true and heightRate to the user-provided value
    inside the SetCameraHeightDuration event of P2E1.xml.
    """
    if not (HEIGHT_RATE_MIN <= height_rate <= HEIGHT_RATE_MAX):
        raise ValueError(
            f"height_rate must be between {HEIGHT_RATE_MIN} and {HEIGHT_RATE_MAX}"
        )

    text = decoded.decode("utf-8")

    # leftTimeSlerpBack: false -> true
    pattern_slerp = re.compile(
        r'(<bool name="leftTimeSlerpBack" value=")false(" )'
    )
    new_text, n_slerp = pattern_slerp.subn(r"\g<1>true\g<2>", text)
    if n_slerp != 1:
        raise ValueError(
            f"Expected exactly one leftTimeSlerpBack attribute, found {n_slerp}"
        )

    # heightRate: X.XXX -> user value, formatted with 3 decimals
    formatted_rate = f"{height_rate:.3f}"
    pattern_rate = re.compile(
        r'(<float name="heightRate" value=")[0-9]+\.[0-9]+(" )'
    )
    new_text, n_rate = pattern_rate.subn(rf"\g<1>{formatted_rate}\g<2>", new_text)
    if n_rate != 1:
        raise ValueError(f"Expected exactly one heightRate attribute, found {n_rate}")

    return new_text.encode("utf-8")


def build_common_pkg(insert_back_snippet: bool) -> bytes:
    pkg_bytes = COMMON_PKG_PATH.read_bytes()
    return pc.patch_pkg_xml(
        pkg_bytes,
        BACK_XML_ENTRY,
        lambda decoded: transform_back_xml(decoded, insert_back_snippet),
    )


def build_actor530_pkg(height_rate: float) -> bytes:
    pkg_bytes = ACTOR530_PKG_PATH.read_bytes()
    return pc.patch_pkg_xml(
        pkg_bytes,
        P2E1_XML_ENTRY,
        lambda decoded: transform_p2e1_xml(decoded, height_rate),
    )
