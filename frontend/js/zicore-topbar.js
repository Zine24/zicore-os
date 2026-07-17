/* ═══════════════════════════════════════════════════════════════
   ZICORE TOPBAR — Unified user control component
   Include: <script src="/js/zicore-topbar.js"></script>
   Then call: ZICORE_TOPBAR.init({title, tabs, activeTab})
   ═══════════════════════════════════════════════════════════════ */

const ZICORE_TOPBAR = {
  user: null,
  zntBalance: 0,
  dropdownOpen: false,

  async init(opts = {}) {
    const token = localStorage.getItem('zicore_sso_token');
    if (token) {
      try {
        const r = await fetch('/api/sso/me', { headers: { 'Authorization': 'Bearer ' + token } });
        if (r.ok) {
          const d = await r.json();
          this.user = d.user || d;
        } else {
          localStorage.removeItem('zicore_sso_token');
          localStorage.removeItem('zicore_sso_user');
        }
      } catch(e) {}
    }

    if (this.user) {
      try {
        const t = localStorage.getItem('zicore_sso_token');
        const r = await fetch('/api/bank/balance', { headers: { 'Authorization': 'Bearer ' + t } });
        const d = await r.json();
        this.zntBalance = d.balance || 0;
      } catch(e) {}
    }

    this.render(opts);
    this.startClock();

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.ztopbar-menu-btn') && !e.target.closest('.ztopbar-dropdown')) {
        this.closeDropdown();
      }
    });
  },

  render(opts) {
    const el = document.querySelector('.ztopbar');
    if (!el) return;

    const userName = this.user?.display_name || this.user?.name || this.user?.email?.split('@')[0] || '';
    const userEmail = this.user?.email || '';
    const initial = userName ? userName[0].toUpperCase() : '';
    const znt = this.formatZNT(this.zntBalance);

    let tabsHtml = '';
    if (opts.tabs) {
      tabsHtml = '<div class="ztopbar-tabs">';
      opts.tabs.forEach(t => {
        const active = t.id === opts.activeTab ? ' active' : '';
        tabsHtml += '<a class="ztopbar-tab' + active + '" href="' + (t.href || '#') + '">' + t.label + '</a>';
      });
      tabsHtml += '</div>';
    }

    el.innerHTML =
      '<div class="ztopbar-inner">' +
        '<a href="/" class="ztopbar-brand">' +
          '<svg viewBox="0 0 36 42" width="28" height="32"><polygon points="18,2 34,10 34,30 18,38 2,30 2,10" fill="none" stroke="url(#tbg)" stroke-width="1.5"/><defs><linearGradient id="tbg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#00e5ff"/><stop offset="100%" stop-color="#7c4dff"/></linearGradient></defs><text x="18" y="25" text-anchor="middle" fill="url(#tbg)" font-size="14" font-weight="700" font-family="sans-serif">Z</text></svg>' +
          '<span class="ztopbar-title">' + (opts.brand || 'ZICORE') + '</span>' +
        '</a>' +
        tabsHtml +
        '<div class="ztopbar-spacer"></div>' +
        (this.user ?
          '<div class="ztopbar-user">' +
            '<div class="ztopbar-znt" title="ZiVault - Universal Asset Vault">' +
              '<span class="ztopbar-znt-icon">&#9889;</span>' +
              '<span class="ztopbar-znt-amt">' + znt + ' ZNT</span>' +
            '</div>' +
            '<div class="ztopbar-clock" id="zicoreClock">--:--:--</div>' +
            '<div class="ztopbar-menu-btn" onclick="ZICORE_TOPBAR.toggleDropdown()">' + initial + '</div>' +
            '<div class="ztopbar-dropdown" id="zicoreDropdown">' +
              '<div class="ztopbar-dd-header">' +
                '<div class="ztopbar-dd-name">' + userName + '</div>' +
                '<div class="ztopbar-dd-email">' + userEmail + '</div>' +
                '<div class="ztopbar-dd-balance"><span data-i18n="topbar.balance">Saldo</span>: <span>' + znt + ' ZNT</span></div>' +
              '</div>' +
              '<div class="ztopbar-dd-sep"></div>' +
              '<a class="ztopbar-dd-item" href="/zivault"><span>&#127974;</span><span data-i18n="topbar.vault">ZiVault</span></a>' +
              '<a class="ztopbar-dd-item" href="/mail"><span>&#9993;</span><span data-i18n="topbar.mail">Mail</span></a>' +
              '<a class="ztopbar-dd-item" href="/storage"><span>&#9729;</span><span data-i18n="topbar.storage">Storage</span></a>' +
              '<a class="ztopbar-dd-item" href="/settings"><span>&#9881;</span><span data-i18n="topbar.settings">Configuracion</span></a>' +
              '<div class="ztopbar-dd-sep"></div>' +
              '<a class="ztopbar-dd-item" href="/services"><span>&#128203;</span><span data-i18n="topbar.services">Servicios</span></a>' +
              '<a class="ztopbar-dd-item" href="/api-docs"><span>&#128218;</span>API Docs</a>' +
              '<div class="ztopbar-dd-sep"></div>' +
              '<div class="ztopbar-dd-item danger" onclick="ZICORE_TOPBAR.logout()"><span>&#9211;</span><span data-i18n="topbar.logout">Cerrar Sesion</span></div>' +
            '</div>' +
          '</div>'
        :
          '<div class="ztopbar-user">' +
            '<div class="ztopbar-clock" id="zicoreClock">--:--:--</div>' +
            '<a href="/login" class="ztopbar-login"><span data-i18n="topbar.login">Iniciar Sesion</span></a>' +
          '</div>'
        ) +
      '</div>';
  },

  toggleDropdown() {
    const dd = document.getElementById('zicoreDropdown');
    if (!dd) return;
    this.dropdownOpen = !this.dropdownOpen;
    dd.classList.toggle('open', this.dropdownOpen);
  },

  closeDropdown() {
    const dd = document.getElementById('zicoreDropdown');
    if (dd) dd.classList.remove('open');
    this.dropdownOpen = false;
  },

  logout() {
    const token = localStorage.getItem('zicore_sso_token');
    if (token) {
      fetch('/api/sso/logout', { method: 'POST', headers: { 'Authorization': 'Bearer ' + token } }).catch(() => {});
    }
    localStorage.removeItem('zicore_sso_token');
    localStorage.removeItem('zicore_sso_user');
    document.cookie = 'zicore_sso_token=; path=/; max-age=0';
    window.location.href = '/login';
  },

  formatZNT(amount) {
    if (amount >= 1000000) return (amount / 1000000).toFixed(1) + 'M';
    if (amount >= 1000) return (amount / 1000).toFixed(1) + 'K';
    return amount.toFixed(2);
  },

  startClock() {
    const update = () => {
      const el = document.getElementById('zicoreClock');
      if (el) el.textContent = new Date().toLocaleTimeString('es-MX', { hour12: false });
    };
    update();
    setInterval(update, 1000);
  },

  async refreshBalance() {
    const token = localStorage.getItem('zicore_sso_token');
    if (!token) return;
    try {
      const r = await fetch('/api/bank/balance', { headers: { 'Authorization': 'Bearer ' + token } });
      const d = await r.json();
      this.zntBalance = d.balance || 0;
      const el = document.querySelector('.ztopbar-znt-amt');
      if (el) el.textContent = this.formatZNT(this.zntBalance) + ' ZNT';
    } catch(e) {}
  }
};
