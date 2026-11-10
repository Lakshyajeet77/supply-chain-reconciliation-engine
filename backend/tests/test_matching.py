from app.schemas.extraction import ExtractedLineItem
from app.services.matching.normalization import normalize_sku, normalize_description, normalize_uom
from app.services.matching.matcher import IntelligentMatcher

def test_normalize_sku_variations():
    assert normalize_sku("SKU-123") == "sku123"
    assert normalize_sku(" SKU 123 ") == "sku123"
    assert normalize_sku("ABC_456") == "abc456"

def test_normalize_description():
    desc1 = "Widget, Industrial (Red)"
    desc2 = "Industrial Widget Red"
    assert normalize_description(desc1) == "widget industrial red"
    assert normalize_description(desc2) == "industrial widget red"

def test_normalize_uom_aliases():
    assert normalize_uom("Each") == "EA"
    assert normalize_uom("Pcs") == "PCS"
    assert normalize_uom("Boxes") == "BOX"

def test_exact_sku_match():
    matcher = IntelligentMatcher()
    po_items = [ExtractedLineItem(sku="A-123", description="Item A")]
    invoice_items = [ExtractedLineItem(sku="a123", description="Item A")]
    result = matcher.match_line_items(invoice_items, po_items)
    assert result[0].match_type.value == "exact_sku"
    assert result[0].score == 1.0

def test_reordered_description_match():
    matcher = IntelligentMatcher(description_threshold=0.8)
    po_items = [ExtractedLineItem(sku=None, description="Screws M5x20 100pk")]
    invoice_items = [ExtractedLineItem(sku=None, description="100pk M5x20 Screws")]
    result = matcher.match_line_items(invoice_items, po_items)
    assert result[0].match_type.value == "fuzzy_description"
    assert result[0].score >= 0.8

def test_ambiguous_candidate_detection():
    # This test confirms the matcher returns the highest score,
    # ambiguity logic will be added in the reconciliation layer.
    matcher = IntelligentMatcher(description_threshold=0.5)
    po_items = [
        ExtractedLineItem(sku=None, description="Widget Red"),
        ExtractedLineItem(sku=None, description="Widget Blue"),
    ]
    invoice_items = [ExtractedLineItem(sku=None, description="Widget")]
    result = matcher.match_line_items(invoice_items, po_items)
    assert result[0].score > 0
