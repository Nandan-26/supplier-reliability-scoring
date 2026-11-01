from scripts.check_reproducibility import run_check


def test_full_table_checksum_reproducibility_on_small_fixture(tmp_path):
    report = run_check(
        tmp_path / "reproducibility.json",
        seed=20261022,
        suppliers=20,
        pos=50,
        shipments=50,
        inspections=50,
    )
    assert report["overall_passed"] is True
    assert report["differences"] == []
    assert report["tables_compared"] >= 14
    assert report["ground_truth_compared"] is True
    assert report["malformed_cases_compared"] is True


def test_generator_and_scoring_versions_are_explicit_and_consistent():
    from src.generator import GENERATOR_VERSION
    from src.scoring import SCORING_CONFIG_VERSION, SCORING_ENGINE_VERSION

    assert GENERATOR_VERSION == "1.1.0"
    assert SCORING_ENGINE_VERSION == "2.0.0"
    assert SCORING_CONFIG_VERSION == "v2.0"
