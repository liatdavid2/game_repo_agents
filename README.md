# Game Repo LangGraph Agent

A simple LangGraph-based agent that creates or edits very small child-friendly browser games and publishes them to a Git repository.

The script takes a free-text game request, generates a complete game with:

- `index.html`
- `style.css`
- `script.js`

Then it saves the game inside a local Git repo under a `games/` folder, commits the change, and pushes it to GitHub.

---
## Demo Video

[![Watch the demo](https://img.youtube.com/vi/pFAwtT-79fc/0.jpg)](https://youtu.be/pFAwtT-79fc)

---

## What It Does

This project supports two modes:

### 1. Create a new game
- Takes a free-text description
- Uses OpenAI to generate a new game
- Saves it in a new versioned folder such as:
  - `games/fairy-star-collector-1`
  - `games/fairy-star-collector-2`

### 2. Edit an existing game
- Finds the latest matching game folder
- Loads the existing `index.html`, `style.css`, and `script.js`
- Sends them to the model with the new request
- Saves the updated files back into that existing folder

The workflow is orchestrated with LangGraph nodes.

---

## Main Features

- LangGraph workflow with clear node-based execution
- Free-text game generation
- Existing game editing
- Automatic versioning for new games
- Git add / commit / push
- Console progress messages for each step
- `.env` support for API key and model name

---

## Example Commands


### Create new game
```
python game_repo_langgraph.py ^
  --repo_path "C:\Users\liat\Documents\work\GALI" ^
  --mode create ^
  --description "Create a simple purple game where a fairy collects stars and bubbles."
  ```


### Edit an existing game

```
python game_repo_langgraph.py ^
  --repo_path "C:\Users\liat\Documents\work\GALI" ^
  --mode edit ^
  --game_name "fairy-star-bubble-collector-1" ^
  --description "update fairy image to https://image.similarpng.com/file/similarpng/very-thumbnail/2021/05/Cute-little-fairy-with-beautiful-long-braided-hairstyle-holding-a-lantern-on-transparent-background-PNG.png"
```

---

## Agent Diagram

```text
User Request
    |
    v
+----------------------+
|   prepare_paths      |
|----------------------|
| Validate repo        |
| Ensure games/ exists |
| Resolve mode         |
| Resolve target game  |
+----------------------+
    |
    v
+----------------------+
|   generate_files     |
|----------------------|
| Create mode:         |
|   generate new game  |
| Edit mode:           |
|   load existing game |
|   update with model  |
+----------------------+
    |
    v
+----------------------+
|     save_files       |
|----------------------|
| Create mode:         |
|   create next folder |
|   base-name-1        |
|   base-name-2        |
| Edit mode:           |
|   overwrite current  |
+----------------------+
    |
    v
+----------------------+
|   publish_to_git     |
|----------------------|
| git add              |
| git commit           |
| git push             |
+----------------------+
    |
    v
   Result