from mangai_workers.detection import detect_regions_from_asset


def test_detect_regions_from_asset_is_deterministic_for_same_file(tmp_path) -> None:
    asset_path = tmp_path / "page-a.bin"
    asset_path.write_bytes(b"asset-a" * 32)

    first_run = detect_regions_from_asset(asset_path=asset_path, page_width=1600, page_height=2400)
    second_run = detect_regions_from_asset(asset_path=asset_path, page_width=1600, page_height=2400)

    assert first_run == second_run
    assert len(first_run) >= 2
    assert all(candidate.confidence >= 0.76 for candidate in first_run)


def test_detect_regions_from_asset_changes_with_asset_bytes(tmp_path) -> None:
    asset_a = tmp_path / "page-a.bin"
    asset_b = tmp_path / "page-b.bin"
    asset_a.write_bytes(b"asset-a" * 32)
    asset_b.write_bytes(b"asset-b" * 32)

    result_a = detect_regions_from_asset(asset_path=asset_a, page_width=1600, page_height=2400)
    result_b = detect_regions_from_asset(asset_path=asset_b, page_width=1600, page_height=2400)

    assert result_a != result_b
    for candidate in [*result_a, *result_b]:
        box = candidate.bounding_box
        assert 0 <= box["x"] <= 1600
        assert 0 <= box["y"] <= 2400
        assert box["width"] > 0
        assert box["height"] > 0
