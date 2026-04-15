from flask import render_template_string
from game_library import list_games


LIBRARY_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Game Library</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 1100px;
      margin: 40px auto;
      padding: 0 16px;
      background: #f7f3ff;
      color: #222;
    }
    h1 {
      color: #6d3ccf;
    }
    .topbar {
      margin-bottom: 20px;
    }
    .topbar a {
      text-decoration: none;
      background: #7c4dff;
      color: white;
      padding: 10px 14px;
      border-radius: 10px;
      margin-right: 8px;
      display: inline-block;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 18px;
    }
    .card {
      background: white;
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }
    .title {
      font-weight: bold;
      margin-bottom: 10px;
      word-break: break-word;
      font-size: 16px;
    }
    .preview-frame {
      width: 100%;
      height: 220px;
      border: 1px solid #ddd;
      border-radius: 12px;
      background: #fff;
      overflow: hidden;
      margin-bottom: 12px;
      position: relative;
    }
    .preview-frame iframe {
      width: 800px;
      height: 600px;
      border: 0;
      transform: scale(0.34);
      transform-origin: top left;
      pointer-events: none;
    }
    .actions a {
      text-decoration: none;
      background: #26a69a;
      color: white;
      padding: 10px 14px;
      border-radius: 10px;
      display: inline-block;
      margin-right: 8px;
      margin-top: 4px;
    }
    .actions a.edit {
      background: #ff7043;
    }
    .muted {
      color: #666;
      font-size: 13px;
      margin-bottom: 8px;
    }
  </style>
</head>
<body>
  <h1>Game Library</h1>

  <div class="topbar">
    <a href="/">Create Game</a>
  </div>

  {% if games %}
    <div class="grid">
      {% for game in games %}
        <div class="card">
          <div class="title">{{ game.name }}</div>

          <div class="preview-frame">
            <iframe
              src="/play/{{ game.folder }}/index.html"
              loading="lazy"
              title="{{ game.name }}"
            ></iframe>
          </div>

          <div class="muted">Folder: {{ game.folder }}</div>

          <div class="actions">
            <a href="/play/{{ game.folder }}/index.html" target="_blank">Play</a>
            <a class="edit" href="/?mode=edit&game_name={{ game.folder }}">Edit</a>
          </div>
        </div>
      {% endfor %}
    </div>
  {% else %}
    <p>No games found yet.</p>
  {% endif %}
</body>
</html>
"""


def render_library(repo_path: str):
    games = list_games(repo_path)
    return render_template_string(LIBRARY_PAGE, games=games)