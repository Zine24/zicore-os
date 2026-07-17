/**
 * ZICORE Universal Translator — 5 languages (EN/ES/FR/DE/AR)
 * Free API via MyMemory (no key required, 5000 chars/day)
 * Include: <script src="/js/zicore-translate.js"></script>
 * Init: ZICORE_TRANSLATE.init({target:'container_id'})
 */
const ZICORE_TRANSLATE = {
  LANGUAGES: [
    {code:'en', name:'English',    flag:'🇬🇧', dir:'ltr'},
    {code:'es', name:'Español',    flag:'🇪🇸', dir:'ltr'},
    {code:'fr', name:'Français',   flag:'🇫🇷', dir:'ltr'},
    {code:'de', name:'Deutsch',    flag:'🇩🇪', dir:'ltr'},
    {code:'ar', name:'العربية',    flag:'🇸🇦', dir:'rtl'},
  ],
  sourceLang: 'es',
  targetLang: 'en',
  widgetEl: null,
  isOpen: false,

  init(opts = {}) {
    this.sourceLang = opts.source || 'es';
    this.targetLang = opts.target || 'en';
    this._injectCSS();
    this._createWidget(opts.container);
    this._loadVoices();
  },

  _injectCSS() {
    if (document.getElementById('zicore-translate-css')) return;
    var css = document.createElement('style');
    css.id = 'zicore-translate-css';
    css.textContent = `
.zt-fab{position:fixed;bottom:20px;right:20px;width:48px;height:48px;border-radius:50%;
  background:linear-gradient(135deg,rgba(0,229,255,0.15),rgba(124,77,255,0.15));
  border:1px solid rgba(0,229,255,0.2);backdrop-filter:blur(16px);cursor:pointer;
  display:flex;align-items:center;justify-content:center;font-size:20px;z-index:500;
  transition:all .3s;box-shadow:0 4px 20px rgba(0,0,0,0.4)}
.zt-fab:hover{transform:scale(1.1);box-shadow:0 6px 30px rgba(0,229,255,0.2);border-color:rgba(0,229,255,0.4)}
.zt-fab.active{background:linear-gradient(135deg,rgba(0,229,255,0.25),rgba(124,77,255,0.25))}

.zt-panel{position:fixed;bottom:80px;right:20px;width:380px;max-height:520px;
  background:rgba(10,14,26,0.97);border:1px solid rgba(0,229,255,0.12);border-radius:12px;
  backdrop-filter:blur(24px);z-index:501;display:none;flex-direction:column;overflow:hidden;
  box-shadow:0 12px 50px rgba(0,0,0,0.6)}
.zt-panel.open{display:flex}

.zt-header{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid rgba(0,229,255,0.08)}
.zt-header-title{font-size:11px;font-weight:700;letter-spacing:2px;color:var(--cyan);text-transform:uppercase;flex:1}
.zt-header-close{background:none;border:none;color:var(--text2);cursor:pointer;font-size:14px;padding:2px 6px;border-radius:4px}
.zt-header-close:hover{color:var(--red);background:rgba(255,51,51,0.1)}

.zt-lang-bar{display:flex;align-items:center;gap:4px;padding:8px 14px;border-bottom:1px solid rgba(0,229,255,0.06)}
.zt-lang-btn{flex:1;padding:6px 4px;border:1px solid transparent;border-radius:6px;background:none;
  color:var(--text2);font-size:10px;text-align:center;cursor:pointer;transition:all .2s;white-space:nowrap}
.zt-lang-btn:hover{color:var(--text);background:rgba(0,229,255,0.04)}
.zt-lang-btn.active{color:var(--cyan);border-color:rgba(0,229,255,0.2);background:rgba(0,229,255,0.06)}
.zt-lang-btn .flag{font-size:14px;display:block;margin-bottom:2px}
.zt-lang-btn .code{font-size:8px;letter-spacing:1px;text-transform:uppercase;font-weight:600}

.zt-swap{width:32px;height:32px;border-radius:50%;border:1px solid rgba(0,229,255,0.15);
  background:rgba(0,229,255,0.04);color:var(--cyan);cursor:pointer;display:flex;
  align-items:center;justify-content:center;font-size:14px;flex-shrink:0;transition:all .2s}
.zt-swap:hover{background:rgba(0,229,255,0.1);border-color:rgba(0,229,255,0.3)}

.zt-body{flex:1;display:flex;flex-direction:column;overflow:hidden}
.zt-textarea{width:100%;height:100px;padding:10px 14px;background:rgba(0,0,0,0.3);
  border:none;border-bottom:1px solid rgba(0,229,255,0.06);color:var(--text);
  font-size:13px;font-family:inherit;resize:none;outline:none;line-height:1.5}
.zt-textarea::placeholder{color:var(--text2)}
.zt-textarea[dir="rtl"]{direction:rtl;text-align:right}

.zt-result{flex:1;padding:10px 14px;font-size:13px;line-height:1.5;color:var(--text);
  overflow-y:auto;min-height:80px;max-height:180px}
.zt-result[dir="rtl"]{direction:rtl;text-align:right}
.zt-result.empty{color:var(--text2);font-style:italic}

.zt-actions{display:flex;gap:6px;padding:8px 14px;border-top:1px solid rgba(0,229,255,0.06)}
.zt-action{flex:1;padding:7px;border:1px solid rgba(0,229,255,0.1);border-radius:6px;
  background:rgba(0,229,255,0.03);color:var(--text2);font-size:10px;cursor:pointer;
  text-align:center;transition:all .2s;letter-spacing:.5px;text-transform:uppercase;font-weight:600}
.zt-action:hover{color:var(--cyan);border-color:rgba(0,229,255,0.2);background:rgba(0,229,255,0.06)}
.zt-action:disabled{opacity:.4;cursor:not-allowed}
.zt-action.translating{animation:zt-pulse 1s infinite}
@keyframes zt-pulse{0%,100%{opacity:1}50%{opacity:.5}}

.zt-voices{display:flex;gap:4px;padding:4px 14px 8px}
.zt-voice-btn{padding:4px 8px;border:1px solid rgba(0,229,255,0.08);border-radius:4px;
  background:none;color:var(--text2);font-size:9px;cursor:pointer;transition:all .2s}
.zt-voice-btn:hover{color:var(--cyan);border-color:rgba(0,229,255,0.2)}
.zt-voice-btn.active{color:var(--cyan);border-color:rgba(0,229,255,0.3);background:rgba(0,229,255,0.06)}

.zt-status{padding:4px 14px;font-size:9px;color:var(--text2);border-top:1px solid rgba(0,229,255,0.04);text-align:center}
.zt-status.error{color:var(--red)}
.zt-status.ok{color:var(--green)}

@media(max-width:480px){
  .zt-panel{right:8px;left:8px;width:auto;bottom:76px}
  .zt-fab{bottom:16px;right:16px}
}`;
    document.head.appendChild(css);
  },

  _createWidget(container) {
    var fab = document.createElement('div');
    fab.className = 'zt-fab';
    fab.innerHTML = '🌐';
    fab.title = 'ZICORE Translator';
    fab.onclick = () => this.toggle();
    document.body.appendChild(fab);
    this.fabEl = fab;

    var panel = document.createElement('div');
    panel.className = 'zt-panel';
    panel.id = 'ztPanel';

    var srcLangs = this.LANGUAGES.map(l =>
      '<div class="zt-lang-btn' + (l.code === this.sourceLang ? ' active' : '') + '" data-role="src" data-lang="' + l.code + '">'
      + '<span class="flag">' + l.flag + '</span><span class="code">' + l.code + '</span></div>'
    ).join('');
    var tgtLangs = this.LANGUAGES.map(l =>
      '<div class="zt-lang-btn' + (l.code === this.targetLang ? ' active' : '') + '" data-role="tgt" data-lang="' + l.code + '">'
      + '<span class="flag">' + l.flag + '</span><span class="code">' + l.code + '</span></div>'
    ).join('');

    panel.innerHTML =
      '<div class="zt-header">' +
        '<div class="zt-header-title">🌐 Translator</div>' +
        '<button class="zt-header-close" onclick="ZICORE_TRANSLATE.toggle()">✕</button>' +
      '</div>' +
      '<div class="zt-lang-bar">' +
        '<div style="flex:1;display:flex;gap:2px;flex-wrap:wrap" id="ztSrcLangs">' + srcLangs + '</div>' +
        '<button class="zt-swap" onclick="ZICORE_TRANSLATE.swap()" title="Swap languages">⇄</button>' +
        '<div style="flex:1;display:flex;gap:2px;flex-wrap:wrap" id="ztTgtLangs">' + tgtLangs + '</div>' +
      '</div>' +
      '<div class="zt-body">' +
        '<textarea class="zt-textarea" id="ztInput" placeholder="Escribe o pega texto..." dir="ltr"></textarea>' +
        '<div class="zt-result empty" id="ztResult">Traducción aquí...</div>' +
      '</div>' +
      '<div class="zt-voices" id="ztVoices"></div>' +
      '<div class="zt-actions">' +
        '<button class="zt-action" onclick="ZICORE_TRANSLATE.translate()" id="ztTranslateBtn">▶ Traducir</button>' +
        '<button class="zt-action" onclick="ZICORE_TRANSLATE.speakSource()">🔊 Escuchar</button>' +
        '<button class="zt-action" onclick="ZICORE_TRANSLATE.speakResult()">🔊 Resultado</button>' +
        '<button class="zt-action" onclick="ZICORE_TRANSLATE.copyResult()">📋 Copiar</button>' +
        '<button class="zt-action" onclick="ZICORE_TRANSLATE.micInput()">🎤 Mic</button>' +
      '</div>' +
      '<div class="zt-status" id="ztStatus">Listo</div>';

    document.body.appendChild(panel);
    this.panelEl = panel;

    // Language selector events
    panel.querySelectorAll('.zt-lang-btn').forEach(btn => {
      btn.onclick = () => {
        var role = btn.dataset.role;
        var lang = btn.dataset.lang;
        if (role === 'src') {
          this.sourceLang = lang;
          panel.querySelectorAll('#ztSrcLangs .zt-lang-btn').forEach(b => b.classList.remove('active'));
        } else {
          this.targetLang = lang;
          panel.querySelectorAll('#ztTgtLangs .zt-lang-btn').forEach(b => b.classList.remove('active'));
        }
        btn.classList.add('active');
        // Auto-translate if there's text
        var input = document.getElementById('ztInput');
        if (input && input.value.trim()) this.translate();
        this._updatePlaceholder();
      };
    });

    // Translate on Enter (Ctrl+Enter for newline)
    document.getElementById('ztInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.ctrlKey) {
        e.preventDefault();
        this.translate();
      }
    });
  },

  _updatePlaceholder() {
    var input = document.getElementById('ztInput');
    if (!input) return;
    var placeholders = {
      es: 'Escribe o pega texto...',
      en: 'Type or paste text...',
      fr: 'Écrivez ou collez du texte...',
      de: 'Text eingeben oder einfügen...',
      ar: 'اكتب أو الصق النص...'
    };
    input.placeholder = placeholders[this.sourceLang] || placeholders.es;
    input.dir = this.sourceLang === 'ar' ? 'rtl' : 'ltr';
  },

  toggle() {
    this.isOpen = !this.isOpen;
    this.panelEl.classList.toggle('open', this.isOpen);
    this.fabEl.classList.toggle('active', this.isOpen);
    if (this.isOpen) {
      document.getElementById('ztInput').focus();
      this._updatePlaceholder();
    }
  },

  swap() {
    var tmp = this.sourceLang;
    this.sourceLang = this.targetLang;
    this.targetLang = tmp;
    // Update UI
    var panel = this.panelEl;
    panel.querySelectorAll('#ztSrcLangs .zt-lang-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.lang === this.sourceLang);
    });
    panel.querySelectorAll('#ztTgtLangs .zt-lang-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.lang === this.targetLang);
    });
    // Swap text
    var input = document.getElementById('ztInput');
    var result = document.getElementById('ztResult');
    if (result && !result.classList.contains('empty')) {
      input.value = result.textContent;
      this.translate();
    }
    this._updatePlaceholder();
  },

  async translate() {
    var input = document.getElementById('ztInput');
    var result = document.getElementById('ztResult');
    var status = document.getElementById('ztStatus');
    var btn = document.getElementById('ztTranslateBtn');
    var text = input.value.trim();
    if (!text) { result.textContent = 'Traducción aquí...'; result.classList.add('empty'); return; }

    btn.classList.add('translating');
    btn.disabled = true;
    status.textContent = 'Traduciendo...';
    status.className = 'zt-status';

    try {
      var src = this.sourceLang;
      var tgt = this.targetLang;
      // MyMemory API: free, no key, 5000 chars/day
      var url = 'https://api.mymemory.translated.net/get?q=' + encodeURIComponent(text)
        + '&langpair=' + src + '|' + tgt;
      var resp = await fetch(url);
      var data = await resp.json();

      if (data.responseStatus === 200 && data.responseData) {
        var translated = data.responseData.translatedText;
        // MyMemory sometimes returns ALL CAPS — normalize
        if (translated === translated.toUpperCase() && text !== text.toUpperCase()) {
          translated = translated.charAt(0).toUpperCase() + translated.slice(1).toLowerCase();
        }
        result.textContent = translated;
        result.classList.remove('empty');
        result.dir = tgt === 'ar' ? 'rtl' : 'ltr';
        status.textContent = this.LANGUAGES.find(l => l.code === src).flag + ' → '
          + this.LANGUAGES.find(l => l.code === tgt).flag + ' OK';
        status.className = 'zt-status ok';
      } else {
        result.textContent = 'Error: ' + (data.responseDetails || 'Translation failed');
        result.classList.add('empty');
        status.textContent = 'Error de traducción';
        status.className = 'zt-status error';
      }
    } catch (e) {
      result.textContent = 'Error de conexión: ' + e.message;
      result.classList.add('empty');
      status.textContent = 'Sin conexión';
      status.className = 'zt-status error';
    }

    btn.classList.remove('translating');
    btn.disabled = false;
  },

  speakSource() {
    var text = document.getElementById('ztInput').value.trim();
    if (!text) return;
    this._speak(text, this.sourceLang);
  },

  speakResult() {
    var result = document.getElementById('ztResult');
    if (!result || result.classList.contains('empty')) return;
    this._speak(result.textContent, this.targetLang);
  },

  _speak(text, lang) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    var utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang;
    utter.rate = 1.0;
    utter.pitch = 1.0;
    // Find best voice for language
    var voices = window.speechSynthesis.getVoices();
    var best = voices.find(v => v.lang.startsWith(lang));
    if (best) utter.voice = best;
    window.speechSynthesis.speak(utter);
  },

  _loadVoices() {
    if (!window.speechSynthesis) return;
    var load = () => {
      var voices = window.speechSynthesis.getVoices();
      // Pre-render voice buttons if needed
    };
    load();
    window.speechSynthesis.onvoiceschanged = load;
  },

  copyResult() {
    var result = document.getElementById('ztResult');
    if (!result || result.classList.contains('empty')) return;
    navigator.clipboard.writeText(result.textContent).then(() => {
      var status = document.getElementById('ztStatus');
      status.textContent = 'Copiado al portapapeles';
      status.className = 'zt-status ok';
      setTimeout(() => { status.textContent = 'Listo'; status.className = 'zt-status'; }, 2000);
    });
  },

  micInput() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      var status = document.getElementById('ztStatus');
      status.textContent = 'Reconocimiento de voz no soportado';
      status.className = 'zt-status error';
      return;
    }
    var recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = this.sourceLang;

    var status = document.getElementById('ztStatus');
    var input = document.getElementById('ztInput');
    status.textContent = '🎤 Escuchando... (' + this.sourceLang.toUpperCase() + ')';
    status.className = 'zt-status';

    recognition.onresult = function(event) {
      var transcript = '';
      for (var i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      input.value = transcript;
      status.textContent = '🎤 Texto capturado — traduciendo...';
    };

    recognition.onend = function() {
      status.textContent = 'Listo';
      status.className = 'zt-status';
      // Auto-translate after mic
      if (input.value.trim()) ZICORE_TRANSLATE.translate();
    };

    recognition.onerror = function(e) {
      status.textContent = 'Error: ' + (e.error === 'not-allowed' ? 'Micrófono no permitido' : e.error);
      status.className = 'zt-status error';
    };

    recognition.start();
  },

  // Get current target language for external voice systems
  getTargetLang() {
    return this.targetLang;
  },
  getSourceLang() {
    return this.sourceLang;
  }
};
