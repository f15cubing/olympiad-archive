"""Unit tests for the controlled tag vocabulary / normalization layer."""

import pytest

from ai_tagging.tag_vocab import (
    canonical_field,
    normalize_tag,
    normalize_technique,
    normalize_topic,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Algebra", "Algebra"),
        ("algebra", "Algebra"),
        ("  ALGEBRA  ", "Algebra"),
        ("number theory", "Number Theory"),
        ("Number Theory", "Number Theory"),
        ("NT", "Number Theory"),
        ("combo", "Combinatorics"),
        ("geo", "Geometry"),
    ],
)
def test_canonical_field(raw, expected):
    assert canonical_field(raw) == expected


def test_canonical_field_returns_none_for_non_field():
    assert canonical_field("induction") is None
    assert canonical_field("cyclic quadrilaterals") is None


def test_field_aliases_collapse_to_one_tag():
    # Whether a field arrives as a field or a topic, it lands on one canonical row.
    assert normalize_tag("number theory") == "Number Theory"
    assert normalize_tag("Number Theory") == "Number Theory"
    assert normalize_tag("NT") == "Number Theory"


def test_technique_is_namespaced_and_aliased():
    assert normalize_technique("induction") == "technique: induction"
    assert normalize_technique("PHP") == "technique: pigeonhole"
    assert normalize_technique("technique: Pigeonhole Principle") == "technique: pigeonhole"
    # normalize_tag dispatches prefixed strings to the technique path
    assert normalize_tag("technique: vieta") == "technique: vieta's formulas"


def test_topics_lowercased_and_aliased():
    assert normalize_topic("Cyclic Quadrilateral") == "cyclic quadrilaterals"
    assert normalize_topic("functional equation") == "functional equations"
    assert normalize_tag("  Functional   Equation ") == "functional equations"


def test_technique_and_topic_stay_distinct():
    # A technique tag and a same-named topic must not collide.
    assert normalize_tag("technique: induction") != normalize_tag("induction")


def test_idempotent():
    for raw in ["Algebra", "technique: induction", "cyclic quadrilaterals", "NT"]:
        once = normalize_tag(raw)
        assert normalize_tag(once) == once
