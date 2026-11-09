"use strict";
// DOM mínimo em memória: verificar texto e ambas as origens sem navegador/rede.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

class Element {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.classList = { toggle() {} };
  }
  set innerHTML(_) { throw new Error("HTML dinâmico não permitido"); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  addEventListener() {}
  querySelectorAll() { return []; }
  setAttribute() {}
}
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  },
  createElement(tag) { return new Element(tag); },
  querySelectorAll() { return []; },
};
const rec = (origin, mitigation) => ({
  hypothesis_id: "h1",
  payload: { origin, mitigation, validation: "Conferir", incident_response: "Preservar" },
});
const fixture = {
  hypotheses: [{
    id: "h1", title: "Sintético", evidence: [], controls: ["Conferir controle"],
    uncertainty: "Pendente", origin: "rule", status: "candidate", reviewer: null,
    reasoning_trace: [{ tool: "get_alerts", reason: "Conferir",
                       model_note: "<img onerror=executed=true>" }],
  }],
  evidence: [],
  stages: [{ name: "finalizacao", status: "pending" }],
  recommendations: [
    rec(undefined, "Baseline legado"),
    rec("llm", "<script>executed=true</script>"),
    rec("rule", "Baseline mais recente"),
  ],
};
const source = fs.readFileSync(path.join(__dirname, "../tramontosec/web/app.js"), "utf8");
const startup = source.lastIndexOf("(async () => {");
assert(startup > 0, "Entrada do dashboard identificada para impedir rede no teste");
const context = vm.createContext({ document, fixture });
vm.runInContext(source.slice(0, startup), context);
vm.runInContext("current = fixture; selectFinding(fixture.hypotheses[0]);", context);
const flatten = (element) =>
  element.textContent + element.children.map(flatten).join(" ");
const advice = elements.get("blue-advice");
assert.equal(advice.children.filter((child) => child.tag === "h3").length, 2);
assert.match(flatten(advice), /Baseline mais recente/);
assert.doesNotMatch(flatten(advice), /Baseline legado/);
assert.match(flatten(advice), /<script>executed=true<\/script>/);
assert.match(flatten(advice), /sugestão de modelo não verificada/);
assert.match(elements.get("uncertainty").textContent, /nota do modelo \(não verificada\)/);
assert.equal(context.executed, undefined);
fixture.recommendations.pop();
fixture.hypotheses[0].reasoning_trace[0].model_note = null;
vm.runInContext("selectFinding(fixture.hypotheses[0]);", context);
assert.match(flatten(advice), /Baseline legado/);
assert.doesNotMatch(elements.get("uncertainty").textContent, /nota do modelo/);
console.log("Dashboard DOM: origens, legado e model_note exibidos com textContent; sem HTML executado.");
