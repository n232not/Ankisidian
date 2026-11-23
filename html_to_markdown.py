"""
Ankisidian - HTML to Markdown Converter
Handles HTML formatting from Anki cards, MathJax/LaTeX, Cloze deletions,
media tags, tables, lists, and HTML entities into clean Obsidian Markdown.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import List, Tuple
from urllib.parse import unquote


class HTMLToMarkdownParser(HTMLParser):
    def __init__(self, cloze_style: str = "highlight", use_wikilinks: bool = True):
        super().__init__()
        self.cloze_style = cloze_style
        self.use_wikilinks = use_wikilinks
        self.result: List[str] = []
        self.tag_stack: List[str] = []
        self.list_stack: List[Tuple[str, int]] = []  # ('ul'|'ol', count)
        self.in_pre = False
        self.in_code = False
        self.current_href: str | None = None
        self.link_text: List[str] = []

    def get_markdown(self) -> str:
        text = "".join(self.result)
        # Normalize excessive blank lines (max 2 consecutive newlines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        self.tag_stack.append(tag)
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag in ("p", "div"):
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n\n")
        elif tag == "br":
            self.result.append("\n")
        elif tag in ("b", "strong"):
            self.result.append("**")
        elif tag in ("i", "em"):
            self.result.append("*")
        elif tag in ("s", "strike", "del"):
            self.result.append("~~")
        elif tag == "u":
            self.result.append("<u>")
        elif tag == "mark":
            self.result.append("==")
        elif tag == "code":
            if not self.in_pre:
                self.in_code = True
                self.result.append("`")
        elif tag == "pre":
            self.in_pre = True
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
            self.result.append("```\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n\n")
            self.result.append("#" * level + " ")
        elif tag == "blockquote":
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n\n")
            self.result.append("> ")
        elif tag == "ul":
            self.list_stack.append(("ul", 0))
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
        elif tag == "ol":
            self.list_stack.append(("ol", 1))
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
        elif tag == "li":
            indent = "  " * (len(self.list_stack) - 1)
            if self.list_stack:
                list_type, count = self.list_stack[-1]
                if list_type == "ol":
                    prefix = f"{indent}{count}. "
                    self.list_stack[-1] = (list_type, count + 1)
                else:
                    prefix = f"{indent}- "
            else:
                prefix = "- "
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
            self.result.append(prefix)
        elif tag == "a":
            self.current_href = attr_dict.get("href", "")
            self.link_text = []
        elif tag == "img":
            src = attr_dict.get("src", "")
            alt = attr_dict.get("alt", "")
            if src:
                clean_src = unquote(src.split("/")[-1].split("?")[0])
                if self.use_wikilinks:
                    self.result.append(f"![[{clean_src}]]")
                else:
                    self.result.append(f"![{alt or clean_src}]({src})")
        elif tag == "hr":
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n\n")
            self.result.append("---\n\n")

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in self.tag_stack:
            self.tag_stack.remove(tag)

        if tag in ("p", "div"):
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n\n")
        elif tag in ("b", "strong"):
            self.result.append("**")
        elif tag in ("i", "em"):
            self.result.append("*")
        elif tag in ("s", "strike", "del"):
            self.result.append("~~")
        elif tag == "u":
            self.result.append("</u>")
        elif tag == "mark":
            self.result.append("==")
        elif tag == "code":
            if not self.in_pre:
                self.in_code = False
                self.result.append("`")
        elif tag == "pre":
            self.in_pre = False
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
            self.result.append("```\n\n")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.result.append("\n\n")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            if self.result and not self.result[-1].endswith("\n"):
                self.result.append("\n")
        elif tag == "a":
            if self.current_href:
                label = "".join(self.link_text).strip() or self.current_href
                self.result.append(f"[{label}]({self.current_href})")
            self.current_href = None
            self.link_text = []

    def handle_data(self, data: str):
        if self.current_href is not None:
            self.link_text.append(data)
            return

        if not self.in_pre:
            # Replace non-breaking spaces
            data = data.replace("\xa0", " ")
        self.result.append(data)


def convert_clozes(text: str, style: str = "highlight") -> str:
    """
    Converts Anki cloze syntax {{c1::answer[::hint]}} to Obsidian markdown.
    style options:
      - 'highlight': ==answer== (or ==answer== (hint))
      - 'bold': **answer** (or **answer** (hint))
      - 'keep': preserve {{c1::answer}}
      - 'spoiler': >!answer!<
    """
    if style == "keep":
        return text

    pattern = re.compile(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", re.DOTALL)

    def repl(match: re.Match) -> str:
        answer = match.group(1).strip()
        hint = match.group(2).strip() if match.group(2) else ""

        if style == "highlight":
            res = f"=={answer}=="
            if hint:
                res += f" *({hint})*"
            return res
        elif style == "bold":
            res = f"**{answer}**"
            if hint:
                res += f" *({hint})*"
            return res
        elif style == "spoiler":
            res = f"%%{answer}%%"
            if hint:
                res += f" *({hint})*"
            return res
        return answer

    return pattern.sub(repl, text)


def convert_latex(text: str) -> str:
    """
    Converts Anki LaTeX tags to standard Obsidian MathJax ($ and $$).
    - [latex]...[/latex] -> $$\n...\n$$
    - [$]...[/$] -> $...$
    - [$$]...[/$$] -> $$\n...\n$$
    - \\( ... \\) -> $...$
    - \\[ ... \\] -> $$\n...\n$$
    """
    # Block latex
    text = re.sub(
        r"\[latex\](.*?)\[/latex\]",
        lambda m: f"$$\n{m.group(1).strip()}\n$$",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r"\[\$\$\](.*?)\[/\$\$\]",
        lambda m: f"$$\n{m.group(1).strip()}\n$$",
        text,
        flags=re.DOTALL,
    )
    # Inline latex
    text = re.sub(
        r"\[\$\](.*?)\[/\$\]",
        lambda m: f"${m.group(1).strip()}$",
        text,
        flags=re.DOTALL,
    )

    # Anki MathJax block \\[ ... \\] -> $$ ... $$
    text = re.sub(
        r"\\\[(.*?)\\\]",
        lambda m: f"$$\n{m.group(1).strip()}\n$$",
        text,
        flags=re.DOTALL,
    )

    # Anki MathJax inline \\( ... \\) -> $ ... $
    text = re.sub(
        r"\\\((.*?)\\\)",
        lambda m: f"${m.group(1).strip()}$",
        text,
        flags=re.DOTALL,
    )

    return text


def convert_sound_tags(text: str, use_wikilinks: bool = True) -> str:
    """
    Converts [sound:filename.mp3] to Obsidian audio embeds.
    """
    def repl(m: re.Match) -> str:
        filename = m.group(1).strip()
        if use_wikilinks:
            return f"![[{filename}]]"
        else:
            return f"[Audio: {filename}]({filename})"

    return re.sub(r"\[sound:([^\]]+)\]", repl, text)


def anki_html_to_markdown(
    raw_html: str,
    cloze_style: str = "highlight",
    use_wikilinks: bool = True,
) -> str:
    """
    Main pipeline to convert Anki field HTML to clean Obsidian Markdown.
    """
    if not raw_html:
        return ""

    # 1. First convert Anki audio tags [sound:...]
    content = convert_sound_tags(raw_html, use_wikilinks=use_wikilinks)

    # 2. Convert LaTeX and MathJax tags
    content = convert_latex(content)

    # 3. Convert Cloze syntax
    content = convert_clozes(content, style=cloze_style)

    # 4. Parse HTML tags and build markdown
    parser = HTMLToMarkdownParser(
        cloze_style=cloze_style, use_wikilinks=use_wikilinks
    )
    parser.feed(content)
    md = parser.get_markdown()

    # 5. Decode any leftover HTML entities (like &lt;, &gt;, &quot;)
    md = html.unescape(md)

    return md.strip()
