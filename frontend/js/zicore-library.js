/* ═══════════════════════════════════════════════════════════════
   ZICORE Library — Global Sidebar Component
   Persistent asset library accessible from any page
   ═══════════════════════════════════════════════════════════════ */

(function(){
  'use strict';

  const NS = 'ZICORE_LIBRARY';
  const CSS_ID = 'zicore-library-css';
  const BASE = window.ZICORE_API || '';

  /* ── state ─────────────────────────────────────────────────── */
  let state = {
    open: false,
    tab: 'all',           // all | images | audio | video | 3d | favorites
    assets: [],
    loading: false,
    search: '',
    // player
    player: { active: false, asset: null, playing: false, progress: 0, duration: 0, volume: 0.7 },
    // playlist (ordered list for prev/next)
    playlist: [],
    playlistIndex: -1,
    shuffle: false,
    repeat: 'none',       // none | all | one
  };

  let audioEl = null;
  let videoEl = null;
  let progressInterval = null;

  /* ── icons (inline SVG) ────────────────────────────────────── */
  const ICO = {
    library: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    close:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 6L6 18M6 6l12 12"/></svg>',
    play:    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
    pause:   '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
    prev:    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>',
    next:    '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zM4 18l8.5-6L4 6z"/></svg>',
    shuffle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>',
    repeat:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 1l4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="M7 23l-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>',
    vol:     '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 5L6 9H2v6h4l5 4V5z"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
    mute:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M11 5L6 9H2v6h4l5 4V5z"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>',
    fav:     '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14 2 9.27l6.91-1.01z"/></svg>',
    favO:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14 2 9.27l6.91-1.01z"/></svg>',
    audio:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    image:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
    video:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="15" height="14" rx="2"/><path d="M22 7l-5 3.5L22 14V7z"/></svg>',
    mesh:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
  };

  /* ── type helpers ──────────────────────────────────────────── */
  const TYPE_ICONS = { audio: ICO.audio, image: ICO.image, video: ICO.video, '3d': ICO.mesh };
  const TYPE_LABELS = { audio: 'AUDIO', image: 'IMAGE', video: 'VIDEO', '3d': '3D' };
  const TYPE_CSS = { audio: 'audio', image: 'image', video: 'video', '3d': 'threed' };

  function extOf(path) {
    return (path || '').split('.').pop().toLowerCase();
  }
  function guessType(asset) {
    if (asset.output_type) return asset.output_type;
    const ext = extOf(asset.file_path || asset.path || '');
    if (['mp3','wav','ogg','flac','m4a','aac'].includes(ext)) return 'audio';
    if (['mp4','webm','ogv','mov','mkv'].includes(ext)) return 'video';
    if (['png','jpg','jpeg','gif','bmp','tga','webp','svg'].includes(ext)) return 'image';
    if (['stl','obj','glb','gltf','ply','3ds','step','stp'].includes(ext)) return '3d';
    return asset.type || 'image';
  }
  function displayName(asset) {
    const p = asset.file_path || asset.path || '';
    const name = p.split('/').pop() || 'Untitled';
    return name.length > 24 ? name.slice(0,22) + '..' : name;
  }
  function fileUrl(asset) {
    const p = asset.file_path || asset.path || '';
    if (!p) return '';
    if (p.startsWith('http')) return p;
    return '/media/' + p.replace(/^media\//, '');
  }
  function thumbUrl(asset) {
    const t = asset.thumbnail_path;
    if (t) return t.startsWith('http') ? t : '/media/' + t.replace(/^media\//, '');
    const type = guessType(asset);
    if (type === 'image') return fileUrl(asset);
    return '';
  }
  function formatDuration(sec) {
    if (!sec || isNaN(sec)) return '0:00';
    const m = Math.floor(sec/60);
    const s = Math.floor(sec%60);
    return m + ':' + String(s).padStart(2,'0');
  }

  /* ── API ───────────────────────────────────────────────────── */
  async function fetchAssets() {
    state.loading = true;
    renderBody();
    try {
      const res = await fetch(BASE + '/api/library/unified');
      const data = await res.json();
      state.assets = Array.isArray(data) ? data : (data.assets || data.items || []);
    } catch(e) {
      console.warn('[ZLIB] fetch error:', e);
      state.assets = [];
    }
    state.loading = false;
    renderBody();
  }

  async function toggleFavorite(id) {
    const a = state.assets.find(x => x.id === id);
    if (!a) return;
    a.is_favorite = a.is_favorite ? 0 : 1;
    renderBody();
    try {
      await fetch(BASE + '/api/library/generation/' + id, {
        method: 'PUT',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ is_favorite: a.is_favorite ? 1 : 0 })
      });
    } catch(e) {}
  }

  /* ── player ────────────────────────────────────────────────── */
  function playAsset(asset) {
    stopPlayer();
    state.player.asset = asset;
    state.player.playing = true;
    state.player.progress = 0;
    const type = guessType(asset);
    const url = fileUrl(asset);

    if (type === 'audio') {
      audioEl = new Audio(url);
      audioEl.volume = state.player.volume;
      audioEl.addEventListener('loadedmetadata', () => {
        state.player.duration = audioEl.duration;
        renderPlayer();
      });
      audioEl.addEventListener('ended', () => onTrackEnd());
      audioEl.play().catch(()=>{});
      progressInterval = setInterval(() => {
        if (audioEl) {
          state.player.progress = audioEl.currentTime;
          updateSeekUI();
        }
      }, 500);
    } else if (type === 'video') {
      videoEl = document.createElement('video');
      videoEl.src = url;
      videoEl.volume = state.player.volume;
      videoEl.style.cssText = 'width:100%;max-height:80px;border-radius:4px;object-fit:contain;background:#000';
      const cont = document.getElementById('zlib-player-extra');
      if (cont) { cont.innerHTML = ''; cont.appendChild(videoEl); }
      videoEl.addEventListener('loadedmetadata', () => {
        state.player.duration = videoEl.duration;
        renderPlayer();
      });
      videoEl.addEventListener('ended', () => onTrackEnd());
      videoEl.play().catch(()=>{});
      progressInterval = setInterval(() => {
        if (videoEl) {
          state.player.progress = videoEl.currentTime;
          updateSeekUI();
        }
      }, 500);
    } else {
      // image / 3d — just show thumbnail, no real playback
      state.player.duration = 0;
      state.player.progress = 0;
    }

    // update playlist position
    const idx = state.playlist.findIndex(x => x.id === asset.id);
    if (idx >= 0) state.playlistIndex = idx;
    else { state.playlist.push(asset); state.playlistIndex = state.playlist.length - 1; }

    renderPlayer();
    renderBody();
  }

  function stopPlayer() {
    if (audioEl) { audioEl.pause(); audioEl = null; }
    if (videoEl) { videoEl.pause(); videoEl.remove(); videoEl = null; }
    if (progressInterval) { clearInterval(progressInterval); progressInterval = null; }
    state.player.playing = false;
  }

  function togglePlayPause() {
    if (!state.player.asset) return;
    if (state.player.playing) {
      if (audioEl) audioEl.pause();
      if (videoEl) videoEl.pause();
      state.player.playing = false;
    } else {
      if (audioEl) audioEl.play().catch(()=>{});
      if (videoEl) videoEl.play().catch(()=>{});
      state.player.playing = true;
    }
    renderPlayer();
  }

  function prevTrack() {
    if (state.playlist.length === 0) return;
    let idx = state.playlistIndex - 1;
    if (idx < 0) idx = state.playlist.length - 1;
    playAsset(state.playlist[idx]);
  }

  function nextTrack() {
    if (state.playlist.length === 0) return;
    if (state.repeat === 'one') {
      if (state.player.asset) playAsset(state.player.asset);
      return;
    }
    let idx = state.playlistIndex + 1;
    if (idx >= state.playlist.length) {
      if (state.repeat === 'all') idx = 0;
      else { stopPlayer(); renderPlayer(); return; }
    }
    playAsset(state.playlist[idx]);
  }

  function onTrackEnd() { nextTrack(); }

  function seekTo(pct) {
    const dur = state.player.duration || 0;
    if (!dur) return;
    const t = pct * dur;
    if (audioEl) audioEl.currentTime = t;
    if (videoEl) videoEl.currentTime = t;
    state.player.progress = t;
    updateSeekUI();
  }

  function setVolume(v) {
    state.player.volume = v;
    if (audioEl) audioEl.volume = v;
    if (videoEl) videoEl.volume = v;
    renderPlayer();
  }

  function updateSeekUI() {
    const slider = document.getElementById('zlib-seek');
    const time = document.getElementById('zlib-time');
    if (slider && state.player.duration) {
      slider.value = state.player.progress / state.player.duration;
    }
    if (time) {
      time.textContent = formatDuration(state.player.progress) + ' / ' + formatDuration(state.player.duration);
    }
  }

  /* ── filter ────────────────────────────────────────────────── */
  function filteredAssets() {
    let list = state.assets;
    if (state.tab === 'favorites') return list.filter(a => a.is_favorite);
    if (state.tab !== 'all') return list.filter(a => guessType(a) === state.tab);
    return list;
  }

  /* ── render ────────────────────────────────────────────────── */
  function renderPanel() {
    let el = document.getElementById('zlib-panel');
    if (el) return el;

    // inject CSS
    if (!document.getElementById(CSS_ID)) {
      const link = document.createElement('link');
      link.id = CSS_ID;
      link.rel = 'stylesheet';
      link.href = '/css/zicore-library.css';
      document.head.appendChild(link);
    }

    // backdrop
    const bd = document.createElement('div');
    bd.id = 'zlib-backdrop';
    bd.className = 'zlib-backdrop';
    bd.onclick = () => toggle(false);
    document.body.appendChild(bd);

    // panel
    el = document.createElement('div');
    el.id = 'zlib-panel';
    el.className = 'zlib-panel';
    el.innerHTML = `
      <div class="zlib-header">
        <span class="zlib-header-title">LIBRARY</span>
        <span class="zlib-header-count" id="zlib-count"></span>
        <button class="zlib-header-close" onclick="ZICORE_LIBRARY.toggle(false)">${ICO.close}</button>
      </div>
      <div class="zlib-tabs" id="zlib-tabs">
        <button class="zlib-tab active" data-tab="all">ALL</button>
        <button class="zlib-tab" data-tab="images">IMAGES</button>
        <button class="zlib-tab" data-tab="audio">AUDIO</button>
        <button class="zlib-tab" data-tab="video">VIDEO</button>
        <button class="zlib-tab" data-tab="3d">3D</button>
        <button class="zlib-tab" data-tab="favorites">FAVS</button>
      </div>
      <div class="zlib-search"><div class="zlib-search-wrap">
        <input type="text" id="zlib-search" placeholder="Search library..." />
      </div></div>
      <div class="zlib-assets" id="zlib-assets"></div>
      <div id="zlib-player-extra"></div>
      <div class="zlib-player" id="zlib-player" style="display:none"></div>
    `;
    document.body.appendChild(el);

    // tab clicks
    el.querySelectorAll('.zlib-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        state.tab = btn.dataset.tab;
        el.querySelectorAll('.zlib-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderBody();
      });
    });

    // search
    document.getElementById('zlib-search').addEventListener('input', (e) => {
      state.search = e.target.value.toLowerCase();
      renderBody();
    });

    renderBody();
  }

  function renderBody() {
    const cont = document.getElementById('zlib-assets');
    if (!cont) return;

    const countEl = document.getElementById('zlib-count');
    if (countEl) countEl.textContent = state.assets.length + ' ASSETS';

    if (state.loading) {
      cont.innerHTML = '<div class="zlib-loading">LOADING</div>';
      return;
    }

    let items = filteredAssets();
    if (state.search) {
      items = items.filter(a => {
        const hay = ((a.prompt||'') + ' ' + (a.file_path||'') + ' ' + (a.tags||'')).toLowerCase();
        return hay.includes(state.search);
      });
    }

    if (items.length === 0) {
      cont.innerHTML = `<div class="zlib-empty"><div class="zlib-empty-icon">${ICO.library}</div><div class="zlib-empty-text">NO ASSETS</div></div>`;
      return;
    }

    let html = '<div class="zlib-grid">';
    for (const a of items) {
      const type = guessType(a);
      const thumb = thumbUrl(a);
      const playing = state.player.asset && state.player.asset.id === a.id;
      const isAudio = type === 'audio';
      html += `<div class="zlib-card${playing?' playing':''}" data-id="${a.id}" ondblclick="ZICORE_LIBRARY.play(${a.id})">
        <div class="zlib-card-thumb">
          ${thumb ? `<img src="${thumb}" loading="lazy" />` : `<span class="zlib-type-icon">${TYPE_ICONS[type]||''}</span>`}
          <div class="zlib-card-playing">▶</div>
        </div>
        <div class="zlib-card-info">
          <div class="zlib-card-name">${displayName(a)}</div>
          <div class="zlib-card-meta">
            <span class="zlib-card-badge ${TYPE_CSS[type]||''}">${TYPE_LABELS[type]||type}</span>
            <span>${a.engine||''}</span>
            <span style="margin-left:auto;cursor:pointer;color:${a.is_favorite?'#ff9100':'#303848'}" onclick="event.stopPropagation();ZICORE_LIBRARY.fav(${a.id})">${a.is_favorite?ICO.fav:ICO.favO}</span>
          </div>
        </div>
      </div>`;
    }
    html += '</div>';
    cont.innerHTML = html;
  }

  function renderPlayer() {
    const el = document.getElementById('zlib-player');
    if (!el) return;
    const a = state.player.asset;
    if (!a) { el.style.display = 'none'; return; }
    el.style.display = '';

    const thumb = thumbUrl(a);
    const type = guessType(a);
    el.innerHTML = `
      <div class="zlib-player-info">
        <div class="zlib-player-thumb">${thumb ? `<img src="${thumb}" />` : (TYPE_ICONS[type]||'')}</div>
        <div class="zlib-player-track">
          <div class="zlib-player-name">${displayName(a)}</div>
          <div class="zlib-player-type">${TYPE_LABELS[type]||type} · ${a.engine||''}</div>
        </div>
      </div>
      <div class="zlib-player-controls">
        <button class="zlib-ctrl-btn${state.shuffle?' active':''}" onclick="ZICORE_LIBRARY.toggleShuffle()" title="Shuffle">${ICO.shuffle}</button>
        <button class="zlib-ctrl-btn" onclick="ZICORE_LIBRARY.prev()" title="Previous">${ICO.prev}</button>
        <button class="zlib-ctrl-btn play-btn" onclick="ZICORE_LIBRARY.playPause()">${state.player.playing ? ICO.pause : ICO.play}</button>
        <button class="zlib-ctrl-btn" onclick="ZICORE_LIBRARY.next()" title="Next">${ICO.next}</button>
        <button class="zlib-ctrl-btn${state.repeat!=='none'?' active':''}" onclick="ZICORE_LIBRARY.toggleRepeat()" title="Repeat">${ICO.repeat}</button>
      </div>
      <div class="zlib-player-seek">
        <input type="range" class="zlib-seek-slider" id="zlib-seek" min="0" max="1" step="0.001" value="0"
          oninput="ZICORE_LIBRARY.seek(this.valueAsNumber)" />
      </div>
      <div class="zlib-player-row">
        <span class="zlib-player-time" id="zlib-time">0:00 / 0:00</span>
        <div class="zlib-player-volume" style="margin-left:auto;display:flex;align-items:center;gap:4px">
          <button class="zlib-ctrl-btn" onclick="ZICORE_LIBRARY.toggleMute()" style="width:20px;height:20px">${state.player.volume === 0 ? ICO.mute : ICO.vol}</button>
          <input type="range" class="zlib-vol-slider" min="0" max="1" step="0.05" value="${state.player.volume}"
            oninput="ZICORE_LIBRARY.vol(this.valueAsNumber)" />
        </div>
      </div>
    `;
  }

  /* ── FAB button ────────────────────────────────────────────── */
  function renderFAB() {
    if (document.getElementById('zlib-fab')) return;
    const fab = document.createElement('button');
    fab.id = 'zlib-fab';
    fab.className = 'zlib-fab';
    fab.title = 'Library';
    fab.innerHTML = ICO.library;
    fab.onclick = () => toggle(!state.open);
    document.body.appendChild(fab);
  }

  /* ── public API ────────────────────────────────────────────── */
  function toggle(open) {
    state.open = typeof open === 'boolean' ? open : !state.open;
    renderPanel();
    const panel = document.getElementById('zlib-panel');
    const backdrop = document.getElementById('zlib-backdrop');
    const fab = document.getElementById('zlib-fab');
    if (panel) panel.classList.toggle('open', state.open);
    if (backdrop) backdrop.classList.toggle('open', state.open);
    if (fab) fab.classList.toggle('open', state.open);
    if (state.open && state.assets.length === 0) fetchAssets();
    if (state.open) renderPlayer();
  }

  function play(id) {
    const a = state.assets.find(x => x.id === id);
    if (a) playAsset(a);
  }

  function fav(id) { toggleFavorite(id); }
  function playPause() { togglePlayPause(); }
  function prev() { prevTrack(); }
  function next() { nextTrack(); }
  function seek(pct) { seekTo(pct); }
  function vol(v) { setVolume(v); }

  function toggleShuffle() {
    state.shuffle = !state.shuffle;
    renderPlayer();
  }

  function toggleRepeat() {
    const modes = ['none','all','one'];
    const i = modes.indexOf(state.repeat);
    state.repeat = modes[(i+1) % modes.length];
    renderPlayer();
  }

  function toggleMute() {
    if (state.player.volume > 0) {
      state.player._prevVol = state.player.volume;
      setVolume(0);
    } else {
      setVolume(state.player._prevVol || 0.7);
    }
  }

  /* ── inject into every page ────────────────────────────────── */
  function init() {
    renderFAB();
    // auto-fetch on init
    fetchAssets();
  }

  /* ── expose ────────────────────────────────────────────────── */
  window[NS] = { init, toggle, play, fav, playPause, prev, next, seek, vol, toggleShuffle, toggleRepeat, toggleMute, state };

  // auto-init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
