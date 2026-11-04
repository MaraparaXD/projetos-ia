# TramontoSec AI — Red Team Agent v0.4 (primeira especialização)

**Estado:** protótipo de análise **passiva** de evidências já coletadas e sanitizadas. Não realiza varreduras de rede, exploração, autenticações, testes contra produção ou correções. Acesso autorizado à infraestrutura não é solicitado nem utilizado pelo código.

## Problema que resolve

A experiência de auditoria de infraestrutura demonstrou que configuração observada, exposição pública, exploração e incidente são conceitos diferentes. Este perfil recebe apenas metadados estruturados, sob escopo declarado, e gera hipóteses condicionais com contraprovas a verificar e revisão obrigatória por auditor humano.

A implementação acrescenta a ferramenta `analyze_infra` ao agente Red, preservando `analyze_recon`, Static, Blue, SQLite, CLI, Ollama local opcional e as cinco etapas Tramonto.

## Entrada v1

JSON com `schema: tramontosec.infra.v1`, `synthetic: bool` e `assets` (1–50). Cada `asset` precisa coincidir com o escopo autorizado no projeto. Campos opcionais: `network`, `auth`, `services`, `availability`, `access`. Valores são enumerados e numéricos, sem logs brutos, comentários livres, IPs, credenciais, URLs ou caminhos. A ausência de um dado é representada como `unknown`, não como `no`.

Um exemplo **inteiramente fictício** está em `examples/infra.synthetic.json`. Seus nomes, números e configurações não descrevem a VPS TechSIGAS.

## Como experimentar

No diretório `agents/tramontosec-ai`:

```powershell
python -m tramontosec --workspace "$env:LOCALAPPDATA\TramontoSec-Lab" project-create --project redlab --name "Red Lab" --objective "Revisar exposições passivas" --asset lab.example.invalid --synthetic --ack-authorized
python -m tramontosec --workspace "$env:LOCALAPPDATA\TramontoSec-Lab" evidence-import --project redlab --tool infra --file examples/infra.synthetic.json --ack-redacted-input
```

Depois siga as instruções de `DEMO.md` para atestar humanamente `adequacao`, `verificacao` e `preparacao` e executar `plan --agent red` seguido de `run`. As hipóteses começam como **candidatas**, não confirmadas.

## Hipóteses cobertas no primeiro incremento

- Política de entrada permissiva com borda não comprovada.
- Login administrativo root por senha, com ressalva de pré-condições.
- Publicação de interface de gestão e possível impacto do socket Docker.
- Publicação de API de objetos S3 sem presumir acesso indevido.
- Builds privilegiados, sem alegar escape de contêiner.
- Ponto único de falha sem recuperação validada.
- Alto volume de falhas de autenticação sem alegar invasão.

O limiar de falhas é uma **heurística inicial para triagem**, não um detector estatístico validado. Não usar a saída para bloquear IPs ou agir automaticamente.

## Metodologia e pesquisa

Adequação e Verificação estabelecem escopo e permissões; Preparação valida as evidências; Execução executa **apenas a análise offline**; Finalização depende da apreciação humana. Não se deve atribuir superioridade científica a este incremento. O trabalho do Codex na VPS não é prova de capacidades executadas por este agente. Futuros experimentos devem usar cenários sintéticos, gabaritos humanos e métricas de precisão e cobertura.
