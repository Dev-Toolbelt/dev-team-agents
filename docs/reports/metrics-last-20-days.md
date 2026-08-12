# Métricas de Uso PostHog — Últimos 20 Dias

**Janela:** 2026-07-23 18:17 UTC → 2026-08-12 14:01 UTC (20 dias, `now() - INTERVAL 20 DAY`)
**Gerado em:** 2026-08-12
**Fuso horário usado nas métricas de tempo:** UTC (`timestamp` bruto do PostHog)
**Total de eventos na janela:** 1.284 (2 eventos manuais de teste e 1 evento malformado excluídos de 1.287 linhas brutas)
**Fonte:** Projeto PostHog `430371` ("Default project"), tabela `events` via HogQL, gerado conforme `docs/prompts/posthog-metrics-report.md`

> ⚠️ **Ressalva de amostra:** estes dados refletem as sessões locais de um único
> desenvolvedor (a distribuição geográfica abaixo mostra o porquê). **Não** são
> representativos da base instalada mais ampla — `agent_spawned` e `command_invoked`,
> em particular, têm volume muito baixo nesta janela e não devem ser lidos como
> sinal de adoção ainda.

---

## 1. Comandos mais chamados

Apenas 5 eventos `command_invoked` caíram na janela — amostra pequena demais para um ranking significativo, mas listada por completude.

| Comando | Chamadas |
|---|---|
| `architect` | 1 |
| `review` | 1 |
| `pr` | 1 |
| `sync-rules` | 1 |
| `status` | 1 |

**Conclusão:** o volume de `command_invoked` (5) está muito abaixo do volume de `agent_completed` (664) na mesma janela — a maior parte do trabalho no período foi conduzida diretamente via spawn de agentes, não pela camada de slash-commands `/devteam:*`, ou o evento simplesmente sub-dispara. Vale checar o matcher de nome de comando em `scripts/hooks/pre-tool-use/02b-telemetry.sh` contra o uso real.

---

## 2. Agentes mais chamados

Ranqueado por `agent_completed` (nenhum evento `agent_spawned` apareceu nesta janela, então a contagem de conclusões é usada como proxy).

| Posição | Agente | Conclusões |
|---|---|---|
| 1 | **backend-developer** | 177 |
| 2 | frontend-developer | 133 |
| 3 | devops-specialist | 67 |
| 4 | security-specialist | 63 |
| 5 | backend-test-specialist | 50 |
| 5 | frontend-test-specialist | 50 |
| 7 | software-architect | 43 |
| 8 | test-author | 39 |
| 9 | technical-writer | 10 |
| 9 | product-analyst | 10 |
| 11 | code-reviewer | 6 |
| 11 | qa-specialist | 6 |
| 13 | backend-reviewer | 5 |
| 13 | frontend-reviewer | 5 |

**Conclusão:** `backend-developer` é o agente mais invocado (27% de todas as conclusões), seguido por `frontend-developer` (20%) — juntos, quase metade de toda a atividade de agentes na janela.

---

## 3. Ranking de modelos utilizados, agrupado por provider

| Provider | Modelo | Chamadas |
|---|---|---|
| claude | **claude-sonnet-5** | 499 |
| claude | claude-opus-5[1m] | 116 |
| claude | claude-haiku-4-5-20251001 | 49 |

**Conclusão:** toda a atividade registrada rodou na Claude — 75% em Sonnet 5, 17% em Opus 5 (contexto de 1M), 7% em Haiku 4.5. Nenhum outro provider apareceu na janela.

---

## 4. Ranking de consumo de tokens

Total de tokens (input + output + cache_creation + cache_read) por agente, em ordem decrescente.

| Posição | Agente | Total de tokens | Chamadas |
|---|---|---|---|
| 1 | **backend-developer** | 586.179.566 | 177 |
| 2 | frontend-developer | 328.738.619 | 133 |
| 3 | test-author | 314.928.051 | 39 |
| 4 | security-specialist | 156.221.148 | 63 |
| 5 | software-architect | 146.726.525 | 43 |
| 6 | frontend-test-specialist | 120.737.348 | 50 |
| 7 | devops-specialist | 110.507.050 | 67 |
| 8 | backend-test-specialist | 52.021.265 | 50 |
| 9 | backend-reviewer | 15.857.617 | 5 |
| 10 | technical-writer | 14.793.236 | 10 |
| 11 | frontend-reviewer | 13.651.733 | 5 |
| 12 | qa-specialist | 13.397.030 | 6 |
| 13 | product-analyst | 12.320.175 | 10 |
| 14 | code-reviewer | 3.328.352 | 6 |

**Totais da janela:** input 843.081 · output 5.499.345 · cache creation 136.003.707 · **cache read 1.747.061.582**

**Conclusão:** `backend-developer` lidera tanto em número de chamadas quanto em tokens totais. Os tokens de cache-read dominam o total por larga margem em todos os agentes (ver § 12).

---

## 5. Agentes que mais consomem tokens em média (por chamada)

| Posição | Agente | Média de tokens/chamada | Chamadas |
|---|---|---|---|
| 1 | **test-author** | 8.075.078 | 39 |
| 2 | software-architect | 3.412.245 | 43 |
| 3 | backend-developer | 3.311.749 | 177 |
| 4 | backend-reviewer | 3.171.523 | 5 |
| 5 | frontend-reviewer | 2.730.347 | 5 |
| 6 | security-specialist | 2.479.701 | 63 |
| 7 | frontend-developer | 2.471.719 | 133 |
| 8 | frontend-test-specialist | 2.414.747 | 50 |
| 9 | qa-specialist | 2.232.838 | 6 |
| 10 | devops-specialist | 1.649.359 | 67 |
| 11 | technical-writer | 1.479.324 | 10 |
| 12 | product-analyst | 1.232.018 | 10 |
| 13 | backend-test-specialist | 1.040.425 | 50 |
| 14 | code-reviewer | 554.725 | 6 |

*(`command_invoked` não carrega dados de token, então a média por comando não pode ser calculada a partir deste evento.)*

**Conclusão:** `test-author` tem, de longe, a maior média por chamada (2,4× o segundo colocado) apesar de um volume de chamadas mediano — cada invocação faz um trabalho de contexto incomumente grande em relação aos seus pares.

---

## 6. Ranking de país, estado e cidade

| País | Eventos |
|---|---|
| **Brasil** | 1.283 |
| França | 1 |

| Estado/Região | Eventos |
|---|---|
| **Ceará** | 1.260 |
| São Paulo | 23 |
| Île-de-France | 1 |

| Cidade | Eventos |
|---|---|
| **Fortaleza** | 1.260 |
| Bauru | 23 |
| Aulnay-sous-Bois | 1 |

**Conclusão:** isso confirma a ressalva de amostra do início — 98% dos eventos se originam de uma única cidade (Fortaleza, CE), ou seja, é telemetria de dogfood/máquina de desenvolvimento, ainda não uma base de usuários distribuída.

> 🔒 **Nota de privacidade (fora do escopo deste relatório, já resolvida):** foi
> identificado que todo evento bruto desta janela carrega a propriedade `$ip` com o IP
> literal do cliente, contradizendo a afirmação anterior do `PRIVACY.md` de que IPs eram
> descartados na ingestão. A causa raiz era a configuração `anonymize_ips=false` no
> projeto PostHog — já corrigida (`anonymize_ips` ativado, `PRIVACY.md` atualizado). Como
> a correção não é retroativa, os **1.284 eventos já ingeridos nesta janela continuam
> com `$ip` bruto armazenado** no PostHog; apenas eventos capturados a partir da
> ativação deixarão de reter o IP. A janela de 20 dias precisa "rolar" além da data da
> correção para essa nota desaparecer de futuras execuções deste relatório.

---

## 7. Ranking das versões usadas no período

| Posição | Versão | Eventos |
|---|---|---|
| 1 | **v2.44.0** | 791 |
| 2 | v2.29.0 | 149 |
| 3 | v1.8.2 | 111 |
| 4 | v1.8.1 | 46 |
| 5 | *desconhecida* | 40 |
| 6 | v2.31.0 | 19 |
| 7 | v1.11.0 | 16 |
| 8 | v2.15.1 | 10 |
| 9 | v2.30.1 | 9 |
| 10 | v2.27.3 | 5 |
| 10 | v2.32.0 | 5 |
| 12 | v2.7.0 | 4 |
| 12 | v2.16.0 | 4 |
| 12 | v2.20.0 | 4 |
| 12 | v2.27.0 | 4 |
| 12 | v2.41.2 | 4 |
| *(+9 outras versões com ≤3 eventos cada)* | | |

**Conclusão:** `v2.44.0` (a ponta atual) domina com 62% dos eventos, esperado já que a maior parte do volume é da sessão de hoje. A cauda longa de versões antigas (v1.8.x, v2.7–v2.41.x) reflete eventos históricos retidos dentro da janela de 20 dias, não instalações concorrentes. `desconhecida` (40 eventos, 3%) vem de eventos `install`/`update` capturados antes da versão ser resolvida — ver seção "Observações".

---

## 8. Lista de modelos utilizados agrupada por agente

| Agente | Modelo(s) usado(s) | Observação |
|---|---|---|
| backend-developer | claude-sonnet-5 (177) | modelo único |
| frontend-developer | claude-sonnet-5 (133) | modelo único |
| devops-specialist | claude-sonnet-5 (67) | modelo único |
| security-specialist | claude-opus-5[1m] (63) | modelo único |
| backend-test-specialist | claude-sonnet-5 (50) | modelo único |
| frontend-test-specialist | claude-sonnet-5 (50) | modelo único |
| software-architect | claude-opus-5[1m] (43) | modelo único |
| test-author | claude-haiku-4-5-20251001 (39) | modelo único |
| technical-writer | claude-haiku-4-5-20251001 (10) | modelo único |
| product-analyst | claude-opus-5[1m] (10) | modelo único |
| code-reviewer | claude-sonnet-5 (6) | modelo único |
| qa-specialist | claude-sonnet-5 (6) | modelo único |
| backend-reviewer | claude-sonnet-5 (5) | modelo único |
| frontend-reviewer | claude-sonnet-5 (5) | modelo único |

**Conclusão:** todo agente nesta janela chamou **exatamente um** modelo — nenhum agente se dividiu entre múltiplos modelos ou providers. Isso bate com o mapeamento tier→modelo de `tiers.json` em `CLAUDE.md` (`reasoning`→opus, `backend-exec`/`frontend`→sonnet, `repetitive`→haiku), sem desvio observado entre o tier configurado e o modelo resolvido.

---

## 9. Dias e horários de maior uso (UTC)

**Por dia da semana:**

| Dia | Eventos |
|---|---|
| **Quarta-feira** | 829 |
| Quinta-feira | 151 |
| Sexta-feira | 137 |
| Sábado | 47 |
| Terça-feira | 47 |
| Segunda-feira | 43 |
| Domingo | 30 |

**Por hora do dia (UTC):**

| Hora | Eventos | | Hora | Eventos |
|---|---|---|---|---|
| 00 | 46 | | 12 | 11 |
| 01 | 231 | | 13 | 298 |
| 02 | 93 | | 14 | 29 |
| 03 | 28 | | 15 | 22 |
| 04 | 17 | | 16 | 18 |
| 05 | 1 | | 17 | 25 |
| 06 | 9 | | 18 | 40 |
| 07 | 14 | | 19 | 49 |
| 08 | 0 | | 20 | 41 |
| 09 | 0 | | 21 | 25 |
| 10 | 188 | | 22 | 52 |
| 11 | 14 | | 23 | 33 |

**Conclusão:** ⚠️ fortemente enviesado pelo dia de hoje (2026-08-12, uma quarta-feira, contribuiu com 796 dos 1.284 eventos — ver a tendência diária na § 11). Os horários de pico, 01h e 13h UTC, correspondem a aproximadamente 22h e 10h em `America/Fortaleza` (UTC-3, a geografia dominante da § 6) — consistentes com um padrão de trabalho no final da noite e meio da manhã para esse único contribuidor. Trate o ranking por dia da semana como pouco confiável até o volume ficar mais distribuído ao longo de semanas.

---

## 10. Taxa de novas instalações vs atualizações

| Evento | Contagem |
|---|---|
| `first_install` | 10 |
| `install` (reinstalação/atualização via instalador) | 76 |
| `update` (atualização manual via `update.sh`) | 33 |

**Conclusão:** reinstalações/atualizações superam instalações novas em ~11:1 nesta janela — esperado para uma cópia local em desenvolvimento ativo, reinstalada/atualizada repetidamente durante testes, não crescimento orgânico de novos usuários.

---

## 11. Volume de eventos por dia

| Data | Eventos |
|---|---|
| 2026-07-23 | 28 |
| 2026-07-24 | 93 |
| 2026-07-25 | 37 |
| 2026-07-26 | 19 |
| 2026-07-27 | 6 |
| 2026-07-28 | 22 |
| 2026-07-29 | 2 |
| 2026-07-30 | 4 |
| 2026-07-31 | 7 |
| 2026-08-01 | 4 |
| 2026-08-02 | 8 |
| 2026-08-03 | 30 |
| 2026-08-04 | 11 |
| 2026-08-05 | 31 |
| 2026-08-06 | 119 |
| 2026-08-07 | 37 |
| 2026-08-08 | 6 |
| 2026-08-09 | 3 |
| 2026-08-10 | 7 |
| 2026-08-11 | 14 |
| **2026-08-12** | **796** |

**Conclusão:** a janela é dominada pelo dia atual (62% do volume total) — consistente com este relatório sendo gerado no meio da sessão de 2026-08-12. Excluindo hoje, 2026-08-06 (119) e 2026-07-24 (93) foram os dias de maior volume seguintes.

---

## 12. Eficiência de cache

| Métrica | Valor |
|---|---|
| Total de tokens de input | 843.081 |
| Total de tokens de cache-read | 1.747.061.582 |
| Total de tokens de cache-creation | 136.003.707 |
| **Proporção cache-read : input** | **~2.072 : 1** |

**Conclusão:** os cache-reads superam largamente os tokens de input frescos em toda a janela — o sistema de prompt-cache está fazendo a esmagadora maioria da entrega de contexto, comportamento esperado para invocações repetidas de agentes compartilhando um contexto de sistema/skill em cache dentro do TTL de 1 hora. É um forte sinal de eficiência, não uma preocupação.

---

## 13. Distribuição de fim de sessão

| `stop_hook_active` | Sessões |
|---|---|
| `false` | 475 |
| `true` | 21 |

**Conclusão:** 96% das sessões terminaram com o stop hook inativo (ou seja, um encerramento limpo e não bloqueado) — apenas 4% atingiram uma condição de stop hook ativo (resumo de sessão obrigatório, falhas de lint, etc.) ao final da sessão.

---

## 14. Comandos/agentes nunca usados no período

Cruzando os nomes observados de `agent_completed` com o roster de agentes em `agents/*.md` (17 agentes no total):

**Agentes com zero conclusões nesta janela:** `database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist` (4 de 17 — nenhuma invocação registrada em 20 dias).

Cruzar os nomes observados de `command_invoked` com o roster de `scripts/lib/commands.json` (comandos `/devteam:*`) não é confiável aqui — apenas 5 dos ~25 comandos documentados dispararam na janela (`architect`, `review`, `pr`, `sync-rules`, `status`), o que significaria 20 comandos com zero uso. Dada a ressalva da § 1 sobre o volume de `command_invoked` estar suspeitosamente baixo em relação a `agent_completed`, esta tabela **não** é confiável como sinal de adoção ainda e não foi detalhada mais — sinalizada como possível lacuna de instrumentação (ver Observações).

---

## Observações

- **São dados de dogfood de um único desenvolvedor, não telemetria de base de usuários.** 98% dos eventos com geolocalização apontam para uma única cidade; trate todo ranking acima como "como o próprio mantenedor deste repo usou", não como adoção em escala.
- **`command_invoked` sub-dispara em relação a `agent_completed`** (5 vs. 664 na mesma janela de 20 dias, mesmo com comandos rotineiramente disparando múltiplos agentes). Vale checar se a detecção de nome de comando em `scripts/hooks/pre-tool-use/02b-telemetry.sh` está perdendo caminhos de invocação (ex.: comandos executados sem a frase-gatilho esperada).
- **`version: "desconhecida"` em 40 eventos (todos `install`/`update`/`agent_completed`)** — a versão nem sempre é resolvida no momento da captura; vale checar se `state.json` é lido antes ou depois da escrita que está sendo reportada.
- **Zero agentes cross-model**: todo agente usou exatamente um modelo para seu tier inteiro nesta janela, batendo com `tiers.json` sem desvio observado — bom sinal de consistência para o contrato tier→modelo descrito em `CLAUDE.md`.
- **Eficiência de cache muito alta** (~2.072:1 cache-read para input) — o sistema de prompt-cache está carregando quase todo o reaproveitamento de contexto, comportamento pretendido, não um sinal de alerta.
- **Lacuna de documentação de privacidade identificada e corrigida durante a geração deste relatório**: valores brutos de `$ip` foram observados nas propriedades dos eventos (ver nota da § 6), apesar do `PRIVACY.md` afirmar que IPs eram descartados na ingestão. A causa raiz (`anonymize_ips=false` no projeto PostHog) foi corrigida e a documentação foi atualizada na mesma sessão.
- **4 agentes com zero atividade** na janela (`database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`) — esperado se nenhum trabalho correspondente (schema, mobile, design, SEO) ocorreu em 20 dias, não necessariamente um defeito.

---

## Resumo estruturado para leitura por LLMs

Bloco denso e sem prosa, otimizado para parsing/ingestão por outro agente ou LLM. Todos os
valores espelham as tabelas acima; nenhum dado novo é introduzido aqui.

```yaml
relatorio:
  titulo: "Metricas de uso PostHog — dev-team-agents"
  janela:
    inicio_utc: "2026-07-23T18:17:25Z"
    fim_utc: "2026-08-12T14:01:04Z"
    dias: 20
  gerado_em: "2026-08-12"
  fonte:
    posthog_project_id: 430371
    total_eventos: 1284
    eventos_excluidos:
      teste_manual: 2
      malformados: 1

  ressalvas:
    - "Amostra de um unico desenvolvedor/maquina — nao representa base de usuarios."
    - "command_invoked com volume muito baixo (5) frente a agent_completed (664) — possivel lacuna de instrumentacao."
    - "62% do volume total concentrado no dia de geracao do relatorio (2026-08-12)."
    - "Ranking por dia da semana pouco confiavel devido ao pico do dia atual."

  contagem_por_tipo_evento:
    agent_completed: 664
    session_end: 496
    install: 76
    update: 33
    first_install: 10
    command_invoked: 5

  top_comandos:
    - {comando: "architect", chamadas: 1}
    - {comando: "review", chamadas: 1}
    - {comando: "pr", chamadas: 1}
    - {comando: "sync-rules", chamadas: 1}
    - {comando: "status", chamadas: 1}

  top_agentes_por_chamadas:
    - {agente: "backend-developer", chamadas: 177}
    - {agente: "frontend-developer", chamadas: 133}
    - {agente: "devops-specialist", chamadas: 67}
    - {agente: "security-specialist", chamadas: 63}
    - {agente: "backend-test-specialist", chamadas: 50}
    - {agente: "frontend-test-specialist", chamadas: 50}
    - {agente: "software-architect", chamadas: 43}
    - {agente: "test-author", chamadas: 39}
    - {agente: "technical-writer", chamadas: 10}
    - {agente: "product-analyst", chamadas: 10}
    - {agente: "code-reviewer", chamadas: 6}
    - {agente: "qa-specialist", chamadas: 6}
    - {agente: "backend-reviewer", chamadas: 5}
    - {agente: "frontend-reviewer", chamadas: 5}

  modelos_por_provider:
    claude:
      - {modelo: "claude-sonnet-5", chamadas: 499}
      - {modelo: "claude-opus-5[1m]", chamadas: 116}
      - {modelo: "claude-haiku-4-5-20251001", chamadas: 49}

  modelo_por_agente:
    backend-developer: "claude-sonnet-5"
    frontend-developer: "claude-sonnet-5"
    devops-specialist: "claude-sonnet-5"
    security-specialist: "claude-opus-5[1m]"
    backend-test-specialist: "claude-sonnet-5"
    frontend-test-specialist: "claude-sonnet-5"
    software-architect: "claude-opus-5[1m]"
    test-author: "claude-haiku-4-5-20251001"
    technical-writer: "claude-haiku-4-5-20251001"
    product-analyst: "claude-opus-5[1m]"
    code-reviewer: "claude-sonnet-5"
    qa-specialist: "claude-sonnet-5"
    backend-reviewer: "claude-sonnet-5"
    frontend-reviewer: "claude-sonnet-5"
    observacao: "Nenhum agente usou mais de um modelo na janela — sem desvio do mapeamento tiers.json."

  tokens_totais_janela:
    input: 843081
    output: 5499345
    cache_creation: 136003707
    cache_read: 1747061582
    proporcao_cache_read_input: "~2072:1"

  tokens_por_agente_total_desc:
    - {agente: "backend-developer", total: 586179566, chamadas: 177}
    - {agente: "frontend-developer", total: 328738619, chamadas: 133}
    - {agente: "test-author", total: 314928051, chamadas: 39}
    - {agente: "security-specialist", total: 156221148, chamadas: 63}
    - {agente: "software-architect", total: 146726525, chamadas: 43}
    - {agente: "frontend-test-specialist", total: 120737348, chamadas: 50}
    - {agente: "devops-specialist", total: 110507050, chamadas: 67}
    - {agente: "backend-test-specialist", total: 52021265, chamadas: 50}
    - {agente: "backend-reviewer", total: 15857617, chamadas: 5}
    - {agente: "technical-writer", total: 14793236, chamadas: 10}
    - {agente: "frontend-reviewer", total: 13651733, chamadas: 5}
    - {agente: "qa-specialist", total: 13397030, chamadas: 6}
    - {agente: "product-analyst", total: 12320175, chamadas: 10}
    - {agente: "code-reviewer", total: 3328352, chamadas: 6}

  tokens_por_agente_media_desc:
    - {agente: "test-author", media: 8075078}
    - {agente: "software-architect", media: 3412245}
    - {agente: "backend-developer", media: 3311749}
    - {agente: "backend-reviewer", media: 3171523}
    - {agente: "frontend-reviewer", media: 2730347}
    - {agente: "security-specialist", media: 2479701}
    - {agente: "frontend-developer", media: 2471719}
    - {agente: "frontend-test-specialist", media: 2414747}
    - {agente: "qa-specialist", media: 2232838}
    - {agente: "devops-specialist", media: 1649359}
    - {agente: "technical-writer", media: 1479324}
    - {agente: "product-analyst", media: 1232018}
    - {agente: "backend-test-specialist", media: 1040425}
    - {agente: "code-reviewer", media: 554725}

  geografia:
    paises: [{nome: "Brasil", eventos: 1283}, {nome: "Franca", eventos: 1}]
    estados: [{nome: "Ceara", eventos: 1260}, {nome: "Sao Paulo", eventos: 23}, {nome: "Ile-de-France", eventos: 1}]
    cidades: [{nome: "Fortaleza", eventos: 1260}, {nome: "Bauru", eventos: 23}, {nome: "Aulnay-sous-Bois", eventos: 1}]

  versoes_top:
    - {versao: "v2.44.0", eventos: 791}
    - {versao: "v2.29.0", eventos: 149}
    - {versao: "v1.8.2", eventos: 111}
    - {versao: "v1.8.1", eventos: 46}
    - {versao: "desconhecida", eventos: 40}
    - {versao: "v2.31.0", eventos: 19}
    - {versao: "v1.11.0", eventos: 16}

  uso_por_dia_semana_utc:
    quarta: 829
    quinta: 151
    sexta: 137
    sabado: 47
    terca: 47
    segunda: 43
    domingo: 30

  uso_por_hora_utc_pico:
    - {hora: 1, eventos: 231}
    - {hora: 13, eventos: 298}
    - {hora: 10, eventos: 188}
    - {hora: 2, eventos: 93}

  instalacoes:
    first_install: 10
    install: 76
    update: 33
    proporcao_reinstall_para_novo: "~11:1"

  eficiencia_cache:
    proporcao_cache_read_input: "~2072:1"
    interpretacao: "positiva — alto reaproveitamento de contexto via prompt cache"

  fim_de_sessao:
    stop_hook_ativo_false: 475
    stop_hook_ativo_true: 21
    percentual_limpo: "96%"

  cobertura_zero_uso:
    agentes_sem_atividade:
      - "database-specialist"
      - "mobile-developer"
      - "ui-ux-designer"
      - "seo-specialist"
    comandos_sem_atividade_confiavel: false
    motivo: "amostra de command_invoked pequena demais (5 eventos) para inferir cobertura"

  achado_seguranca_privacidade:
    descricao: "Propriedade $ip com IP bruto do cliente presente em eventos, contradizendo PRIVACY.md"
    causa_raiz: "anonymize_ips=false no projeto PostHog 430371"
    status: "corrigido — anonymize_ips ativado e PRIVACY.md atualizado"
    retroatividade: "correcao nao retroativa — os 1284 eventos ja ingeridos nesta janela ainda retem $ip bruto"

  perguntas_em_aberto_para_proxima_janela:
    - "command_invoked continua sub-disparando em relacao a agent_completed?"
    - "version: desconhecida ainda aparece apos revisar ordem de leitura/escrita de state.json?"
    - "geografia ja reflete usuarios reais alem da maquina de desenvolvimento?"
```
