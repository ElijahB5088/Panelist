import pytest

from app.metadata import MetadataResult
from app.metadata_mapping import compare_metadata, map_metadata, normalize_media_type


def test_mapping_normalizes_identity_fields_and_reports_match_quality():
    match = map_metadata(
        MetadataResult(
            source="comicvine",
            source_id="1",
            title="Saga!",
            creator="Brian K. Vaughan",
            release_date="2012-03-14",
            media_type="comics",
        )
    )

    assert match.identity.key == "saga|brian k vaughan|2012|comic"
    assert match.confidence == 1.0
    assert match.reason == "title_creator_year"


def test_mapping_does_not_invent_missing_identity_fields():
    match = map_metadata(MetadataResult("openlibrary", "1", "Saga"))

    assert match.identity.creator == ""
    assert match.identity.release_year == ""
    assert match.confidence == 0.5
    assert match.reason == "title_only"


def test_mapping_normalizes_media_type_aliases():
    assert normalize_media_type("manhwa") == "manga"
    assert normalize_media_type("comics") == "comic"
    assert normalize_media_type(None, source="comicvine", title="Hunter x Hunter") == "comic"


@pytest.mark.parametrize(
    ("source", "tracker_source"),
    [("anilist", None), ("kitsu", None), ("mal", None), (None, "kitsu"), (None, "mal")],
)
def test_mapping_prefers_authoritative_manga_sources(source, tracker_source):
    assert normalize_media_type("comic", source=source, tracker_source=tracker_source) == "manga"


def test_mapping_preserves_non_latin_identity_text():
    match = map_metadata(MetadataResult("anilist", "1", "進撃の巨人"))

    assert match.identity.title == "進撃の巨人"
    assert match.reason == "title_only"


def test_comparison_accepts_normalized_title_and_creator():
    comparison = compare_metadata(
        MetadataResult("comicvine", "1", "Saga!", "Brian K. Vaughan"),
        title=" saga ",
        creator="Brian K Vaughan",
        media_type="comic",
    )

    assert comparison.accepted is True


def test_comparison_rejects_title_creator_and_type_mismatches():
    result = MetadataResult("comicvine", "1", "Saga", "Other Creator", media_type="comic")

    assert not compare_metadata(result, "Different Saga", "Other Creator", "comic").accepted
    assert not compare_metadata(result, "Saga", "Brian K. Vaughan", "comic").accepted
    assert not compare_metadata(result, "Saga", "Other Creator", "manga").accepted


def test_comparison_uses_provider_type_fallback_when_explicit_type_is_missing():
    comparison = compare_metadata(
        MetadataResult("comicvine", "1", "Saga", "Creator"),
        title="Saga",
        creator="Creator",
        media_type="comic",
    )

    assert comparison.accepted is True


def test_comparison_accepts_a_title_alias():
    comparison = compare_metadata(
        MetadataResult(
            "anilist",
            "1",
            "Attack on Titan",
            "Hajime Isayama",
            aliases=["Shingeki no Kyojin"],
        ),
        title="Shingeki no Kyojin",
        creator="Hajime Isayama",
        media_type="manga",
    )

    assert comparison.accepted is True