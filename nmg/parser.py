"""
Parses dconf-dump / dconf-ini text (the format produced by `dconf dump /`)
into an ordered mapping of {section_path: [(key, nix_expression), ...]}.

The value grammar handled here is GVariant's text format as emitted by
dconf: quoted strings, booleans, bare numbers, typed scalars
(uint32/uint64/int32/int64/int16/uint16/byte/handle/double), arrays `[...]`,
tuples `(...)`, dicts `{...}`, variants `<...>`, and `@type` annotations
(most commonly `@as []` for an empty typed array).

Each value is converted directly into a Nix expression string suitable for
home-manager's `dconf.settings`, using `lib.hm.gvariant.mk*` helpers where
GVariant type information would otherwise be lost (e.g. distinguishing a
uint32 from a plain int, or a tuple from an array).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TYPE_KEYWORD_RE = re.compile(
    r"(uint64|uint32|uint16|int64|int32|int16|byte|handle|double)\s+"
)

_TYPE_FN_MAP = {
    "uint64": "mkUint64",
    "uint32": "mkUint32",
    "uint16": "mkUint16",
    "int64": "mkInt64",
    "int32": "mkInt32",
    "int16": "mkInt16",
    "byte": "mkUint8",
    "handle": "mkHandle",
    "double": "mkDouble",
}


class GVariantParseError(ValueError):
    pass


class _ValueParser:
    """Recursive-descent parser over a single GVariant text-format value."""

    def __init__(self, s: str):
        self.s = s
        self.i = 0
        self.n = len(s)

    def _ws(self) -> None:
        while self.i < self.n and self.s[self.i] in " \t":
            self.i += 1

    def _peek(self) -> str:
        return self.s[self.i] if self.i < self.n else ""

    def parse_value(self) -> str:
        self._ws()
        c = self._peek()
        if c in ("'", '"'):
            return self._parse_string()
        if c == "[":
            return self._parse_array()
        if c == "(":
            return self._parse_tuple()
        if c == "{":
            return self._parse_dict()
        if c == "<":
            return self._parse_variant()
        if c == "@":
            return self._parse_type_annotation()

        m = _TYPE_KEYWORD_RE.match(self.s[self.i :])
        if m:
            kw = m.group(1)
            self.i += m.end()
            val = self.parse_value()
            return f"(lib.hm.gvariant.{_TYPE_FN_MAP[kw]} {val})"

        if self.s[self.i : self.i + 4] == "true":
            self.i += 4
            return "true"
        if self.s[self.i : self.i + 5] == "false":
            self.i += 5
            return "false"

        return self._parse_bare_token()

    def _parse_type_annotation(self) -> str:
        # e.g. "@as []" or "@a{sv} {}" -- skip the type token, parse the value.
        self.i += 1
        depth = 0
        while self.i < self.n:
            ch = self.s[self.i]
            if ch in "{(":
                depth += 1
            elif ch in "})":
                depth -= 1
            elif ch == " " and depth == 0:
                break
            self.i += 1
        self._ws()
        return self.parse_value()

    def _parse_bare_token(self) -> str:
        start = self.i
        while self.i < self.n and self.s[self.i] not in ",)]}>":
            self.i += 1
        tok = self.s[start : self.i].strip()
        if tok == "":
            raise GVariantParseError(
                f"unexpected character {self._peek()!r} at position {self.i} in {self.s!r}"
            )
        if tok.startswith("-"):
            # Nix's list/tuple-argument grammar parses elements at
            # expr_select precedence, which does not include unary minus.
            # A bare "-0.399" as a list element is a syntax error; always
            # parenthesize negative numeric literals so they stand alone
            # as a self-contained expression in any context.
            return f"({tok})"
        return tok

    def _parse_string(self) -> str:
        quote = self.s[self.i]
        self.i += 1
        out = []
        while self.i < self.n and self.s[self.i] != quote:
            ch = self.s[self.i]
            if ch == "\\" and self.i + 1 < self.n:
                out.append(ch)
                out.append(self.s[self.i + 1])
                self.i += 2
                continue
            out.append(ch)
            self.i += 1
        self.i += 1  # closing quote
        content = "".join(out)
        content = content.replace("\\", "\\\\").replace('"', '\\"')
        content = content.replace("${", "\\${")
        return f'"{content}"'

    def _parse_list_items(self, close: str) -> list[str]:
        items = []
        self._ws()
        if self._peek() == close:
            self.i += 1
            return items
        while True:
            self._ws()
            items.append(self.parse_value())
            self._ws()
            if self._peek() == ",":
                self.i += 1
                continue
            if self._peek() == close:
                self.i += 1
                break
            raise GVariantParseError(
                f"expected ',' or {close!r} at position {self.i} in {self.s!r}"
            )
        return items

    @staticmethod
    def _wrap(items: list[str]) -> str:
        wrapped = []
        for it in items:
            if " " in it and not (it.startswith('"') and it.endswith('"')):
                wrapped.append(f"({it})")
            else:
                wrapped.append(it)
        return " ".join(wrapped)

    def _parse_array(self) -> str:
        self.i += 1  # consume '['
        items = self._parse_list_items("]")
        return "[ " + self._wrap(items) + " ]" if items else "[ ]"

    def _parse_tuple(self) -> str:
        self.i += 1  # consume '('
        items = self._parse_list_items(")")
        return "(lib.hm.gvariant.mkTuple [ " + self._wrap(items) + " ])"

    def _parse_variant(self) -> str:
        self.i += 1  # consume '<'
        self._ws()
        v = self.parse_value()
        self._ws()
        if self._peek() == ">":
            self.i += 1
        return f"(lib.hm.gvariant.mkVariant {v})"

    def _parse_dict(self) -> str:
        self.i += 1  # consume '{'
        self._ws()
        if self._peek() == "}":
            self.i += 1
            return "[ ]"
        entries = []
        while True:
            self._ws()
            key = self.parse_value()
            self._ws()
            if self._peek() == ":":
                self.i += 1
            self._ws()
            val = self.parse_value()
            keyname = key if (key.startswith('"') and key.endswith('"')) else f'"{key}"'
            entries.append(f"(lib.hm.gvariant.mkDictionaryEntry [ {keyname} {val} ])")
            self._ws()
            if self._peek() == ",":
                self.i += 1
                continue
            if self._peek() == "}":
                self.i += 1
                break
            raise GVariantParseError(
                f"expected ',' or '}}' at position {self.i} in {self.s!r}"
            )
        return "[ " + " ".join(entries) + " ]"


def parse_value(text: str) -> str:
    """Parse a single GVariant text-format value into a Nix expression."""
    p = _ValueParser(text)
    return p.parse_value()


@dataclass
class DconfDoc:
    """An ordered, parsed representation of a dconf dump."""

    order: list[str] = field(default_factory=list)
    sections: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


_SECTION_RE = re.compile(r"^\[(.+)\]$")
_KV_RE = re.compile(r"^([^=]+)=(.*)$")


def parse_dconf_ini(text: str) -> DconfDoc:
    """Parse the full text of a `dconf dump /`-style ini into a DconfDoc."""
    doc = DconfDoc()
    cur: str | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        m = _SECTION_RE.match(line)
        if m:
            cur = m.group(1)
            if cur not in doc.sections:
                doc.sections[cur] = []
                doc.order.append(cur)
            continue
        if cur is None:
            continue
        m = _KV_RE.match(line)
        if not m:
            continue
        key, valtext = m.group(1), m.group(2)
        try:
            nixval = parse_value(valtext)
        except GVariantParseError as e:
            doc.errors.append(f"line {lineno} ({cur}/{key}): {e}")
            nixval = f'"__PARSE_ERROR__: {valtext}"'
        doc.sections[cur].append((key, nixval))
    return doc
