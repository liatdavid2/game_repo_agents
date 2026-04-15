import json
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string, send_from_directory, abort
from game_library_ui import render_library

app = Flask(__name__)

REPO_PATH = r"C:\Users\liat\Documents\work\GALI"
GAME_SCRIPT = Path(__file__).resolve().parent / "game_repo_langgraph.py"

HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Voice Game Creator</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 900px;
      margin: 40px auto;
      padding: 0 16px;
      background: #f7f3ff;
      color: #222;
    }
    h1 {
      color: #6d3ccf;
    }
    .card {
      background: white;
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }
    .tab-btn {
      border: none;
      border-radius: 12px;
      padding: 12px 18px;
      font-size: 16px;
      cursor: pointer;
      background: #e8ddff;
      color: #4b2ca3;
      font-weight: bold;
    }
    .tab-btn.active {
      background: #7c4dff;
      color: white;
    }
    .tab-panel {
      display: none;
    }
    .tab-panel.active {
      display: block;
    }
    button, select, input {
      border: none;
      border-radius: 12px;
      padding: 12px 18px;
      font-size: 16px;
      margin-right: 8px;
      margin-bottom: 8px;
      box-sizing: border-box;
    }
    input, select {
      border: 1px solid #ccc;
      background: white;
      color: #222;
    }
    .record {
      background: #7c4dff;
      color: white;
    }
    .stop {
      background: #ff7043;
      color: white;
    }
    .action {
      background: #26a69a;
      color: white;
    }
    textarea {
      width: 100%;
      min-height: 140px;
      margin-top: 12px;
      padding: 12px;
      border-radius: 12px;
      border: 1px solid #ccc;
      font-size: 15px;
      box-sizing: border-box;
    }
    pre {
      background: #111;
      color: #eee;
      padding: 14px;
      border-radius: 12px;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    .small {
      color: #555;
      font-size: 14px;
    }
    .status {
      margin-top: 12px;
      font-weight: bold;
    }
    .row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 8px;
    }
    label {
      font-size: 14px;
      color: #444;
      display: block;
      margin-bottom: 6px;
    }
    .field {
      margin-bottom: 10px;
    }
    .text-input {
      width: 100%;
      max-width: 420px;
    }
  </style>
</head>
<body>
  <h1>Voice Game Creator</h1>

  <div class="card">
    <p class="small">
      Record a game idea, then create a new game or edit an existing one.
      Best support is usually in Chrome or Edge.
    </p>

    <div class="row">
      <label for="language">Language:</label>
      <select id="language">
        <option value="he-IL">עברית</option>
        <option value="en-US" selected>English</option>
      </select>
      <button class="record" onclick="startRecording()">Record</button>
      <button class="stop" onclick="stopRecording()">Stop</button>
    </div>

    <div class="tabs">
    <button id="tab-create-btn" class="tab-btn active" onclick="showTab('create')">Create Game</button>
    <button class="tab-btn" onclick="window.location.href='/library'">Game Library</button>
    </div>

    <div id="tab-create" class="tab-panel active">
      <div class="field">
        <label for="create-description">Game description</label>
        <textarea id="create-description" placeholder="The voice transcript will appear here..."></textarea>
      </div>
      <button class="action" onclick="submitGame('create')">Create Game</button>
    </div>

    <div id="tab-edit" class="tab-panel">
      <div class="field">
        <label for="game-name">Existing game name</label>
        <input id="game-name" class="text-input" type="text" placeholder="example: fairy-star-bubble-collector-1">
      </div>
      <div class="field">
        <label for="edit-description">Edit request</label>
        <textarea id="edit-description" placeholder="The voice transcript will appear here..."></textarea>
      </div>
      <button class="action" onclick="submitGame('edit')">Edit Game</button>
    </div>

    <div class="status" id="status">Ready</div>

    <h3>Server Response</h3>
    <pre id="output"></pre>
  </div>

  <script>
    let recognition = null;
    let isRecording = false;
    let activeTab = "create";

    function applyQueryParams() {
        const params = new URLSearchParams(window.location.search);
        const mode = params.get("mode");
        const gameName = params.get("game_name");

        if (mode === "edit") {
            showTab("edit");
        }

        if (gameName) {
            const input = document.getElementById("game-name");
            if (input) {
            input.value = gameName;
            }
        }
        }

    function setStatus(text) {
      document.getElementById("status").innerText = text;
    }

    function getSelectedLanguage() {
      return document.getElementById("language").value;
    }

    function getActiveTextarea() {
      if (activeTab === "edit") {
        return document.getElementById("edit-description");
      }
      return document.getElementById("create-description");
    }

    function showTab(tabName) {
      activeTab = tabName;

      document.getElementById("tab-create").classList.remove("active");
      document.getElementById("tab-edit").classList.remove("active");
      document.getElementById("tab-create-btn").classList.remove("active");
      document.getElementById("tab-edit-btn").classList.remove("active");

      document.getElementById("tab-" + tabName).classList.add("active");
      document.getElementById("tab-" + tabName + "-btn").classList.add("active");
    }

    function startRecording() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setStatus("Speech recognition is not supported in this browser.");
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = getSelectedLanguage();
      recognition.interimResults = true;
      recognition.continuous = false;

      recognition.onstart = function() {
        isRecording = true;
        setStatus("Recording...");
      };

      recognition.onresult = function(event) {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        getActiveTextarea().value = transcript.trim();
      };

      recognition.onerror = function(event) {
        setStatus("Speech recognition error: " + event.error);
      };

      recognition.onend = function() {
        isRecording = false;
        setStatus("Recording stopped");
      };

      recognition.start();
    }

    function stopRecording() {
      if (recognition && isRecording) {
        recognition.stop();
      }
    }

    async function submitGame(mode) {
      const output = document.getElementById("output");
      const language = getSelectedLanguage();
      const description = mode === "edit"
        ? document.getElementById("edit-description").value.trim()
        : document.getElementById("create-description").value.trim();
      const gameName = document.getElementById("game-name").value.trim();

      if (!description) {
        setStatus("Please record or type a description first.");
        return;
      }

      if (mode === "edit" && !gameName) {
        setStatus("Please enter an existing game name.");
        return;
      }

      setStatus(mode === "edit" ? "Editing game..." : "Creating game...");
      output.textContent = "";

      try {
        const response = await fetch("/run_game_action", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            description: description,
            language: language,
            mode: mode,
            game_name: gameName
          })
        });

        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);

        if (response.ok) {
          setStatus(mode === "edit" ? "Game updated" : "Game created");
        } else {
          setStatus("Failed");
        }
      } catch (err) {
        output.textContent = String(err);
        setStatus("Request failed");
      }
    }

    applyQueryParams();
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/library", methods=["GET"])
def library():
    return render_library(REPO_PATH)

@app.route("/play/<game_name>/<path:filename>", methods=["GET"])
def play_game_file(game_name, filename):
    games_root = Path(REPO_PATH) / "games"
    game_dir = games_root / game_name

    if not game_dir.exists() or not game_dir.is_dir():
        abort(404)

    return send_from_directory(game_dir, filename)

@app.route("/run_game_action", methods=["POST"])
def run_game_action():
    payload = request.get_json(force=True)
    description = (payload.get("description") or "").strip()
    language = (payload.get("language") or "").strip()
    mode = (payload.get("mode") or "create").strip().lower()
    game_name = (payload.get("game_name") or "").strip()

    if not description:
        return jsonify({"error": "Missing description"}), 400

    if mode not in {"create", "edit"}:
        return jsonify({"error": "Invalid mode"}), 400

    if mode == "edit" and not game_name:
        return jsonify({"error": "Missing game_name for edit mode"}), 400

    if not GAME_SCRIPT.exists():
        return jsonify({"error": f"Missing script: {GAME_SCRIPT}"}), 500

    cmd = [
        sys.executable,
        str(GAME_SCRIPT),
        "--repo_path",
        REPO_PATH,
        "--mode",
        mode,
        "--description",
        description,
    ]

    if mode == "edit":
        cmd.extend(["--game_name", game_name])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=False
    )

    response = {
        "command": cmd,
        "language": language,
        "mode": mode,
        "game_name": game_name,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

    if result.returncode != 0:
        return jsonify(response), 500

    parsed = None
    try:
        parsed = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        parsed = None

    response["parsed_result"] = parsed
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)