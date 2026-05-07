# 3. Pontos de Melhoria em Agentes e Skills

← [Voltar ao índice](index.md)

---

## 3.1 Agentes acima do limite de ~200 linhas

O `CLAUDE.md` estabelece "Max ~200 lines per agent; move reference material to skills".
Quatro agentes excedem:

| Agente | Linhas | Excesso | Material candidato a virar skill |
|--------|--------|---------|----------------------------------|
| `setup-assistant.md` | 404 | +204 | Configuração de Graphify, Issue Tracker matrix |
| `frontend-developer.md` | 331 | +131 | Detecção de stack (React/Vue/Svelte), conventions de routing |
| `database-specialist.md` | 313 | +113 | Tabela de comparação de bancos (relacionais vs document) |
| `backend-developer.md` | 286 | +86 | Convenções REST + GraphQL hoje inline |

> **Fingerprints:** `agent-setup-assistant-size`, `agent-frontend-developer-size`, `agent-database-specialist-size`, `agent-backend-developer-size`

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Cada agente carrega apenas o que precisa; agentes mais leves no contexto |
| **Positivo** | Reusabilidade: a tabela de bancos serve `database-specialist` mas também `software-architect` |
| **Negativo** | Trabalho de migração; risco de quebrar referências (mitigável com `orphan-skill-scan`) |
| **Negativo** | Aumenta latência de "skill loading" em 1 round se o agente passa a precisar carregar uma skill nova por sessão |

## 3.2 Skills ausentes de alto valor

A audiência alvo do projeto é um time completo de software, mas algumas skills
recorrentes em times reais não existem:

| Skill faltante | Justificativa | Fingerprint |
|----------------|---------------|-------------|
| `incident-response` (runbook + post-mortem) | Hoje o `devops-specialist` cobre deploy mas não há padrão de incidente | `skill-add-incident-response` |
| `feature-flags` (LaunchDarkly, Unleash, Flagsmith) | Padrão moderno; não há skill citável | `skill-add-feature-flags` |
| `observability/SLO-SLI` | Hoje só há `monitoring/SKILL.md` (Prometheus/Loki); falta camada de SLO | `skill-add-observability-slo` |
| `load-testing` (k6, Artillery, Locust) | Testes de carga não estão cobertos pelo `test-pyramid` ou `test-strategy` | `skill-add-load-testing` |

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Cobre lacunas reais de operação em produção |
| **Positivo** | Reduz dependência de "improviso" do agente em cenários comuns |
| **Negativo** | Manutenção: 4 skills novos para serem versionados |
| **Negativo** | Risco de skills "esquecidos" (mitigado pelo `orphan-skill-scan`) |

## 3.3 Skill duplicada ou potencialmente fundível

`skills/integrations/database-multitenancy/SKILL.md` é referenciada **duas vezes** na
mesma tabela do `database-specialist.md` (uma para RLS, outra para `pgvector`). Isso
sugere que a skill tenta cobrir dois temas distintos. Avaliar se vale a pena dividir
em `database-multitenancy` e `database-vector`.

| Impacto | Detalhe |
|---------|---------|
| **Positivo** | Skills mais coesas; carregamento mais barato (não traz vector quando o caso é só RLS) |
| **Negativo** | Mais arquivos para gerenciar; pode gerar fragmentação se houver overlap |

## 3.4 Reforço da política de comentários em mais agentes

`comments-policy` é carregada em 9 agentes. Falta carregamento em `software-architect`,
`product-analyst`, `setup-assistant`, `technical-writer`, `qa-specialist`, mesmo que a
política seja útil quando esses agentes geram código exemplificativo (templates,
trechos em ADRs, snippets em runbooks).

**Sugestão:** Avaliar se a `comments-policy` cabe como **skill universal**
(carregada via `project-context`) em vez de listada por agente.
