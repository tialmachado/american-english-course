/* Flashcards SRS page: shows decks overview + daily review queue. */

const STATE = {
  course_id: null,
  queue: [],
  index: 0,
  revealed: false,
  reviewed_today: 0,
};

function fmtNextInterval(quality, current) {
  // Display estimate of the next interval before the user clicks the button.
  // Mirrors the server-side SM-2 update.
  const ease = current.ease_factor || 2.5;
  const streak = current.streak || 0;
  if (quality < 3) return "1 min";
  let days;
  if (streak === 0) days = 1;
  else if (streak === 1) days = 6;
  else days = Math.round((current.interval_days || 0) * ease);
  if (days < 1) return "1 dia";
  if (days === 1) return "1 dia";
  return `${days} dias`;
}

export async function renderFlashcards(main) {
  main.innerHTML = `<div class="loading">Carregando…</div>`;
  const decks = await (await fetch("/api/flashcards/decks")).json();
  if (!decks.decks.length) {
    main.innerHTML = `
      <h2>Flashcards</h2>
      <div class="empty-state">
        <p>Nenhum deck disponível ainda.</p>
        <p class="muted">Gere os cards rodando:<br>
          <code>./.venv/bin/python scripts/build_flashcards.py</code></p>
      </div>`;
    return;
  }

  main.innerHTML = `
    <h2 style="margin-bottom:6px;">Flashcards <span class="muted" style="font-size:13px;font-weight:400;">— revisão espaçada (SM-2)</span></h2>
    <details class="fc-howto">
      <summary>Como funciona?</summary>
      <ol>
        <li>Aparece a palavra/frase em <strong>inglês</strong>. Você tenta lembrar do significado (em silêncio).</li>
        <li>Clica em <strong>"Mostrar resposta"</strong> e vê a tradução em pt-BR.</li>
        <li>Compara o que pensou com a tradução e escolhe um dos 4 botões:
          <ul>
            <li><strong>Errou</strong> — não lembrou. Card volta em 1 min.</li>
            <li><strong>Difícil</strong> — lembrou com esforço. Volta amanhã.</li>
            <li><strong>OK</strong> — lembrou. Volta em poucos dias.</li>
            <li><strong>Fácil</strong> — instantâneo. Volta em uma semana.</li>
          </ul>
        </li>
        <li>O sistema espaça as próximas revisões. Palavras que você sabe somem da fila por semanas. As que erra ficam voltando.</li>
      </ol>
    </details>
    <div class="dash-grid" id="fc-decks"></div>
    <div id="fc-area"></div>
  `;
  const decksEl = main.querySelector("#fc-decks");
  for (const d of decks.decks) {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.style.cssText += ";cursor:pointer;";
    card.innerHTML = `
      <div class="label">${d.course_id}</div>
      <div class="value">${d.due}<small> devidos</small></div>
      <div class="muted" style="font-size:12px;margin-top:4px;">
        ${d.learned} aprendidos · ${d.new} novos · ${d.total} total
      </div>
    `;
    card.onclick = () => startReview(main, d.course_id);
    decksEl.appendChild(card);
  }
}

async function startReview(main, course_id) {
  STATE.course_id = course_id;
  STATE.queue = [];
  STATE.index = 0;
  STATE.reviewed_today = 0;
  STATE.revealed = false;
  await fetchQueue();
  renderCurrent(main);
}

async function fetchQueue() {
  const res = await fetch(`/api/flashcards/due?course_id=${STATE.course_id}&limit=20`);
  const data = await res.json();
  STATE.queue = data.cards || [];
  STATE.index = 0;
  STATE.revealed = false;
}

function renderCurrent(main) {
  const area = main.querySelector("#fc-area");
  if (!area) return;
  if (STATE.index >= STATE.queue.length) {
    if (STATE.reviewed_today === 0) {
      area.innerHTML = `
        <div class="stat-card" style="text-align:center;padding:40px;">
          <h3 style="margin-bottom:8px;">Nada por revisar agora 🎉</h3>
          <p class="muted">Volte mais tarde — novos cartões e revisões aparecem conforme o agendamento.</p>
        </div>`;
    } else {
      area.innerHTML = `
        <div class="stat-card" style="text-align:center;padding:40px;">
          <h3 style="margin-bottom:8px;">Sessão concluída 💪</h3>
          <p class="muted">${STATE.reviewed_today} cartões revisados nesta sessão.</p>
          <button class="primary" id="fc-again" style="margin-top:12px;">Buscar mais</button>
        </div>`;
      area.querySelector("#fc-again").onclick = async () => {
        await fetchQueue();
        STATE.reviewed_today = 0;
        renderCurrent(main);
      };
    }
    return;
  }
  const card = STATE.queue[STATE.index];
  area.innerHTML = `
    <div class="flashcard">
      <div class="fc-meta">
        <span>Cartão ${STATE.index + 1} de ${STATE.queue.length}</span>
        <span class="muted">${card.lesson_code} · ${card.is_new ? "NOVO" : `streak ${card.streak}`}</span>
      </div>
      <div class="fc-front">${escape(card.front)}</div>
      <div class="fc-back ${STATE.revealed ? 'show' : ''}">
        ${card.back ? `<div class="fc-def">${escape(card.back)}</div>` : ""}
        ${card.example ? `<div class="fc-example">"${escape(card.example)}"</div>` : ""}
        ${!card.back && !card.example ? `<div class="fc-def muted" style="font-style:italic;">Sem definição extraída. Avalie como você se saiu lembrando.</div>` : ""}
      </div>
      <div class="fc-actions">
        ${!STATE.revealed ? `
          <button class="primary" id="fc-reveal">Mostrar resposta</button>
        ` : `
          <button class="fc-grade" data-q="0">Errou<br><small>1 min</small></button>
          <button class="fc-grade" data-q="3">Difícil<br><small>${fmtNextInterval(3, card)}</small></button>
          <button class="fc-grade" data-q="4">OK<br><small>${fmtNextInterval(4, card)}</small></button>
          <button class="fc-grade" data-q="5">Fácil<br><small>${fmtNextInterval(5, card)}</small></button>
        `}
      </div>
    </div>
  `;
  if (!STATE.revealed) {
    area.querySelector("#fc-reveal").onclick = () => {
      STATE.revealed = true;
      renderCurrent(main);
    };
  } else {
    area.querySelectorAll(".fc-grade").forEach((btn) => {
      btn.onclick = async () => {
        const q = parseInt(btn.dataset.q);
        await fetch("/api/flashcards/review", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({card_id: card.id, quality: q}),
        });
        STATE.index++;
        STATE.revealed = false;
        STATE.reviewed_today++;
        renderCurrent(main);
      };
    });
  }
}

function escape(s) {
  return String(s).replace(/[&<>"']/g, c => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]
  ));
}
