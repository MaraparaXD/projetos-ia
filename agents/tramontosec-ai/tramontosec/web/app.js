"use strict";
const $ = (id) => document.getElementById(id);
const profileNames = {
  red: "Red Team",
  static: "Análise estática",
  blue: "Blue Team",
};
const stageNames = {
  adequacao: "Adequação",
  verificacao: "Verificação",
  preparacao: "Preparação",
  execucao: "Execução",
  finalizacao: "Finalização",
};
const statusNames = {
  candidate: "Candidata",
  in_review: "Em revisão",
  accepted: "Aceita pelo auditor",
  rejected: "Rejeitada",
  planned: "Planejada",
  running: "Em execução",
  completed: "Concluída",
  failed: "Falhou",
  interrupted: "Interrompida",
  cancelled: "Cancelada",
};
const eventNames = {
  project_created: "Projeto criado",
  evidence_imported: "Evidência importada",
  plan_created: "Plano registrado",
  task_started: "Especialista iniciado",
  human_review_requested: "Revisão humana solicitada",
  human_decision: "Decisão humana registrada",
  stage_attested: "Etapa atestada",
  task_failed: "Tarefa falhou",
  task_cancelled: "Tarefa cancelada",
  report_exported: "Relatório exportado",
  interrupted_tasks_detected: "Interrupção identificada",
};
let current = null,
  selected = null,
  csrf = "",
  activeView = "overview",
  requestVersion = 0;
const node = (tag, text, className) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
};
function message(text = "", error = false) {
  $("message").textContent = text;
  $("message").classList.toggle("error", error);
}
async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    let reason =
      "Não foi possível carregar os dados. Use Atualizar para tentar novamente.";
    try {
      reason = (await response.json()).error || reason;
    } catch {}
    throw new Error(reason);
  }
  return response;
}
function badge(status) {
  return node(
    "span",
    statusNames[status] || status,
    "badge " +
      ({ in_review: "review", accepted: "accepted", rejected: "rejected" }[
        status
      ] || ""),
  );
}
function showView(name) {
  activeView = name;
  document
    .querySelectorAll(".view")
    .forEach((el) => (el.hidden = el.id !== name + "-view"));
  document.querySelectorAll(".nav-item").forEach((el) => {
    const active = el.dataset.view === name;
    el.classList.toggle("active", active);
    if (active) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
}
document
  .querySelectorAll(".nav-item")
  .forEach((el) =>
    el.addEventListener("click", () => showView(el.dataset.view)),
  );
function evidenceBlock(e) {
  const block = node("div", undefined, "evidence-entry");
  const payload = e.payload;
  block.append(
    node(
      "p",
      e.kind === "scanner"
        ? "Análise: " + payload.tool
        : e.kind === "recon"
          ? "Reconhecimento passivo"
          : "Baseline Git",
    ),
  );
  if (e.kind === "scanner") {
    payload.alerts
      .slice(0, 30)
      .forEach((a) =>
        block.append(
          node("p", `${a.location}:${a.line || "?"} — ${a.rule_id}`),
        ),
      );
    block.append(node("p", "Commit: " + (payload.commit || "não informado")));
    if (payload.alerts.length > 30)
      block.append(node("p", "Mais alertas disponíveis pela CLI."));
  } else if (e.kind === "recon")
    payload.assets.forEach((a) =>
      block.append(
        node(
          "p",
          `${a.asset} | Serviços: ${a.services.join(", ") || "não informados"} | Controles declarados: ${a.controls.join(", ") || "não informados"}`,
        ),
      ),
    );
  else
    block.append(
      node(
        "p",
        `HEAD ${payload.head} | Árvore limpa: ${payload.clean ? "sim" : "não"}`,
      ),
    );
  block.append(
    node("p", "SHA-256: " + e.sha256, "digest"),
    node("p", "Evidência: " + e.id, "digest"),
  );
  return block;
}
function selectFinding(h, scroll = false) {
  selected = h.id;
  $("detail").hidden = false;
  $("review-panel").hidden = false;
  $("selected-title").textContent = h.title;
  $("evidence-detail").replaceChildren(
    ...current.evidence
      .filter((e) => h.evidence.includes(e.id))
      .map(evidenceBlock),
  );
  $("uncertainty").textContent = h.uncertainty;
  $("controls").replaceChildren(...h.controls.map((c) => node("li", c)));
  $("blue-advice").replaceChildren();
  const advice = current.recommendations
    .filter((r) => r.hypothesis_id === h.id)
    .at(-1);
  if (advice) {
    const r = advice.payload;
    $("blue-advice").append(
      node("h3", "Revisão Blue Team"),
      node("p", r.mitigation),
      node("p", "Como validar: " + r.validation),
      node("p", "Resposta a incidente: " + r.incident_response),
    );
  }
  $("last-decision").textContent = h.reviewer
    ? `${statusNames[h.status]} por ${h.reviewer}. Justificativa: ${h.reason}`
    : "Nenhuma decisão humana registrada para esta hipótese.";
  $("reason").value = "";
  $("ack").checked = false;
  $("decision").value = "in_review";
  const finalized = current.stages.some(
    (s) => s.name === "finalizacao" && s.status === "completed",
  );
  $("review-lock").hidden = !finalized;
  $("review-form")
    .querySelectorAll("input,select,textarea,button")
    .forEach((el) => (el.disabled = finalized));
  document.querySelectorAll("#findings tr").forEach((row) => {
    const active = row.dataset.id === h.id;
    row.classList.toggle("selected-row", active);
    row.querySelector("button").setAttribute("aria-expanded", String(active));
  });
  if (scroll) {
    $("detail-title").focus({ preventScroll: true });
    $("detail").scrollIntoView({
      block: "start",
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
  }
}
function render(data) {
  current = data;
  const p = data.project;
  $("project-title").textContent = p.name;
  document.title = p.name + " — TramontoSec AI";
  $("objective").textContent = p.objective;
  $("notice").hidden = false;
  $("notice").replaceChildren(
    node(
      "strong",
      p.synthetic
        ? "Demonstração sintética. "
        : "Avaliação local confidencial. ",
    ),
    document.createTextNode(
      p.synthetic
        ? "Dados fictícios. Nenhum sistema real foi acessado."
        : "Escopo autorizado: " + p.scope.assets.join(", "),
    ),
  );
  $("stages").replaceChildren();
  const firstPending = data.stages.findIndex((s) => s.status !== "completed");
  data.stages.forEach((s, i) => {
    const li = node(
      "li",
      undefined,
      s.status === "completed"
        ? "completed"
        : i === firstPending
          ? "current"
          : "",
    );
    if (i === firstPending) li.setAttribute("aria-current", "step");
    const n = node("span", String(i + 1), "stage-number");
    const copy = node("div", stageNames[s.name], "stage-copy");
    copy.append(
      node(
        "span",
        s.status === "completed"
          ? "Revisada"
          : i === firstPending
            ? "Revisão pendente"
            : "Pendente",
      ),
    );
    li.append(n, copy);
    $("stages").append(li);
  });
  $("finding-count").textContent = String(data.hypotheses.length);
  $("findings").replaceChildren();
  $("no-findings").hidden = Boolean(data.hypotheses.length);
  data.hypotheses.forEach((h) => {
    const tr = node("tr");
    tr.dataset.id = h.id;
    const action = node("button", "Ver evidências");
    action.type = "button";
    action.setAttribute("aria-controls", "detail");
    action.setAttribute("aria-expanded", "false");
    action.setAttribute("aria-label", "Ver evidências: " + h.title);
    action.addEventListener("click", () => selectFinding(h, true));
    const state = node("td"),
      cell = node("td");
    state.append(badge(h.status));
    cell.append(action);
    tr.append(
      node("td", h.title),
      node("td", h.profiles.map((p) => profileNames[p]).join(", ")),
      state,
      cell,
    );
    $("findings").append(tr);
  });
  $("specialists").replaceChildren();
  Object.entries(profileNames).forEach(([profile, label]) => {
    const task = data.tasks.filter((t) => t.profile === profile).at(-1);
    const li = node("li");
    li.append(node("span", label), badge(task?.status || "Não planejada"));
    $("specialists").append(li);
  });
  const modes = data.tasks.map((t) => t.output?.mode).filter(Boolean),
    assisted = modes.includes("local_llm_assisted"),
    fallback = modes.includes("deterministic_fallback");
  $("processing-mode").textContent = assisted
    ? "Assistência de modelo local"
    : "Processamento determinístico";
  $("model-note").textContent = assisted
    ? "Inferência local registrada. Sugestões exigem revisão humana."
    : fallback
      ? "Provedor indisponível ou inválido. Regras determinísticas preservadas."
      : "Sem modelo local habilitado. Não houve inferência de IA.";
  $("evidence-count").textContent = String(data.evidence.length);
  $("all-evidence").replaceChildren(...data.evidence.map(evidenceBlock));
  if (!data.evidence.length)
    $("all-evidence").append(
      node("p", "Importe evidências sanitizadas pela CLI.", "subtle"),
    );
  $("events").replaceChildren();
  [...data.runtime_events].reverse().forEach((e) => {
    const li = node("li"),
      time = node(
        "time",
        new Intl.DateTimeFormat("pt-BR", {
          dateStyle: "short",
          timeStyle: "short",
        }).format(new Date(e.at)),
      );
    time.dateTime = e.at;
    const body = node("div");
    body.append(node("strong", eventNames[e.verb] || e.verb));
    const d = e.details;
    const details = [
      d.profile ? profileNames[d.profile] : "",
      d.stage ? stageNames[d.stage] : "",
      d.reviewer || "",
      d.reason || "",
      d.decision ? statusNames[d.decision] : "",
      {
        deterministic: "Análise determinística",
        deterministic_fallback: "Fallback determinístico",
        local_llm_assisted: "Assistência de modelo local",
      }[d.mode] || "",
    ]
      .filter(Boolean)
      .join(" · ");
    if (details) body.append(node("p", details));
    li.append(time, body);
    $("events").append(li);
  });
  $("detail").hidden = true;
  $("review-panel").hidden = true;
  if (data.hypotheses.length)
    selectFinding(
      data.hypotheses.find((h) => h.id === selected) || data.hypotheses[0],
    );
  $("export").disabled = false;
  $("empty").hidden = true;
  $("audit-content").hidden = false;
  showView(activeView);
}
async function loadProject(id) {
  const version = ++requestVersion;
  current = null;
  $("audit-content").hidden = true;
  message();
  $("export").disabled = true;
  try {
    const data = await (
      await api("/api/project?project=" + encodeURIComponent(id))
    ).json();
    if (version !== requestVersion) return;
    render(data);
  } catch (e) {
    if (version !== requestVersion) return;
    $("audit-content").hidden = true;
    message(e.message, true);
  }
}
async function loadProjects() {
  $("refresh").disabled = true;
  try {
    const result = await (await api("/api/projects")).json();
    csrf = result.csrf;
    const previous = $("project-select").value;
    $("project-select").replaceChildren(
      ...result.projects.map((p) => {
        const o = node("option", p.name + (p.synthetic ? " (sintético)" : ""));
        o.value = p.id;
        return o;
      }),
    );
    if (result.projects.length) {
      if (result.projects.some((p) => p.id === previous))
        $("project-select").value = previous;
      await loadProject($("project-select").value);
    } else {
      $("empty").hidden = false;
      $("audit-content").hidden = true;
      $("project-title").textContent = "Auditorias locais";
      $("project-select").append(node("option", "Nenhum projeto"));
      $("export").disabled = true;
    }
  } catch (e) {
    message(e.message, true);
  } finally {
    $("refresh").disabled = false;
  }
}
$("project-select").addEventListener("change", () => {
  selected = null;
  loadProject($("project-select").value);
});
$("refresh").addEventListener("click", loadProjects);
$("export").addEventListener("click", async () => {
  if (!current) return;
  const project = current.project.id;
  try {
    const response = await api(
      "/api/report?project=" + encodeURIComponent(project),
    );
    const blob = await response.blob(),
      url = URL.createObjectURL(blob),
      link = node("a");
    link.href = url;
    link.download = project + "-tramonto-preliminar.md";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message("Relatório exportado. As etapas pendentes continuam registradas.");
  } catch (e) {
    message(e.message, true);
  }
});
$("review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selected || !current) return;
  if ($("decision").value === "accepted" && !$("ack").checked) {
    message(
      "Para aceitar, confirme a conferência independente das evidências.",
      true,
    );
    $("ack").focus();
    return;
  }
  $("save-review").disabled = true;
  const project = current.project.id;
  try {
    await api("/api/review", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        project,
        id: selected,
        decision: $("decision").value,
        reviewer: $("reviewer").value,
        reason: $("reason").value,
        ack: $("ack").checked,
      }),
    });
    if (current?.project.id === project) await loadProject(project);
    message("Decisão registrada no histórico da avaliação.");
  } catch (e) {
    message(e.message, true);
  } finally {
    $("save-review").disabled = false;
  }
});
(async () => {
  try {
    const token = new URLSearchParams(location.hash.slice(1)).get("session");
    if (token) {
      history.replaceState(null, "", location.pathname);
      const response = await api("/api/session", {
        method: "POST",
        headers: { "X-Local-Token": token },
      });
      csrf = (await response.json()).csrf;
    }
    await loadProjects();
  } catch (e) {
    message(e.message, true);
  }
})();
