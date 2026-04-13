import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import TypedDict, Optional, Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

# ---------------------------
# ENV
# ---------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MINI_GPT = os.getenv("MINI_GPT", "gpt-4.1-mini")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------
# OUTPUT SCHEMA
# ---------------------------
class GameFiles(BaseModel):
    title: str = Field(description="Short game title")
    index_html: str = Field(description="Complete HTML file")
    style_css: str = Field(description="Complete CSS file")
    script_js: str = Field(description="Complete JavaScript file")


# ---------------------------
# GRAPH STATE
# ---------------------------
class GameState(TypedDict, total=False):
    user_description: str
    repo_path: str
    mode: str
    game_name: Optional[str]

    title: str
    index_html: str
    style_css: str
    script_js: str

    target_root_dir: str
    game_dir: str
    commit_message: str
    logs: List[str]
    result: Dict[str, Any]
    error: Optional[str]


# ---------------------------
# LOGGING
# ---------------------------
def log_step(state: GameState, message: str) -> None:
    if "logs" not in state or state["logs"] is None:
        state["logs"] = []
    state["logs"].append(message)
    print(f"[INFO] {message}", flush=True)


# ---------------------------
# HELPERS
# ---------------------------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "new-game"


def run_git(repo_path: Path, args: list[str], allow_fail: bool = False) -> None:
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        shell=False
    )

    if result.stdout.strip():
        print(f"[GIT STDOUT] {result.stdout.strip()}", flush=True)
    if result.stderr.strip():
        print(f"[GIT STDERR] {result.stderr.strip()}", flush=True)

    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def read_text_if_exists(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def generate_new_game_with_openai(user_description: str) -> GameFiles:
    system_prompt = """
You create very small child-friendly browser games.

Return ONLY valid JSON with exactly these keys:
- title
- index_html
- style_css
- script_js

Rules:
- Single screen
- Very simple
- Child-friendly
- Plain HTML, CSS, JavaScript only
- No npm
- No frameworks
- No external CDN
- Must run by opening index.html directly
- Include score
- Include start or restart button
- Include clear win or lose message
- Keep code readable
- Use English in code and comments
"""

    user_prompt = f"""
User description:
{user_description}

Create a complete playable game using only:
- index.html
- style.css
- script.js

Return JSON only.
"""

    response = client.chat.completions.create(
        model=MINI_GPT,
        temperature=0.4,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return GameFiles(**data)


def edit_existing_game_with_openai(
    user_description: str,
    game_title: str,
    index_html: str,
    style_css: str,
    script_js: str,
) -> GameFiles:
    system_prompt = """
You edit an existing very small child-friendly browser game.

Return ONLY valid JSON with exactly these keys:
- title
- index_html
- style_css
- script_js

Rules:
- Preserve the game as a simple browser game
- Plain HTML, CSS, JavaScript only
- No npm
- No frameworks
- No external CDN
- Must run by opening index.html directly
- Keep code readable
- Use English in code and comments
- Apply the user's requested changes to the existing game files
"""

    user_prompt = f"""
The user wants to edit an existing game.

User request:
{user_description}

Existing title:
{game_title}

Existing index.html:
{index_html}

Existing style.css:
{style_css}

Existing script.js:
{script_js}

Return the full updated files as JSON only.
"""

    response = client.chat.completions.create(
        model=MINI_GPT,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return GameFiles(**data)


# ---------------------------
# NODES
# ---------------------------
def resolve_target_game(state: GameState) -> GameState:
    log_step(state, "Resolving repository and target game path")

    repo_path = Path(state["repo_path"]).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_path}")

    if not (repo_path / ".git").exists():
        raise ValueError(f"Path is not a git repo: {repo_path}")

    games_root = repo_path / "games"
    games_root.mkdir(parents=True, exist_ok=True)

    mode = state.get("mode", "create").lower()
    game_name = state.get("game_name")

    if mode == "edit":
        if not game_name:
            raise ValueError("For edit mode, --game_name is required")

        game_dir = games_root / slugify(game_name)
        if not game_dir.exists():
            raise FileNotFoundError(f"Game folder does not exist: {game_dir}")

        log_step(state, f"Edit mode selected for existing game: {game_dir}")
        return {
            "target_root_dir": str(games_root),
            "game_dir": str(game_dir),
        }

    log_step(state, "Create mode selected")
    return {
        "target_root_dir": str(games_root),
    }


def generate_or_edit_game_files(state: GameState) -> GameState:
    mode = state.get("mode", "create").lower()

    if mode == "edit":
        game_dir = Path(state["game_dir"]).resolve()
        log_step(state, f"Loading existing files from: {game_dir}")

        existing_html = read_text_if_exists(game_dir / "index.html")
        existing_css = read_text_if_exists(game_dir / "style.css")
        existing_js = read_text_if_exists(game_dir / "script.js")

        if not existing_html and not existing_css and not existing_js:
            raise ValueError("Existing game files are missing or empty")

        existing_title = game_dir.name
        log_step(state, "Sending existing game files to model for editing")

        files = edit_existing_game_with_openai(
            user_description=state["user_description"],
            game_title=existing_title,
            index_html=existing_html,
            style_css=existing_css,
            script_js=existing_js,
        )

        log_step(state, f"Model returned updated files for game: {files.title}")
        return {
            "title": files.title,
            "index_html": files.index_html,
            "style_css": files.style_css,
            "script_js": files.script_js,
            "commit_message": f"Edit game: {files.title}",
        }

    log_step(state, "Sending new game request to model")
    files = generate_new_game_with_openai(state["user_description"])
    log_step(state, f"Model returned new game files: {files.title}")

    return {
        "title": files.title,
        "index_html": files.index_html,
        "style_css": files.style_css,
        "script_js": files.script_js,
        "commit_message": f"Add game: {files.title}",
    }


def save_game_to_repo(state: GameState) -> GameState:
    repo_path = Path(state["repo_path"]).resolve()
    games_root = Path(state["target_root_dir"]).resolve()

    if state.get("mode", "create").lower() == "edit":
        game_dir = Path(state["game_dir"]).resolve()
        log_step(state, f"Saving updated files into existing folder: {game_dir}")
    else:
        game_slug = slugify(state["title"])
        game_dir = games_root / game_slug
        game_dir.mkdir(parents=True, exist_ok=True)
        log_step(state, f"Saving new game into folder: {game_dir}")

    (game_dir / "index.html").write_text(state["index_html"], encoding="utf-8")
    (game_dir / "style.css").write_text(state["style_css"], encoding="utf-8")
    (game_dir / "script.js").write_text(state["script_js"], encoding="utf-8")

    relative_game_dir = str(game_dir.relative_to(repo_path))
    log_step(state, f"Files written successfully under: {relative_game_dir}")

    return {
        "game_dir": str(game_dir),
    }


def git_publish(state: GameState) -> GameState:
    repo_path = Path(state["repo_path"]).resolve()
    game_dir = Path(state["game_dir"]).resolve()
    relative_game_dir = str(game_dir.relative_to(repo_path))

    log_step(state, f"Running git add for: {relative_game_dir}")
    run_git(repo_path, ["add", relative_game_dir])

    log_step(state, f"Running git commit: {state['commit_message']}")
    run_git(repo_path, ["commit", "-m", state["commit_message"]], allow_fail=True)

    log_step(state, "Running git push")
    run_git(repo_path, ["push"], allow_fail=False)

    log_step(state, "Git publish completed successfully")

    return {
        "result": {
            "title": state["title"],
            "mode": state.get("mode", "create"),
            "game_dir": str(game_dir),
            "files": [
                str(game_dir / "index.html"),
                str(game_dir / "style.css"),
                str(game_dir / "script.js"),
            ],
            "commit_message": state["commit_message"],
            "model_used": MINI_GPT,
            "logs": state.get("logs", []),
        }
    }


# ---------------------------
# GRAPH
# ---------------------------
def build_graph():
    graph = StateGraph(GameState)

    graph.add_node("resolve_target_game", resolve_target_game)
    graph.add_node("generate_or_edit_game_files", generate_or_edit_game_files)
    graph.add_node("save_game_to_repo", save_game_to_repo)
    graph.add_node("git_publish", git_publish)

    graph.add_edge(START, "resolve_target_game")
    graph.add_edge("resolve_target_game", "generate_or_edit_game_files")
    graph.add_edge("generate_or_edit_game_files", "save_game_to_repo")
    graph.add_edge("save_game_to_repo", "git_publish")
    graph.add_edge("git_publish", END)

    return graph.compile()


# ---------------------------
# MAIN
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_path", required=True, help="Path to local git repo")
    parser.add_argument("--description", required=True, help="Free-text game request")
    parser.add_argument(
        "--mode",
        choices=["create", "edit"],
        default="create",
        help="Create a new game or edit an existing one"
    )
    parser.add_argument(
        "--game_name",
        default=None,
        help="Existing game folder name for edit mode"
    )
    args = parser.parse_args()

    app = build_graph()

    initial_state: GameState = {
        "user_description": args.description,
        "repo_path": args.repo_path,
        "mode": args.mode,
        "game_name": args.game_name,
        "logs": [],
    }

    try:
        print("[INFO] Starting workflow", flush=True)
        result = app.invoke(initial_state)
        print("[INFO] Workflow finished", flush=True)
        print(json.dumps(result.get("result", result), indent=2, ensure_ascii=False))
    except Exception as exc:
        error_payload = {
            "error": str(exc),
            "logs": initial_state.get("logs", []),
        }
        print(json.dumps(error_payload, indent=2, ensure_ascii=False))
        raise


if __name__ == "__main__":
    main()