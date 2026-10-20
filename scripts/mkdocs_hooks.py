"""MkDocs hooks for विचारालय (listed under `hooks:` in mkdocs.yml).

1. Devanagari-safe slugify, copied from ssengine's mkdocs_hooks.py. The
   default slugify drops vowel signs and the virama, so a heading like
   "प्रभेदाः" would get the id "परभद". This one keeps them. It's used for
   heading anchors and, as a fallback, for blog post and category URLs.
2. Sanskrit nav labels for folders, from `extra.section_titles`.
3. Footnote-marker shorthand, also from ssengine: `सुखं^१` -> `सुखं<sup>१</sup>`.
"""

import re
import unicodedata

from mkdocs.structure.nav import Section

# --- 1. Devanagari-safe slugify -------------------------------------------

_RE_TAGS = re.compile(r"</?[^>]*>", re.UNICODE)
_RE_WS = re.compile(r"\s+", re.UNICODE)
_COMBINING_CATEGORIES = ("Mn", "Mc", "Me")


def devanagari_safe_slugify(text: str, sep: str) -> str:
    """Keep letters, digits, `-`, `_` and combining marks; whitespace -> sep."""
    text = _RE_TAGS.sub("", text)
    text = unicodedata.normalize("NFC", text).strip().lower()
    kept = "".join(
        ch for ch in text
        if ch.isalnum() or ch in "-_" or ch.isspace()
        or unicodedata.category(ch) in _COMBINING_CATEGORIES
    )
    return _RE_WS.sub(sep, kept)


def on_config(config, **kwargs):
    config["mdx_configs"].setdefault("toc", {})["slugify"] = devanagari_safe_slugify
    # A post without `slug:` (or a Devanagari category name) would
    # otherwise get a mangled URL from the blog plugin's own slugify.
    blog = config["plugins"].get("material/blog")
    if blog is not None:
        blog.config.post_slugify = devanagari_safe_slugify
        blog.config.categories_slugify = devanagari_safe_slugify
    return config


# --- 2. Sanskrit labels for folders in the nav ------------------------------

def _section_dir(section: Section, depth: int):
    """The folder a nav section stands for: the first `depth` path parts of
    any page inside it."""
    for item in section.children:
        if isinstance(item, Section):
            found = _section_dir(item, depth)
            if found:
                return found
        elif getattr(item, "file", None) is not None:
            parts = item.file.src_uri.split("/")
            if len(parts) > depth:
                return "/".join(parts[:depth])
    return None


def _relabel(items, titles, depth):
    for item in items:
        if isinstance(item, Section):
            path = _section_dir(item, depth)
            if path in titles:
                item.title = titles[path]
            _relabel(item.children, titles, depth + 1)


def on_nav(nav, config, **kwargs):
    titles = (config.get("extra") or {}).get("section_titles") or {}
    if titles:
        _relabel(nav.items, {k.strip("/"): v for k, v in titles.items()}, 1)
    return nav


# --- 3. Footnote-marker shorthand -----------------------------------------
# Only a caret followed by Devanagari digits (०-९) is touched. `\^१` gives a
# literal `^१`. Fenced code blocks are left alone.

_RE_FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.MULTILINE | re.DOTALL)
_RE_SUP = re.compile(r"(\\?)\^([०-९]+)")


def _sup(m):
    return f"^{m.group(2)}" if m.group(1) else f"<sup>{m.group(2)}</sup>"


def on_page_markdown(markdown, **kwargs):
    out, pos = [], 0
    for f in _RE_FENCE.finditer(markdown):
        out.append(_RE_SUP.sub(_sup, markdown[pos:f.start()]))
        out.append(f.group(0))
        pos = f.end()
    out.append(_RE_SUP.sub(_sup, markdown[pos:]))
    return "".join(out)
