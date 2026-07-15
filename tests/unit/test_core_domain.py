"""
Offline unit tests for match-track domain logic (no MongoDB required).

These lock in the stage structures, max scores, subtotals, and multigun
aggregate calculations so later feature work does not silently break scoring.
"""

from datetime import datetime

import pytest

from backend.core import (
    AggregateType,
    BasicMatchType,
    CaliberType,
    Match,
    MatchTypeInstance,
    Score,
    ScoreStage,
    calculate_aggregates,
    calculate_score_subtotals,
    calculate_shooter_averages_by_caliber,
    get_match_type_max_score,
    get_stages_for_match_type,
)


# ---------------------------------------------------------------------------
# Match type stage structures (must match range-officer scorecards)
# ---------------------------------------------------------------------------

EXPECTED_STAGES = {
    BasicMatchType.NMC: {
        "entry_stages": ["SF", "TF", "RF"],
        "max_score": 300,
    },
    BasicMatchType.SIXHUNDRED: {
        "entry_stages": ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"],
        "max_score": 600,
    },
    BasicMatchType.NINEHUNDRED: {
        "entry_stages": [
            "SF1",
            "SF2",
            "SFNMC",
            "TFNMC",
            "RFNMC",
            "TF1",
            "TF2",
            "RF1",
            "RF2",
        ],
        "max_score": 900,
    },
    BasicMatchType.PRESIDENTS: {
        "entry_stages": ["SF1", "SF2", "TF", "RF"],
        "max_score": 400,
    },
}


@pytest.mark.parametrize("match_type", list(BasicMatchType))
def test_stage_structure_matches_spec(match_type):
    cfg = get_stages_for_match_type(match_type)
    expected = EXPECTED_STAGES[match_type]
    assert cfg["entry_stages"] == expected["entry_stages"]
    assert cfg["max_score"] == expected["max_score"]
    assert get_match_type_max_score(match_type) == expected["max_score"]


def test_900_subtotal_blocks_keep_nmc_separate():
    """SF/TF/RF do not include NMC mid-block; NMC is its own 300-pt subtotal."""
    cfg = get_stages_for_match_type(BasicMatchType.NINEHUNDRED)
    assert set(cfg["subtotal_mappings"].keys()) == {"SF", "NMC", "TF", "RF"}
    assert cfg["subtotal_mappings"]["SF"] == ["SF1", "SF2"]
    assert cfg["subtotal_mappings"]["NMC"] == ["SFNMC", "TFNMC", "RFNMC"]
    assert cfg["subtotal_mappings"]["TF"] == ["TF1", "TF2"]
    assert cfg["subtotal_mappings"]["RF"] == ["RF1", "RF2"]


def test_caliber_and_aggregate_enums():
    assert {c.value for c in CaliberType} == {
        ".22",
        "CF",
        ".45",
        "Service Pistol",
        "Service Revolver",
        "DR",
    }
    assert AggregateType.EIGHTEEN_HUNDRED_2X900.value == "1800 (2x900)"
    assert AggregateType.EIGHTEEN_HUNDRED_3X600.value == "1800 (3x600)"
    assert AggregateType.TWENTY_SEVEN_HUNDRED.value == "2700 (3x900)"


# ---------------------------------------------------------------------------
# Score subtotals
# ---------------------------------------------------------------------------

def _score_with_stages(stages, match_type_instance="900_1", caliber=CaliberType.TWENTYTWO):
    total = sum(s for s, _ in stages if s is not None)
    total_x = sum(x for s, x in stages if s is not None and x is not None)
    return Score(
        shooter_id="s1",
        match_id="m1",
        caliber=caliber,
        match_type_instance=match_type_instance,
        stages=[
            ScoreStage(name=name, score=sc, x_count=xc)
            for name, (sc, xc) in zip(
                get_stages_for_match_type(BasicMatchType.NINEHUNDRED)["entry_stages"],
                stages,
            )
        ],
        total_score=total if any(s is not None for s, _ in stages) else None,
        total_x_count=total_x if any(s is not None for s, _ in stages) else None,
    )


def test_900_subtotals_sum_entry_stages():
    # Entry order: SF1,SF2,SFNMC,TFNMC,RFNMC,TF1,TF2,RF1,RF2
    stages = [
        (90, 2),  # SF1
        (91, 1),  # SF2
        (92, 3),  # SFNMC
        (88, 0),  # TFNMC
        (89, 1),  # RFNMC
        (90, 2),  # TF1
        (85, 0),  # TF2
        (86, 1),  # RF1
        (87, 0),  # RF2
    ]
    score = _score_with_stages(stages)
    cfg = get_stages_for_match_type(BasicMatchType.NINEHUNDRED)
    sub = calculate_score_subtotals(score, cfg)

    assert sub["SF"]["score"] == 90 + 91
    assert sub["SF"]["x_count"] == 2 + 1
    assert sub["NMC"]["score"] == 92 + 88 + 89
    assert sub["NMC"]["x_count"] == 3 + 0 + 1
    assert sub["TF"]["score"] == 90 + 85
    assert sub["RF"]["score"] == 86 + 87


def test_subtotals_ignore_null_stage_scores():
    stages = [
        (90, 1),
        (None, None),
        (92, 2),  # SFNMC
        (None, None),
        (None, None),
        (80, 0),
        (None, None),
        (70, 1),
        (None, None),
    ]
    score = _score_with_stages(stages)
    cfg = get_stages_for_match_type(BasicMatchType.NINEHUNDRED)
    sub = calculate_score_subtotals(score, cfg)
    assert sub["SF"]["score"] == 90  # SF1 only (SFNMC is NMC)
    assert sub["NMC"]["score"] == 92
    assert sub["TF"]["score"] == 80  # TF1 only
    assert sub["RF"]["score"] == 70  # RF1 only


# ---------------------------------------------------------------------------
# Multigun aggregates
# ---------------------------------------------------------------------------

def _match(aggregate_type, match_types):
    return Match(
        name="Test",
        date=datetime(2026, 7, 1),
        location="Range",
        match_types=match_types,
        aggregate_type=aggregate_type,
    )


def _score_blob(instance_name, caliber, total, x=0):
    return {
        "score": {
            "match_type_instance": instance_name,
            "caliber": caliber.value if isinstance(caliber, CaliberType) else caliber,
            "total_score": total,
            "total_x_count": x,
        }
    }


def test_1800_from_two_900s_takes_top_two_per_caliber():
    match = _match(
        AggregateType.EIGHTEEN_HUNDRED_2X900,
        [
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name="900_A",
                calibers=[CaliberType.TWENTYTWO, CaliberType.CENTERFIRE],
            ),
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name="900_B",
                calibers=[CaliberType.TWENTYTWO, CaliberType.CENTERFIRE],
            ),
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name="900_C",
                calibers=[CaliberType.TWENTYTWO],
            ),
        ],
    )
    scores = {
        "900_A_.22": _score_blob("900_A", CaliberType.TWENTYTWO, 850, 10),
        "900_B_.22": _score_blob("900_B", CaliberType.TWENTYTWO, 860, 12),
        "900_C_.22": _score_blob("900_C", CaliberType.TWENTYTWO, 840, 8),  # dropped
        "900_A_CF": _score_blob("900_A", CaliberType.CENTERFIRE, 800, 5),
        "900_B_CF": _score_blob("900_B", CaliberType.CENTERFIRE, 810, 6),
    }
    aggs = calculate_aggregates(scores, match)
    assert aggs["1800_.22"]["score"] == 850 + 860
    assert aggs["1800_.22"]["x_count"] == 10 + 12
    assert set(aggs["1800_.22"]["components"]) == {"900_A", "900_B"}
    assert aggs["1800_CF"]["score"] == 800 + 810


def test_1800_from_three_600s():
    match = _match(
        AggregateType.EIGHTEEN_HUNDRED_3X600,
        [
            MatchTypeInstance(
                type=BasicMatchType.SIXHUNDRED,
                instance_name="600_1",
                calibers=[CaliberType.FORTYFIVE],
            ),
            MatchTypeInstance(
                type=BasicMatchType.SIXHUNDRED,
                instance_name="600_2",
                calibers=[CaliberType.FORTYFIVE],
            ),
            MatchTypeInstance(
                type=BasicMatchType.SIXHUNDRED,
                instance_name="600_3",
                calibers=[CaliberType.FORTYFIVE],
            ),
        ],
    )
    scores = {
        "600_1_.45": _score_blob("600_1", CaliberType.FORTYFIVE, 550, 4),
        "600_2_.45": _score_blob("600_2", CaliberType.FORTYFIVE, 560, 5),
        "600_3_.45": _score_blob("600_3", CaliberType.FORTYFIVE, 540, 3),
    }
    aggs = calculate_aggregates(scores, match)
    assert aggs["1800_.45"]["score"] == 550 + 560 + 540
    assert aggs["1800_.45"]["x_count"] == 4 + 5 + 3


def test_2700_from_three_900s():
    match = _match(
        AggregateType.TWENTY_SEVEN_HUNDRED,
        [
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name=f"900_{i}",
                calibers=[CaliberType.SERVICEPISTOL],
            )
            for i in range(1, 4)
        ],
    )
    scores = {
        f"900_{i}_Service Pistol": _score_blob(
            f"900_{i}", CaliberType.SERVICEPISTOL, 800 + i, i
        )
        for i in range(1, 4)
    }
    aggs = calculate_aggregates(scores, match)
    assert aggs["2700_Service Pistol"]["score"] == 801 + 802 + 803


def test_aggregates_skip_null_totals():
    match = _match(
        AggregateType.EIGHTEEN_HUNDRED_2X900,
        [
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name="900_A",
                calibers=[CaliberType.TWENTYTWO],
            ),
            MatchTypeInstance(
                type=BasicMatchType.NINEHUNDRED,
                instance_name="900_B",
                calibers=[CaliberType.TWENTYTWO],
            ),
        ],
    )
    scores = {
        "900_A_.22": _score_blob("900_A", CaliberType.TWENTYTWO, 850, 10),
        "900_B_.22": {
            "score": {
                "match_type_instance": "900_B",
                "caliber": ".22",
                "total_score": None,
                "total_x_count": None,
            }
        },
    }
    aggs = calculate_aggregates(scores, match)
    # Only one valid 900 — should not form an 1800
    assert "1800_.22" not in aggs


def test_named_submatch_instance_survives_on_model():
    """Option to name individual sub matches (e.g. '22 EIC')."""
    mt = MatchTypeInstance(
        type=BasicMatchType.NMC,
        instance_name="22 EIC",
        calibers=[CaliberType.TWENTYTWO],
    )
    m = _match(AggregateType.NONE, [mt])
    assert m.match_types[0].instance_name == "22 EIC"


# ---------------------------------------------------------------------------
# Averages exclude null totals
# ---------------------------------------------------------------------------

def test_shooter_averages_exclude_null_totals():
    scores = [
        Score(
            shooter_id="s1",
            match_id="m1",
            caliber=CaliberType.TWENTYTWO,
            match_type_instance="NMC1",
            stages=[
                ScoreStage(name="SF", score=90, x_count=1),
                ScoreStage(name="TF", score=95, x_count=2),
                ScoreStage(name="RF", score=92, x_count=1),
            ],
            total_score=277,
            total_x_count=4,
        ),
        Score(
            shooter_id="s1",
            match_id="m2",
            caliber=CaliberType.TWENTYTWO,
            match_type_instance="NMC2",
            stages=[
                ScoreStage(name="SF", score=None, x_count=None),
                ScoreStage(name="TF", score=None, x_count=None),
                ScoreStage(name="RF", score=None, x_count=None),
            ],
            total_score=None,
            total_x_count=None,
            not_shot=True,
        ),
        Score(
            shooter_id="s1",
            match_id="m3",
            caliber=CaliberType.TWENTYTWO,
            match_type_instance="NMC3",
            stages=[
                ScoreStage(name="SF", score=0, x_count=0),
                ScoreStage(name="TF", score=0, x_count=0),
                ScoreStage(name="RF", score=0, x_count=0),
            ],
            total_score=0,
            total_x_count=0,
        ),
    ]
    avgs = calculate_shooter_averages_by_caliber(scores)
    assert CaliberType.TWENTYTWO in avgs
    data = avgs[CaliberType.TWENTYTWO]
    # Null total excluded; 0 included → two valid matches
    assert data["valid_matches_count"] == 2
    assert data["total_score_avg"] == 138.5  # (277 + 0) / 2
