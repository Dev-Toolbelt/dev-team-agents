# Métricas de Uso DevTeam Agents — Últimos 20 Dias

**Janela:** 2026-07-25 22:07 → 2026-08-14 22:07, horário de `America/Sao_Paulo` (20 dias)
**Primeiro evento observado na janela:** 2026-07-26 09:34 (`America/Sao_Paulo`)
**Gerado em:** 2026-08-14 22:07 (`America/Sao_Paulo`)
**Fuso horário usado nas métricas de tempo:** `America/Sao_Paulo` (UTC−3)
**Total de eventos na janela:** 2.947 (métricas de agente calculadas sobre 1.659 `agent_completed` válidos — 3 eventos manuais de teste `__manual_verification_test__` excluídos de 1.662)
**ID do projeto PostHog:** 430371

---

## 0. Distribuição por tipo de evento

**Conclusão:** `agent_completed` domina o volume com 1.662 eventos (56,4%); `command_invoked` responde por apenas 11 (0,4%), o que mantém o padrão já observado no relatório anterior — o trabalho é conduzido por spawn direto de agentes, não pela camada de slash-commands.

| Evento | Ocorrências | % |
|---|---:|---:|
| **`agent_completed`** | **1.662** | **56,4%** |
| `session_end` | 1.140 | 38,7% |
| `install` | 92 | 3,1% |
| `update` | 35 | 1,2% |
| `command_invoked` | 11 | 0,4% |
| `first_install` | 7 | 0,2% |
| `agent_spawned` | 0 | 0,0% |

> `agent_spawned` **não disparou nenhuma vez** na janela. Todas as métricas de agente usam `agent_completed` como proxy.

## 1. Comandos mais chamados

**Conclusão:** `status` lidera com 3 invocações de um total de apenas 11 — amostra pequena demais para um ranking significativo, mas o dado em si é o achado: 27 dos 34 comandos canônicos não registraram nenhuma invocação (ver seção 14).

| Comando | Chamadas |
|---|---:|
| **`status`** | **3** |
| `architect` | 2 |
| `review` | 2 |
| `install` | 1 |
| `pr` | 1 |
| `push` | 1 |
| `sync-rules` | 1 |

## 2. Agentes mais invocados

**Conclusão:** `software-architect` lidera com 325 conclusões (19,6% de 1.659), seguido de perto por `frontend-developer` (288) e `backend-developer` (232) — os três somam 51,0% de toda a atividade de agentes.

| Agente | Conclusões | % |
|---|---:|---:|
| **`software-architect`** | **325** | **19,6%** |
| `frontend-developer` | 288 | 17,4% |
| `backend-developer` | 232 | 14,0% |
| `devops-specialist` | 119 | 7,2% |
| `security-specialist` | 111 | 6,7% |
| `frontend-test-specialist` | 106 | 6,4% |
| `backend-test-specialist` | 93 | 5,6% |
| `nextjs-spa-specialist` ⚠️ | 66 | 4,0% |
| `qa-specialist` | 63 | 3,8% |
| `code-reviewer` | 60 | 3,6% |
| `test-author` ⚠️ | 45 | 2,7% |
| `database-specialist` | 41 | 2,5% |
| `product-analyst` | 40 | 2,4% |
| `technical-writer` | 21 | 1,3% |
| `laravel-specialist` ⚠️ | 15 | 0,9% |
| `Explore` ⚠️ | 12 | 0,7% |
| `frontend-reviewer` | 10 | 0,6% |
| `backend-reviewer` | 8 | 0,5% |
| `ui-ux-designer` | 2 | 0,1% |
| `unknown` ⚠️ | 2 | 0,1% |

> ⚠️ = nome fora do roster canônico de `agents/*.md`. `nextjs-spa-specialist`, `laravel-specialist` e `test-author` são agentes locais de projeto ou nomes legados; `Explore` é subagente nativo do Claude Code; `unknown` indica evento sem `agent_name` resolvido.

## 3. Ranking de modelos utilizados, agrupado por provider

**Conclusão:** 100% das conclusões vieram do provider `claude`; `claude-sonnet-5` responde por 62,4% das execuções, e nenhum evento de `opencode` ou `codex` apareceu na janela.

| Provider | Modelo | Execuções | % |
|---|---|---:|---:|
| **`claude`** | **`claude-sonnet-5`** | **1.036** | **62,4%** |
| `claude` | `claude-opus-5[1m]` | 476 | 28,7% |
| `claude` | `claude-haiku-4-5-20251001` | 147 | 8,9% |

## 4. Ranking de consumo de tokens (total por agente)

**Conclusão:** `software-architect` consumiu 11,18 M tokens — 44,1% dos 25,35 M totais da janela, mais que os três agentes seguintes somados.

| Agente | Tokens totais | % | Input | Output |
|---|---:|---:|---:|---:|
| **`software-architect`** | **11.179.267** | **44,1%** | 520.623 | 10.658.644 |
| `frontend-developer` | 3.171.037 | 12,5% | 950.606 | 2.220.431 |
| `backend-developer` | 2.511.268 | 9,9% | 50.570 | 2.460.698 |
| `nextjs-spa-specialist` | 1.467.016 | 5,8% | 75.966 | 1.391.050 |
| `test-author` | 1.139.704 | 4,5% | 47.292 | 1.092.412 |
| `security-specialist` | 939.014 | 3,7% | 16.685 | 922.329 |
| `frontend-test-specialist` | 931.701 | 3,7% | 43.332 | 888.369 |
| `backend-test-specialist` | 860.049 | 3,4% | 71.586 | 788.463 |
| `qa-specialist` | 660.552 | 2,6% | 74.319 | 586.233 |
| `devops-specialist` | 655.532 | 2,6% | 83.001 | 572.531 |
| `product-analyst` | 462.980 | 1,8% | 1.440 | 461.540 |
| `database-specialist` | 430.124 | 1,7% | 3.040 | 427.084 |
| `laravel-specialist` | 398.472 | 1,6% | 17.908 | 380.564 |
| `code-reviewer` | 242.239 | 1,0% | 22.877 | 219.362 |
| `technical-writer` | 110.639 | 0,4% | 23.616 | 87.023 |
| `ui-ux-designer` | 64.708 | 0,3% | 40.596 | 24.112 |
| `backend-reviewer` | 59.268 | 0,2% | 482 | 58.786 |
| `frontend-reviewer` | 36.596 | 0,1% | 372 | 36.224 |
| `Explore` | 26.140 | 0,1% | 204 | 25.936 |
| `unknown` | 2.940 | 0,0% | 24 | 2.916 |
| **Total** | **25.349.246** | **100%** | **2.044.539** | **23.304.707** |

> **Anomalia de dados:** output representa 91,9% dos tokens totais e input apenas 8,1% — proporção invertida em relação ao consumo real esperado de um agente de código (input tipicamente domina). Ver Observações.

## 5. Agentes que mais consomem tokens em média (por invocação)

**Conclusão:** `software-architect` também lidera a média, com 34.398 tokens por invocação — 2,3× a média global de 15.281 tokens/execução.

| Agente | Média de tokens/execução | Execuções |
|---|---:|---:|
| **`software-architect`** | **34.398** | 325 |
| `ui-ux-designer` | 32.354 | 2 ⚠️ amostra baixa |
| `laravel-specialist` | 26.565 | 15 |
| `test-author` | 25.327 | 45 |
| `nextjs-spa-specialist` | 22.227 | 66 |
| `product-analyst` | 11.575 | 40 |
| `frontend-developer` | 11.011 | 288 |
| `backend-developer` | 10.824 | 232 |
| `database-specialist` | 10.491 | 41 |
| `qa-specialist` | 10.485 | 63 |
| `backend-test-specialist` | 9.248 | 93 |
| `frontend-test-specialist` | 8.790 | 106 |
| `security-specialist` | 8.460 | 111 |
| `backend-reviewer` | 7.409 | 8 |
| `devops-specialist` | 5.509 | 119 |
| `technical-writer` | 5.269 | 21 |
| `code-reviewer` | 4.037 | 60 |
| `frontend-reviewer` | 3.660 | 10 |
| `Explore` | 2.178 | 12 |
| `unknown` | 1.470 | 2 |

> **Por comando: não calculável.** O evento `command_invoked` não carrega contadores de token, e não há chave de correlação entre um `command_invoked` e os `agent_completed` que ele originou. Média por comando fica indisponível até que a telemetria emita um identificador de sessão/execução compartilhado.

## 6. Ranking de país, estado e cidade

**Conclusão:** 100% dos eventos vieram do Brasil, e 99,4% de Fortaleza/CE — a base instalada ativa na janela é essencialmente um único operador, o que limita qualquer leitura de "adoção" nos demais rankings.

### País

| País | Eventos | % |
|---|---:|---:|
| **Brasil** | **2.947** | **100,0%** |

### Estado

| Estado | Eventos | % |
|---|---:|---:|
| **Ceará** | **2.928** | **99,4%** |
| São Paulo | 19 | 0,6% |

### Cidade

| Cidade | Eventos | % |
|---|---:|---:|
| **Fortaleza** | **2.928** | **99,4%** |
| Bauru | 19 | 0,6% |

## 7. Ranking das versões usadas no período

**Conclusão:** `v2.44.0` e `v2.44.1` concentram 63,6% dos eventos — a base ativa está em dia, mas 370 eventos (12,6%) reportaram `version: unknown`, um buraco de instrumentação.

| Versão | Eventos | % |
|---|---:|---:|
| **`v2.44.0`** | **951** | **32,3%** |
| `v2.44.1` | 922 | 31,3% |
| `unknown` ⚠️ | 370 | 12,6% |
| `v2.44.2` | 228 | 7,7% |
| `v2.29.0` | 149 | 5,1% |
| `v2.39.2` | 133 | 4,5% |
| `v2.31.0` | 48 | 1,6% |
| `v2.17.3` | 20 | 0,7% |
| `v1.8.1` | 13 | 0,4% |
| `v2.15.1` | 10 | 0,3% |
| `v2.30.1` | 9 | 0,3% |
| `v1.8.2` | 8 | 0,3% |
| Outras 42 versões | 86 | 2,9% |

## 8. Modelos utilizados, agrupados por agente

**Conclusão:** nenhum agente invocou mais de um modelo na janela — o mapeamento tier → modelo está consistente. Os três agentes em Haiku (`test-author`, `laravel-specialist`, `nextjs-spa-specialist`) são todos nomes fora do roster canônico.

| Agente | Modelo(s) | Execuções |
|---|---|---:|
| `software-architect` | `claude-opus-5[1m]` | 325 |
| `security-specialist` | `claude-opus-5[1m]` | 111 |
| `product-analyst` | `claude-opus-5[1m]` | 40 |
| `frontend-developer` | `claude-sonnet-5` | 288 |
| `backend-developer` | `claude-sonnet-5` | 232 |
| `devops-specialist` | `claude-sonnet-5` | 119 |
| `frontend-test-specialist` | `claude-sonnet-5` | 106 |
| `backend-test-specialist` | `claude-sonnet-5` | 93 |
| `qa-specialist` | `claude-sonnet-5` | 63 |
| `code-reviewer` | `claude-sonnet-5` | 60 |
| `database-specialist` | `claude-sonnet-5` | 41 |
| `Explore` | `claude-sonnet-5` | 12 |
| `frontend-reviewer` | `claude-sonnet-5` | 10 |
| `backend-reviewer` | `claude-sonnet-5` | 8 |
| `ui-ux-designer` | `claude-sonnet-5` | 2 |
| `unknown` | `claude-sonnet-5` | 2 |
| `nextjs-spa-specialist` ⚠️ | `claude-haiku-4-5-20251001` | 66 |
| `test-author` ⚠️ | `claude-haiku-4-5-20251001` | 45 |
| `technical-writer` | `claude-haiku-4-5-20251001` | 21 |
| `laravel-specialist` ⚠️ | `claude-haiku-4-5-20251001` | 15 |

## 9. Dias e horários de maior uso

**Conclusão:** o uso é fortemente concentrado em quarta e quinta-feira (73,4% dos eventos) e no pico das 10h; finais de semana são praticamente inativos (41 eventos, 1,4%).

### Por dia da semana

| Dia | Eventos | % |
|---|---:|---:|
| **Quarta** | **1.130** | **38,3%** |
| Quinta | 1.033 | 35,1% |
| Sexta | 375 | 12,7% |
| Terça | 322 | 10,9% |
| Segunda | 46 | 1,6% |
| Domingo | 31 | 1,1% |
| Sábado | 10 | 0,3% |

### Por hora do dia (`America/Sao_Paulo`)

| Hora | Eventos | Hora | Eventos |
|---|---:|---|---:|
| **10h** | **376** | 18h | 100 |
| 12h | 313 | 13h | 99 |
| 15h | 256 | 23h | 97 |
| 14h | 240 | 20h | 72 |
| 17h | 224 | 21h | 69 |
| 22h | 221 | 00h | 36 |
| 07h | 188 | 08h | 29 |
| 11h | 187 | 01h | 17 |
| 16h | 166 | 04h | 14 |
| 19h | 122 | 03h | 9 |
| 09h | 111 | 02h | 1 |
| — | — | 05h–06h | 0 |

## 10. Taxa de novas instalações vs atualizações

**Conclusão:** apenas 7 dos 134 eventos da família de instalação (5,2%) foram `first_install` — a janela é dominada por reinstalações e updates da base existente, não por aquisição nova.

| Evento | Ocorrências | % da família |
|---|---:|---:|
| **`install`** | **92** | **68,7%** |
| `update` | 35 | 26,1% |
| `first_install` | 7 | 5,2% |

Todos os 35 eventos `update` reportaram `mode: manual` — **o caminho de auto-update não disparou nenhuma vez na janela.**

## 11. Volume de eventos por dia

**Conclusão:** 2.614 dos 2.947 eventos (88,7%) caem em apenas 4 dias (11–14/08); os primeiros 16 dias da janela somam 333 eventos.

| Data | Eventos | Data | Eventos |
|---|---:|---|---:|
| 2026-07-26 | 18 | 2026-08-05 | 47 |
| 2026-07-27 | 5 | 2026-08-06 | 136 |
| 2026-07-28 | 22 | 2026-08-07 | 22 |
| 2026-07-29 | 4 | 2026-08-08 | 6 |
| 2026-07-30 | 2 | 2026-08-09 | 4 |
| 2026-07-31 | 7 | 2026-08-10 | 7 |
| 2026-08-01 | 4 | 2026-08-11 | 294 |
| 2026-08-02 | 9 | **2026-08-12** | **1.079** |
| 2026-08-03 | 34 | 2026-08-13 | 895 |
| 2026-08-04 | 6 | 2026-08-14 | 346 |

## 12. Eficiência de cache

**Conclusão: não calculável nesta janela.** Os campos `cache_creation_tokens` e `cache_read_tokens` estão **nulos em 100% dos 1.662 eventos `agent_completed`** — nenhum evento reportou valor de cache, zero ou não.

| Métrica | Valor |
|---|---:|
| Eventos `agent_completed` com campos de cache preenchidos | 0 de 1.662 |
| `cache_read_tokens` agregado | — (indisponível) |
| `cache_creation_tokens` agregado | — (indisponível) |
| Razão `cache_read` / `input` | — (indisponível) |

## 13. Distribuição de fim de sessão

**Conclusão:** 97,7% dos `session_end` reportaram `stop_hook_active=false` — o hook de parada raramente está ativo no momento do encerramento.

| `stop_hook_active` | Eventos | % |
|---|---:|---:|
| **`false`** | **1.114** | **97,7%** |
| `true` | 26 | 2,3% |

## 14. Comandos e agentes nunca usados no período

**Conclusão:** 27 dos 34 comandos canônicos (79,4%) e 3 dos 18 agentes canônicos não registraram uma única invocação na janela — a cobertura do surface de comandos é o maior gap de uso do projeto.

### Comandos com zero invocações (27 de 34)

`adr` · `audit` · `backend` · `commit` · `dba` · `design` · `devops` · `docs` · `explain` · `fix` · `frontend` · `fullstack` · `health-check` · `learn` · `mobile` · `plan` · `qa` · `refactor` · `relayout` · `rule` · `security` · `seo` · `setup` · `symlinks` · `tester` · `update` · `version`

### Agentes canônicos com zero execuções (3 de 18)

`mobile-developer` · `seo-specialist` · `setup-assistant`

### Nomes observados fora do roster canônico (5)

| Nome | Execuções | Natureza provável |
|---|---:|---|
| `nextjs-spa-specialist` | 66 | agente local de projeto |
| `test-author` | 45 | nome legado (agente removido do roster) |
| `laravel-specialist` | 15 | agente local de projeto |
| `Explore` | 12 | subagente nativo do Claude Code |
| `unknown` | 2 | `agent_name` não resolvido na emissão |

## Sistema operacional (complementar)

| SO | Eventos | % |
|---|---:|---:|
| **`darwin`** | **2.735** | **92,8%** |
| `mingw64_nt-10.0-26200` | 191 | 6,5% |
| `linux` | 21 | 0,7% |

---

## Observações

- **Proporção input/output invertida.** Output responde por 23,3 M dos 25,35 M tokens (91,9%) contra 2,04 M de input (8,1%). Um agente de código real lê muito mais do que escreve — essa razão sugere que `input_tokens` está sendo subcontado (ou que `output_tokens` está agregando o total) em `scripts/helpers/telemetry-send.sh`. Enquanto isso não for verificado, todos os números absolutos de token devem ser lidos como ordem de grandeza, não como custo real.
- **Telemetria de cache totalmente ausente.** `cache_creation_tokens` e `cache_read_tokens` chegaram nulos em 1.662 de 1.662 eventos. A métrica de eficiência de cache — o sinal mais direto de reuso de contexto — está cega desde a instrumentação, não por falta de uso de cache.
- **A camada de slash-commands é praticamente invisível na telemetria.** 11 `command_invoked` contra 1.662 `agent_completed` (0,66%), e `agent_spawned` com zero eventos. Ou os comandos de fato não são usados, ou `command_invoked`/`agent_spawned` subdisparam. As duas hipóteses têm consequências muito diferentes e o dado atual não as separa.
- **Concentração extrema de origem e de tempo.** 99,4% dos eventos vêm de uma única cidade e 88,7% de apenas 4 dias corridos (11–14/08). Os rankings deste relatório descrevem o padrão de trabalho de um operador em uma sprint intensa — não adoção de produto.
- **Nomes fora do roster somaram 138 execuções (8,3%).** `test-author` (45) continua disparando apesar de não existir mais em `agents/*.md`, e `nextjs-spa-specialist`/`laravel-specialist` (81) são agentes locais de projeto. O campo `agent_name` não distingue agente do framework de agente do projeto, o que polui todos os rankings por agente.
- **`version: unknown` em 12,6% dos eventos** e 100% dos updates em `mode: manual` — o caminho de auto-update não produziu um único evento na janela.

---

## Resumo estruturado para leitura por LLMs

```yaml
janela:
  inicio: "2026-07-25T22:07:00-03:00"
  fim: "2026-08-14T22:07:00-03:00"
  primeiro_evento_observado: "2026-07-26T09:34:00-03:00"
  dias: 20
  timezone: "America/Sao_Paulo"
  projeto_posthog: 430371
  total_eventos: 2947
  agent_completed_validos: 1659
  excluidos_teste_manual: 3

eventos_por_tipo:
  agent_completed: 1662
  session_end: 1140
  install: 92
  update: 35
  command_invoked: 11
  first_install: 7
  agent_spawned: 0

top_comandos_por_chamadas:
  status: 3
  architect: 2
  review: 2
  install: 1
  pr: 1
  push: 1
  sync-rules: 1

top_agentes_por_chamadas:
  software-architect: 325
  frontend-developer: 288
  backend-developer: 232
  devops-specialist: 119
  security-specialist: 111
  frontend-test-specialist: 106
  backend-test-specialist: 93
  nextjs-spa-specialist: 66
  qa-specialist: 63
  code-reviewer: 60
  test-author: 45
  database-specialist: 41
  product-analyst: 40
  technical-writer: 21
  laravel-specialist: 15
  Explore: 12
  frontend-reviewer: 10
  backend-reviewer: 8
  ui-ux-designer: 2
  unknown: 2

modelos_por_provider:
  claude:
    claude-sonnet-5: 1036
    claude-opus-5[1m]: 476
    claude-haiku-4-5-20251001: 147

tokens_totais:
  total: 25349246
  input: 2044539
  output: 23304707
  cache_creation: null
  cache_read: null
  media_por_execucao: 15281

tokens_por_agente_total_desc:
  software-architect: 11179267
  frontend-developer: 3171037
  backend-developer: 2511268
  nextjs-spa-specialist: 1467016
  test-author: 1139704
  security-specialist: 939014
  frontend-test-specialist: 931701
  backend-test-specialist: 860049
  qa-specialist: 660552
  devops-specialist: 655532
  product-analyst: 462980
  database-specialist: 430124
  laravel-specialist: 398472
  code-reviewer: 242239
  technical-writer: 110639
  ui-ux-designer: 64708
  backend-reviewer: 59268
  frontend-reviewer: 36596
  Explore: 26140
  unknown: 2940

media_tokens_por_execucao_desc:
  software-architect: 34398
  ui-ux-designer: 32354
  laravel-specialist: 26565
  test-author: 25327
  nextjs-spa-specialist: 22227
  product-analyst: 11575
  frontend-developer: 11011
  backend-developer: 10824
  database-specialist: 10491
  qa-specialist: 10485
  backend-test-specialist: 9248
  frontend-test-specialist: 8790
  security-specialist: 8460
  backend-reviewer: 7409
  devops-specialist: 5509
  technical-writer: 5269
  code-reviewer: 4037
  frontend-reviewer: 3660
  Explore: 2178
  unknown: 1470

media_tokens_por_comando: nao_calculavel_sem_chave_de_correlacao

geografia:
  paises:
    Brasil: 2947
  estados:
    Ceara: 2928
    Sao Paulo: 19
  cidades:
    Fortaleza: 2928
    Bauru: 19

versoes_desc:
  v2.44.0: 951
  v2.44.1: 922
  unknown: 370
  v2.44.2: 228
  v2.29.0: 149
  v2.39.2: 133
  v2.31.0: 48
  v2.17.3: 20
  v1.8.1: 13
  v2.15.1: 10
  v2.30.1: 9
  v1.8.2: 8
  outras_42_versoes: 86

modelos_por_agente:
  software-architect: [claude-opus-5[1m]]
  security-specialist: [claude-opus-5[1m]]
  product-analyst: [claude-opus-5[1m]]
  frontend-developer: [claude-sonnet-5]
  backend-developer: [claude-sonnet-5]
  devops-specialist: [claude-sonnet-5]
  frontend-test-specialist: [claude-sonnet-5]
  backend-test-specialist: [claude-sonnet-5]
  qa-specialist: [claude-sonnet-5]
  code-reviewer: [claude-sonnet-5]
  database-specialist: [claude-sonnet-5]
  Explore: [claude-sonnet-5]
  frontend-reviewer: [claude-sonnet-5]
  backend-reviewer: [claude-sonnet-5]
  ui-ux-designer: [claude-sonnet-5]
  unknown: [claude-sonnet-5]
  nextjs-spa-specialist: [claude-haiku-4-5-20251001]
  test-author: [claude-haiku-4-5-20251001]
  technical-writer: [claude-haiku-4-5-20251001]
  laravel-specialist: [claude-haiku-4-5-20251001]

uso_por_dia_da_semana:
  quarta: 1130
  quinta: 1033
  sexta: 375
  terca: 322
  segunda: 46
  domingo: 31
  sabado: 10

uso_por_hora_local:
  "10": 376
  "12": 313
  "15": 256
  "14": 240
  "17": 224
  "22": 221
  "07": 188
  "11": 187
  "16": 166
  "19": 122
  "09": 111
  "18": 100
  "13": 99
  "23": 97
  "20": 72
  "21": 69
  "00": 36
  "08": 29
  "01": 17
  "04": 14
  "03": 9
  "02": 1
  "05": 0
  "06": 0

volume_por_dia:
  "2026-07-26": 18
  "2026-07-27": 5
  "2026-07-28": 22
  "2026-07-29": 4
  "2026-07-30": 2
  "2026-07-31": 7
  "2026-08-01": 4
  "2026-08-02": 9
  "2026-08-03": 34
  "2026-08-04": 6
  "2026-08-05": 47
  "2026-08-06": 136
  "2026-08-07": 22
  "2026-08-08": 6
  "2026-08-09": 4
  "2026-08-10": 7
  "2026-08-11": 294
  "2026-08-12": 1079
  "2026-08-13": 895
  "2026-08-14": 346

instalacoes_vs_atualizacoes:
  install: 92
  update: 35
  first_install: 7
  taxa_novas_instalacoes: 0.052
  update_modes:
    manual: 35
    auto: 0

eficiencia_cache: nao_calculavel_campos_nulos_em_1662_de_1662_eventos

fim_de_sessao:
  stop_hook_active_false: 1114
  stop_hook_active_true: 26

sistema_operacional:
  darwin: 2735
  mingw64_nt-10.0-26200: 191
  linux: 21

cobertura:
  comandos_canonicos: 34
  comandos_usados: 7
  comandos_sem_uso: [adr, audit, backend, commit, dba, design, devops, docs, explain, fix, frontend, fullstack, health-check, learn, mobile, plan, qa, refactor, relayout, rule, security, seo, setup, symlinks, tester, update, version]
  agentes_canonicos: 18
  agentes_usados: 15
  agentes_sem_uso: [mobile-developer, seo-specialist, setup-assistant]
  nomes_fora_do_roster:
    nextjs-spa-specialist: 66
    test-author: 45
    laravel-specialist: 15
    Explore: 12
    unknown: 2

anomalias_de_dados:
  - razao_output_input_invertida: {output_pct: 0.919, input_pct: 0.081}
  - tokens_de_cache_ausentes: {eventos_afetados: 1662, total: 1662}
  - command_invoked_subdisparo_suspeito: {command_invoked: 11, agent_completed: 1662}
  - agent_spawned_zero_eventos: true
  - version_unknown: {eventos: 370, pct: 0.126}
```
