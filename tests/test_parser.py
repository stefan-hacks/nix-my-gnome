from nmg.parser import parse_dconf_ini, parse_value


def test_scalar_types():
    assert parse_value("'hello'") == '"hello"'
    assert parse_value("true") == "true"
    assert parse_value("false") == "false"
    assert parse_value("42") == "42"
    assert parse_value("1.0") == "1.0"
    assert parse_value("uint32 1") == "(lib.hm.gvariant.mkUint32 1)"
    assert parse_value("uint64 10") == "(lib.hm.gvariant.mkUint64 10)"
    assert parse_value("int64 1785169314187520") == (
        "(lib.hm.gvariant.mkInt64 1785169314187520)"
    )


def test_array():
    assert parse_value("['a', 'b']") == '[ "a" "b" ]'
    assert parse_value("@as []") == "[ ]"


def test_tuple():
    assert parse_value("(812, 504)") == "(lib.hm.gvariant.mkTuple [ 812 504 ])"
    assert parse_value("(true, 1.0, 1.0)") == (
        "(lib.hm.gvariant.mkTuple [ true 1.0 1.0 ])"
    )


def test_array_of_tuples():
    assert parse_value("[('xkb', 'us'), ('xkb', 'gb')]") == (
        '[ ((lib.hm.gvariant.mkTuple [ "xkb" "us" ])) '
        '((lib.hm.gvariant.mkTuple [ "xkb" "gb" ])) ]'
    )


def test_negative_numbers_are_parenthesized():
    # Nix's list-element grammar (expr_select) doesn't include unary minus,
    # so a bare "-0.399" inside `[ ... ]` is a syntax error in real Nix/
    # nixfmt. Negative literals must always be self-contained.
    assert parse_value("-0.399") == "(-0.399)"
    assert parse_value("[-1, -2]") == "[ (-1) (-2) ]"
    assert parse_value("(-0.1, -0.2)") == (
        "(lib.hm.gvariant.mkTuple [ (-0.1) (-0.2) ])"
    )


def test_dict():
    result = parse_value("{'position': <0>}")
    assert result == '{ "position" = (lib.hm.gvariant.mkVariant 0); }'


def test_variant_wrapping_tuple():
    result = parse_value("<(uint32 2, <('a', true)>)>")
    assert result == (
        "(lib.hm.gvariant.mkVariant (lib.hm.gvariant.mkTuple "
        "[ ((lib.hm.gvariant.mkUint32 2)) "
        '((lib.hm.gvariant.mkVariant (lib.hm.gvariant.mkTuple [ "a" true ]))) ]))'
    )


def test_string_escaping():
    assert parse_value("'a \"quoted\" word'") == '"a \\"quoted\\" word"'
    # a single literal backslash in the source value becomes an escaped
    # backslash in the Nix double-quoted string
    assert parse_value("'path\\with\\backslash'") == '"path\\\\with\\\\backslash"'


def test_full_document():
    text = """
[org/gnome/desktop/interface]
clock-format='12h'
enable-animations=true
cursor-size=24

[org/gnome/shell]
enabled-extensions=['foo@bar.com', 'baz@qux.com']
"""
    doc = parse_dconf_ini(text)
    assert doc.order == ["org/gnome/desktop/interface", "org/gnome/shell"]
    assert doc.errors == []
    kvs = dict(doc.sections["org/gnome/desktop/interface"])
    assert kvs["clock-format"] == '"12h"'
    assert kvs["enable-animations"] == "true"
    assert kvs["cursor-size"] == "24"


def test_empty_section_is_skipped_by_emit():
    text = "[org/gnome/evolution-data-server/calendar]\n\n[org/gnome/foo]\nbar=1\n"
    doc = parse_dconf_ini(text)
    assert doc.sections["org/gnome/evolution-data-server/calendar"] == []
    assert doc.sections["org/gnome/foo"] == [("bar", "1")]
