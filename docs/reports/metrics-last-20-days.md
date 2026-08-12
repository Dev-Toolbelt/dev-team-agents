# Métricas de Uso PostHog — Últimos 20 Dias

**Janela:** 2026-07-23 18:17 UTC → 2026-08-12 15:44 UTC (20 dias, `now() - INTERVAL 20 DAY`)
**Gerado em:** 2026-08-12
**Fuso horário usado nas métricas de tempo:** UTC (`timestamp` bruto do PostHog)
**Total de eventos na janela:** 1.484 (2 eventos manuais de teste `__manual_verification_test__` e 1 evento malformado com `agent_name`/`model` nulos excluídos de 1.487 linhas brutas)
**Fonte:** Projeto PostHog `430371` ("Default project"), tabela `events` via HogQL, gerado conforme `docs/prompts/posthog-metrics-report.md`

> ⚠️ **Ressalva de amostra:** estes dados refletem as sessões locais de um único
> desenvolvedor (a distribuição geográfica abaixo mostra o porquê). **Não** são
> representativos da base instalada mais ampla — `agent_spawned` e `command_invoked`,
> em particular, têm volume muito baixo nesta janela e não devem ser lidos como
> sinal de adoção ainda.

---

## 1. Comandos mais chamados

Apenas 7 eventos `command_invoked` caíram na janela — amostra pequena demais para um ranking significativo, mas listada por completude.

| Comando | Chamadas |
|---|---|
| `architect` | 2 |
| `push` | 1 |
| `status` | 1 |
| `sync-rules` | 1 |
| `pr` | 1 |
| `review` | 1 |

**Conclusão:** o volume de `command_invoked` (7) está muito abaixo do volume de `agent_completed` (803) na mesma janela — a maior parte do trabalho no período foi conduzida diretamente via spawn de agentes, não pela camada de slash-commands `/devteam:*`, ou o evento simplesmente sub-dispara. Vale checar o matcher de nome de comando em `scripts/hooks/pre-tool-use/02b-telemetry.sh` contra o uso real.

---

## 2. Agentes mais chamados

Ranqueado por `agent_completed` (nenhum evento `agent_spawned` apareceu nesta janela, então a contagem de conclusões é usada como proxy).

| Posição | Agente | Conclusões |
|---|---|---|
| 1 | **backend-developer** | 195 |
| 2 | frontend-developer | 152 |
| 3 | software-architect | 90 |
| 4 | security-specialist | 73 |
| 5 | devops-specialist | 71 |
| 6 | frontend-test-specialist | 61 |
| 7 | backend-test-specialist | 54 |
| 8 | test-author | 45 |
| 9 | qa-specialist | 13 |
| 9 | technical-writer | 13 |
| 11 | code-reviewer | 12 |
| 11 | product-analyst | 12 |
| 13 | backend-reviewer | 6 |
| 13 | frontend-reviewer | 6 |

**Conclusão:** `backend-developer` é o agente mais invocado (24,3% de todas as conclusões), seguido por `frontend-developer` (18,9%) — juntos, 43,2% de toda a atividade de agentes na janela.

---

## 3. Ranking de modelos utilizados, agrupado por provider

| Provider | Modelo | Chamadas |
|---|---|---|
| claude | **claude-sonnet-5** | 570 |
| claude | claude-opus-5[1m] | 175 |
| claude | claude-haiku-4-5-20251001 | 58 |

**Conclusão:** toda a atividade registrada rodou na Claude — 71,0% em Sonnet 5, 21,8% em Opus 5 (contexto de 1M), 7,2% em Haiku 4.5. Nenhum outro provider apareceu na janela. (Os 2 eventos manuais `__manual_verification_test__`, rodados em `claude-sonnet-4-5`, foram excluídos deste ranking — ver nota no cabeçalho.)

---

## 4. Ranking de consumo de tokens

Total de tokens (input + output + cache_creation + cache_read) por agente, em ordem decrescente.

| Posição | Agente | Total de tokens | Chamadas |
|---|---|---|---|
| 1 | **backend-developer** | 693.294.212 | 195 |
| 2 | frontend-developer | 388.745.340 | 152 |
| 3 | test-author | 371.111.987 | 45 |
| 4 | software-architect | 300.079.305 | 90 |
| 5 | security-specialist | 179.515.358 | 73 |
| 6 | frontend-test-specialist | 153.399.264 | 61 |
| 7 | devops-specialist | 116.652.699 | 71 |
| 8 | backend-test-specialist | 53.496.496 | 54 |
| 9 | qa-specialist | 32.014.392 | 13 |
| 10 | backend-reviewer | 19.713.773 | 6 |
| 11 | frontend-reviewer | 17.017.787 | 6 |
| 12 | technical-writer | 15.180.739 | 13 |
| 13 | product-analyst | 14.784.210 | 12 |
| 14 | code-reviewer | 11.947.029 | 12 |

**Totais da janela:** input 959.983 · output 6.890.257 · cache creation 175.567.933 · **cache read 2.183.534.418**

**Conclusão:** `backend-developer` lidera tanto em número de chamadas quanto em tokens totais. Os tokens de cache-read dominam o total por larga margem em todos os agentes (ver § 12).

---

## 5. Agentes que mais consomem tokens em média (por chamada)

| Posição | Agente | Média de tokens/chamada | Chamadas |
|---|---|---|---|
| 1 | **test-author** | 8.246.933 | 45 |
| 2 | backend-developer | 3.555.354 | 195 |
| 3 | software-architect | 3.334.214 | 90 |
| 4 | backend-reviewer | 3.285.628 | 6 |
| 5 | frontend-reviewer | 2.836.297 | 6 |
| 6 | frontend-developer | 2.557.535 | 152 |
| 7 | frontend-test-specialist | 2.514.742 | 61 |
| 8 | qa-specialist | 2.462.645 | 13 |
| 9 | security-specialist | 2.459.114 | 73 |
| 10 | devops-specialist | 1.642.995 | 71 |
| 11 | product-analyst | 1.232.017 | 12 |
| 12 | technical-writer | 1.167.749 | 13 |
| 13 | code-reviewer | 995.585 | 12 |
| 14 | backend-test-specialist | 990.675 | 54 |

*(`command_invoked` não carrega dados de token, então a média por comando não pode ser calculada a partir deste evento.)*

**Conclusão:** `test-author` tem, de longe, a maior média por chamada (2,3× o segundo colocado) apesar de um volume de chamadas mediano — cada invocação faz um trabalho de contexto incomumente grande em relação aos seus pares.

---

## 6. Ranking de país, estado e cidade

| País | Eventos |
|---|---|
| **Brasil** | 1.483 |
| França | 1 |

| Estado/Região | Eventos |
|---|---|
| **Ceará** | 1.460 |
| São Paulo | 23 |
| Île-de-France | 1 |

| Cidade | Eventos |
|---|---|
| **Fortaleza** | 1.460 |
| Bauru | 23 |
| Aulnay-sous-Bois | 1 |

**Conclusão:** isso confirma a ressalva de amostra do início — 98% dos eventos se originam de uma única cidade (Fortaleza, CE), ou seja, é telemetria de dogfood/máquina de desenvolvimento, ainda não uma base de usuários distribuída.

> 🔒 **Nota de privacidade (fora do escopo deste relatório, já resolvida):** a correção de `anonymize_ips` no projeto PostHog não é retroativa — a maioria dos eventos desta janela de 20 dias foi ingerida **antes** da correção e ainda retém a propriedade `$ip` bruta armazenada no PostHog (identificado na execução anterior deste relatório, em 2026-08-12). Apenas eventos capturados a partir da ativação deixam de reter o IP. A janela de 20 dias precisa "rolar" além da data da correção para essa nota desaparecer de futuras execuções deste relatório.

---

## 7. Ranking das versões usadas no período

| Posição | Versão | Eventos |
|---|---|---|
| 1 | **v2.44.0** | 891 |
| 2 | v2.29.0 | 149 |
| 3 | v1.8.2 | 111 |
| 4 | v2.39.2 | 99 |
| 5 | v1.8.1 | 46 |
| 5 | *desconhecida* | 46 |
| 7 | v2.31.0 | 19 |
| 8 | v1.11.0 | 16 |
| 9 | v2.15.1 | 10 |
| 10 | v2.30.1 | 9 |
| *(+40 outras versões com ≤5 eventos cada)* | | |

**Conclusão:** `v2.44.0` (a ponta atual) domina com 59,9% dos eventos, esperado já que a maior parte do volume é da sessão de hoje. A cauda longa de versões antigas (v1.8.x, v2.7–v2.41.x) reflete eventos históricos retidos dentro da janela de 20 dias, não instalações concorrentes. `desconhecida` (46 eventos, 3,1%) vem de eventos `install`/`update`/`agent_completed` capturados antes da versão ser resolvida — ver seção "Observações".

---

## 8. Lista de modelos utilizados agrupada por agente

| Agente | Modelo(s) usado(s) | Observação |
|---|---|---|
| backend-developer | claude-sonnet-5 (195) | modelo único |
| frontend-developer | claude-sonnet-5 (152) | modelo único |
| software-architect | claude-opus-5[1m] (90) | modelo único |
| security-specialist | claude-opus-5[1m] (73) | modelo único |
| devops-specialist | claude-sonnet-5 (71) | modelo único |
| frontend-test-specialist | claude-sonnet-5 (61) | modelo único |
| backend-test-specialist | claude-sonnet-5 (54) | modelo único |
| test-author | claude-haiku-4-5-20251001 (45) | modelo único |
| qa-specialist | claude-sonnet-5 (13) | modelo único |
| technical-writer | claude-haiku-4-5-20251001 (13) | modelo único |
| code-reviewer | claude-sonnet-5 (12) | modelo único |
| product-analyst | claude-opus-5[1m] (12) | modelo único |
| backend-reviewer | claude-sonnet-5 (6) | modelo único |
| frontend-reviewer | claude-sonnet-5 (6) | modelo único |

**Conclusão:** todo agente nesta janela chamou **exatamente um** modelo — nenhum agente se dividiu entre múltiplos modelos ou providers. Isso bate com o mapeamento tier→modelo de `tiers.json` em `CLAUDE.md` (`reasoning`→opus, `backend-exec`/`frontend`→sonnet, `repetitive`→haiku), sem desvio observado entre o tier configurado e o modelo resolvido.

---

## 9. Dias e horários de maior uso (UTC)

**Por dia da semana:**

| Dia | Eventos |
|---|---|
| **Quarta-feira** | 1.032 |
| Quinta-feira | 151 |
| Sexta-feira | 137 |
| Sábado | 47 |
| Terça-feira | 47 |
| Segunda-feira | 43 |
| Domingo | 30 |

**Por hora do dia (UTC):**

| Hora | Eventos | | Hora | Eventos |
|---|---|---|---|---|
| 00 | 49 | | 12 | 11 |
| 01 | 231 | | 13 | 298 |
| 02 | 93 | | 14 | 134 |
| 03 | 28 | | 15 | 117 |
| 04 | 17 | | 16 | 18 |
| 05 | 1 | | 17 | 25 |
| 06 | 9 | | 18 | 40 |
| 07 | 14 | | 19 | 49 |
| 08 | 0 | | 20 | 41 |
| 09 | 0 | | 21 | 25 |
| 10 | 188 | | 22 | 52 |
| 11 | 14 | | 23 | 33 |

**Conclusão:** ⚠️ fortemente enviesado pelo dia de hoje (2026-08-12, uma quarta-feira, contribuiu com 996 dos 1.484 eventos — ver a tendência diária na § 11). Os horários de pico, 13h e 01h UTC, correspondem a aproximadamente 10h e 22h em `America/Fortaleza` (UTC-3, a geografia dominante da § 6) — consistentes com um padrão de trabalho no final da noite e meio da manhã para esse único contribuidor. Trate o ranking por dia da semana como pouco confiável até o volume ficar mais distribuído ao longo de semanas.

---

## 10. Taxa de novas instalações vs atualizações

| Evento | Contagem |
|---|---|
| `first_install` | 10 |
| `install` (reinstalação/atualização via instalador) | 76 |
| `update` (atualização manual via `update.sh`) | 34 |

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
| **2026-08-12** | **996** |

**Conclusão:** a janela é dominada pelo dia atual (67,1% do volume total) — consistente com este relatório sendo gerado no meio da sessão de 2026-08-12. Excluindo hoje, 2026-08-06 (119) e 2026-07-24 (93) foram os dias de maior volume seguintes.

---

## 12. Eficiência de cache

| Métrica | Valor |
|---|---|
| Total de tokens de input | 959.983 |
| Total de tokens de cache-read | 2.183.534.418 |
| Total de tokens de cache-creation | 175.567.933 |
| **Proporção cache-read : input** | **~2.275 : 1** |

**Conclusão:** os cache-reads superam largamente os tokens de input frescos em toda a janela — o sistema de prompt-cache está fazendo a esmagadora maioria da entrega de contexto, comportamento esperado para invocações repetidas de agentes compartilhando um contexto de sistema/skill em cache dentro do TTL de 1 hora. É um forte sinal de eficiência, não uma preocupação.

---

## 13. Distribuição de fim de sessão

| `stop_hook_active` | Sessões |
|---|---|
| `false` | 532 |
| `true` | 22 |

**Conclusão:** 96,0% das sessões terminaram com o stop hook inativo (ou seja, um encerramento limpo e não bloqueado) — apenas 4,0% atingiram uma condição de stop hook ativo (resumo de sessão obrigatório, falhas de lint, etc.) ao final da sessão.

---

## 14. Comandos/agentes nunca usados no período

Cruzando os nomes observados de `agent_completed` com o roster de agentes em `agents/*.md` (18 agentes no total):

**Agentes com zero conclusões nesta janela:** `database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`, `setup-assistant` (5 de 18 — nenhuma invocação registrada em 20 dias).

Cruzar os nomes observados de `command_invoked` com o roster de `scripts/lib/commands.json` (comandos `/devteam:*`) não é confiável aqui — apenas 6 dos ~25 comandos documentados dispararam na janela (`architect`, `push`, `status`, `sync-rules`, `pr`, `review`), o que significaria ~19 comandos com zero uso. Dada a ressalva da § 1 sobre o volume de `command_invoked` estar suspeitosamente baixo em relação a `agent_completed`, esta tabela **não** é confiável como sinal de adoção ainda e não foi detalhada mais — sinalizada como possível lacuna de instrumentação (ver Observações).

---

## Observações

- **São dados de dogfood de um único desenvolvedor, não telemetria de base de usuários.** 98% dos eventos com geolocalização apontam para uma única cidade; trate todo ranking acima como "como o próprio mantenedor deste repo usou", não como adoção em escala.
- **`command_invoked` sub-dispara em relação a `agent_completed`** (7 vs. 803 na mesma janela de 20 dias, mesmo com comandos rotineiramente disparando múltiplos agentes). Vale checar se a detecção de nome de comando em `scripts/hooks/pre-tool-use/02b-telemetry.sh` está perdendo caminhos de invocação (ex.: comandos executados sem a frase-gatilho esperada).
- **`version: "desconhecida"` em 46 eventos** — a versão nem sempre é resolvida no momento da captura; vale checar se `state.json` é lido antes ou depois da escrita que está sendo reportada.
- **Zero agentes cross-model**: todo agente usou exatamente um modelo para seu tier inteiro nesta janela, batendo com `tiers.json` sem desvio observado — bom sinal de consistência para o contrato tier→modelo descrito em `CLAUDE.md`.
- **Eficiência de cache muito alta** (~2.275:1 cache-read para input) — o sistema de prompt-cache está carregando quase todo o reaproveitamento de contexto, comportamento pretendido, não um sinal de alerta.
- **5 agentes com zero atividade** na janela (`database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`, `setup-assistant`) — esperado se nenhum trabalho correspondente (schema, mobile, design, SEO, onboarding de novo projeto) ocorreu em 20 dias, não necessariamente um defeito.
- **2 eventos de teste manual (`__manual_verification_test__`, modelo `claude-sonnet-4-5`) e 1 evento malformado (`agent_name`/`model` nulos)** foram excluídos de todas as métricas de agente/modelo/token acima para não distorcer os rankings — ver o total ajustado no cabeçalho.

---

## Resumo estruturado para leitura por LLMs

Bloco denso e sem prosa, otimizado para parsing/ingestão por outro agente ou LLM. Todos os
valores espelham as tabelas acima; nenhum dado novo é introduzido aqui.

```yaml
relatorio:
  titulo: "Metricas de uso PostHog — dev-team-agents"
  janela:
    inicio_utc: "2026-07-23T18:17:25Z"
    fim_utc: "2026-08-12T15:44:41Z"
    dias: 20
  gerado_em: "2026-08-12"
  fonte:
    posthog_project_id: 430371
    total_eventos: 1484
    eventos_excluidos:
      teste_manual: 2
      malformados: 1

  ressalvas:
    - "Amostra de um unico desenvolvedor/maquina — nao representa base de usuarios."
    - "command_invoked com volume muito baixo (7) frente a agent_completed (803) — possivel lacuna de instrumentacao."
    - "67% do volume total concentrado no dia de geracao do relatorio (2026-08-12)."
    - "Ranking por dia da semana pouco confiavel devido ao pico do dia atual."

  contagem_por_tipo_evento:
    agent_completed: 803
    session_end: 554
    install: 76
    update: 34
    first_install: 10
    command_invoked: 7

  top_comandos:
    - {comando: "architect", chamadas: 2}
    - {comando: "push", chamadas: 1}
    - {comando: "status", chamadas: 1}
    - {comando: "sync-rules", chamadas: 1}
    - {comando: "pr", chamadas: 1}
    - {comando: "review", chamadas: 1}

  top_agentes_por_chamadas:
    - {agente: "backend-developer", chamadas: 195}
    - {agente: "frontend-developer", chamadas: 152}
    - {agente: "software-architect", chamadas: 90}
    - {agente: "security-specialist", chamadas: 73}
    - {agente: "devops-specialist", chamadas: 71}
    - {agente: "frontend-test-specialist", chamadas: 61}
    - {agente: "backend-test-specialist", chamadas: 54}
    - {agente: "test-author", chamadas: 45}
    - {agente: "qa-specialist", chamadas: 13}
    - {agente: "technical-writer", chamadas: 13}
    - {agente: "code-reviewer", chamadas: 12}
    - {agente: "product-analyst", chamadas: 12}
    - {agente: "backend-reviewer", chamadas: 6}
    - {agente: "frontend-reviewer", chamadas: 6}

  modelos_por_provider:
    claude:
      - {modelo: "claude-sonnet-5", chamadas: 570}
      - {modelo: "claude-opus-5[1m]", chamadas: 175}
      - {modelo: "claude-haiku-4-5-20251001", chamadas: 58}

  modelo_por_agente:
    backend-developer: "claude-sonnet-5"
    frontend-developer: "claude-sonnet-5"
    software-architect: "claude-opus-5[1m]"
    security-specialist: "claude-opus-5[1m]"
    devops-specialist: "claude-sonnet-5"
    frontend-test-specialist: "claude-sonnet-5"
    backend-test-specialist: "claude-sonnet-5"
    test-author: "claude-haiku-4-5-20251001"
    qa-specialist: "claude-sonnet-5"
    technical-writer: "claude-haiku-4-5-20251001"
    code-reviewer: "claude-sonnet-5"
    product-analyst: "claude-opus-5[1m]"
    backend-reviewer: "claude-sonnet-5"
    frontend-reviewer: "claude-sonnet-5"
    observacao: "Nenhum agente usou mais de um modelo na janela — sem desvio do mapeamento tiers.json."

  tokens_totais_janela:
    input: 959983
    output: 6890257
    cache_creation: 175567933
    cache_read: 2183534418
    proporcao_cache_read_input: "~2275:1"

  tokens_por_agente_total_desc:
    - {agente: "backend-developer", total: 693294212, chamadas: 195}
    - {agente: "frontend-developer", total: 388745340, chamadas: 152}
    - {agente: "test-author", total: 371111987, chamadas: 45}
    - {agente: "software-architect", total: 300079305, chamadas: 90}
    - {agente: "security-specialist", total: 179515358, chamadas: 73}
    - {agente: "frontend-test-specialist", total: 153399264, chamadas: 61}
    - {agente: "devops-specialist", total: 116652699, chamadas: 71}
    - {agente: "backend-test-specialist", total: 53496496, chamadas: 54}
    - {agente: "qa-specialist", total: 32014392, chamadas: 13}
    - {agente: "backend-reviewer", total: 19713773, chamadas: 6}
    - {agente: "frontend-reviewer", total: 17017787, chamadas: 6}
    - {agente: "technical-writer", total: 15180739, chamadas: 13}
    - {agente: "product-analyst", total: 14784210, chamadas: 12}
    - {agente: "code-reviewer", total: 11947029, chamadas: 12}

  tokens_por_agente_media_desc:
    - {agente: "test-author", media: 8246933}
    - {agente: "backend-developer", media: 3555354}
    - {agente: "software-architect", media: 3334214}
    - {agente: "backend-reviewer", media: 3285628}
    - {agente: "frontend-reviewer", media: 2836297}
    - {agente: "frontend-developer", media: 2557535}
    - {agente: "frontend-test-specialist", media: 2514742}
    - {agente: "qa-specialist", media: 2462645}
    - {agente: "security-specialist", media: 2459114}
    - {agente: "devops-specialist", media: 1642995}
    - {agente: "product-analyst", media: 1232017}
    - {agente: "technical-writer", media: 1167749}
    - {agente: "code-reviewer", media: 995585}
    - {agente: "backend-test-specialist", media: 990675}

  geografia:
    paises: [{nome: "Brasil", eventos: 1483}, {nome: "Franca", eventos: 1}]
    estados: [{nome: "Ceara", eventos: 1460}, {nome: "Sao Paulo", eventos: 23}, {nome: "Ile-de-France", eventos: 1}]
    cidades: [{nome: "Fortaleza", eventos: 1460}, {nome: "Bauru", eventos: 23}, {nome: "Aulnay-sous-Bois", eventos: 1}]

  versoes_top:
    - {versao: "v2.44.0", eventos: 891}
    - {versao: "v2.29.0", eventos: 149}
    - {versao: "v1.8.2", eventos: 111}
    - {versao: "v2.39.2", eventos: 99}
    - {versao: "v1.8.1", eventos: 46}
    - {versao: "desconhecida", eventos: 46}
    - {versao: "v2.31.0", eventos: 19}

  uso_por_dia_semana_utc:
    quarta: 1032
    quinta: 151
    sexta: 137
    sabado: 47
    terca: 47
    segunda: 43
    domingo: 30

  uso_por_hora_utc_pico:
    - {hora: 13, eventos: 298}
    - {hora: 1, eventos: 231}
    - {hora: 10, eventos: 188}
    - {hora: 14, eventos: 134}
    - {hora: 15, eventos: 117}

  instalacoes:
    first_install: 10
    install: 76
    update: 34
    proporcao_reinstall_para_novo: "~11:1"

  eficiencia_cache:
    proporcao_cache_read_input: "~2275:1"
    interpretacao: "positiva — alto reaproveitamento de contexto via prompt cache"

  fim_de_sessao:
    stop_hook_ativo_false: 532
    stop_hook_ativo_true: 22
    percentual_limpo: "96%"

  cobertura_zero_uso:
    agentes_sem_atividade:
      - "database-specialist"
      - "mobile-developer"
      - "ui-ux-designer"
      - "seo-specialist"
      - "setup-assistant"
    comandos_sem_atividade_confiavel: false
    motivo: "amostra de command_invoked pequena demais (7 eventos) para inferir cobertura"

  perguntas_em_aberto_para_proxima_janela:
    - "command_invoked continua sub-disparando em relacao a agent_completed?"
    - "version: desconhecida ainda aparece apos revisar ordem de leitura/escrita de state.json?"
    - "geografia ja reflete usuarios reais alem da maquina de desenvolvimento?"
```
