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
