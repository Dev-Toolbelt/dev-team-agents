# Referências e Consistência — 2026-05-21

> 3 sugestões originais. Cada item traz **trecho/evidência**, **motivo** e **impactos positivos e negríativos** da correção proposta. Todas foram cruzadas contra o banco de 437 fingerprints (`_index.md`) e são inéditas.

---

## R1 — `graphify-setup` cria sub-script de Stop com prefixo `02-`, violando a convenção de tiers (cleanup → `99-`) e colidindo com `02-orphan-skill-scan.sh`

**Severidade:** MEDIUM
**Fingerprint:** `ref-graphify-setup-stop-subscript-prefix-02-violates-cleanup-99-tier-collides-with-orphan-skill-scan-propagated-three-files`

**Evidência** — `skills/devops/graphify-setup/SKILL.md:160-166`:

```bash
cat > .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh << 'EOF'
#!/usr/bin/env bash
# Stop sub-script: rebuild the Graphify knowledge graph after each session.
set -euo pipefail
bash "$(...)/scripts/graphify-refresh.sh"
EOF
```

A convenção de sub-scripts de Stop (CLAUDE.md, seção "Stop Hook Sub-script Convention") define tiers explícitos:

| Prefixo | Reservado para |
|---------|----------------|
| `01-` | Coleta de estado |
| `02-` | **Checagens de integridade do repositório** |
| `03-` | Validação estática |
| `04-` | Notificações |
| `05-` | Telemetria |
| `99-` | **Tarefas finais / cleanup** |

**Motivo:** um *rebuild* de grafo de conhecimento é uma tarefa de finalização/cleanup — pertence ao tier **`99-`**, não ao `02-` (integridade de repo). Pior: em um projeto com Graphify habilitado, a ordenação alfabética do dispatcher coloca `02-graphify-refresh.sh` **antes** de `02-orphan-skill-scan.sh` (`g` < `o`), fazendo um rebuild rodar no meio do tier de integridade. O prefixo errado ainda é **propagado em 3 lugares**: `graphify-setup/SKILL.md` (gerador), `skills/shared/setup-health-check/references/checks-list.md:71,79` (health check valida o nome errado) e `agents/setup-assistant.md:146` (menciona o registro). Distinto de `ref-claude-md-356-stop-subscript-convention-omits-02b-...` (2026-05-19), que era sobre o `02b` do próprio repo na tabela; aqui o problema é uma skill **gerando** um sub-script no tier errado nos projetos dos usuários.

**Impacto positivo da correção:** alinha o sub-script gerado à própria convenção do projeto; elimina a colisão de ordenação com a checagem de integridade; corrige a fonte (skill) e os dois consumidores que validam/documentam o nome.

**Impacto negativo / risco:** projetos já existentes terão um `02-graphify-refresh.sh` legado; será preciso uma etapa de migração no `setup-health-check` (detectar o `02-` antigo e renomear para `99-`) para não deixar dois sub-scripts. Mudança coordenada em 3 arquivos.

---

## R2 — `CODEOWNERS` tem lacunas de cobertura assimétricas: `helpers/`, par README e 5 domínios de skill ficam sem revisor obrigatório

**Severidade:** MEDIUM
**Fingerprint:** `gov-codeowners-coverage-gaps-helpers-readme-pair-canonical-docs-and-skill-domains-unowned-asymmetric`

**Evidência** — `.github/CODEOWNERS` (íntegro). Domínios de skill cobertos: `architecture/`, `security/`, `devops/`, `database/`, `testing/`. **Não cobertos:** `integrations/`, `ui-libraries/`, `mobile/`, `design/`, `skill-creator/`. Também sem regra de ownership: `helpers/` (scripts de runtime, incluindo `telemetry-send.sh`), `README.md` / `README.pt-BR.md`, `docs/agents.md` / `docs/installation.md` (referências canônicas), `CLAUDE-md/` e `.github/` (o próprio CODEOWNERS).

**Motivo:** o arquivo declara intenção de "Core package files — maintainer review required", mas a cobertura é incompleta e assimétrica. Em particular:

- `helpers/` contém os scripts shellcheck'ados no CI e a telemetria — são *runtime sensível* e ficam sem revisor obrigatório.
- `README.md` / `README.pt-BR.md` são governados por uma **regra de sincronização estrita** (CLAUDE.md: "README Sync Rule") e mesmo assim não exigem revisor — exatamente os arquivos onde drift é mais provável.
- Metade dos domínios de skill exige revisão e a outra metade não, sem critério documentado para a diferença.

Distinto de `ref-no-codeowners-file` (2026-05-09): o arquivo agora existe; o achado é sobre **lacunas de cobertura**, não ausência.

**Impacto positivo da correção:** fecha o gap de governança nos arquivos mais sensíveis (runtime + docs com sync rule); torna a política de ownership consistente entre domínios de skill.

**Impacto negativo / risco:** mais revisões obrigatórias podem adicionar fricção em PRs pequenos (ex.: ajustes de doc). Mitigável usando um glob amplo (`skills/` inteiro) em vez de enumerar domínios um a um, e mantendo `docs/reports/` sem owner (auto-gerado). Requer que o time `@Dev-Toolbelt/maintainers` exista e tenha membros suficientes para não virar gargalo.

---

## R3 — File Structure da CLAUDE.md: a subárvore `skills/` omite `database/`, `mobile/` e `skill-creator/` (3 de 11 domínios)

**Severidade:** LOW-MEDIUM
**Fingerprint:** `ref-claude-md-file-structure-skills-subtree-omits-database-mobile-skill-creator-three-of-eleven-domains`

**Evidência** — `CLAUDE.md`, bloco "File Structure", subárvore `skills/`:

```
├── skills/
│   ├── shared/
│   ├── architecture/
│   ├── testing/
│   ├── security/
│   ├── design/
│   ├── devops/      ← one skill per platform
│   ├── integrations/
│   └── ui-libraries/
```

Lista 8 domínios. O diretório real tem **11**:

```
architecture  database  design  devops  integrations
mobile  security  shared  skill-creator  testing  ui-libraries
```

Faltam **`database/`**, **`mobile/`** e **`skill-creator/`**. (Bônus: só `devops/` carrega anotação "one skill per platform"; as demais não têm anotação, gerando inconsistência visual.)

**Motivo:** é a referência estrutural canônica do projeto. `database/` e `mobile/` têm agentes dedicados (`database-specialist`, `mobile-developer`) e várias skills cada; `skill-creator/` é uma skill user-invocável registrada na própria CLAUDE.md. Omiti-los da árvore induz a erro quem usa o documento como mapa. Distinto dos achados anteriores de File Structure — aqueles eram sobre diretórios de topo (`helpers/`, `PRIVACY.md`, `CLAUDE-md/`, 2026-05-18) e sobre a enumeração de `scripts/` (2026-05-20); este é especificamente sobre a **subárvore de `skills/`**.

**Impacto positivo da correção:** referência canônica passa a refletir a realidade do repo; reduz risco de um agente/autor "não encontrar" um domínio que existe. Correção de baixíssimo risco (apenas documentação).

**Impacto negativo / risco:** praticamente nulo. Atenção apenas para replicar a edição em `README.pt-BR.md`/docs traduzidos se a árvore for espelhada lá, conforme a "README Sync Rule".
