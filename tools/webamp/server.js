/**
 * ZICORE Webamp Server
 * Winamp 2 clone in the browser
 * MIT License - Signed by ZineMotion
 */
const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.WEBAMP_PORT || 4002;

// Music directory
const MUSIC_DIR = path.join(__dirname, 'music');
if (!fs.existsSync(MUSIC_DIR)) fs.mkdirSync(MUSIC_DIR, { recursive: true });

app.use('/music', express.static(MUSIC_DIR));

app.get('/', (req, res) => {
  const files = [];
  try {
    fs.readdirSync(MUSIC_DIR).forEach(f => {
      if (/\.(mp3|wav|ogg|m4a|flac)$/i.test(f)) {
        files.push({ name: path.basename(f, path.extname(f)), file: `/music/${encodeURIComponent(f)}` });
      }
    });
  } catch(e) {}

  res.send(`<!DOCTYPE html>
<html><head><title>ZICORE Audio Player</title>
<style>
  body { background: #1a1a2e; color: #e0e0e0; font-family: 'Courier New', monospace; margin: 0; padding: 20px; }
  h1 { color: #0f6; text-shadow: 0 0 10px #0f6; }
  #player { background: #111; border: 2px solid #333; padding: 20px; border-radius: 8px; max-width: 500px; margin: 20px 0; }
  #player.active { border-color: #0f6; box-shadow: 0 0 20px rgba(0,255,102,0.2); }
  .display { background: #000; color: #0f6; padding: 15px; font-family: 'Courier New', monospace; border-radius: 4px; margin-bottom: 15px; }
  .time { font-size: 24px; font-weight: bold; }
  .track-info { font-size: 14px; margin-top: 5px; color: #888; }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; }
  button { background: #222; color: #0f6; border: 1px solid #0f6; padding: 10px 20px; cursor: pointer; border-radius: 4px; font-family: inherit; }
  button:hover { background: #0f6; color: #000; }
  button.active { background: #0f6; color: #000; }
  .playlist { margin-top: 20px; }
  .playlist-item { padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #222; }
  .playlist-item:hover { background: #222; color: #0f6; }
  .playlist-item.playing { color: #0f6; font-weight: bold; }
  .volume { margin-top: 10px; }
  input[type="range"] { width: 100%; accent-color: #0f6; }
  .info { color: #666; font-size: 12px; margin-top: 20px; }
</style></head><body>
<h1>ZICORE Audio Player</h1>
<p>Winamp 2 clone - place music in <code>tools/webamp/music/</code></p>
<div id="player" class="active">
  <div class="display">
    <div class="time" id="time">00:00</div>
    <div class="track-info" id="trackInfo">No track loaded</div>
    <div style="margin-top:8px;height:4px;background:#333;border-radius:2px;">
      <div id="progress" style="height:100%;background:#0f6;width:0%;border-radius:2px;transition:width 0.3s;"></div>
    </div>
  </div>
  <div class="controls">
    <button onclick="prevTrack()">⏮ Prev</button>
    <button onclick="togglePlay()" id="playBtn">▶ Play</button>
    <button onclick="nextTrack()">Next ⏭</button>
    <button onclick="stopTrack()">⏹ Stop</button>
  </div>
  <div class="volume">
    <label>Volume: <span id="volLabel">80</span>%</label>
    <input type="range" min="0" max="100" value="80" oninput="setVolume(this.value)">
  </div>
</div>
<div class="playlist">
  <h3>Playlist</h3>
  <div id="playlist">${files.length > 0 ? files.map((f,i) => 
    `<div class="playlist-item" onclick="playTrack(${i})" data-idx="${i}">${f.name}</div>`
  ).join('') : '<p>No music files found. Place .mp3, .wav, .ogg in music/</p>'}</div>
</div>
<div class="info">
  <p>Signed by ZineMotion | ZICORE System Audio Player</p>
</div>
<audio id="audio" preload="auto"></audio>
<script>
const tracks = ${JSON.stringify(files)};
let currentTrack = 0;
let playing = false;
const audio = document.getElementById('audio');

function playTrack(idx) {
  if (idx < 0 || idx >= tracks.length) return;
  currentTrack = idx;
  audio.src = tracks[idx].file;
  audio.play();
  playing = true;
  document.getElementById('playBtn').textContent = '⏸ Pause';
  document.getElementById('trackInfo').textContent = tracks[idx].name;
  document.querySelectorAll('.playlist-item').forEach((el,i) => {
    el.classList.toggle('playing', i === idx);
  });
}

function togglePlay() {
  if (!audio.src && tracks.length > 0) { playTrack(0); return; }
  if (playing) { audio.pause(); playing = false; document.getElementById('playBtn').textContent = '▶ Play'; }
  else { audio.play(); playing = true; document.getElementById('playBtn').textContent = '⏸ Pause'; }
}

function stopTrack() { audio.pause(); audio.currentTime = 0; playing = false; document.getElementById('playBtn').textContent = '▶ Play'; }
function prevTrack() { playTrack(currentTrack - 1); }
function nextTrack() { playTrack(currentTrack + 1); }
function setVolume(v) { audio.volume = v / 100; document.getElementById('volLabel').textContent = v; }

audio.addEventListener('timeupdate', () => {
  const m = Math.floor(audio.currentTime / 60);
  const s = Math.floor(audio.currentTime % 60);
  document.getElementById('time').textContent = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
  if (audio.duration) document.getElementById('progress').style.width = (audio.currentTime / audio.duration * 100) + '%';
});
audio.addEventListener('ended', nextTrack);
audio.volume = 0.8;
</script></body></html>`);
});

app.listen(PORT, () => {
  console.log(`[ZICORE Webamp] Running on http://localhost:${PORT}`);
  console.log(`[ZICORE Webamp] Place music in: ${MUSIC_DIR}`);
});
