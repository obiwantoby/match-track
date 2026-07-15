"""Unit tests for NRA bulletin standings — locked to sample report rules."""

from backend.bulletin import (
    CompetitorResult,
    build_bulletin,
    build_class_section,
    build_open_place_awards,
    build_special_category_awards,
    event_score_from_score_doc,
    format_score_x,
    rank_competitors,
    sum_stages,
)


def _c(
    sid,
    name,
    score,
    x=0,
    *,
    num=None,
    rating="HM",
    division="Civilian",
    cats=None,
):
    return CompetitorResult(
        shooter_id=sid,
        name=name,
        competitor_number=num,
        rating=rating,
        division=division,
        special_categories=cats or [],
        score=score,
        x_count=x,
    )


def test_format_score_x_matches_samples():
    assert format_score_x(194, 8) == "194.8  x"
    assert format_score_x(298, 21) == "298.21  x"
    assert format_score_x(889, 54) == "889.54  x"
    assert format_score_x(2659, 156) == "2659  156  x"


def test_rank_score_then_x_then_competitor_number():
    a = _c("a", "A", 100, 5, num=200)
    b = _c("b", "B", 100, 10, num=100)  # higher X wins
    c = _c("c", "C", 99, 20, num=1)
    ranked = rank_competitors([a, b, c])
    assert [r.shooter_id for r in ranked] == ["b", "a", "c"]


def test_open_place_awards_labels():
    ranked = rank_competitors(
        [
            _c("1", "First", 300, 10, num=1),
            _c("2", "Second", 299, 9, num=2),
            _c("3", "Third", 298, 8, num=3),
            _c("4", "Fourth", 297, 7, num=4),
        ]
    )
    rows = build_open_place_awards(ranked)
    assert len(rows) == 3
    assert rows[0]["award_label"] == "Match Winner"
    assert rows[1]["award_label"] == "Second Place"
    assert rows[2]["award_label"] == "Third Place"
    assert rows[0]["score_display"] == "300.10  x"


def test_special_category_awards_order_and_eligibility():
    ranked = rank_competitors(
        [
            _c("w", "Winner Civ", 300, 10, num=1, division="Civilian", cats=["Veteran"]),
            _c("p", "Cop", 290, 5, num=2, division="Police", rating="MA"),
            _c("s", "Service Guy", 280, 4, num=3, division="Service"),
            _c("sen", "Senior Guy", 270, 3, num=4, cats=["Senior"]),
            _c("gs", "GS Guy", 260, 2, num=5, cats=["Grand Senior"]),
            _c("wm", "Woman", 250, 1, num=6, cats=["Women"], division="Police"),
        ]
    )
    specials = build_special_category_awards(ranked)
    by_label = {r["award_label"]: r for r in specials}
    assert by_label["High Senior"]["name"] == "Senior Guy"
    assert by_label["High Woman"]["name"] == "Woman"
    assert by_label["High Civilian"]["name"] == "Winner Civ"
    assert by_label["High Police"]["name"] == "Cop"
    assert by_label["High Service"]["name"] == "Service Guy"
    assert by_label["High Grand Senior"]["name"] == "GS Guy"
    assert by_label["High Veteran"]["name"] == "Winner Civ"


def test_class_police_service_groups_both():
    ranked = rank_competitors(
        [
            _c("1", "P1", 290, 10, num=1, rating="HM", division="Police"),
            _c("2", "S1", 280, 5, num=2, rating="HM", division="Service"),
            _c("3", "C1", 300, 20, num=3, rating="HM", division="Civilian"),
        ]
    )
    sec = build_class_section(
        ranked,
        ratings=["HM"],
        division_mode="police_service",
        class_key="HM",
        division_label="Police/Service",
        section_title="HIGH MASTER -- POLICE/SERVICE",
    )
    assert sec["competitor_count"] == 2
    assert sec["rows"][0]["name"] == "P1"
    assert sec["rows"][0]["award_label"] == "First High Master - Police/Service"
    assert sec["rows"][1]["name"] == "S1"


def test_ss_mk_combined_all_categories():
    ranked = rank_competitors(
        [
            _c("1", "SS Civ", 200, 5, num=1, rating="SS", division="Civilian"),
            _c("2", "MK Pol", 210, 3, num=2, rating="MK", division="Police"),
            _c("3", "EX", 250, 1, num=3, rating="EX", division="Civilian"),
        ]
    )
    sec = build_class_section(
        ranked,
        ratings=["SS", "MK"],
        division_mode="all",
        class_key="SSMK",
        division_label="All Categories",
        section_title="SHARPSHOOTER/MARKSMAN -- ALL CATEGORIES",
    )
    assert sec["competitor_count"] == 2
    assert sec["rows"][0]["name"] == "MK Pol"  # higher score
    assert "Sharpshooter/Marksman" in (sec["rows"][0]["award_label"] or "")


def test_name_suffixes_gs_vet():
    c = _c("1", "Bennett, Dennis", 100, 1, cats=["Grand Senior", "Veteran"])
    assert c.name_with_suffixes() == "Bennett, Dennis GS VET"


def test_sum_stages_slow_fire_excludes_sfnmc():
    from backend.bulletin import SLOW_STAGES, NMC_BLOCK_STAGES, event_score_from_score_doc

    stages = [
        {"name": "SF1", "score": 90, "x_count": 2},
        {"name": "SF2", "score": 91, "x_count": 1},
        {"name": "SFNMC", "score": 95, "x_count": 4},
        {"name": "TF1", "score": 88, "x_count": 0},
    ]
    s, x = sum_stages(stages, SLOW_STAGES)
    assert s == 181
    assert x == 3
    nmc_s, nmc_x = sum_stages(stages, NMC_BLOCK_STAGES)
    assert nmc_s == 95
    assert nmc_x == 4
    doc = {"stages": stages, "total_score": 900, "total_x_count": 20}
    assert event_score_from_score_doc(doc, "slow") == (181, 3)
    assert event_score_from_score_doc(doc, "nmc") == (95, 4)


def test_event_score_not_shot():
    assert event_score_from_score_doc({"not_shot": True, "total_score": 0}, "total") == (
        None,
        None,
    )


def test_full_bulletin_structure():
    results = [
        _c("1", "Alpha", 300, 15, num=101, rating="HM", division="Civilian", cats=["Veteran"]),
        _c("2", "Bravo", 295, 10, num=202, rating="MA", division="Police"),
        _c("3", "Charlie", 290, 8, num=303, rating="SS", division="Civilian"),
    ]
    b = build_bulletin(
        tournament_title="NRA REGISTERED MATCH -- TEST",
        date_line="July 4, 2026",
        location="Test Range",
        match_no=1,
        event_title=".22 NMC MATCH",
        results=results,
    )
    assert b["header"]["bulletin_title"] == "TOURNAMENT RESULTS BULLETIN"
    assert b["competitor_count"] == 3
    assert b["open_place_awards"][0]["award_label"] == "Match Winner"
    assert len(b["special_category_awards"]) >= 2
    assert any(s["title"].startswith("HIGH MASTER") for s in b["class_sections"])
    assert any("SHARPSHOOTER" in s["title"] for s in b["class_sections"])
