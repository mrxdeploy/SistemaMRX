/**
 * criarAutocomplete — combobox reutilizável de busca com digitar.
 *
 * @param {object} opts
 *   input        {HTMLInputElement}  campo de texto visível
 *   hidden       {HTMLInputElement}  campo hidden que recebe o id selecionado
 *   lista        {HTMLElement}       <ul> ou <div> que será o dropdown
 *   dados        {Array}             lista estática [{id, nome, nome_busca, documento?, cidade?}, ...]
 *   url          {string}            (alternativo a dados) endpoint GET ?q=
 *   campoTexto   {string}            chave do item para exibição (default 'nome')
 *   campoSecundario {string}         chave do item para linha secundária (default 'documento')
 *   onSelect     {Function}          callback(item) chamado ao selecionar
 *   placeholder  {string}            placeholder do input (opcional)
 *   semResultadoCadastrar {Function} callback ao clicar "+ Cadastrar..." (opcional)
 */
function criarAutocomplete(opts) {
  const {
    input, hidden, lista,
    dados: dadosEstaticos,
    url,
    campoTexto = 'nome',
    campoSecundario = 'documento',
    onSelect,
    placeholder,
    semResultadoCadastrar,
  } = opts;

  if (!input || !hidden || !lista) throw new Error('criarAutocomplete: input, hidden e lista são obrigatórios');

  let _dados = dadosEstaticos || [];
  let _debounce = null;
  let _activeIdx = -1;
  let _itensVisiveis = [];

  // ── Setup inicial ───────────────────────────────────────────────────────────

  if (placeholder) input.placeholder = placeholder;
  input.setAttribute('autocomplete', 'off');
  input.setAttribute('role', 'combobox');
  input.setAttribute('aria-expanded', 'false');
  input.setAttribute('aria-haspopup', 'listbox');
  input.setAttribute('aria-controls', lista.id || 'ac-lista');
  lista.setAttribute('role', 'listbox');

  // Estilo do dropdown
  lista.style.cssText = [
    'position:absolute', 'z-index:9999', 'left:0', 'right:0', 'top:calc(100% + 2px)',
    'margin:0', 'padding:4px 0', 'list-style:none',
    'background:#1a2332', 'border:1.5px solid #059669',
    'border-radius:8px', 'max-height:320px', 'overflow-y:auto',
    'box-shadow:0 8px 24px rgba(0,0,0,.5)'
  ].join(';');

  // Garantia de position:relative no wrapper
  const wrapper = input.closest('.fornecedor-combo') || input.parentElement;
  if (wrapper && getComputedStyle(wrapper).position === 'static') {
    wrapper.style.position = 'relative';
  }

  // ── Eventos ─────────────────────────────────────────────────────────────────

  input.addEventListener('focus', () => _abrir());

  input.addEventListener('input', () => {
    if (hidden.value) {
      hidden.value = '';  // usuário alterou texto → invalida seleção anterior
    }
    clearTimeout(_debounce);
    _debounce = setTimeout(() => _filtrar(input.value), 200);
  });

  input.addEventListener('keydown', (e) => {
    if (!_visivel()) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); _moverFoco(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); _moverFoco(-1); }
    else if (e.key === 'Enter')  { e.preventDefault(); if (_activeIdx >= 0) _selecionar(_itensVisiveis[_activeIdx]); }
    else if (e.key === 'Escape') { _fechar(); }
  });

  input.addEventListener('blur', () => setTimeout(_fechar, 160));

  document.addEventListener('click', (e) => {
    if (!lista.contains(e.target) && e.target !== input) _fechar();
  });

  // ── Busca / filtro ───────────────────────────────────────────────────────────

  async function _abrir() {
    if (url && !_dados.length) await _carregarURL('');
    _filtrar(input.value);
  }

  async function _carregarURL(q) {
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
      const res = await fetch(`${url}?q=${encodeURIComponent(q)}&limit=200`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) _dados = await res.json();
    } catch (_) {}
  }

  function _normalizar(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function _filtrar(q) {
    const qn = _normalizar(q.trim());
    let resultado;

    if (!qn) {
      resultado = [..._dados];
    } else {
      const comecam = [], contem = [];
      for (const item of _dados) {
        const nb = item.nome_busca || _normalizar(item[campoTexto] || '');
        if (nb.startsWith(qn)) comecam.push(item);
        else if (nb.includes(qn)) contem.push(item);
      }
      // JS sort já mantém a ordem de inserção (estável em V8) — dados já vêm alphabetical do backend
      resultado = [...comecam, ...contem];
    }

    _itensVisiveis = resultado;
    _activeIdx = -1;
    _renderizar(resultado, q.trim());
  }

  // ── Renderização ─────────────────────────────────────────────────────────────

  function _renderizar(itens, q) {
    lista.innerHTML = '';

    if (!itens.length) {
      const li = _criarLi();
      li.innerHTML = '<span style="color:#94a3b8;font-size:.875rem">Nenhum fornecedor encontrado</span>';
      li.style.cursor = 'default';
      li.style.minHeight = '44px';
      lista.appendChild(li);

      if (semResultadoCadastrar) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = '+ Cadastrar fornecedor';
        btn.style.cssText = 'display:block;width:100%;padding:10px 16px;background:none;border:none;color:#059669;font-size:.875rem;font-weight:600;cursor:pointer;text-align:left';
        btn.addEventListener('click', () => { _fechar(); semResultadoCadastrar(); });
        lista.appendChild(btn);
      }
    } else {
      const qn = _normalizar(q);
      itens.forEach((item, idx) => {
        const li = _criarLi();
        li.dataset.idx = idx;
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', 'false');

        const nomeTxt = item[campoTexto] || '';
        const secundario = item[campoSecundario] || '';
        const cidade = item.cidade || '';

        li.innerHTML = `
          <div style="font-size:.9rem;font-weight:500;color:#e2e8f0">${_highlight(nomeTxt, qn)}</div>
          ${secundario || cidade ? `<div style="font-size:.78rem;color:#64748b;margin-top:1px">${_esc(secundario)}${secundario && cidade ? ' · ' : ''}${_esc(cidade)}</div>` : ''}
        `;

        li.addEventListener('mousedown', (e) => { e.preventDefault(); _selecionar(item); });
        li.addEventListener('mousemove', () => { _activeIdx = idx; _destacar(); });
        lista.appendChild(li);
      });
    }

    _mostrarLista();
  }

  function _criarLi() {
    const li = document.createElement('li');
    li.style.cssText = 'padding:10px 16px;cursor:pointer;min-height:44px;display:flex;flex-direction:column;justify-content:center;border-radius:4px;margin:1px 4px';
    return li;
  }

  function _destacar() {
    lista.querySelectorAll('li[role="option"]').forEach((li, i) => {
      const ativo = i === _activeIdx;
      li.style.background = ativo ? '#059669' : '';
      li.style.color = ativo ? '#fff' : '';
      li.setAttribute('aria-selected', String(ativo));
      if (ativo) li.querySelectorAll('div').forEach(d => d.style.color = ativo ? '#fff' : '');
    });
  }

  function _moverFoco(dir) {
    const max = lista.querySelectorAll('li[role="option"]').length - 1;
    _activeIdx = Math.max(0, Math.min(_activeIdx + dir, max));
    _destacar();
    lista.querySelectorAll('li[role="option"]')[_activeIdx]?.scrollIntoView({ block: 'nearest' });
  }

  function _highlight(texto, qn) {
    if (!qn) return _esc(texto);
    const tn = _normalizar(texto);
    const idx = tn.indexOf(qn);
    if (idx < 0) return _esc(texto);
    return _esc(texto.slice(0, idx))
      + `<strong>${_esc(texto.slice(idx, idx + qn.length))}</strong>`
      + _esc(texto.slice(idx + qn.length));
  }

  function _esc(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ── Seleção ───────────────────────────────────────────────────────────────────

  function _selecionar(item) {
    input.value = item[campoTexto] || '';
    hidden.value = item.id;
    _fechar();
    if (onSelect) onSelect(item);
  }

  // ── Abertura / fechamento ─────────────────────────────────────────────────────

  function _mostrarLista() {
    lista.hidden = false;
    lista.style.display = '';
    input.setAttribute('aria-expanded', 'true');
  }

  function _fechar() {
    lista.hidden = true;
    lista.style.display = 'none';
    input.setAttribute('aria-expanded', 'false');
    _activeIdx = -1;
  }

  function _visivel() {
    return !lista.hidden;
  }

  // ── API pública ───────────────────────────────────────────────────────────────

  return {
    setDados(novosDados) {
      _dados = novosDados || [];
    },
    setValor(id, texto) {
      hidden.value = id;
      input.value = texto || '';
    },
    limpar() {
      hidden.value = '';
      input.value = '';
      _fechar();
    },
    getSelecionado() {
      return hidden.value ? _dados.find(d => String(d.id) === String(hidden.value)) || null : null;
    },
    focar() {
      input.focus();
    },
  };
}

if (typeof module !== 'undefined' && module.exports) module.exports = criarAutocomplete;
else window.criarAutocomplete = criarAutocomplete;
