/**
 * FornecedorAutocomplete — combobox reutilizável para seleção de fornecedor.
 *
 * Uso mínimo:
 *   const ac = new FornecedorAutocomplete('#meu-input', {
 *     onSelect: (item) => { console.log(item.id, item.nome); }
 *   });
 *
 * API:
 *   ac.setValue(id, nome)  — preenche programaticamente (ex: ao editar)
 *   ac.clear()             — limpa seleção
 *   ac.getSelected()       — retorna { id, nome } ou null
 */
class FornecedorAutocomplete {
  constructor(inputSelector, options = {}) {
    this._input = typeof inputSelector === 'string'
      ? document.querySelector(inputSelector)
      : inputSelector;

    if (!this._input) throw new Error(`FornecedorAutocomplete: elemento não encontrado: ${inputSelector}`);

    this._opts = Object.assign({
      apiUrl: '/api/fornecedores/buscar',
      limit: 20,
      debounceMs: 250,
      placeholder: 'Buscar fornecedor...',
      onSelect: null,
      onClear: null,
      apenasAtivos: true,
    }, options);

    this._selected = null;
    this._debounceTimer = null;
    this._results = [];
    this._activeIndex = -1;

    this._setup();
  }

  // ── Configuração inicial ──────────────────────────────────────────────────

  _setup() {
    // Wrapper para posicionar dropdown
    const wrapper = document.createElement('div');
    wrapper.className = 'ac-wrapper';
    wrapper.style.position = 'relative';
    this._input.parentNode.insertBefore(wrapper, this._input);
    wrapper.appendChild(this._input);

    this._input.setAttribute('autocomplete', 'off');
    this._input.setAttribute('aria-autocomplete', 'list');
    this._input.setAttribute('aria-haspopup', 'listbox');
    this._input.setAttribute('role', 'combobox');
    this._input.setAttribute('aria-expanded', 'false');
    if (this._opts.placeholder) this._input.placeholder = this._opts.placeholder;

    // Dropdown
    this._dropdown = document.createElement('ul');
    this._dropdown.className = 'ac-dropdown';
    this._dropdown.setAttribute('role', 'listbox');
    this._dropdown.style.cssText = [
      'position:absolute', 'z-index:9999', 'left:0', 'right:0', 'top:100%',
      'margin:2px 0 0', 'padding:0', 'list-style:none',
      'background:#1e293b', 'border:1px solid #334155',
      'border-radius:6px', 'max-height:240px', 'overflow-y:auto',
      'box-shadow:0 4px 16px rgba(0,0,0,.4)', 'display:none'
    ].join(';');
    wrapper.appendChild(this._dropdown);

    // Eventos
    this._input.addEventListener('input', () => this._onInput());
    this._input.addEventListener('keydown', (e) => this._onKeyDown(e));
    this._input.addEventListener('blur', () => setTimeout(() => this._close(), 150));
    this._input.addEventListener('focus', () => {
      if (this._input.value.trim()) this._search(this._input.value);
    });
  }

  // ── Eventos de input ─────────────────────────────────────────────────────

  _onInput() {
    const val = this._input.value;
    // Se o campo foi limpo, desseleciona
    if (!val.trim()) {
      this._selected = null;
      this._close();
      if (this._opts.onClear) this._opts.onClear();
      return;
    }
    // Se o usuário digitou após uma seleção, invalida a seleção
    if (this._selected) this._selected = null;

    clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => this._search(val), this._opts.debounceMs);
  }

  _onKeyDown(e) {
    if (!this._results.length) return;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        this._activeIndex = Math.min(this._activeIndex + 1, this._results.length - 1);
        this._renderHighlight();
        break;
      case 'ArrowUp':
        e.preventDefault();
        this._activeIndex = Math.max(this._activeIndex - 1, 0);
        this._renderHighlight();
        break;
      case 'Enter':
        e.preventDefault();
        if (this._activeIndex >= 0) this._select(this._results[this._activeIndex]);
        break;
      case 'Escape':
        this._close();
        break;
    }
  }

  // ── Busca ─────────────────────────────────────────────────────────────────

  async _search(q) {
    try {
      const params = new URLSearchParams({
        q: q.trim(),
        limit: this._opts.limit,
        apenas_ativos: this._opts.apenasAtivos ? 'true' : 'false',
      });
      const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
      const res = await fetch(`${this._opts.apiUrl}?${params}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) return;
      this._results = await res.json();
      this._activeIndex = -1;
      this._render(q.trim());
    } catch (_) {
      // Silencia erros de rede — evita crash do formulário
    }
  }

  // ── Renderização ──────────────────────────────────────────────────────────

  _render(q) {
    this._dropdown.innerHTML = '';
    if (!this._results.length) {
      const li = document.createElement('li');
      li.textContent = 'Nenhum fornecedor encontrado';
      li.style.cssText = 'padding:10px 14px;color:#94a3b8;font-size:.875rem;cursor:default';
      this._dropdown.appendChild(li);
    } else {
      this._results.forEach((item, idx) => {
        const li = document.createElement('li');
        li.setAttribute('role', 'option');
        li.dataset.idx = idx;
        li.style.cssText = 'padding:9px 14px;cursor:pointer;font-size:.875rem;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
        li.innerHTML = this._highlight(item.nome, q);
        if (item.cnpj) {
          const small = document.createElement('span');
          small.textContent = ` — ${item.cnpj}`;
          small.style.cssText = 'color:#64748b;font-size:.8rem';
          li.appendChild(small);
        }
        li.addEventListener('mousedown', (e) => { e.preventDefault(); this._select(item); });
        li.addEventListener('mousemove', () => { this._activeIndex = idx; this._renderHighlight(); });
        this._dropdown.appendChild(li);
      });
    }
    this._open();
  }

  _highlight(text, q) {
    if (!q) return this._escapeHtml(text);
    // Busca accent-insensitive no frontend
    const norm = this._normalize(text);
    const qn = this._normalize(q);
    const idx = norm.indexOf(qn);
    if (idx < 0) return this._escapeHtml(text);
    return (
      this._escapeHtml(text.slice(0, idx)) +
      `<mark style="background:#3b82f6;color:#fff;border-radius:2px;padding:0 1px">${this._escapeHtml(text.slice(idx, idx + q.length))}</mark>` +
      this._escapeHtml(text.slice(idx + q.length))
    );
  }

  _renderHighlight() {
    const items = this._dropdown.querySelectorAll('li[role="option"]');
    items.forEach((li, i) => {
      li.style.background = i === this._activeIndex ? '#1d4ed8' : '';
    });
  }

  // ── Seleção ───────────────────────────────────────────────────────────────

  _select(item) {
    this._selected = item;
    this._input.value = item.nome;
    this._close();
    if (this._opts.onSelect) this._opts.onSelect(item);
  }

  // ── API pública ───────────────────────────────────────────────────────────

  setValue(id, nome) {
    this._selected = { id, nome };
    this._input.value = nome || '';
  }

  clear() {
    this._selected = null;
    this._input.value = '';
    this._close();
  }

  getSelected() {
    return this._selected;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  _open() {
    this._dropdown.style.display = 'block';
    this._input.setAttribute('aria-expanded', 'true');
  }

  _close() {
    this._dropdown.style.display = 'none';
    this._input.setAttribute('aria-expanded', 'false');
    this._results = [];
    this._activeIndex = -1;
  }

  _normalize(str) {
    return str.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}

// Exporta para uso como módulo (opcional) e torna disponível globalmente
if (typeof module !== 'undefined' && module.exports) module.exports = FornecedorAutocomplete;
else window.FornecedorAutocomplete = FornecedorAutocomplete;
