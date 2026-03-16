from pathlib import Path

import mangai_api.repositories.projects as project_store_module
from mangai_api.repositories.projects import LocalProjectStore


def test_local_project_store_retries_state_replace_when_locked(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "api-data"
    store = LocalProjectStore(data_dir=data_dir, api_prefix="/api/v1")
    state = store._load_state()
    replace_calls = {"count": 0}
    original_replace = Path.replace

    def flaky_replace(self: Path, target: Path):
        replace_calls["count"] += 1
        if replace_calls["count"] == 1:
            raise PermissionError("locked")
        return original_replace(self, target)

    monkeypatch.setattr(project_store_module, "sleep", lambda _seconds: None)
    monkeypatch.setattr(Path, "replace", flaky_replace)

    store._save_state_unlocked(state)

    assert replace_calls["count"] == 2
    assert data_dir.joinpath("state.json").exists()
