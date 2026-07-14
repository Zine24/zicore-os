/**
 * ZICORE EmulatorJS Server - Cross-platform
 * Web-based retro game emulator + embedded HTML5 games
 * Signed by ZineMotion
 */
const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.EMULATOR_PORT || 4001;

// Directories
const ROMS_DIR = path.join(__dirname, 'roms');
const GAMES_DIR = path.join(__dirname, 'games');
[ROMS_DIR, GAMES_DIR].forEach(d => { if (!fs.existsSync(d)) fs.mkdirSync(d, { recursive: true }); });

const GAME_DESCRIPTIONS = {
  snake: 'Classic snake game — grow by eating, avoid hitting yourself',
  tetris: 'Falling block puzzle — clear lines by filling rows',
  breakout: 'Brick-breaking paddle game — destroy all bricks',
  '2048': 'Number puzzle — slide tiles to reach 2048',
  pong: 'Classic 2-player pong — first to 11 wins',
  xwing: 'Star Wars X-Wing Alliance — pilot an X-Wing fighter against TIE Fighters with S-foils, lasers, and hyperdrive',
  freespace2: 'FreeSpace 2 Terran Bomber — command a GT Begasus bomber against Shivan fighters with fusion cannons and bombs',
  minesweeper: 'Classic minesweeper — reveal cells, flag mines, clear the board without detonating',
  sudoku: 'Number puzzle — fill 9x9 grid with digits 1-9, each row/column/box unique',
};

// Serve static
app.use('/games', express.static(GAMES_DIR));
app.use('/roms', express.static(ROMS_DIR));

// System detection from ROM extension
const SYSTEM_MAP = {
  '.nes': 'nes', '.sfc': 'snes', '.smc': 'snes', '.gb': 'gb',
  '.gbc': 'gbc', '.gba': 'gba', '.n64': 'n64', '.z64': 'n64',
  '.pce': 'pce', '.sms': 'sms', '.gg': 'sms',
  '.col': 'coleco', '.a26': 'atari2600', '.a52': 'atari5200',
  '.a78': 'atari7800', '.jag': 'jaguar', '.lynx': 'lynx',
  '.zip': 'mame', '.7z': 'mame',
};

app.get('/api/games', (req, res) => {
  const games = [];

  // Embedded HTML5 games (run in RAM, cross-platform)
  try {
    fs.readdirSync(GAMES_DIR).forEach(file => {
      if (file.endsWith('.html')) {
        games.push({
          name: path.basename(file, '.html'),
          file: `/games/${encodeURIComponent(file)}`,
          system: 'html5',
          embedded: true,
          size: 0,
          description: GAME_DESCRIPTIONS[path.basename(file, '.html')] || 'HTML5 game',
        });
      }
    });
  } catch (e) {}

  // ROM files
  try {
    fs.readdirSync(ROMS_DIR).forEach(file => {
      const ext = path.extname(file).toLowerCase();
      const system = SYSTEM_MAP[ext] || 'unknown';
      if (system !== 'unknown') {
        games.push({
          name: path.basename(file, ext),
          file: `/roms/${encodeURIComponent(file)}`,
          system,
          embedded: false,
          size: fs.statSync(path.join(ROMS_DIR, file)).size,
        });
      }
    });
  } catch (e) {}

  res.json({ status: 'ok', games, roms_dir: ROMS_DIR, games_dir: GAMES_DIR });
});

app.get('/', (req, res) => {
  res.send(`<!DOCTYPE html>
<html><head><title>ZICORE Game Emulator</title>
<style>
  body { background: #0a0a1a; color: #0f6; font-family: monospace; margin: 0; padding: 20px; }
  h1 { text-shadow: 0 0 10px #0f6; }
  .subtitle { color: #888; }
  #tabs { display: flex; gap: 10px; margin: 20px 0; }
  .tab { background: #111; border: 1px solid #333; padding: 8px 16px; cursor: pointer; border-radius: 4px; }
  .tab:hover, .tab.active { border-color: #0f6; color: #0f6; }
  #gameList { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin: 20px 0; }
  .game { background: #111; border: 1px solid #333; padding: 15px; cursor: pointer; border-radius: 6px; transition: all 0.2s; }
  .game:hover { border-color: #0f6; box-shadow: 0 0 15px rgba(0,255,102,0.3); transform: translateY(-2px); }
  .game .name { font-size: 16px; font-weight: bold; }
  .game .system { color: #888; font-size: 12px; margin-top: 5px; }
  .game .badge { background: #0f6; color: #000; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
  #player { display: none; margin: 20px 0; }
  #player iframe { width: 100%; height: 80vh; border: 2px solid #0f6; border-radius: 8px; background: #000; }
  .back-btn { background: #222; color: #0f6; border: 1px solid #0f6; padding: 8px 16px; cursor: pointer; margin: 10px 0; }
  .back-btn:hover { background: #0f6; color: #000; }
  .stats { color: #666; font-size: 12px; margin: 10px 0; }
</style></head><body>
<h1>ZICORE Game Emulator</h1>
<p class="subtitle">Retro + HTML5 games - place ROMs in <code>tools/emulatorjs/roms/</code></p>
<div id="tabs">
  <div class="tab active" onclick="filterGames('all')">All</div>
  <div class="tab" onclick="filterGames('html5')">HTML5 (Embedded)</div>
  <div class="tab" onclick="filterGames('retro')">Retro ROMs</div>
</div>
<div id="gameList"><p>Loading...</p></div>
<div id="player">
  <button class="back-btn" onclick="backToList()">Back to List</button>
  <h2 id="gameTitle"></h2>
  <iframe id="gameFrame" src=""></iframe>
</div>
<div class="stats" id="stats"></div>
<script>
let allGames = [];
let currentFilter = 'all';

async function loadGames() {
  const res = await fetch('/api/games');
  const data = await res.json();
  allGames = data.games;
  document.getElementById('stats').textContent =
    data.games.length + ' games available | ' +
    data.games.filter(g=>g.embedded).length + ' embedded | ' +
    data.games.filter(g=>!g.embedded).length + ' ROMs';
  renderGames();
}

function filterGames(filter) {
  currentFilter = filter;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  renderGames();
}

function renderGames() {
  const el = document.getElementById('gameList');
  let filtered = allGames;
  if (currentFilter === 'html5') filtered = allGames.filter(g => g.embedded);
  if (currentFilter === 'retro') filtered = allGames.filter(g => !g.embedded);

  if (filtered.length === 0) {
    el.innerHTML = '<p>No games found. Place ROMs in roms/ or add .html games to games/</p>';
    return;
  }
  el.innerHTML = filtered.map(g =>
    '<div class="game" onclick="playGame(\\'' + g.file + '\\',\\'' + g.name + '\\',\\'' + g.system + '\\')">' +
    '<div class="name">' + g.name + '</div>' +
    '<div class="system">' + g.system.toUpperCase() +
    (g.embedded ? ' <span class="badge">EMBEDDED</span>' : '') +
    '</div>' +
    (g.description ? '<div style="color:#666;font-size:11px;margin-top:6px;line-height:1.4">' + g.description + '</div>' : '') +
    '</div>'
  ).join('');
}

function playGame(url, name, system) {
  document.getElementById('gameTitle').textContent = name + ' (' + system.toUpperCase() + ')';
  document.getElementById('gameFrame').src = url;
  document.getElementById('gameList').style.display = 'none';
  document.getElementById('tabs').style.display = 'none';
  document.getElementById('player').style.display = 'block';
}

function backToList() {
  document.getElementById('player').style.display = 'none';
  document.getElementById('gameList').style.display = 'grid';
  document.getElementById('tabs').style.display = 'flex';
  document.getElementById('gameFrame').src = '';
}

loadGames();
</script></body></html>`);
});

app.listen(PORT, () => {
  console.log(`[ZICORE EmulatorJS] Running on http://localhost:${PORT}`);
  console.log(`[ZICORE EmulatorJS] Embedded games: ${GAMES_DIR}`);
  console.log(`[ZICORE EmulatorJS] ROMs directory: ${ROMS_DIR}`);
});
