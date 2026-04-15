from pathlib import Path
from typing import List, Dict


def list_games(repo_path: str) -> List[Dict[str, str]]:
    games_root = Path(repo_path) / "games"
    if not games_root.exists():
        return []

    items = []
    for child in sorted(games_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue

        index_file = child / "index.html"
        if not index_file.exists():
            continue

        items.append({
            "name": child.name,
            "folder": child.name,
            "index_file": str(index_file),
        })

    return items