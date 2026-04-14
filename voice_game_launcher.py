import json
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

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
      max-width: 760px;
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
    button {
      border: none;
      border-radius: 12px;
      padding: 12px 18px;
      font-size: 16px;
      cursor: pointer;
      margin-right: 8px;
      margin-bottom: 8px;
    }
    .record {
      background: #7c4dff;
      color: white;
    }
    .stop {
      background: #ff7043;
      color: white;
    }
    .create {
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
  </style>
</head>
<body>
  <h1>Voice Game Creator</h1>

  <div class="card">
    <p class="small">
      Click Record, speak the game idea, then click Create Game.
      Best support is usually in Chrome or Edge.
    </p>

    <button class="record" onclick="startRecording()">Record</button>
    <button class="stop" onclick="stopRecording()">Stop</button>
    <button class="create" onclick="createGame()">Create Game</button>

    <div class="status" id="status">Ready</div>

    <textarea id="description" placeholder="The voice transcript will appear here..."></textarea>

    <h3>Server Response</h3>
    <pre id="output"></pre>
  </div>

  <script>
    let recognition = null;
    let isRecording = false;

    function setStatus(text) {
      document.getElementById("status").innerText = text;
    }

    function startRecording() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setStatus("Speech recognition is not supported in this browser.");
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = "en-US";
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
        document.getElementById("description").value = transcript.trim();
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

    async function createGame() {
      const description = document.getElementById("description").value.trim();
      const output = document.getElementById("output");

      if (!description) {
        setStatus("Please record or type a game description first.");
        return;
      }

      setStatus("Creating game...");
      output.textContent = "";

      try {
        const response = await fetch("/create_game", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            description: description
          })
        });

        const data = await response.json();
        output.textContent = JSON.stringify(data, null, 2);

        if (response.ok) {
          setStatus("Game created");
        } else {
          setStatus("Failed");
        }
      } catch (err) {
        output.textContent = String(err);
        setStatus("Request failed");
      }
    }
  </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)


@app.route("/create_game", methods=["POST"])
def create_game():
    payload = request.get_json(force=True)
    description = (payload.get("description") or "").strip()

    if not description:
        return jsonify({"error": "Missing description"}), 400

    if not GAME_SCRIPT.exists():
        return jsonify({"error": f"Missing script: {GAME_SCRIPT}"}), 500

    cmd = [
        sys.executable,
        str(GAME_SCRIPT),
        "--repo_path",
        REPO_PATH,
        "--mode",
        "create",
        "--description",
        description,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=False
    )

    response = {
        "command": cmd,
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