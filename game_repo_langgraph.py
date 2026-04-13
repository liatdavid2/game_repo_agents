import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import TypedDict, Optional, Any, Dict

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

    title: str
    index_html: str
    style_css: str
    script_js: str

    game_dir: str
    commit_message: str
    result: Dict[str, Any]
    error: Optional[str]


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
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def generate_with_openai(user_description: str) -> GameFiles:
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


# ---------------------------
# NODES
# ---------------------------
def generate_game_files(state: GameState) -> GameState:
    files = generate_with_openai(state["user_description"])

    return {
        "title": files.title,
        "index_html": files.index_html,
        "style_css": files.style_css,
        "script_js": files.script_js,
    }


def save_game_to_repo(state: GameState) -> GameState:
    repo_path = Path(state["repo_path"]).resolve()

    if not repo_path.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo_path}")

    if not (repo_path / ".git").exists():
        raise ValueError(f"Path is not a git repo: {repo_path}")

    game_slug = slugify(state["title"])
    game_dir = repo_path / game_slug
    game_dir.mkdir(parents=True, exist_ok=True)

    (game_dir / "index.html").write_text(state["index_html"], encoding="utf-8")
    (game_dir / "style.css").write_text(state["style_css"], encoding="utf-8")
    (game_dir / "script.js").write_text(state["script_js"], encoding="utf-8")

    return {
        "game_dir": str(game_dir),
        "commit_message": f"Add game: {state['title']}",
    }


def git_publish(state: GameState) -> GameState:
    repo_path = Path(state["repo_path"]).resolve()
    game_dir = Path(state["game_dir"]).resolve()

    relative_game_dir = str(game_dir.relative_to(repo_path))

    run_git(repo_path, ["add", relative_game_dir])
    run_git(repo_path, ["commit", "-m", state["commit_message"]], allow_fail=True)
    run_git(repo_path, ["push"], allow_fail=False)

    return {
        "result": {
            "title": state["title"],
            "game_dir": str(game_dir),
            "files": [
                str(game_dir / "index.html"),
                str(game_dir / "style.css"),
                str(game_dir / "script.js"),
            ],
            "commit_message": state["commit_message"],
            "model_used": MINI_GPT,
        }
    }


# ---------------------------
# GRAPH
# ---------------------------
def build_graph():
    graph = StateGraph(GameState)

    graph.add_node("generate_game_files", generate_game_files)
    graph.add_node("save_game_to_repo", save_game_to_repo)
    graph.add_node("git_publish", git_publish)

    graph.add_edge(START, "generate_game_files")
    graph.add_edge("generate_game_files", "save_game_to_repo")
    graph.add_edge("save_game_to_repo", "git_publish")
    graph.add_edge("git_publish", END)

    return graph.compile()


# ---------------------------
# MAIN
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_path", required=True, help="Path to local git repo")
    parser.add_argument("--description", required=True, help="Free-text game description")
    args = parser.parse_args()

    app = build_graph()

    initial_state: GameState = {
        "user_description": args.description,
        "repo_path": args.repo_path,
    }

    result = app.invoke(initial_state)
    print(json.dumps(result.get("result", result), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()