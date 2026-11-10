from rapidfuzz.fuzz import token_sort_ratio
from app.schemas.extraction import ExtractedLineItem
from app.schemas.matching import LineItemMatch, MatchSignal, MatchType
from app.services.matching.normalization import normalize_sku, normalize_description, normalize_uom

class IntelligentMatcher:
    def __init__(self, description_threshold: float = 80):
        self.description_threshold = description_threshold

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        return token_sort_ratio(s1, s2) / 100.0

    def match_line_items(
        self, source_items: list[ExtractedLineItem], target_items: list[ExtractedLineItem]
    ) -> dict[int, LineItemMatch]:
        """
        Pairwise matching of source items against target items.
        Returns a map of source_index -> match result.
        """
        results = {}

        # Pre-index target items for efficiency
        target_by_sku = {normalize_sku(item.sku): item for item in target_items if item.sku}

        for idx, source_item in enumerate(source_items):
            match = self._find_best_match(source_item, target_items, target_by_sku)
            results[idx] = match

        return results

    def _find_best_match(
        self, source: ExtractedLineItem, targets: list[ExtractedLineItem], target_by_sku: dict[str, ExtractedLineItem]
    ) -> LineItemMatch:
        source_sku = normalize_sku(source.sku)

        # 1. Exact SKU Match
        if source_sku and source_sku in target_by_sku:
            return LineItemMatch(
                score=1.0,
                match_type=MatchType.EXACT_SKU,
                signals=[MatchSignal(name="sku_match", score=1.0)],
                explanation=f"Exact SKU match: {source.sku}"
            )

        # 2. Fuzzy Description Match
        best_score = 0.0
        best_match = None

        source_desc = normalize_description(source.description)
        if not source_desc:
            return LineItemMatch(score=0.0, match_type=MatchType.UNMATCHED, explanation="No description to match")

        for target in targets:
            target_desc = normalize_description(target.description)
            score = self._calculate_similarity(source_desc, target_desc)

            if score > best_score:
                best_score = score
                best_match = target

        if best_score >= self.description_threshold:
            # Check UOM compatibility if needed (simplified for M3)
            source_uom = normalize_uom(source.unit_of_measure)
            target_uom = normalize_uom(best_match.unit_of_measure)
            uom_match = source_uom == target_uom

            signals = [
                MatchSignal(name="desc_similarity", score=best_score),
                MatchSignal(name="uom_match", score=1.0 if uom_match else 0.0),
            ]

            return LineItemMatch(
                score=best_score * 0.7 + (1.0 if uom_match else 0.0) * 0.3,
                match_type=MatchType.FUZZY_DESCRIPTION,
                signals=signals,
                explanation=f"Fuzzy description match: {best_match.description} (score: {best_score:.2f})"
            )

        return LineItemMatch(
            score=0.0,
            match_type=MatchType.UNMATCHED,
            explanation="No plausible candidate found"
        )
