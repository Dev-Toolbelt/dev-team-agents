# Métricas de Uso DevTeam Agents — Últimos 20 Dias

**Janela:** 2026-07-23 15:17 → 2026-08-12 12:44, horário de `America/Sao_Paulo` (20 dias)
**Gerado em:** 2026-08-12
**Fuso horário usado nas métricas de tempo:** `America/Sao_Paulo` (UTC-3)
**Total de eventos na janela:** 1.484 (2 eventos manuais de teste `__manual_verification_test__` e 1 evento malformado com `agent_name`/`model` nulos excluídos de 1.487 linhas brutas)

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

## 2. Agentes mais invocados

Ranqueado por `agent_completed` (nenhum evento `agent_spawned` apareceu nesta janela, então a contagem de conclusões é usada como proxy). Top 10.

| Posição | Agente | Conclusões | % |
|---|---|---|---|
| 1 | **backend-developer** | 195 | 24,3% |
| 2 | frontend-developer | 152 | 18,9% |
| 3 | software-architect | 90 | 11,2% |
| 4 | security-specialist | 73 | 9,1% |
| 5 | devops-specialist | 71 | 8,8% |
| 6 | frontend-test-specialist | 61 | 7,6% |
| 7 | backend-test-specialist | 54 | 6,7% |
| 8 | test-author | 45 | 5,6% |
| 9 | qa-specialist | 13 | 1,6% |
| 9 | technical-writer | 13 | 1,6% |

**Conclusão:** `backend-developer` é o agente mais invocado (24,3% de todas as conclusões), seguido por `frontend-developer` (18,9%) — juntos, 43,2% de toda a atividade de agentes na janela.

---

## 3. Ranking de modelos agrupados por provider

| Provider | Modelo | Chamadas | % |
|---|---|---|---|
| claude | **claude-sonnet-5** | 570 | 71,0% |
| claude | claude-opus-5[1m] | 175 | 21,8% |
| claude | claude-haiku-4-5-20251001 | 58 | 7,2% |

**Conclusão:** toda a atividade registrada rodou na Claude — 71,0% em Sonnet 5, 21,8% em Opus 5 (contexto de 1M), 7,2% em Haiku 4.5. Nenhum outro provider apareceu na janela. (Os 2 eventos manuais `__manual_verification_test__`, rodados em `claude-sonnet-4-5`, foram excluídos deste ranking — ver nota no cabeçalho.)

---

## 4. Ranking de consumo de tokens

Total de tokens (input + output + cache_creation + cache_read) por agente, em ordem decrescente. Top 10.

| Posição | Agente | Total de tokens | % | Chamadas |
|---|---|---|---|---|
| 1 | **backend-developer** | 693.294.212 | 29,3% | 195 |
| 2 | frontend-developer | 388.745.340 | 16,4% | 152 |
| 3 | test-author | 371.111.987 | 15,7% | 45 |
| 4 | software-architect | 300.079.305 | 12,7% | 90 |
| 5 | security-specialist | 179.515.358 | 7,6% | 73 |
| 6 | frontend-test-specialist | 153.399.264 | 6,5% | 61 |
| 7 | devops-specialist | 116.652.699 | 4,9% | 71 |
| 8 | backend-test-specialist | 53.496.496 | 2,3% | 54 |
| 9 | qa-specialist | 32.014.392 | 1,4% | 13 |
| 10 | backend-reviewer | 19.713.773 | 0,8% | 6 |

**Totais da janela:** input 959.983 · output 6.890.257 · cache creation 175.567.933 · **cache read 2.183.534.418**

**Conclusão:** `backend-developer` lidera tanto em número de chamadas quanto em tokens totais. Os tokens de cache-read dominam o total por larga margem em todos os agentes (ver § 12).

---

## 5. Agentes que mais consomem tokens em média (por chamada)

Top 10.

| Posição | Agente | Média de tokens/chamada | % | Chamadas |
|---|---|---|---|---|
| 1 | **test-author** | 8.246.933 | 22,1% | 45 |
| 2 | backend-developer | 3.555.354 | 9,5% | 195 |
| 3 | software-architect | 3.334.214 | 8,9% | 90 |
| 4 | backend-reviewer | 3.285.628 | 8,8% | 6 |
| 5 | frontend-reviewer | 2.836.297 | 7,6% | 6 |
| 6 | frontend-developer | 2.557.535 | 6,9% | 152 |
| 7 | frontend-test-specialist | 2.514.742 | 6,7% | 61 |
| 8 | qa-specialist | 2.462.645 | 6,6% | 13 |
| 9 | security-specialist | 2.459.114 | 6,6% | 73 |
| 10 | devops-specialist | 1.642.995 | 4,4% | 71 |

*(`command_invoked` não carrega dados de token, então a média por comando não pode ser calculada a partir deste evento. `%` é a participação de cada agente na soma das médias de todos os agentes.)*

**Conclusão:** `test-author` tem, de longe, a maior média por chamada (2,3× o segundo colocado) apesar de um volume de chamadas mediano — cada invocação faz um trabalho de contexto incomumente grande em relação aos seus pares.

---

## 6. Ranking de país, estado e cidade

| País | Eventos | % |
|---|---|---|
| **Brasil** | 1.483 | 99,9% |
| França | 1 | 0,1% |

| Estado/Região | Eventos | % |
|---|---|---|
| **Ceará** | 1.460 | 98,4% |
| São Paulo | 23 | 1,5% |
| Île-de-France | 1 | 0,1% |

| Cidade | Eventos | % |
|---|---|---|
| **Fortaleza** | 1.460 | 98,4% |
| Bauru | 23 | 1,5% |
| Aulnay-sous-Bois | 1 | 0,1% |

> 🔒 **Nota de privacidade (fora do escopo deste relatório, já resolvida):** a correção de anonimização de IP no backend de telemetria não é retroativa — a maioria dos eventos desta janela de 20 dias foi ingerida **antes** da correção e ainda retém a propriedade `$ip` bruta armazenada (identificado na execução anterior deste relatório, em 2026-08-12). Apenas eventos capturados a partir da ativação deixam de reter o IP. A janela de 20 dias precisa "rolar" além da data da correção para essa nota desaparecer de futuras execuções deste relatório.

---

## 7. Ranking das versões usadas no período

Top 10.

| Posição | Versão | Eventos | % |
|---|---|---|---|
| 1 | **v2.44.0** | 891 | 60,0% |
| 2 | v2.29.0 | 149 | 10,0% |
| 3 | v1.8.2 | 111 | 7,5% |
| 4 | v2.39.2 | 99 | 6,7% |
| 5 | v1.8.1 | 46 | 3,1% |
| 5 | *desconhecida* | 46 | 3,1% |
| 7 | v2.31.0 | 19 | 1,3% |
| 8 | v1.11.0 | 16 | 1,1% |
| 9 | v2.15.1 | 10 | 0,7% |
| 10 | v2.30.1 | 9 | 0,6% |

**Conclusão:** `v2.44.0` (a ponta atual) domina com 60,0% dos eventos, esperado já que a maior parte do volume é da sessão de hoje. A cauda longa de versões antigas (v1.8.x, v2.7–v2.41.x) reflete eventos históricos retidos dentro da janela de 20 dias, não instalações concorrentes. `desconhecida` (46 eventos, 3,1%) vem de eventos `install`/`update`/`agent_completed` capturados antes da versão ser resolvida.

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

## 9. Dias e horários de maior uso (`America/Sao_Paulo`)

**Por dia da semana:**

| Dia | Eventos | % |
|---|---|---|
| **Quarta-feira** | 770 | 51,9% |
| Terça-feira | 318 | 21,4% |
| Quinta-feira | 176 | 11,9% |
| Sexta-feira | 115 | 7,7% |
| Segunda-feira | 46 | 3,1% |
| Domingo | 31 | 2,1% |
| Sábado | 28 | 1,9% |

**Por hora do dia:**

| Hora | Eventos | % |
|---|---|---|
| 00 | 28 | 1,9% |
| 01 | 17 | 1,1% |
| 02 | 1 | 0,1% |
| 03 | 9 | 0,6% |
| 04 | 14 | 0,9% |
| 05 | 0 | 0,0% |
| 06 | 0 | 0,0% |
| **07** | **188** | **12,7%** |
| 08 | 14 | 0,9% |
| 09 | 11 | 0,7% |
| **10** | **298** | **20,1%** |
| 11 | 134 | 9,0% |
| 12 | 117 | 7,9% |
| 13 | 18 | 1,2% |
| 14 | 25 | 1,7% |
| 15 | 40 | 2,7% |
| 16 | 49 | 3,3% |
| 17 | 41 | 2,8% |
| 18 | 25 | 1,7% |
| 19 | 52 | 3,5% |
| 20 | 33 | 2,2% |
| 21 | 46 | 3,1% |
| **22** | **231** | **15,6%** |
| 23 | 93 | 6,3% |

**Conclusão:** ⚠️ fortemente enviesado pelo dia de hoje (2026-08-12, uma quarta-feira, contribuiu com 719 dos 1.484 eventos — ver a tendência diária na § 11). Os horários de pico em `America/Sao_Paulo`, 10h, 22h e 07h, consistentes com um padrão de trabalho no final da noite e meio da manhã para esse único contribuidor. Trate o ranking por dia da semana como pouco confiável até o volume ficar mais distribuído ao longo de semanas.

---

## 10. Taxa de novas instalações vs atualizações

| Evento | Contagem |
|---|---|
| `first_install` | 10 |
| `install` (reinstalação/atualização via instalador) | 76 |
| `update` (atualização manual via `update.sh`) | 34 |

**Conclusão:** reinstalações/atualizações superam instalações novas em ~11:1 nesta janela — esperado para uma cópia local em desenvolvimento ativo, reinstalada/atualizada repetidamente durante testes, não crescimento orgânico de novos usuários.

---

## 11. Volume de eventos por dia (`America/Sao_Paulo`)

| Data | Eventos | % |
|---|---|---|
| 2026-07-23 | 39 | 2,6% |
| 2026-07-24 | 103 | 6,9% |
| 2026-07-25 | 18 | 1,2% |
| 2026-07-26 | 18 | 1,2% |
| 2026-07-27 | 5 | 0,3% |
| 2026-07-28 | 22 | 1,5% |
| 2026-07-29 | 4 | 0,3% |
| 2026-07-30 | 2 | 0,1% |
| 2026-07-31 | 7 | 0,5% |
| 2026-08-01 | 4 | 0,3% |
| 2026-08-02 | 9 | 0,6% |
| 2026-08-03 | 34 | 2,3% |
| 2026-08-04 | 6 | 0,4% |
| 2026-08-05 | 47 | 3,2% |
| 2026-08-06 | 135 | 9,1% |
| 2026-08-07 | 5 | 0,3% |
| 2026-08-08 | 6 | 0,4% |
| 2026-08-09 | 4 | 0,3% |
| 2026-08-10 | 7 | 0,5% |
| 2026-08-11 | 290 | 19,5% |
| **2026-08-12** | **719** | **48,4%** |

**Conclusão:** a janela é dominada pelo dia atual (48,4% do volume total) — consistente com este relatório sendo gerado no meio da sessão de 2026-08-12. Excluindo hoje, 2026-08-11 (290, arraste de eventos que caem cedo em UTC mas ainda no dia anterior em `America/Sao_Paulo`) e 2026-08-06 (135) foram os dias de maior volume seguintes.

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

Cruzando os nomes observados de `agent_completed` com o roster de agentes em `agents/*.md` (18 agentes no total).

**Agentes sem atividade nesta janela:**

| Agente | Conclusões |
|---|---|
| database-specialist | 0 |
| mobile-developer | 0 |
| ui-ux-designer | 0 |
| seo-specialist | 0 |
| setup-assistant | 0 |

**Cobertura de comandos:**

| Métrica | Valor |
|---|---|
| Comandos documentados (`scripts/lib/commands.json`) | ~25 |
| Comandos observados na janela | 6 (`architect`, `push`, `status`, `sync-rules`, `pr`, `review`) |
| Amostra confiável para inferir cobertura | Não — volume de `command_invoked` (7 eventos) suspeitosamente baixo frente a `agent_completed` (803), ver § 1 |

---

## Resumo estruturado para leitura por LLMs

```yaml
relatorio:
  titulo: "Metricas de uso DevTeam Agents — Ultimos 20 dias"
  janela:
    inicio_america_sao_paulo: "2026-07-23T15:17:25-03:00"
    fim_america_sao_paulo: "2026-08-12T12:44:41-03:00"
    dias: 20
    timezone: "America/Sao_Paulo"
  gerado_em: "2026-08-12"
  total_eventos: 1484
  eventos_excluidos:
    teste_manual: 2
    malformados: 1

  ressalvas:
    - "Amostra de um unico desenvolvedor/maquina — nao representa base de usuarios."
    - "command_invoked com volume muito baixo (7) frente a agent_completed (803) — possivel lacuna de instrumentacao."
    - "48% do volume total concentrado no dia de geracao do relatorio (2026-08-12, America/Sao_Paulo)."
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
    - {agente: "backend-developer", chamadas: 195, percentual: 24.3}
    - {agente: "frontend-developer", chamadas: 152, percentual: 18.9}
    - {agente: "software-architect", chamadas: 90, percentual: 11.2}
    - {agente: "security-specialist", chamadas: 73, percentual: 9.1}
    - {agente: "devops-specialist", chamadas: 71, percentual: 8.8}
    - {agente: "frontend-test-specialist", chamadas: 61, percentual: 7.6}
    - {agente: "backend-test-specialist", chamadas: 54, percentual: 6.7}
    - {agente: "test-author", chamadas: 45, percentual: 5.6}
    - {agente: "qa-specialist", chamadas: 13, percentual: 1.6}
    - {agente: "technical-writer", chamadas: 13, percentual: 1.6}

  modelos_por_provider:
    claude:
      - {modelo: "claude-sonnet-5", chamadas: 570, percentual: 71.0}
      - {modelo: "claude-opus-5[1m]", chamadas: 175, percentual: 21.8}
      - {modelo: "claude-haiku-4-5-20251001", chamadas: 58, percentual: 7.2}

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

  tokens_por_agente_total_desc_top10:
    - {agente: "backend-developer", total: 693294212, percentual: 29.3, chamadas: 195}
    - {agente: "frontend-developer", total: 388745340, percentual: 16.4, chamadas: 152}
    - {agente: "test-author", total: 371111987, percentual: 15.7, chamadas: 45}
    - {agente: "software-architect", total: 300079305, percentual: 12.7, chamadas: 90}
    - {agente: "security-specialist", total: 179515358, percentual: 7.6, chamadas: 73}
    - {agente: "frontend-test-specialist", total: 153399264, percentual: 6.5, chamadas: 61}
    - {agente: "devops-specialist", total: 116652699, percentual: 4.9, chamadas: 71}
    - {agente: "backend-test-specialist", total: 53496496, percentual: 2.3, chamadas: 54}
    - {agente: "qa-specialist", total: 32014392, percentual: 1.4, chamadas: 13}
    - {agente: "backend-reviewer", total: 19713773, percentual: 0.8, chamadas: 6}

  tokens_por_agente_media_desc_top10:
    - {agente: "test-author", media: 8246933, percentual: 22.1}
    - {agente: "backend-developer", media: 3555354, percentual: 9.5}
    - {agente: "software-architect", media: 3334214, percentual: 8.9}
    - {agente: "backend-reviewer", media: 3285628, percentual: 8.8}
    - {agente: "frontend-reviewer", media: 2836297, percentual: 7.6}
    - {agente: "frontend-developer", media: 2557535, percentual: 6.9}
    - {agente: "frontend-test-specialist", media: 2514742, percentual: 6.7}
    - {agente: "qa-specialist", media: 2462645, percentual: 6.6}
    - {agente: "security-specialist", media: 2459114, percentual: 6.6}
    - {agente: "devops-specialist", media: 1642995, percentual: 4.4}

  geografia:
    paises: [{nome: "Brasil", eventos: 1483, percentual: 99.9}, {nome: "Franca", eventos: 1, percentual: 0.1}]
    estados: [{nome: "Ceara", eventos: 1460, percentual: 98.4}, {nome: "Sao Paulo", eventos: 23, percentual: 1.5}, {nome: "Ile-de-France", eventos: 1, percentual: 0.1}]
    cidades: [{nome: "Fortaleza", eventos: 1460, percentual: 98.4}, {nome: "Bauru", eventos: 23, percentual: 1.5}, {nome: "Aulnay-sous-Bois", eventos: 1, percentual: 0.1}]

  versoes_top10:
    - {versao: "v2.44.0", eventos: 891, percentual: 60.0}
    - {versao: "v2.29.0", eventos: 149, percentual: 10.0}
    - {versao: "v1.8.2", eventos: 111, percentual: 7.5}
    - {versao: "v2.39.2", eventos: 99, percentual: 6.7}
    - {versao: "v1.8.1", eventos: 46, percentual: 3.1}
    - {versao: "desconhecida", eventos: 46, percentual: 3.1}
    - {versao: "v2.31.0", eventos: 19, percentual: 1.3}
    - {versao: "v1.11.0", eventos: 16, percentual: 1.1}
    - {versao: "v2.15.1", eventos: 10, percentual: 0.7}
    - {versao: "v2.30.1", eventos: 9, percentual: 0.6}

  uso_por_dia_semana_america_sao_paulo:
    quarta: {eventos: 770, percentual: 51.9}
    terca: {eventos: 318, percentual: 21.4}
    quinta: {eventos: 176, percentual: 11.9}
    sexta: {eventos: 115, percentual: 7.7}
    segunda: {eventos: 46, percentual: 3.1}
    domingo: {eventos: 31, percentual: 2.1}
    sabado: {eventos: 28, percentual: 1.9}

  uso_por_hora_america_sao_paulo_top3:
    - {hora: 10, eventos: 298, percentual: 20.1}
    - {hora: 22, eventos: 231, percentual: 15.6}
    - {hora: 7, eventos: 188, percentual: 12.7}

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
