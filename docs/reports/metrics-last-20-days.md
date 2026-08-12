# Métricas de Uso DevTeam Agents — Últimos 20 Dias

**Janela:** 2026-07-23 17:14 → 2026-08-12 17:14, horário de `America/Sao_Paulo` (20 dias)  
**Gerado em:** 2026-08-12 17:27 (`America/Sao_Paulo`)  
**Fuso horário usado nas métricas de tempo:** `America/Sao_Paulo` (UTC−3)  
**Total de eventos na janela:** 1.463 (excluídos 1 evento malformado com `agent_name`/`model` nulos e 2 eventos manuais de teste `__manual_verification_test__`, de 1.466 linhas brutas)  
**ID do projeto PostHog:** 430371

---

## 1. Comandos mais chamados

**Conclusão:** apenas 7 eventos `command_invoked` caíram na janela — amostra pequena demais para um ranking significativo (contra 770 `agent_completed`), indicando que o trabalho foi conduzido via spawn direto de agentes e não pela camada de slash-commands `/devteam:*`, ou que o evento sub-dispara.

| Comando | Chamadas |
|---|---:|
| `architect` | 2 |
| `push` | 1 |
| `status` | 1 |
| `sync-rules` | 1 |
| `pr` | 1 |
| `review` | 1 |

## 2. Agentes mais invocados

**Conclusão:** `backend-developer` lidera com 181 conclusões (23.5% das 770 conclusões de agente). Nenhum evento `agent_spawned` apareceu na janela, então usa-se `agent_completed` como proxy.

| Agente | Conclusões | % |
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

> ⚠️ `test-author` não consta no roster canônico de agentes (`agents/*.md`) — ver seção 14.

## 3. Ranking de modelos agrupados por provider

**Conclusão:** 100% das conclusões usaram o provider `claude`; `claude-sonnet-5` domina com 541 chamadas (70.3%).

| Provider | Modelo | Chamadas | % |
|---|---|---:|---:|
| `claude` | `claude-sonnet-5` | 541 | 70.3% |
| `claude` | `claude-opus-5[1m]` | 172 | 22.3% |
| `claude` | `claude-haiku-4-5-20251001` | 57 | 7.4% |

## 4. Ranking de consumo de tokens

**Conclusão:** `backend-developer` é o maior consumidor, com 629.631.416 tokens (27.8% dos 2.261.108.291 tokens totais). Tokens = input + output + cache_creation + cache_read.

| Agente | Tokens totais | % |
|---|---:|---:|
| `backend-developer` | 629.631.416 | 27.8% |
| `frontend-developer` | 377.583.113 | 16.7% |
| `test-author` | 357.672.470 | 15.8% |
| `software-architect` | 300.079.305 | 13.3% |
| `security-specialist` | 171.959.869 | 7.6% |
| `frontend-test-specialist` | 152.694.710 | 6.8% |
| `devops-specialist` | 112.347.593 | 5.0% |
| `backend-test-specialist` | 52.338.041 | 2.3% |
| `qa-specialist` | 32.014.392 | 1.4% |
| `frontend-reviewer` | 17.017.787 | 0.8% |
| `backend-reviewer` | 15.857.617 | 0.7% |
| `technical-writer` | 15.180.739 | 0.7% |
| `product-analyst` | 14.784.210 | 0.7% |
| `code-reviewer` | 11.947.029 | 0.5% |

## 5. Agentes que mais consomem tokens em média (por chamada)

**Conclusão:** `test-author` tem a maior média, 8.128.920 tokens por chamada (44 chamadas) — muito acima da mediana, puxada por reuso massivo de cache. `command_invoked` não carrega contagem de tokens, então a média por comando não é determinável.

| Agente | Média de tokens/chamada | Chamadas |
|---|---:|---:|
| `test-author` | 8.128.920 | 44 |
| `backend-developer` | 3.478.627 | 181 |
| `software-architect` | 3.334.214 | 90 |
| `backend-reviewer` | 3.171.523 | 5 |
| `frontend-reviewer` | 2.836.298 | 6 |
| `frontend-developer` | 2.604.021 | 145 |
| `frontend-test-specialist` | 2.544.912 | 60 |
| `qa-specialist` | 2.462.646 | 13 |
| `security-specialist` | 2.456.570 | 70 |
| `devops-specialist` | 1.652.170 | 68 |
| `product-analyst` | 1.232.018 | 12 |
| `technical-writer` | 1.167.749 | 13 |
| `backend-test-specialist` | 1.026.236 | 51 |
| `code-reviewer` | 995.586 | 12 |

## 6. Ranking de país, estado e cidade

**Conclusão:** o uso é quase totalmente do Brasil (99.9%), concentrado em Fortaleza/Ceará; há 1 evento isolado da França. Geografia derivada do enriquecimento GeoIP do PostHog (IPs anonimizados).

**País**

| País | Eventos | % |
|---|---:|---:|
| Brazil | 1462 | 99.9% |
| France | 1 | 0.1% |

**Estado / Região**

| Estado | Eventos | % |
|---|---:|---:|
| Ceará | 1439 | 98.4% |
| São Paulo | 23 | 1.6% |
| Île-de-France | 1 | 0.1% |

**Cidade**

| Cidade | Eventos | % |
|---|---:|---:|
| Fortaleza | 1439 | 98.4% |
| Bauru | 23 | 1.6% |
| Aulnay-sous-Bois | 1 | 0.1% |

## 7. Ranking das versões usadas no período

**Conclusão:** `v2.44.0` é a versão mais ativa, com 857 eventos (58.6%); a cauda longa mostra muitas instalações em versões antigas ainda ativas. Top 15 por `properties.version`.

| Versão | Eventos | % |
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

> 53 versões distintas no total; `unknown` aparece em 44 eventos (telemetria sem versão resolvida).

## 8. Lista de modelos utilizados agrupada por agente

**Conclusão:** cada agente usa exatamente um modelo, coerente com seu tier — reasoning→`opus-5`, backend/frontend→`sonnet-5`, repetitive→`haiku`. A exceção é `test-author` (fora do roster) rodando em `haiku`.

| Agente | Modelos (chamadas) |
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

## 9. Dias e horários de maior uso (`America/Sao_Paulo`)

**Conclusão:** Quarta é o dia de pico (744 eventos) e 10h o horário de pico (290 eventos).

**Por dia da semana**

| Dia | Eventos |
|---|---:|
| Segunda | 45 |
| Terça | 311 |
| Quarta | 744 |
| Quinta | 173 |
| Sexta | 132 |
| Sábado | 27 |
| Domingo | 31 |

**Por hora do dia**

| Hora | Eventos |
|---|---:|
| 00h | 28 |
| 01h | 17 |
| 02h | 1 |
| 03h | 9 |
| 04h | 14 |
| 05h | 0 |
| 06h | 0 |
| 07h | 180 |
| 08h | 13 |
| 09h | 11 |
| 10h | 290 |
| 11h | 128 |
| 12h | 112 |
| 13h | 18 |
| 14h | 25 |
| 15h | 50 |
| 16h | 53 |
| 17h | 42 |
| 18h | 25 |
| 19h | 52 |
| 20h | 32 |
| 21h | 46 |
| 22h | 227 |
| 23h | 90 |

## 10. Taxa de novas instalações vs atualizações

**Conclusão:** 10 primeiras instalações, 76 instalações (re)executadas e 34 atualizações (todas em modo `manual`) — o fluxo de update manual domina sobre novas adoções.

| Evento | Contagem |
|---|---:|
| `first_install` (nova adoção) | 10 |
| `install` | 76 |
| `update` | 34 |

## 11. Volume de eventos por dia (`America/Sao_Paulo`)

**Conclusão:** pico em 2026-08-12 com 693 eventos; o volume é altamente irregular, concentrado em poucos dias de trabalho intenso.

| Dia | Eventos |
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

## 12. Eficiência de cache

**Conclusão:** a razão `cache_read` / `input` agregada é 2.278× — reuso de contexto extremamente alto (cada token de input novo é acompanhado de ~2.278 tokens lidos do cache).

Agregado: input `914.547` · cache_read `2.083.181.350` · cache_creation `170.355.329`.

| Agente (top por tokens) | Input | Cache read | Razão read/input |
|---|---:|---:|---:|
| `backend-developer` | 26.692 | 592.594.324 | 22.201× |
| `frontend-developer` | 628.920 | 347.888.772 | 553× |
| `test-author` | 45.710 | 347.113.273 | 7.594× |
| `software-architect` | 79.192 | 253.761.565 | 3.204× |
| `security-specialist` | 13.062 | 156.229.286 | 11.961× |
| `frontend-test-specialist` | 3.174 | 143.019.271 | 45.060× |
| `devops-specialist` | 79.393 | 99.150.834 | 1.249× |
| `backend-test-specialist` | 3.659 | 46.193.772 | 12.625× |

## 13. Distribuição de fim de sessão

**Conclusão:** de 566 eventos `session_end`, 543 (95.9%) tinham `stop_hook_active=false` e 23 (4.1%) `true` — a maioria das sessões encerra sem o hook de parada ativo.

| stop_hook_active | Contagem | % |
|---|---:|---:|
| `false` | 543 | 95.9% |
| `true` | 23 | 4.1% |

## 14. Comandos/agentes nunca usados no período

**Conclusão:** 28 dos 34 comandos canônicos e 5 dos 18 agentes canônicos tiveram zero uso na janela — uma lacuna de cobertura. Além disso, `test-author` foi executado 44 vezes mas **não existe** em `agents/*.md`.

**Comandos sem uso (34 canônicos)**

`adr`, `audit`, `backend`, `commit`, `dba`, `design`, `devops`, `docs`, `explain`, `fix`, `frontend`, `fullstack`, `health-check`, `install`, `learn`, `mobile`, `plan`, `qa`, `refactor`, `relayout`, `rule`, `security`, `seo`, `setup`, `symlinks`, `tester`, `update`, `version`

**Agentes sem uso (18 canônicos)**

`database-specialist`, `mobile-developer`, `seo-specialist`, `setup-assistant`, `ui-ux-designer`

**Agentes observados fora do roster canônico**

`test-author`

## Observações

- **Agente fora do roster:** `test-author` (44 conclusões, 357.672.470 tokens, maior média por chamada) não consta em `agents/*.md`. Provavelmente telemetria de uma versão antiga/fork antes da renomeação para `*-test-specialist` — vale confirmar que nenhum spawn ativo ainda referencia esse nome.
- **Camada de slash-commands quase invisível:** só 7 `command_invoked` contra 770 `agent_completed`. Ou os agentes são spawnados diretamente, ou o disparo de `command_invoked` em `scripts/hooks/pre-tool-use/` está sub-registrando — merece verificação.
- **Reuso de cache dominante:** 2.083.181.350 tokens de cache_read contra apenas 914.547 de input (2.278×). O custo de tokens é quase todo leitura de cache, não input novo — sinal saudável de prompt caching.
- **Concentração geográfica e temporal:** 99.9% dos eventos vêm de Fortaleza/CE e o volume se concentra em 2026-08-12 (693) e no dia anterior — a base de uso ativa é essencialmente de um único operador/local.
- **Cauda longa de versões:** 53 versões distintas ativas, de `v1.x` a `v2.44.0`; instalações antigas continuam emitindo telemetria, o que reforça a necessidade de compatibilidade retroativa do esquema de eventos.

## Resumo estruturado para leitura por LLMs

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
