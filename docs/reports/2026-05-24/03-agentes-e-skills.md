# Agentes e Skills — 2026-05-24

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negativos** da correção proposta. Todas foram cruzadas contra o banco de 493 fingerprints (`_index.md`) e são inéditas.

---

## A1 — A skill compartilhada `architecture-awareness` (comportamental, **não** de detecção) enumera frameworks concretos no corpo e é **eager-loaded** por 3 agentes de código — o mesmo conteúdo stack-prescritivo que o projeto vem removendo dos agentes vive agora na skill canônica

**Severidade:** MEDIUM-HIGH
**Fingerprint:** `skill-architecture-awareness-shared-behavioral-skill-enumerates-react-vue-svelte-angular-blade-twig-erb-jinja-laravel-django-rails-eager-loaded-by-three-coding-agents`

**Evidência** — `skills/shared/architecture-awareness/SKILL.md`:

```
:10  Decoupled SPA: React, Vue, Svelte, Angular consuming an API …
:14  … run vite-bundle-visualizer, webpack-bundle-analyzer, or equivalent …
:17  Server-rendered templates: Blade, Twig, ERB, Jinja, Handlebars …
:27  Monolithic (server-rendered): … (Laravel+Blade, Django+Templates, Rails+ERB, etc.)
```

Carregada **eager** (no Foundational Rule) por:

```
agents/backend-developer.md:39   Load skills/shared/architecture-awareness/SKILL.md …
agents/frontend-developer.md:65  Load skills/shared/architecture-awareness/SKILL.md …
agents/mobile-developer.md:52    Load skills/shared/architecture-awareness/SKILL.md …
```

**Motivo:** o projeto já flagrou e removeu listas de frameworks dos **corpos/descrições** de `frontend-developer` (React/Vue/Svelte/Angular + Blade/Twig/ERB/Jinja), `devops`, `database` e `mobile`. Mas a `architecture-awareness` — a skill que é a **fonte canônica** desse conhecimento e é carregada eager por 3 agentes — ainda contém a lista idêntica (mais Handlebars e ferramentas de bundle). Diferente de skills de **detecção/roteamento** (`auto-routing`, `spawn-classifier`, `stack-detection`, `review-router`), onde nomear frameworks é necessário para detectar, a `architecture-awareness` é **comportamental** (orienta foco em SPA vs server-rendered) — nomear React/Laravel/Django aqui é a mesma violação stack-prescritiva já corrigida nos agentes, só que num andar abaixo. Distinto dos fingerprints `token-architecture-awareness-block-duplicate/still-duplicated`, que tratavam da **duplicação** do bloco entre agentes (token), não da prescritividade **da skill**.

**Impacto positivo da correção:** reescrever em termos de **categorias** ("SPA desacoplada consumindo uma API"; "templates renderizados no servidor") e mover os exemplos concretos para a tabela de detecção (`stack-detection`/`auto-routing`) restaura a conformidade stack-agnostic na fonte canônica — fechando a classe de uma vez para os 3 agentes que a carregam.

**Impacto negativo / risco:** baixo. Risco de perder a ancoragem prática que os exemplos dão ao LLM — mitigável mantendo **um** exemplo neutro por categoria ("ex.: um SPA que consome uma API") em vez da enumeração completa, ou apontando para a `stack-detection` quando o nome concreto for necessário.

---

## A2 — A skill `user-preferences` (fonte de defaults do `setup-assistant` ao criar `preferences.json`) está **defasada** do schema autoritativo — faltam `transcript_multiplier`, `model_max_tokens` e `telemetry`; um `preferences.json` criado por ela nasce **incompleto**

**Severidade:** MEDIUM
**Fingerprint:** `skill-user-preferences-stale-missing-transcript-multiplier-model-max-tokens-telemetry-vs-authoritative-schema-setup-assistant-creates-incomplete-preferences-json`

**Evidência:**

```
# setup-assistant usa a skill para criar o arquivo
agents/setup-assistant.md:115  … create it with all defaults from
                               skills/shared/user-preferences/SKILL.md and the chosen language …

# Chaves presentes em cada fonte (deveriam bater)
skills/shared/user-preferences/SKILL.md →  9 chaves
CLAUDE-md/preferences.md (autoritativo) → 12 chaves
scripts/install.sh                       → 12 chaves

# Faltando na skill:
- transcript_multiplier
- model_max_tokens
- telemetry
```

**Motivo:** há **três** lugares que descrevem o schema de preferências (install.sh, `CLAUDE-md/preferences.md`, e esta skill) e **dois** caminhos que criam o `preferences.json`: o `install.sh` (que foi corrigido em `1aa5787` para incluir `transcript_multiplier`/`model_max_tokens`) e o `setup-assistant` (que cria via esta skill). A correção foi aplicada **só ao caminho do installer** — a skill ficou para trás e nem ganhou `telemetry`. Resultado: um `preferences.json` criado pelo `setup-assistant` nasce sem 3 chaves, violando a regra explícita do próprio `preferences.md:39` ("Never leave a key out — the schema above is the authoritative default set"). O fallback de defaults evita erro em runtime, mas o usuário fica sem as chaves para ajustar (inclusive o opt-out de telemetria). Distinto de `ref-install-fallback-prefs-missing-transcript-multiplier` (que era sobre o **install.sh**, já corrigido): aqui o consumidor defasado é a **skill** usada pelo `setup-assistant`.

**Impacto positivo da correção:** sincronizar a skill com as 12 chaves canônicas garante que ambos os caminhos de criação produzam o mesmo arquivo completo. Melhor ainda: fazer a skill **referenciar** o schema de `CLAUDE-md/preferences.md` em vez de recopiá-lo, eliminando a terceira cópia divergente.

**Impacto negativo / risco:** baixo. Sem a sincronização, o pior caso é cosmético (usuário não vê `telemetry`/`model_max_tokens` no arquivo) graças ao fallback — mas é exatamente o tipo de deriva silenciosa que o projeto combate. Mitigação: fonte única + um teste que compare as chaves dos três pontos.

---

## A3 — A `description` do `backend-developer` enumera paradigmas (REST API, GraphQL, MVC, server-rendered templates) na **superfície de identidade**, enquanto o corpo declara "not attached to any specific stack" — último agente de código da família description não auditado

**Severidade:** LOW-MEDIUM
**Fingerprint:** `agent-backend-developer-description-enumerates-rest-graphql-mvc-server-rendered-paradigms-on-identity-surface-last-coding-agent-desc-while-body-claims-stack-agnostic`

**Evidência** — `agents/backend-developer.md`:

```
:3  description: … Works in both decoupled (REST API, GraphQL) and
                  monolithic (MVC, server-rendered templates) architectures …
:9  You are not attached to any specific stack — you adapt to the
    project's technology and conventions.
```

**Motivo:** depois que `devops`, `database`, `mobile` e `frontend` tiveram suas descriptions flagradas por enumerar tecnologias na identidade, o `backend-developer` é o **último agente de código cuja description nunca foi auditada** nesse eixo — e ela **enumera** (REST API, GraphQL, MVC, server-rendered templates). **Ressalva honesta de severidade:** ao contrário das outras (que listavam **produtos** — MySQL, React, Swift), estas são **paradigmas/estilos arquiteturais**, não frameworks/linguagens/ferramentas — portanto bem mais brandas e, num leitura estrita do "no hardcoded **framework, language, or tool**", arguivelmente **conformes**. O que sustenta o achado não é a violação dura, e sim a **tensão interna**: a linha 9 do corpo afirma explicitamente neutralidade de stack enquanto a linha 3 fixa paradigmas concretos. Vale uma **decisão consciente** de consistência (manter ou generalizar para "API-first vs server-rendered"), não uma correção urgente.

**Impacto positivo da correção:** se generalizada ("works across API-first and server-rendered backend architectures"), a description fica alinhada com a linha 9 e com o padrão já aplicado aos outros agentes, encerrando a família de descriptions de uma vez.

**Impacto negativo / risco:** baixíssimo, mas com **risco de over-correção**: "REST"/"GraphQL"/"MVC" são vocabulário universal que ajuda o roteamento a entender o escopo do agente; removê-los por purismo pode reduzir clareza sem ganho real de neutralidade. Por isso o item é **LOW** e enquadrado como decisão de consistência, não como bug.
