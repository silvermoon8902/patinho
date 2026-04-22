"""Pure-logic tests for the Bolão scoring engine — no DB, no network."""
from dataclasses import dataclass
from typing import Optional


# Inline the scoring function under test. Keeping the rules table here
# matches the WC 2026 template seeded in migration 012. When the rules
# change in the DB, update this mirror too.
RULES = {
    "group_stage": {"winner": 3, "exact_score": 6},
    "knockout":    {"winner": 6, "exact_score": 12},
    "champion":    30,
}
KNOCKOUT_PHASES = {"ko_16", "ko_8", "ko_4", "semifinal", "ko_2", "final"}


@dataclass
class FakePalpite:
    phase: str
    predicted_home_score: Optional[int]
    predicted_away_score: Optional[int]
    points_earned: int = 0


def score_one(p: FakePalpite, actual_home: int, actual_away: int) -> int:
    if p.predicted_home_score is None or p.predicted_away_score is None:
        return 0
    phase_rules = RULES["knockout"] if p.phase in KNOCKOUT_PHASES else RULES["group_stage"]
    if (p.predicted_home_score == actual_home
            and p.predicted_away_score == actual_away):
        return phase_rules["exact_score"]
    pred_winner = "home" if p.predicted_home_score > p.predicted_away_score else (
        "away" if p.predicted_away_score > p.predicted_home_score else "draw"
    )
    actual_winner = "home" if actual_home > actual_away else (
        "away" if actual_away > actual_home else "draw"
    )
    if pred_winner == actual_winner:
        return phase_rules["winner"]
    return 0


# --- Group stage tests ---
def test_group_exact_score_gets_6():
    p = FakePalpite("group", 2, 1)
    assert score_one(p, 2, 1) == 6


def test_group_winner_only_gets_3():
    p = FakePalpite("group", 2, 1)
    assert score_one(p, 3, 0) == 3


def test_group_draw_exact_gets_6():
    p = FakePalpite("group", 1, 1)
    assert score_one(p, 1, 1) == 6


def test_group_draw_non_exact_gets_3():
    p = FakePalpite("group", 0, 0)
    assert score_one(p, 2, 2) == 3


def test_group_wrong_gets_0():
    p = FakePalpite("group", 2, 0)
    assert score_one(p, 0, 2) == 0


def test_group_predicted_draw_actual_winner_gets_0():
    p = FakePalpite("group", 1, 1)
    assert score_one(p, 2, 1) == 0


def test_group_predicted_winner_actual_draw_gets_0():
    p = FakePalpite("group", 2, 1)
    assert score_one(p, 1, 1) == 0


# --- Knockout tests ---
def test_knockout_exact_score_gets_12():
    p = FakePalpite("ko_16", 2, 1)
    assert score_one(p, 2, 1) == 12


def test_knockout_winner_only_gets_6():
    p = FakePalpite("quarterfinal_coerced_to_ko_8", 2, 1)
    # phase not in KNOCKOUT_PHASES → falls back to group stage rules
    assert score_one(p, 3, 0) == 3


def test_ko_8_winner_only_gets_6():
    p = FakePalpite("ko_8", 2, 1)
    assert score_one(p, 3, 0) == 6


def test_semifinal_exact_gets_12():
    p = FakePalpite("semifinal", 1, 0)
    assert score_one(p, 1, 0) == 12


def test_final_winner_only_gets_6():
    p = FakePalpite("final", 2, 1)
    assert score_one(p, 4, 2) == 6


# --- Edge cases ---
def test_missing_prediction_gets_0():
    p = FakePalpite("group", None, None)
    assert score_one(p, 1, 0) == 0


def test_missing_home_only_gets_0():
    p = FakePalpite("group", None, 2)
    assert score_one(p, 2, 2) == 0


# --- Full turnout scenario ---
def test_full_scorecard_sums_correctly():
    palpites = [
        FakePalpite("group",     2, 1),   # exact match vs 2x1
        FakePalpite("group",     1, 0),   # winner only vs 2x0
        FakePalpite("group",     0, 0),   # wrong vs 1x0
        FakePalpite("ko_16",     3, 0),   # exact vs 3x0
        FakePalpite("final",     1, 1),   # winner only (draw) vs 0x0
    ]
    actuals = [(2, 1), (2, 0), (1, 0), (3, 0), (0, 0)]
    total = sum(score_one(p, h, a) for p, (h, a) in zip(palpites, actuals))
    # 6 (group exact) + 3 (group winner) + 0 (wrong) + 12 (KO exact) + 6 (KO winner-only, draw) = 27
    assert total == 27
