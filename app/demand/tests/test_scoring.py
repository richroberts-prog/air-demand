"""Unit tests for scoring engine.

Tests investor tier detection, funding parsing, score calculations,
and edge cases with missing data.
"""

from app.demand.scoring import (
    calculate_engineer_score,
    calculate_headhunter_score,
    calculate_scores,
    score_excitement_deterministic,
)
from app.demand.scoring.engineer import normalize, score_compensation, score_process_quality
from app.demand.scoring.excitement import score_funding, score_investors
from app.demand.scoring.headhunter import score_competition
from app.shared.constants import (
    HOT_COMPANIES,
    NOTABLE_ANGELS,
    TIER_1_INVESTORS,
    TIER_2_INVESTORS,
)
from app.shared.formatting import parse_funding_amount

# Aliases for backward compatibility with tests
TIER_1_VCS = TIER_1_INVESTORS
TIER_2_VCS = TIER_2_INVESTORS
parse_funding = parse_funding_amount


class TestNormalize:
    """Tests for normalize helper function."""

    def test_normalize_middle_value(self) -> None:
        """Middle value should normalize to 0.5."""
        result = normalize(5, 0, 10)
        assert result == 0.5

    def test_normalize_min_value(self) -> None:
        """Min value should normalize to 0.0."""
        result = normalize(0, 0, 10)
        assert result == 0.0

    def test_normalize_max_value(self) -> None:
        """Max value should normalize to 1.0."""
        result = normalize(10, 0, 10)
        assert result == 1.0

    def test_normalize_clamps_above_max(self) -> None:
        """Values above max should clamp to 1.0."""
        result = normalize(15, 0, 10)
        assert result == 1.0

    def test_normalize_clamps_below_min(self) -> None:
        """Values below min should clamp to 0.0."""
        result = normalize(-5, 0, 10)
        assert result == 0.0

    def test_normalize_none_returns_default(self) -> None:
        """None should return 0.5 (default)."""
        result = normalize(None, 0, 10)
        assert result == 0.5

    def test_normalize_inverse(self) -> None:
        """Inverse flag should flip the scale."""
        result = normalize(10, 0, 10, inverse=True)
        assert result == 0.0

        result = normalize(0, 0, 10, inverse=True)
        assert result == 1.0

    def test_normalize_equal_min_max(self) -> None:
        """Equal min/max should return 0.5."""
        result = normalize(5, 5, 5)
        assert result == 0.5


class TestParseFunding:
    """Tests for funding amount parsing."""

    def test_parse_millions(self) -> None:
        """Parse $XXM format."""
        assert parse_funding("$16.25M") == 16_250_000
        assert parse_funding("100M") == 100_000_000
        assert parse_funding("$5M") == 5_000_000

    def test_parse_billions(self) -> None:
        """Parse $XXB format."""
        assert parse_funding("$1.5B") == 1_500_000_000
        assert parse_funding("2B") == 2_000_000_000

    def test_parse_thousands(self) -> None:
        """Parse $XXK format."""
        assert parse_funding("$500K") == 500_000
        assert parse_funding("750k") == 750_000

    def test_parse_raw_number(self) -> None:
        """Parse raw number."""
        assert parse_funding("1000000") == 1_000_000

    def test_parse_with_commas(self) -> None:
        """Parse numbers with commas."""
        assert parse_funding("$1,000,000") == 1_000_000

    def test_parse_empty_or_none(self) -> None:
        """Empty or None should return 0."""
        assert parse_funding(None) == 0.0
        assert parse_funding("") == 0.0

    def test_parse_invalid(self) -> None:
        """Invalid strings should return 0."""
        assert parse_funding("unknown") == 0.0
        assert parse_funding("N/A") == 0.0


class TestScoreInvestors:
    """Tests for investor tier scoring."""

    def test_tier1_vc_detection(self) -> None:
        """Tier-1 VCs should be detected and scored highly."""
        investors = ["Sequoia Capital", "Andreessen Horowitz"]
        score, tier1_count, signals = score_investors(investors)

        assert tier1_count == 2
        assert score >= 0.6
        assert any("Tier-1" in s for s in signals)

    def test_tier2_vc_detection(self) -> None:
        """Tier-2 VCs should be detected."""
        investors = ["Spark Capital", "Felicis Ventures"]
        score, tier1_count, signals = score_investors(investors)

        assert tier1_count == 0
        assert score >= 0.3
        assert any("Tier-2" in s for s in signals)

    def test_notable_angels_detection(self) -> None:
        """Notable angels should be detected."""
        investors = ["Elad Gil", "Nat Friedman"]
        score, tier1_count, signals = score_investors(investors)

        assert tier1_count == 0
        assert score >= 0.3
        assert any("angel" in s.lower() for s in signals)

    def test_yc_detection(self) -> None:
        """Y Combinator variants should be detected."""
        investors = ["Y Combinator"]
        _, tier1_count, _ = score_investors(investors)
        assert tier1_count == 1

        investors = ["YC W24"]
        _, tier1_count, _ = score_investors(investors)
        assert tier1_count == 1

    def test_empty_investors(self) -> None:
        """Empty investor list should return below-average score."""
        score, tier1_count, signals = score_investors([])
        assert score == 0.3
        assert tier1_count == 0
        assert signals == []

    def test_mixed_investors(self) -> None:
        """Mixed tiers should be scored appropriately."""
        investors = ["Sequoia", "Spark Capital", "Random Angel"]
        score, tier1_count, _ = score_investors(investors)

        assert tier1_count == 1
        assert score >= 0.44  # tier1 (0.30) + tier2 (0.15), allow float tolerance


class TestScoreFunding:
    """Tests for funding score calculation."""

    def test_high_funding_high_score(self) -> None:
        """$100M+ funding should score 1.0."""
        score, signals = score_funding("$100M", "SERIES_C")
        assert score >= 0.9
        assert any("well-funded" in s.lower() for s in signals)

    def test_series_a_sweet_spot(self) -> None:
        """Series A is the sweet spot for engineers."""
        score, _ = score_funding("$20M", "SERIES_A")
        assert score >= 0.7

    def test_seed_stage(self) -> None:
        """Seed stage should score lower."""
        score, _ = score_funding("$5M", "SEED")
        assert score < 0.8

    def test_unknown_funding(self) -> None:
        """Unknown funding should score average."""
        score, _ = score_funding(None, None)
        assert 0.3 <= score <= 0.5


class TestScoreCompensation:
    """Tests for compensation scoring."""

    def test_high_salary_high_score(self) -> None:
        """$300k+ salary should score excellently for engineers."""
        eng_score, hh_score, signals = score_compensation(300000, 18.0)
        assert eng_score == 1.0
        assert hh_score == 1.0
        assert any("excellent" in s.lower() for s in signals)

    def test_average_salary(self) -> None:
        """$200k salary should score moderately."""
        eng_score, _, _ = score_compensation(200000, 15.0)
        assert 0.5 <= eng_score <= 0.7

    def test_high_fee_bonus(self) -> None:
        """High fee (18%+) should score well for headhunters."""
        _, hh_score, signals = score_compensation(250000, 20.0)
        assert hh_score >= 0.8
        assert any("20.0%" in s for s in signals)

    def test_none_values(self) -> None:
        """None values should return default scores."""
        eng_score, hh_score, _ = score_compensation(None, None)
        assert eng_score == 0.3  # Low for missing salary
        assert 0.3 <= hh_score <= 0.5  # Default fee of 15%


class TestScoreProcessQuality:
    """Tests for process quality scoring."""

    def test_fast_process_high_score(self) -> None:
        """Fast, efficient process should score high."""
        eng_score, hh_score, signals = score_process_quality(
            manager_rating=4.8,
            responsiveness_days=0.5,
            interview_stages=3,
            highlights=["NO_FINAL_ROUNDS", "TRUSTED_CLIENT"],
        )
        assert eng_score >= 0.8
        assert hh_score >= 0.79  # Allow slight tolerance for float math
        assert any("no final" in s.lower() for s in signals)

    def test_slow_process_low_score(self) -> None:
        """Long process should score lower for engineers."""
        eng_score, _, _ = score_process_quality(
            manager_rating=3.5,
            responsiveness_days=5,
            interview_stages=8,
            highlights=[],
        )
        assert eng_score <= 0.6

    def test_badges_boost_score(self) -> None:
        """Good badges should boost score."""
        eng1, hh1, _ = score_process_quality(4.0, 2.0, 5, [])
        eng2, hh2, _ = score_process_quality(
            4.0, 2.0, 5, ["NO_FINAL_ROUNDS", "TRUSTED_CLIENT", "RESPONSIVE"]
        )

        assert eng2 > eng1
        assert hh2 > hh1


class TestScoreCompetition:
    """Tests for competition scoring (headhunter perspective)."""

    def test_blue_ocean_high_score(self) -> None:
        """Zero recruiters should score excellently."""
        score, signals = score_competition(
            approved_recruiters=0,
            total_interviewing=2,
            total_hired=1,
        )
        assert score >= 0.8
        assert any("blue ocean" in s.lower() for s in signals)

    def test_crowded_market_low_score(self) -> None:
        """Many recruiters should score poorly."""
        score, signals = score_competition(
            approved_recruiters=15,
            total_interviewing=20,
            total_hired=0,
        )
        assert score <= 0.5
        assert any("crowded" in s.lower() for s in signals)

    def test_proven_buyer(self) -> None:
        """Companies that hire should score well."""
        _, signals = score_competition(
            approved_recruiters=5,
            total_interviewing=3,
            total_hired=3,
        )
        assert any("proven buyer" in s.lower() for s in signals)


class TestScoreExcitementDeterministic:
    """Tests for deterministic excitement scoring."""

    def test_hot_company_instant_high(self) -> None:
        """Known hot companies should get instant 0.95."""
        for company in ["Anthropic", "OpenAI", "Stripe"]:
            score, signals = score_excitement_deterministic(
                company_name=company,
                investors=[],
                funding_amount=None,
                funding_stage=None,
                industries=[],
                founding_year=None,
                company_size=None,
                title="Engineer",
            )
            assert score == 0.95
            assert any("hot company" in s.lower() for s in signals)

    def test_multiple_tier1_investors(self) -> None:
        """Multiple tier-1 investors should boost excitement."""
        score, signals = score_excitement_deterministic(
            company_name="CoolStartup",
            investors=["Sequoia", "a16z", "Benchmark"],
            funding_amount="$50M",
            funding_stage="SERIES_B",
            industries=["ai"],
            founding_year=2023,
            company_size=50,
            title="Senior Engineer",
        )
        assert score >= 0.7
        assert any("tier-1" in s.lower() for s in signals)

    def test_ai_industry_boost(self) -> None:
        """AI industry should boost excitement."""
        score_ai, signals_ai = score_excitement_deterministic(
            company_name="AIStartup",
            investors=["Some VC"],
            funding_amount="$10M",
            funding_stage="SERIES_A",
            industries=["ai", "machine_learning"],
            founding_year=2022,
            company_size=30,
            title="Engineer",
        )

        score_other, _ = score_excitement_deterministic(
            company_name="OtherStartup",
            investors=["Some VC"],
            funding_amount="$10M",
            funding_stage="SERIES_A",
            industries=["retail"],
            founding_year=2022,
            company_size=30,
            title="Engineer",
        )

        assert score_ai > score_other
        assert any("AI" in s for s in signals_ai)


class TestCalculateEngineerScore:
    """Tests for full engineer score calculation."""

    def test_high_quality_role(self) -> None:
        """High quality role should score well."""
        role_data = {
            "name": "Staff Engineer",
            "salaryUpperBound": 350000,
            "percent_fee": 18,
            "investors": ["Sequoia Capital", "Andreessen Horowitz"],
            "company": {
                "name": "CoolStartup",
                "fundingAmount": "$50M",
                "size": 50,
                "industries": ["ai"],
                "foundingYear": 2022,
                "company_metadata": {"last_funding_round": "SERIES_B"},
            },
            "manager_rating": 4.8,
            "responsiveness_days": 0.5,
            "interview_stages": 4,
            "role_metadata": {"highlights": ["NO_FINAL_ROUNDS", "TRUSTED_CLIENT"]},
            "tech_stack": ["Python", "TypeScript", "React", "Kubernetes"],
            "hiring_count": 2,
        }

        result = calculate_engineer_score(role_data)

        assert result.score >= 0.7
        assert "compensation" in result.breakdown
        assert "company_quality" in result.breakdown
        assert len(result.signals) > 0

    def test_low_quality_role(self) -> None:
        """Low quality role should score poorly."""
        role_data = {
            "name": "Junior Engineer",
            "salaryUpperBound": 120000,
            "percent_fee": 10,
            "investors": [],
            "company": {
                "name": "BoringCorp",
                "fundingAmount": None,
                "size": 500,
                "industries": ["retail"],
                "company_metadata": {},
            },
            "manager_rating": 3.5,
            "responsiveness_days": 4,
            "interview_stages": 8,
            "role_metadata": {"highlights": []},
            "tech_stack": ["Java", "Oracle"],
            "hiring_count": 1,
        }

        result = calculate_engineer_score(role_data)
        assert result.score < 0.5

    def test_missing_data_handled(self) -> None:
        """Missing data should be handled gracefully."""
        role_data = {
            "name": "Engineer",
            "company": {},
        }

        result = calculate_engineer_score(role_data)
        assert 0.0 <= result.score <= 1.0
        assert result.breakdown is not None


class TestCalculateHeadhunterScore:
    """Tests for full headhunter score calculation."""

    def test_attractive_placement(self) -> None:
        """Attractive role for placement should score well."""
        role_data = {
            "name": "Senior Engineer",
            "salaryUpperBound": 280000,
            "percent_fee": 18,
            "manager_rating": 4.9,
            "responsiveness_days": 0.5,
            "interview_stages": 4,
            "role_metadata": {"highlights": ["ROLE_BONUS", "TRUSTED_CLIENT"]},
            "approved_recruiters_count": 2,
            "total_interviewing": 3,
            "total_hired": 2,
            "hiring_count": 3,
            "role_types": ["full_stack_engineer"],
            "locations": ["new_york"],
            "workplace_type": "Remote",
        }

        result = calculate_headhunter_score(role_data)

        assert result.score >= 0.7
        assert "placement_probability" in result.breakdown
        assert "commission_value" in result.breakdown

    def test_crowded_role_lower_score(self) -> None:
        """Crowded role should score lower for headhunters."""
        role_data = {
            "name": "Engineer",
            "salaryUpperBound": 200000,
            "percent_fee": 15,
            "manager_rating": 4.0,
            "responsiveness_days": 2.0,
            "interview_stages": 5,
            "role_metadata": {"highlights": []},
            "approved_recruiters_count": 20,  # Very crowded
            "total_interviewing": 30,
            "total_hired": 0,  # Never hired through platform
            "hiring_count": 1,
            "role_types": ["backend_engineer"],
            "locations": ["san_francisco"],
            "workplace_type": "On-site",
        }

        result = calculate_headhunter_score(role_data)
        assert result.score < 0.6


class TestCalculateScores:
    """Tests for the master calculate_scores function."""

    def test_returns_all_scores(self) -> None:
        """Should return all score types."""
        role_data = {
            "name": "Senior Engineer",
            "salaryUpperBound": 250000,
            "percent_fee": 16,
            "investors": ["Y Combinator"],
            "company": {
                "name": "TestCo",
                "fundingAmount": "$15M",
                "size": 40,
                "industries": ["developer_tools"],
                "company_metadata": {"last_funding_round": "SERIES_A"},
            },
            "manager_rating": 4.5,
            "responsiveness_days": 1.0,
            "interview_stages": 5,
            "role_metadata": {"highlights": []},
            "tech_stack": ["Python", "React"],
            "role_types": ["full_stack_engineer"],
            "approved_recruiters_count": 3,
            "total_interviewing": 5,
            "total_hired": 1,
            "hiring_count": 2,
        }

        scores = calculate_scores(role_data)

        assert "engineer_score" in scores
        assert "headhunter_score" in scores
        assert "excitement_score" in scores
        assert "combined_score" in scores
        assert "score_breakdown" in scores

        # All scores should be in valid range
        assert 0.0 <= scores["engineer_score"] <= 1.0
        assert 0.0 <= scores["headhunter_score"] <= 1.0
        assert 0.0 <= scores["excitement_score"] <= 1.0
        assert 0.0 <= scores["combined_score"] <= 1.0

    def test_enrichment_override(self) -> None:
        """Enrichment score should override deterministic excitement."""
        role_data = {
            "name": "Engineer",
            "company": {"name": "UnknownCo"},
        }

        # Without enrichment (baseline)
        _ = calculate_scores(role_data)

        # With enrichment override
        scores_with_enrich = calculate_scores(role_data, enrichment_score=0.85)

        assert scores_with_enrich["excitement_score"] == 0.85
        assert "LLM-enriched" in scores_with_enrich["score_breakdown"]["excitement"]["signals"][0]

    def test_combined_score_weighting(self) -> None:
        """Combined score should be weighted correctly."""
        role_data = {
            "name": "Engineer",
            "salaryUpperBound": 250000,
            "percent_fee": 15,
            "company": {"name": "TestCo"},
        }

        scores = calculate_scores(role_data)

        # Combined = 45% engineer + 55% headhunter
        expected_combined = scores["engineer_score"] * 0.45 + scores["headhunter_score"] * 0.55
        assert abs(scores["combined_score"] - round(expected_combined, 2)) < 0.01


class TestInvestorTierConstants:
    """Tests for investor tier constant sets."""

    def test_tier1_contains_top_vcs(self) -> None:
        """Tier 1 should contain the most elite VCs."""
        expected = {"sequoia", "a16z", "benchmark", "y combinator"}
        assert expected.issubset(TIER_1_VCS)

    def test_tier2_contains_strong_vcs(self) -> None:
        """Tier 2 should contain strong but not elite VCs."""
        expected = {"spark capital", "felicis", "first round capital", "lux capital"}
        assert expected.issubset(TIER_2_VCS)

    def test_no_overlap_tier1_tier2(self) -> None:
        """Tier 1 and 2 should not overlap."""
        assert TIER_1_VCS.isdisjoint(TIER_2_VCS)

    def test_notable_angels(self) -> None:
        """Notable angels should include known tech leaders."""
        expected = {"elad gil", "nat friedman", "naval ravikant"}
        assert expected.issubset(NOTABLE_ANGELS)

    def test_hot_companies(self) -> None:
        """Hot companies should include known hot startups."""
        expected = {"anthropic", "stripe", "notion", "linear"}
        assert expected.issubset(HOT_COMPANIES)
