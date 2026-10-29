# Demonstração acadêmica fictícia

Sem contato com terceiros. Arquivos e repo Git são gerados no workspace local,
fora do monorepositório. Todo ativo usa domínio reservado .invalid.

```powershell
$ws = Join-Path $env:LOCALAPPDATA 'TramontoSec-Demo'
python -m tramontosec --workspace "$ws" demo --project aurora-demo --ack-synthetic-review
python -m tramontosec --workspace "$ws" audit --project aurora-demo
python -m tramontosec --workspace "$ws" history --project aurora-demo
python -m tramontosec --workspace "$ws" dashboard --port 8765
```

O comando cria avaliação, escopo, baseline Git real do repo fictício, recon e
Semgrep sintéticos e AST sem executar código. Atesta três etapas como exercício
fictício, planeja e executa Red → Static → Blue. Com ack-synthetic-review,
registra decisão in_review atribuída ao auditor de demonstração; sem a opção,
essa decisão fica pendente. Nunca aceita automaticamente hipóteses.

Esperado: três tarefas, três hipóteses (HTTP, SSH, execução dinâmica),
recomendações Blue e relatório preliminar. Semgrep e AST equivalentes são
associados, sem alegar validação independente. Execução/Finalização pendentes.

## Decisão do auditor

Copie o ID exibido por audit, ou use o dashboard:

```powershell
python -m tramontosec --workspace "$ws" finding-review --project aurora-demo --id ID --decision in_review --reviewer "Auditor acadêmico" --reason "Conferir controles e falso positivo"
python -m tramontosec --workspace "$ws" report --project aurora-demo
```

Aceitar exige ack-reviewed-evidence, auditor e justificativa. Após decisões
accepted/rejected para todas as hipóteses e tarefas resolvidas, pode atestar
execucao e finalizacao com stage. Exportar não conclui avaliação.

## Fluxo manual

```powershell
python -m tramontosec --workspace "$ws" project-create --project manual-demo --name "Laboratório" --objective "Revisar dados fictícios" --asset app.example.invalid --synthetic --ack-authorized
python -m tramontosec --workspace "$ws" evidence-import --project manual-demo --tool recon --file .\examples\recon.synthetic.json --ack-redacted-input
python -m tramontosec --workspace "$ws" evidence-import --project manual-demo --tool semgrep --file .\examples\semgrep.synthetic.json --ack-redacted-input
python -m tramontosec --workspace "$ws" stage --project manual-demo --name adequacao --reviewer "Auditor" --reason "Escopo fictício conferido" --ack-human
python -m tramontosec --workspace "$ws" stage --project manual-demo --name verificacao --reviewer "Auditor" --reason "Autorização e guarda conferidas" --ack-human
python -m tramontosec --workspace "$ws" stage --project manual-demo --name preparacao --reviewer "Auditor" --reason "Evidências conferidas; sem repo no escopo" --ack-human
python -m tramontosec --workspace "$ws" plan --project manual-demo --agent red --agent static --agent blue
python -m tramontosec --workspace "$ws" run --project manual-demo
python -m tramontosec --workspace "$ws" report --project manual-demo
```

Análise local: informe --repo na criação, registre baseline com SHA-1 completo
e use analyze-local --path src/demo.py. Use somente repo fictício no exercício.
Para repetir, escolha outro --project. examples/demo_findings.json é a fixture
legada do ZIP, com baseline de zeros deliberadamente inválida.
