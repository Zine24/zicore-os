/**
 * ZICORE i18n — English/Spanish toggle
 * Usage: Include <script src="/js/zicore-i18n.js"></script> then ZICORE_I18N.init()
 * Elements with data-i18n="key" get auto-translated.
 * Toggle button auto-injected into .ztopbar if present.
 */
const ZICORE_I18N = {
  lang: localStorage.getItem('zicore_lang') || 'en',
  dict: {},

  async init() {
    try {
      const r = await fetch('/data/i18n.json');
      if (r.ok) this.dict = await r.json();
    } catch (e) {}
    this.apply();
    this._injectToggle();
  },

  t(key) {
    return (this.dict[this.lang] && this.dict[this.lang][key]) || key;
  },

  apply() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const val = this.t(key);
      if (val !== key) el.textContent = val;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const val = this.t(key);
      if (val !== key) el.placeholder = val;
    });
    document.documentElement.lang = this.lang;
  },

  toggle() {
    this.lang = this.lang === 'en' ? 'es' : 'en';
    localStorage.setItem('zicore_lang', this.lang);
    this.apply();
    const btn = document.getElementById('i18nToggle');
    if (btn) btn.textContent = this.lang === 'en' ? 'EN' : 'ES';
  },

  _injectToggle() {
    const bar = document.querySelector('.ztopbar-inner') || document.querySelector('.ztopbar');
    if (!bar) return;
    const btn = document.createElement('div');
    btn.id = 'i18nToggle';
    btn.style.cssText = 'font-size:10px;font-weight:700;letter-spacing:1px;padding:4px 8px;border:1px solid rgba(0,229,255,0.15);border-radius:4px;color:var(--cyan);cursor:pointer;transition:all .2s;user-select:none';
    btn.textContent = this.lang === 'en' ? 'EN' : 'ES';
    btn.title = 'Toggle language / Cambiar idioma';
    btn.onclick = () => this.toggle();
    btn.onmouseenter = () => { btn.style.borderColor = 'rgba(0,229,255,0.4)'; };
    btn.onmouseleave = () => { btn.style.borderColor = 'rgba(0,229,255,0.15)'; };
    const clock = bar.querySelector('.ztopbar-clock');
    if (clock) bar.insertBefore(btn, clock);
    else bar.appendChild(btn);
  }
};
