# DevTeam Agents Usage Metrics — Last 20 Days

**Window:** 2026-07-23 17:14 → 2026-08-12 17:14, `America/Sao_Paulo` time (20 days)  
**Generated:** 2026-08-12 17:27 (`America/Sao_Paulo`)  
**Timezone used for time-based metrics:** `America/Sao_Paulo` (UTC−3)  
**Total events in window:** 1,463 (excluded 1 malformed event with null `agent_name`/`model` and 2 manual test events `__manual_verification_test__`, out of 1,466 raw rows)  
**PostHog project ID:** 430371

---

## 1. Most-called commands

**Conclusion:** only 7 `command_invoked` events fell in the window — too small a sample for a meaningful ranking (against 770 `agent_completed`), suggesting work was driven by direct agent spawns rather than the `/devteam:*` slash-command layer, or that the event under-fires.

| Command | Calls |
|---|---:|
| `architect` | 2 |
| `push` | 1 |
| `status` | 1 |
| `sync-rules` | 1 |
| `pr` | 1 |
| `review` | 1 |

## 2. Most-invoked agents

**Conclusion:** `backend-developer` leads with 181 completions (23.5% of 770 agent completions). No `agent_spawned` event appeared in the window, so `agent_completed` is used as a proxy.

| Agent | Completions | % |
|---|---:|---:|
| `backend-developer` | 181 | 23.5% |
| `frontend-developer` | 145 | 18.8% |
| `software-architect` | 90 | 11.7% |
| `security-specialist` | 70 | 9.1% |
| `devops-specialist` | 68 | 8.8% |
| `frontend-test-specialist` | 60 | 7.8% |
| `backend-test-specialist` | 51 | 6.6% |
| `test-author` ⚠️ | 44 | 5.7% |
| `qa-specialist` | 13 | 1.7% |
| `technical-writer` | 13 | 1.7% |
| `code-reviewer` | 12 | 1.6% |
| `product-analyst` | 12 | 1.6% |
| `frontend-reviewer` | 6 | 0.8% |
| `backend-reviewer` | 5 | 0.6% |

> ⚠️ `test-author` is not in the canonical agent roster (`agents/*.md`) — see section 14.

## 3. Model ranking grouped by provider

**Conclusion:** 100% of completions used the `claude` provider; `claude-sonnet-5` dominates with 541 calls (70.3%).

| Provider | Model | Calls | % |
|---|---|---:|---:|
| `claude` | `claude-sonnet-5` | 541 | 70.3% |
| `claude` | `claude-opus-5[1m]` | 172 | 22.3% |
| `claude` | `claude-haiku-4-5-20251001` | 57 | 7.4% |

## 4. Token consumption ranking

**Conclusion:** `backend-developer` is the biggest consumer at 629,631,416 tokens (27.8% of 2,261,108,291 total). Tokens = input + output + cache_creation + cache_read.

| Agent | Total tokens | % |
|---|---:|---:|
| `backend-developer` | 629,631,416 | 27.8% |
| `frontend-developer` | 377,583,113 | 16.7% |
| `test-author` | 357,672,470 | 15.8% |
| `software-architect` | 300,079,305 | 13.3% |
| `security-specialist` | 171,959,869 | 7.6% |
| `frontend-test-specialist` | 152,694,710 | 6.8% |
| `devops-specialist` | 112,347,593 | 5.0% |
| `backend-test-specialist` | 52,338,041 | 2.3% |
| `qa-specialist` | 32,014,392 | 1.4% |
| `frontend-reviewer` | 17,017,787 | 0.8% |
| `backend-reviewer` | 15,857,617 | 0.7% |
| `technical-writer` | 15,180,739 | 0.7% |
| `product-analyst` | 14,784,210 | 0.7% |
| `code-reviewer` | 11,947,029 | 0.5% |

## 5. Agents with the highest average tokens per call

**Conclusion:** `test-author` has the highest average, 8,128,920 tokens per call (44 calls) — well above the median, driven by heavy cache reuse. `command_invoked` carries no token counts, so per-command average is not determinable.

| Agent | Avg tokens/call | Calls |
|---|---:|---:|
| `test-author` | 8,128,920 | 44 |
| `backend-developer` | 3,478,627 | 181 |
| `software-architect` | 3,334,214 | 90 |
| `backend-reviewer` | 3,171,523 | 5 |
| `frontend-reviewer` | 2,836,298 | 6 |
| `frontend-developer` | 2,604,021 | 145 |
| `frontend-test-specialist` | 2,544,912 | 60 |
| `qa-specialist` | 2,462,646 | 13 |
| `security-specialist` | 2,456,570 | 70 |
| `devops-specialist` | 1,652,170 | 68 |
| `product-analyst` | 1,232,018 | 12 |
| `technical-writer` | 1,167,749 | 13 |
| `backend-test-specialist` | 1,026,236 | 51 |
| `code-reviewer` | 995,586 | 12 |

## 6. Country, state, and city ranking

**Conclusion:** usage is almost entirely from Brazil (99.9%), concentrated in Fortaleza/Ceará; there is 1 isolated event from France. Geography derived from PostHog GeoIP enrichment (IPs anonymized).

**Country**

| Country | Events | % |
|---|---:|---:|
| Brazil | 1462 | 99.9% |
| France | 1 | 0.1% |

**State / Region**

| State | Events | % |
|---|---:|---:|
| Ceará | 1439 | 98.4% |
| São Paulo | 23 | 1.6% |
| Île-de-France | 1 | 0.1% |

**City**

| City | Events | % |
|---|---:|---:|
| Fortaleza | 1439 | 98.4% |
| Bauru | 23 | 1.6% |
| Aulnay-sous-Bois | 1 | 0.1% |

## 7. Version ranking used in the period

**Conclusion:** `v2.44.0` is the most active version at 857 events (58.6%); a long tail shows many installs on older versions still active. Top 15 by `properties.version`.

| Version | Events | % |
|---|---:|---:|
| `v2.44.0` | 857 | 58.6% |
| `v2.29.0` | 149 | 10.2% |
| `v1.8.2` | 107 | 7.3% |
| `v2.39.2` | 99 | 6.8% |
| `v1.8.1` | 46 | 3.1% |
| `unknown` | 44 | 3.0% |
| `v2.17.3` | 20 | 1.4% |
| `v2.31.0` | 19 | 1.3% |
| `v1.11.0` | 16 | 1.1% |
| `v2.15.1` | 10 | 0.7% |
| `v2.30.1` | 9 | 0.6% |
| `v2.32.0` | 5 | 0.3% |
| `v2.27.3` | 5 | 0.3% |
| `v2.41.2` | 4 | 0.3% |
| `v2.27.0` | 4 | 0.3% |

> 53 distinct versions in total; `unknown` appears in 44 events (telemetry with no resolved version).

## 8. Models used, grouped by agent

**Conclusion:** each agent uses exactly one model, consistent with its tier — reasoning→`opus-5`, backend/frontend→`sonnet-5`, repetitive→`haiku`. The exception is `test-author` (off-roster) running on `haiku`.

| Agent | Models (calls) |
|---|---|
| `backend-developer` | `claude-sonnet-5` (181) |
| `backend-reviewer` | `claude-sonnet-5` (5) |
| `backend-test-specialist` | `claude-sonnet-5` (51) |
| `code-reviewer` | `claude-sonnet-5` (12) |
| `devops-specialist` | `claude-sonnet-5` (68) |
| `frontend-developer` | `claude-sonnet-5` (145) |
| `frontend-reviewer` | `claude-sonnet-5` (6) |
| `frontend-test-specialist` | `claude-sonnet-5` (60) |
| `product-analyst` | `claude-opus-5[1m]` (12) |
| `qa-specialist` | `claude-sonnet-5` (13) |
| `security-specialist` | `claude-opus-5[1m]` (70) |
| `software-architect` | `claude-opus-5[1m]` (90) |
| `technical-writer` | `claude-haiku-4-5-20251001` (13) |
| `test-author` ⚠️ | `claude-haiku-4-5-20251001` (44) |

## 9. Busiest days and hours (`America/Sao_Paulo`)

**Conclusion:** Wednesday is the peak day (744 events) and 10:00 the peak hour (290 events).

**By day of week**

| Day | Events |
|---|---:|
| Monday | 45 |
| Tuesday | 311 |
| Wednesday | 744 |
| Thursday | 173 |
| Friday | 132 |
| Saturday | 27 |
| Sunday | 31 |

**By hour of day**

| Hour | Events |
|---|---:|
| 00:00 | 28 |
| 01:00 | 17 |
| 02:00 | 1 |
| 03:00 | 9 |
| 04:00 | 14 |
| 05:00 | 0 |
| 06:00 | 0 |
| 07:00 | 180 |
| 08:00 | 13 |
| 09:00 | 11 |
| 10:00 | 290 |
| 11:00 | 128 |
| 12:00 | 112 |
| 13:00 | 18 |
| 14:00 | 25 |
| 15:00 | 50 |
| 16:00 | 53 |
| 17:00 | 42 |
| 18:00 | 25 |
| 19:00 | 52 |
| 20:00 | 32 |
| 21:00 | 46 |
| 22:00 | 227 |
| 23:00 | 90 |

## 10. New installs vs. updates rate

**Conclusion:** 10 first installs, 76 (re)run installs and 34 updates (all in `manual` mode) — the manual update flow dominates over new adoptions.

| Event | Count |
|---|---:|
| `first_install` (new adoption) | 10 |
| `install` | 76 |
| `update` | 34 |

## 11. Daily event volume (`America/Sao_Paulo`)

**Conclusion:** peak on 2026-08-12 with 693 events; volume is highly uneven, concentrated on a few heavy-work days.

| Day | Events |
|---|---:|
| 2026-07-23 | 36 |
| 2026-07-24 | 103 |
| 2026-07-25 | 17 |
| 2026-07-26 | 18 |
| 2026-07-27 | 5 |
| 2026-07-28 | 22 |
| 2026-07-29 | 4 |
| 2026-07-30 | 2 |
| 2026-07-31 | 7 |
| 2026-08-01 | 4 |
| 2026-08-02 | 9 |
| 2026-08-03 | 33 |
| 2026-08-04 | 6 |
| 2026-08-05 | 47 |
| 2026-08-06 | 135 |
| 2026-08-07 | 22 |
| 2026-08-08 | 6 |
| 2026-08-09 | 4 |
| 2026-08-10 | 7 |
| 2026-08-11 | 283 |
| 2026-08-12 | 693 |

## 12. Cache efficiency

**Conclusion:** the aggregate `cache_read` / `input` ratio is 2,278× — extremely high context reuse (each new input token is accompanied by ~2,278 tokens read from cache).

Aggregate: input `914,547` · cache_read `2,083,181,350` · cache_creation `170,355,329`.

| Agent (top by tokens) | Input | Cache read | read/input ratio |
|---|---:|---:|---:|
| `backend-developer` | 26,692 | 592,594,324 | 22,201× |
| `frontend-developer` | 628,920 | 347,888,772 | 553× |
| `test-author` | 45,710 | 347,113,273 | 7,594× |
| `software-architect` | 79,192 | 253,761,565 | 3,204× |
| `security-specialist` | 13,062 | 156,229,286 | 11,961× |
| `frontend-test-specialist` | 3,174 | 143,019,271 | 45,060× |
| `devops-specialist` | 79,393 | 99,150,834 | 1,249× |
| `backend-test-specialist` | 3,659 | 46,193,772 | 12,625× |

## 13. Session-end distribution

**Conclusion:** of 566 `session_end` events, 543 (95.9%) had `stop_hook_active=false` and 23 (4.1%) `true` — most sessions end with the stop hook inactive.

| stop_hook_active | Count | % |
|---|---:|---:|
| `false` | 543 | 95.9% |
| `true` | 23 | 4.1% |

## 14. Commands/agents never used in the period

**Conclusion:** 28 of 34 canonical commands and 5 of 18 canonical agents saw zero use in the window — a coverage gap. Also, `test-author` ran 44 times but **does not exist** in `agents/*.md`.

**Unused commands (34 canonical)**

`adr`, `audit`, `backend`, `commit`, `dba`, `design`, `devops`, `docs`, `explain`, `fix`, `frontend`, `fullstack`, `health-check`, `install`, `learn`, `mobile`, `plan`, `qa`, `refactor`, `relayout`, `rule`, `security`, `seo`, `setup`, `symlinks`, `tester`, `update`, `version`

**Unused agents (18 canonical)**

`database-specialist`, `mobile-developer`, `seo-specialist`, `setup-assistant`, `ui-ux-designer`

**Agents observed outside the canonical roster**

`test-author`

## Observations

- **Off-roster agent:** `test-author` (44 completions, 357,672,470 tokens, highest average per call) is absent from `agents/*.md`. Likely telemetry from an older version/fork before the rename to `*-test-specialist` — worth confirming no active spawn still references that name.
- **Slash-command layer nearly invisible:** only 7 `command_invoked` against 770 `agent_completed`. Either agents are spawned directly, or `command_invoked` firing in `scripts/hooks/pre-tool-use/` is under-recording — worth verifying.
- **Cache reuse dominates:** 2,083,181,350 cache_read tokens against only 914,547 input (2,278×). Token cost is almost entirely cache reads, not new input — a healthy prompt-caching signal.
- **Geographic and temporal concentration:** 99.9% of events come from Fortaleza/CE and volume concentrates on 2026-08-12 (693) and the day before — the active user base is essentially a single operator/location.
- **Long version tail:** 53 distinct versions active, from `v1.x` to `v2.44.0`; old installs keep emitting telemetry, reinforcing the need for backward compatibility in the event schema.

## Machine-readable summary for LLMs

```yaml
janela_inicio_sp: "2026-07-23 17:14"
janela_fim_sp: "2026-08-12 17:14"
fuso: America/Sao_Paulo
projeto_posthog: 430371
total_eventos_usados: 1463
total_eventos_brutos: 1466
excluidos_malformados: 1
excluidos_manuais: 2
total_agent_completed: 770
total_command_invoked: 7
total_tokens: 2261108291
comandos_por_chamadas_desc:
  - {comando: architect, chamadas: 2}
  - {comando: push, chamadas: 1}
  - {comando: status, chamadas: 1}
  - {comando: sync-rules, chamadas: 1}
  - {comando: pr, chamadas: 1}
  - {comando: review, chamadas: 1}
top_agentes_por_chamadas:
  - {agente: backend-developer, chamadas: 181}
  - {agente: frontend-developer, chamadas: 145}
  - {agente: software-architect, chamadas: 90}
  - {agente: security-specialist, chamadas: 70}
  - {agente: devops-specialist, chamadas: 68}
  - {agente: frontend-test-specialist, chamadas: 60}
  - {agente: backend-test-specialist, chamadas: 51}
  - {agente: test-author, chamadas: 44}
  - {agente: qa-specialist, chamadas: 13}
  - {agente: technical-writer, chamadas: 13}
  - {agente: code-reviewer, chamadas: 12}
  - {agente: product-analyst, chamadas: 12}
  - {agente: frontend-reviewer, chamadas: 6}
  - {agente: backend-reviewer, chamadas: 5}
provider_modelo:
  - {provider: claude, modelo: "claude-sonnet-5", chamadas: 541}
  - {provider: claude, modelo: "claude-opus-5[1m]", chamadas: 172}
  - {provider: claude, modelo: "claude-haiku-4-5-20251001", chamadas: 57}
tokens_por_agente_total_desc:
  - {agente: backend-developer, tokens: 629631416}
  - {agente: frontend-developer, tokens: 377583113}
  - {agente: test-author, tokens: 357672470}
  - {agente: software-architect, tokens: 300079305}
  - {agente: security-specialist, tokens: 171959869}
  - {agente: frontend-test-specialist, tokens: 152694710}
  - {agente: devops-specialist, tokens: 112347593}
  - {agente: backend-test-specialist, tokens: 52338041}
  - {agente: qa-specialist, tokens: 32014392}
  - {agente: frontend-reviewer, tokens: 17017787}
  - {agente: backend-reviewer, tokens: 15857617}
  - {agente: technical-writer, tokens: 15180739}
  - {agente: product-analyst, tokens: 14784210}
  - {agente: code-reviewer, tokens: 11947029}
media_tokens_por_agente_desc:
  - {agente: test-author, media_tokens: 8128920, chamadas: 44}
  - {agente: backend-developer, media_tokens: 3478627, chamadas: 181}
  - {agente: software-architect, media_tokens: 3334214, chamadas: 90}
  - {agente: backend-reviewer, media_tokens: 3171523, chamadas: 5}
  - {agente: frontend-reviewer, media_tokens: 2836298, chamadas: 6}
  - {agente: frontend-developer, media_tokens: 2604021, chamadas: 145}
  - {agente: frontend-test-specialist, media_tokens: 2544912, chamadas: 60}
  - {agente: qa-specialist, media_tokens: 2462646, chamadas: 13}
  - {agente: security-specialist, media_tokens: 2456570, chamadas: 70}
  - {agente: devops-specialist, media_tokens: 1652170, chamadas: 68}
  - {agente: product-analyst, media_tokens: 1232018, chamadas: 12}
  - {agente: technical-writer, media_tokens: 1167749, chamadas: 13}
  - {agente: backend-test-specialist, media_tokens: 1026236, chamadas: 51}
  - {agente: code-reviewer, media_tokens: 995586, chamadas: 12}
geografia:
  pais:
    - {nome: "Brazil", eventos: 1462}
    - {nome: "France", eventos: 1}
  estado:
    - {nome: "Ceará", eventos: 1439}
    - {nome: "São Paulo", eventos: 23}
    - {nome: "Île-de-France", eventos: 1}
  cidade:
    - {nome: "Fortaleza", eventos: 1439}
    - {nome: "Bauru", eventos: 23}
    - {nome: "Aulnay-sous-Bois", eventos: 1}
versoes_desc:
  - {versao: "v2.44.0", eventos: 857}
  - {versao: "v2.29.0", eventos: 149}
  - {versao: "v1.8.2", eventos: 107}
  - {versao: "v2.39.2", eventos: 99}
  - {versao: "v1.8.1", eventos: 46}
  - {versao: "unknown", eventos: 44}
  - {versao: "v2.17.3", eventos: 20}
  - {versao: "v2.31.0", eventos: 19}
  - {versao: "v1.11.0", eventos: 16}
  - {versao: "v2.15.1", eventos: 10}
  - {versao: "v2.30.1", eventos: 9}
  - {versao: "v2.32.0", eventos: 5}
  - {versao: "v2.27.3", eventos: 5}
  - {versao: "v2.41.2", eventos: 4}
  - {versao: "v2.27.0", eventos: 4}
versoes_distintas_total: 53
modelos_por_agente:
  backend-developer: {"claude-sonnet-5": 181}
  backend-reviewer: {"claude-sonnet-5": 5}
  backend-test-specialist: {"claude-sonnet-5": 51}
  code-reviewer: {"claude-sonnet-5": 12}
  devops-specialist: {"claude-sonnet-5": 68}
  frontend-developer: {"claude-sonnet-5": 145}
  frontend-reviewer: {"claude-sonnet-5": 6}
  frontend-test-specialist: {"claude-sonnet-5": 60}
  product-analyst: {"claude-opus-5[1m]": 12}
  qa-specialist: {"claude-sonnet-5": 13}
  security-specialist: {"claude-opus-5[1m]": 70}
  software-architect: {"claude-opus-5[1m]": 90}
  technical-writer: {"claude-haiku-4-5-20251001": 13}
  test-author: {"claude-haiku-4-5-20251001": 44}
uso_por_dia_semana:
  - {dia: Segunda, eventos: 45}
  - {dia: Terça, eventos: 311}
  - {dia: Quarta, eventos: 744}
  - {dia: Quinta, eventos: 173}
  - {dia: Sexta, eventos: 132}
  - {dia: Sábado, eventos: 27}
  - {dia: Domingo, eventos: 31}
uso_por_hora:
  - {hora: 0, eventos: 28}
  - {hora: 1, eventos: 17}
  - {hora: 2, eventos: 1}
  - {hora: 3, eventos: 9}
  - {hora: 4, eventos: 14}
  - {hora: 5, eventos: 0}
  - {hora: 6, eventos: 0}
  - {hora: 7, eventos: 180}
  - {hora: 8, eventos: 13}
  - {hora: 9, eventos: 11}
  - {hora: 10, eventos: 290}
  - {hora: 11, eventos: 128}
  - {hora: 12, eventos: 112}
  - {hora: 13, eventos: 18}
  - {hora: 14, eventos: 25}
  - {hora: 15, eventos: 50}
  - {hora: 16, eventos: 53}
  - {hora: 17, eventos: 42}
  - {hora: 18, eventos: 25}
  - {hora: 19, eventos: 52}
  - {hora: 20, eventos: 32}
  - {hora: 21, eventos: 46}
  - {hora: 22, eventos: 227}
  - {hora: 23, eventos: 90}
instalacoes:
  first_install: 10
  install: 76
  update: 34
volume_diario:
  - {dia: "2026-07-23", eventos: 36}
  - {dia: "2026-07-24", eventos: 103}
  - {dia: "2026-07-25", eventos: 17}
  - {dia: "2026-07-26", eventos: 18}
  - {dia: "2026-07-27", eventos: 5}
  - {dia: "2026-07-28", eventos: 22}
  - {dia: "2026-07-29", eventos: 4}
  - {dia: "2026-07-30", eventos: 2}
  - {dia: "2026-07-31", eventos: 7}
  - {dia: "2026-08-01", eventos: 4}
  - {dia: "2026-08-02", eventos: 9}
  - {dia: "2026-08-03", eventos: 33}
  - {dia: "2026-08-04", eventos: 6}
  - {dia: "2026-08-05", eventos: 47}
  - {dia: "2026-08-06", eventos: 135}
  - {dia: "2026-08-07", eventos: 22}
  - {dia: "2026-08-08", eventos: 6}
  - {dia: "2026-08-09", eventos: 4}
  - {dia: "2026-08-10", eventos: 7}
  - {dia: "2026-08-11", eventos: 283}
  - {dia: "2026-08-12", eventos: 693}
eficiencia_cache:
  input_total: 914547
  cache_read_total: 2083181350
  cache_creation_total: 170355329
  razao_read_input: 2277.83
  por_agente_top:
    - {agente: backend-developer, input: 26692, cache_read: 592594324, razao: 22201.2}
    - {agente: frontend-developer, input: 628920, cache_read: 347888772, razao: 553.15}
    - {agente: test-author, input: 45710, cache_read: 347113273, razao: 7593.81}
    - {agente: software-architect, input: 79192, cache_read: 253761565, razao: 3204.38}
    - {agente: security-specialist, input: 13062, cache_read: 156229286, razao: 11960.59}
    - {agente: frontend-test-specialist, input: 3174, cache_read: 143019271, razao: 45059.63}
    - {agente: devops-specialist, input: 79393, cache_read: 99150834, razao: 1248.86}
    - {agente: backend-test-specialist, input: 3659, cache_read: 46193772, razao: 12624.7}
fim_de_sessao:
  stop_hook_false: 543
  stop_hook_true: 23
  total: 566
cobertura:
  comandos_sem_uso: [adr, audit, backend, commit, dba, design, devops, docs, explain, fix, frontend, fullstack, health-check, install, learn, mobile, plan, qa, refactor, relayout, rule, security, seo, setup, symlinks, tester, update, version]
  agentes_sem_uso: [database-specialist, mobile-developer, seo-specialist, setup-assistant, ui-ux-designer]
  agentes_fora_do_roster: [test-author]
achado_configuracao:
  agente_fora_do_roster: test-author
  chamadas: 44
  modelo: claude-haiku-4-5-20251001
  nota: "nome ausente de agents/*.md; provavel telemetria de versao antiga/fork"
```
