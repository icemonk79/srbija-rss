#!/usr/bin/env python3
"""Replace emoji and pictographic symbols with hosted Twemoji <img> tags,
and map other risky glyphs (arrows, minus sign, etc.) to ASCII / Latin-1.

Twemoji graphics: Copyright 2014-2021 Twitter, Inc. and other contributors;
Copyright 2022-present Jason Sofonia & Justine De Caires.
Licensed under CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/
Source: https://github.com/jdecked/twemoji (v17.0.3), 72x72 PNG assets.
"""
from __future__ import annotations

import os
import re
import shutil
import unicodedata
import urllib.request

CACHE_DIR = os.environ.get("TWEMOJI_CACHE", "/workspace/twemoji-72x72")
TWEMOJI_DOWNLOAD = (
    "https://cdn.jsdelivr.net/gh/jdecked/twemoji@v17.0.3/assets/72x72/{name}"
)

ZWJ = "\u200d"
VS16 = "\ufe0f"
VS15 = "\ufe0e"
KEYCAP = "\u20e3"

# Applied to a single character (a following VS15/VS16 is consumed).
# These must not appear in the live feed in the U+2190-U+2BFF range.
ASCII_MAP = {
    "\u2190": "<-",  # ←
    "\u2191": "^",   # ↑
    "\u2192": "->",  # →
    "\u2193": "v",   # ↓
    "\u2194": "<->", # ↔
    "\u2195": "^v",  # ↕
    "\u2196": "<-",  # ↖
    "\u2197": "->",  # ↗
    "\u2198": "->",  # ↘
    "\u2199": "<-",  # ↙
    "\u21a9": "<-",  # ↩
    "\u21aa": "->",  # ↪
    "\u21d0": "<=",  # ⇐
    "\u21d1": "^",   # ⇑
    "\u21d2": "=>",  # ⇒
    "\u21d3": "v",   # ⇓
    "\u21d4": "<=>", # ⇔
    "\u21e7": "^",   # ⇧
    "\u27a1": "->",  # ➡  (also often an emoji; ASCII is clearer in text)
    "\u2b05": "<-",  # ⬅
    "\u2b06": "^",   # ⬆
    "\u2b07": "v",   # ⬇
    "\u2212": "-",   # minus sign (in the verification range)
    "\u2213": "-/+",
    "\u2215": "/",
    "\u2217": "*",
    "\u2218": "o",
    "\u2219": "*",
    "\u221a": "sqrt",
    "\u221e": "inf",
    "\u2227": "&&",
    "\u2228": "||",
    "\u2229": "&",
    "\u222a": "|",
    "\u223c": "~",
    "\u2248": "~=",
    "\u2260": "!=",
    "\u2261": "==",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u00d7": "x",   # multiplication sign; Latin-1, but ASCII is safer
    "\u00f7": "/",
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    # U+2013 en dash and U+2014 em dash are kept (device font has them)
    "\u2213": "-/+",
}

# Dingbats without a Twemoji PNG, or when the image cannot be resolved.
LABEL_MAP = {
    "\u2713": "[OK]",  # ✓
    "\u2717": "[X]",   # ✗
    "\u2718": "[X]",   # ✘
    "\u2610": "[ ]",
    "\u2611": "[OK]",
    "\u2612": "[X]",
}

# Common section-header and status emoji to pre-seed into each repo
# so a future report still has icons if the cache is missing.
SEED_CODEPOINTS = """
1f525 1f6e1 1fa9f 1f6f0 2b50 1f4b8 26a1 1f393 1f3e2 1f427 1f4bb 1f4d6
1f4b0 1f310 1f52d 1f4ca 1f3af 1f9ed 1f500 1f7e2 1f534 1f4c5 1f305 1f319
1f5a5 1f6a8 2600 1f3db 1f9fe 2139 2705 274c 26a0 2714 2611 1f4a1 1f4dd
1f9e0 2695 1f6a2 1f4e1 1f512 1f511 1f510 1f6e1 1f4c8 1f4c9 1f4b9 1f7e0
1f7e1 1f7e3 1f7e4 2b55 26aa 26ab 23f0 231a 1f4f1 1f50d 2757 2753 2755
1f4da 1f4d5 1f4d7 1f4d8 1f4d9 1f4d4 1f4cb 1f4cc 1f4a0 1f680 1f6f0 1f30d
1f321 1f9ec 1f4b5 1f4b6 1f4b4 1f4b3 1f4b1 1f4b2 1f3e0 1f3e5 1f393 1f4d6
1f4ca 1f4c6 1f4c5 1f5d3 1f4ce 1f4c4 1f4dd 1f4e6 1f50c 1f50b 1f4bb 1f5a5
1f310 1f3af 1f524 1f4ac 1f4ad 1f4af 1f449 1f448 1f447 1f446 2705 274c
26a0 2139 1f6d1 1f6a8 1f198 1f199 1f197 1f3c6 1f947 1f948 1f949 1f4e2
1f4e3 1f4e1 1f4fa 1f4f0 1f4f6 1f5a8 1f5b1 1f5c2 1f5c3 1f5c4 1f5d2 1f5f3
1f9fe 1f9be 1fa7a 1fa78 1fa79 2699 26a1 23e9 23ea 23ed 23ee 23f8 23f9
23fa 25b6 25c0 25fc 25fb 23cf 1f500 1f501 1f502 1f504 1f3b5 1f3b6 1f3a7
1f9ed 1f9f0 1f6e0 1f527 1f528 1f529 1f517 1f4be 1f4bf 1f4c0 1f4bd 1f4bb
1f4e7 1f4e8 1f4e9 1f4eb 1f4ea 1f4ec 1f4ed 1f4ee 1f4ef 1f4cc 1f4cd 1f4ce
1f6a2 2693 1f30a 1f6f3 1f4a7 1f321 1f9e0 1f9ec 1f49b 2764 1f49a 1f499
1f4a1 1f31e 1f31d 1f31f 2b50 1f31a 1f31b 1f31c 1f311 1f312 1f313 1f314
1f315 2600 2601 2602 26c8 1f327 1f326 1f324 1f325 26c5 1f308 1f305 1f304
1f307 1f306 1f303 1f30c 1f4a8 1f32a 1f32b 1f32c 1f300 1f525 1f4a5 2728
1f4ab 1f30e 1f30f 1f5fa 1f5fd 1f3db 1f3f0 1f3e2 1f3e3 1f3ad 1f4da 1f4d6
1f4bb 1f427 1f3e2 1f393 1f451 1f6e1 1f6f0 1fa9f 1f6a7 1f6a6 1f6a5 1f6d1
""".split()

NOTICE = """Twemoji graphics
Copyright 2014-2021 Twitter, Inc. and other contributors
Copyright 2022-present Jason Sofonia & Justine De Caires
https://github.com/jdecked/twemoji

Graphics licensed under Creative Commons Attribution 4.0 International (CC-BY 4.0):
https://creativecommons.org/licenses/by/4.0/

These 72x72 PNG assets are from Twemoji v17.0.3 and are hosted here so
e-readers can load them from this same GitHub Pages site (no third-party CDN).
"""

_icon_dir = None
_base_url = None


def setup(icon_dir: str, base_url: str, cache_dir: str | None = None) -> None:
    """Configure output directory and public URL prefix (no trailing slash)."""
    global _icon_dir, _base_url, CACHE_DIR
    _icon_dir = icon_dir
    _base_url = base_url.rstrip("/")
    if cache_dir:
        CACHE_DIR = cache_dir
    os.makedirs(_icon_dir, exist_ok=True)
    notice = os.path.join(_icon_dir, "NOTICE.txt")
    if not os.path.exists(notice):
        with open(notice, "w", encoding="utf-8") as f:
            f.write(NOTICE)
    seed_common()


def seed_common() -> None:
    if not _icon_dir:
        return
    for name in SEED_CODEPOINTS:
        fname = name.strip().lower() + ".png"
        if not fname[:-4]:
            continue
        _ensure_icon(fname, download=False)


def _candidates(seq: str) -> list[str]:
    cps = [ord(c) for c in seq]
    full = "-".join(f"{c:x}" for c in cps) + ".png"
    no_vs = "-".join(f"{c:x}" for c in cps if c not in (0xFE0F, 0xFE0E)) + ".png"
    out = []
    for n in (full, no_vs):
        if n not in out and n != ".png":
            out.append(n)
    return out


def _find_in_dir(directory: str, names: list[str]) -> str | None:
    if not directory or not os.path.isdir(directory):
        return None
    for n in names:
        if os.path.isfile(os.path.join(directory, n)):
            return n
    return None


def _download(name: str, dest: str) -> bool:
    url = TWEMOJI_DOWNLOAD.format(name=name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "citaonica-rss/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if not data or len(data) < 50:
            return False
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        return True
    except Exception:
        return False


def _ensure_icon(name: str, download: bool = True) -> str | None:
    """Make sure icons/<name> exists; return the filename on success."""
    if not _icon_dir or not name.endswith(".png"):
        return None
    dest = os.path.join(_icon_dir, name)
    if os.path.isfile(dest):
        return name
    src = os.path.join(CACHE_DIR, name) if CACHE_DIR else ""
    if src and os.path.isfile(src):
        shutil.copy2(src, dest)
        return name
    if download and _download(name, dest):
        return name
    return None


def resolve_icon(seq: str, download: bool = True) -> str | None:
    names = _candidates(seq)
    found = _find_in_dir(_icon_dir or "", names) or _find_in_dir(CACHE_DIR, names)
    if found:
        return _ensure_icon(found, download=download)
    if download:
        for n in names:
            if _ensure_icon(n, download=True):
                return n
    return None


def _short_label(seq: str) -> str:
    if seq in LABEL_MAP:
        return LABEL_MAP[seq]
    # strip variation selectors for the lookup
    core = "".join(c for c in seq if c not in (VS16, VS15))
    if core in LABEL_MAP:
        return LABEL_MAP[core]
    if core in ASCII_MAP:
        return ASCII_MAP[core]
    # Prefer a readable name over an empty hole.
    names = []
    for c in core:
        n = unicodedata.name(c, "")
        if n:
            names.append(n.split(" WITH ")[0].title())
    if names:
        return "[" + " ".join(names) + "]"
    return ""


def img_tag(filename: str) -> str:
    return (
        f'<img src="{_base_url}/{filename}" alt="" width="20" height="20"/>'
    )


def _is_regional(ch: str) -> bool:
    o = ord(ch)
    return 0x1F1E6 <= o <= 0x1F1FF


def _is_skin(ch: str) -> bool:
    o = ord(ch)
    return 0x1F3FB <= o <= 0x1F3FF


def _is_tag(ch: str) -> bool:
    o = ord(ch)
    return 0xE0020 <= o <= 0xE007F


def _is_pictographic(ch: str) -> bool:
    o = ord(ch)
    if o < 0xA9:
        return False
    # Latin-1 copyright/registered become emoji only with a VS16; handled separately.
    if o in (0xA9, 0xAE):
        return False
    # Keep typographic punctuation and Serbian/Latin letters alone.
    if 0x2000 <= o <= 0x206F:
        return False
    if 0xC0 <= o <= 0x24F:
        return False
    # Letterlike / punctuation often used as emoji (ℹ️ ‼️ ⁉️ ™️)
    if o in (0x203C, 0x2049, 0x2122, 0x2139, 0x2328, 0x23CF, 0x24C2):
        return True
    if 0x231A <= o <= 0x231B:
        return True
    if 0x23E9 <= o <= 0x23F3 or 0x23F8 <= o <= 0x23FA:
        return True
    if o in (0x25AA, 0x25AB, 0x25B6, 0x25C0, 0x25FB, 0x25FC, 0x25FD, 0x25FE):
        return True
    if 0x2600 <= o <= 0x27BF:
        return True
    if 0x2934 <= o <= 0x2935:
        return True
    if 0x2B00 <= o <= 0x2BFF:
        return True
    if o in (0x3030, 0x303D, 0x3297, 0x3299):
        return True
    if 0x1F000 <= o <= 0x1FAFF:
        return True
    if 0x1F200 <= o <= 0x1F6FF:
        return True
    return False


def _is_risky_leftover(ch: str) -> bool:
    o = ord(ch)
    return (0x2190 <= o <= 0x2BFF) or (0x1F000 <= o <= 0x1FAFF) or o in (0xFE0F, 0x200D)


def replace_text(text: str, as_html: bool = True) -> str:
    """Replace emoji/symbols in a plain-text (non-tag) string."""
    if not text:
        return text
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]

        # ASCII-mapped glyphs (arrows, minus, inequalities). Consume VS16/VS15.
        if ch in ASCII_MAP:
            j = i + 1
            if j < n and text[j] in (VS16, VS15):
                j += 1
            # If this arrow is part of a ZWJ emoji sequence, don't flatten it.
            if j < n and text[j] == ZWJ:
                pass
            else:
                out.append(ASCII_MAP[ch])
                i = j
                continue

        # Flag: two regional indicators.
        if _is_regional(ch) and i + 1 < n and _is_regional(text[i + 1]):
            seq = text[i : i + 2]
            out.append(_render(seq, as_html))
            i += 2
            continue

        # © / ® only when they carry an emoji variation selector.
        if ch in ("\u00a9", "\u00ae") and i + 1 < n and text[i + 1] == VS16:
            j = i + 2
            seq = text[i:j]
            out.append(_render(seq, as_html))
            i = j
            continue

        if _is_pictographic(ch):
            j = i + 1
            while j < n and (text[j] in (VS16, VS15) or _is_skin(text[j])):
                j += 1
            while j < n and text[j] == ZWJ:
                j += 1
                if j < n:
                    j += 1
                    while j < n and (text[j] in (VS16, VS15) or _is_skin(text[j])):
                        j += 1
            while j < n and _is_tag(text[j]):
                j += 1
            if j < n and text[j] == KEYCAP:
                j += 1
            # keycap: digit/hash/star + VS16 + combining enclosing keycap already handled
            # if we started on the base and KEYCAP is next after optional VS16
            seq = text[i:j]
            out.append(_render(seq, as_html))
            i = j
            continue

        # Keycap starting at '#', '*', or digit
        if ch in "#*0123456789" and i + 1 < n:
            j = i + 1
            if j < n and text[j] in (VS16, VS15):
                j += 1
            if j < n and text[j] == KEYCAP:
                seq = text[i : j + 1]
                out.append(_render(seq, as_html))
                i = j + 1
                continue

        if ch in (VS16, VS15, ZWJ):
            # Orphaned combiner; drop so it cannot linger in the feed.
            i += 1
            continue

        if _is_risky_leftover(ch):
            out.append(_render(ch, as_html))
            i += 1
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def _render(seq: str, as_html: bool) -> str:
    filename = resolve_icon(seq, download=True)
    if filename and as_html and _base_url:
        return img_tag(filename)
    return _short_label(seq)


_TAG_SPLIT = re.compile(r"(<[^>]+>)")


def replace_html(html: str) -> str:
    """Replace in text nodes only, leaving existing tags (and URLs in attrs) alone."""
    parts = _TAG_SPLIT.split(html)
    for i, part in enumerate(parts):
        if part.startswith("<"):
            continue
        parts[i] = replace_text(part, as_html=True)
    return "".join(parts)


def replace_plain(text: str) -> str:
    """For RSS <title> and other non-HTML fields: ASCII / labels, never <img>."""
    return replace_text(text, as_html=False)
