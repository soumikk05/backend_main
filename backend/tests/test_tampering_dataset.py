from app.tampering.dataset_loader import load_tampering_dataset


def test_dataset_loader_labels_and_splits(tmp_path):
    for folder in ("genuine/passport", "tampered/photo_swap"):
        target = tmp_path / folder
        target.mkdir(parents=True)
        for index in range(10): (target / f"{index}.jpg").write_bytes(b"x")
    splits = load_tampering_dataset(str(tmp_path))
    assert sum(len(items) for items in splits.values()) == 20
    assert {label for items in splits.values() for _, label in items} == {0, 1}
