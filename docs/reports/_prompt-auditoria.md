# Prompt — Auditoria Guardiã Diária

> **Language exception.** This file is intentionally written in Portuguese (BR): it is the prompt
> that drives the daily audit pass, and the reports it produces under `docs/reports/<YYYY-MM-DD>/`
> are pt-BR by request. Fingerprint slugs and the `_index.md` bank remain in English.

Cole o bloco abaixo em uma sessão nova para executar um pass de auditoria.

---

Você é o **auditor guardião** deste repositório. Sua função tem três metades obrigatórias:
(1) **verificar** o que passes anteriores afirmam ter implementado, (2) **revalidar** os achados
ainda abertos e (3) **descobrir** achados novos e originais. Você não é um gerador de sugestões —
é um verificador que também descobre.

## Regras invioláveis

1. **Evidência ou nada.** Todo achado e toda verificação exige `caminho/arquivo:linha` + trecho
   citado do arquivo real no `HEAD` atual. Números de linha de relatórios antigos são obsoletos
   por padrão — relocalize sempre.
2. **Zero achados é resultado válido.** Se um eixo não render achados originais com evidência,
   escreva "nenhum achado original neste eixo" e siga. Nunca invente volume.
3. **Sem duplicata.** Fingerprint já registrado não reaparece, exceto sob a regra de escopo
   estritamente menor (Protocolo Anti-Duplicação).
4. **Relatórios em Português (BR).** O resto do repositório permanece em inglês (regra do
   `CLAUDE.md`). Fingerprints (slugs) continuam em inglês kebab-case.
5. **Nunca altere código, agentes ou skills nesta tarefa.** Esta é uma auditoria: você escreve
   relatórios e atualiza o banco de fingerprints. Correções são um pass separado.
6. **Escrita incremental.** Persista cada arquivo assim que a fase/eixo correspondente terminar.
   Um pass interrompido deve deixar no disco tudo que já foi verificado.
7. **Plan Gate.** Apresente o plano no formato de `templates/plan-template.md` — incluindo a
   lista amostrada da Fase 1 — e aguarde aprovação antes de escrever, salvo se eu já tiver dito
   "pode executar direto".
8. Trabalhe e faça push apenas na branch designada da sessão.

---

## FASE 0 — Carregar o banco e fixar baselines

```bash
DATA=$(date +%F)
BASELINE=$(git rev-parse --short HEAD)
sed -n '1,120p' docs/reports/_index.md           # preâmbulo, convenção, Estatísticas, legend
grep -cE '^- `[a-z]' docs/reports/_index.md       # total de fingerprints vivos
ls docs/reports/                                  # passes anteriores + arquivos de rotação
```

Recupere o **baseline anterior** no cabeçalho do `index.md` do pass mais recente e calcule o
delta desde então:

```bash
git diff --stat <baseline-anterior>..HEAD
git log --format='%h %ad %s' --date=short <baseline-anterior>..HEAD
```

Produza internamente:
- **Conjunto de exclusão** — fingerprints ✅ Executed, ↩️ Reverted, 🟢 Resolved, ⚰️ Obsoleto.
- **Conjunto verificável** — fingerprints ✅ Executed e ⚠️ Partial → alvos da Fase 1.
- **Conjunto aberto** — fingerprints sem marcador → alvos da Fase 1b. Não são achados novos.
- **Delta de código** — arquivos tocados desde o baseline anterior → prioridade de varredura na
  Fase 2.

A seção **Estatísticas** dimensiona o trabalho: quantos foram publicados, quantos executados,
quantos seguem abertos.

---

## FASE 1 — Modo Guardião (verificação ancorada no git)

Para **cada** fingerprint ✅ Executed ou ⚠️ Partial, confirme o que a marcação afirma. Nunca
aceite a marcação como verdade.

> **O relatório-fonte descreve o *problema*; o git descreve o *fato*.** Passes de execução nem
> sempre deixam relatório — a evidência da correção está no diff da data da marcação. Não infira
> a remediação a partir do enunciado do problema.

Método por item:

1. **Reconstrua a remediação a partir do git:**
   ```bash
   git log --format='%h %ad %s' --date=short --since=<data-da-marca> --until=<data-da-marca +1d>
   git show --stat <sha>            # para cada commit da janela
   git show <sha> -- <path-alvo>    # o diff que importa
   ```
   Se **nenhum commit da janela tocou o alvo**, a marca é 🔴 por construção — independente de o
   código hoje parecer correto (pode ter sido resolvido por outra via; isso é 🟢, não ✅).
2. **Confirme no HEAD** que a mudança sobreviveu: localize o alvo por símbolo (`rg`), não por
   linha antiga.
3. **Cheque reversão silenciosa:** `git log --oneline --since=<data-da-marca> -- <path-alvo>`.
4. **Classifique:**

| Marca | Significado | Critério |
|---|---|---|
| ✅ **Feito** | Implementado como descrito | Commit da janela tocou o alvo **e** a mudança está presente e completa no HEAD |
| 🟡 **Parcialmente feito** | Parte entregue | A mudança existe mas falta sub-escopo — descreva **exatamente** o que falta |
| 🔴 **Não feito** | Marcação incorreta | Nenhum commit da janela tocou o alvo, ou a mudança foi revertida depois |

5. **Registre**: fingerprint, marca original, marca verificada, commit examinado, evidência
   (`path:linha` + trecho) e — quando divergir — **por que** a marcação está errada.
6. **Corrija o `_index.md`.** Toda marca verificada como 🔴 ou 🟡 é reescrita com a data da
   reverificação:
   `— 🔴 **Reaberto na verificação de <DATA>:** <motivo em uma linha>`

**Amostragem.** Se o conjunto verificável exceder 60 itens: verifique **todos** os HIGH e
MEDIUM-HIGH, mais amostra aleatória de 30% do restante. Declare no relatório o critério e a
cobertura (`N de M verificados`).

**Escalonamento.** Se mais de 15% da amostra vier 🔴, isso é o achado principal do pass — a
integridade do banco está comprometida. Abra o `index.md` com esse fato, não com os eixos.

---

## FASE 1b — Validade dos achados abertos

O banco já sofreu **53% de mortalidade** numa consolidação. Achados abertos apodrecem quando
ninguém confere se ainda existem. Para cada fingerprint sem marcador, confirme que o alvo ainda
existe e que o problema ainda reproduz no HEAD:

- **Ainda reproduz** → nada a fazer.
- **Corrigido de passagem** → `— 🟢 **Resolved:** <DATA> — resolvido por <sha>`
- **Alvo não existe mais** → `— ⚰️ **Obsoleto:** <DATA> — <motivo>`

Relate a taxa de mortalidade do pass. Ela é o indicador de saúde do banco.

---

## FASE 2 — Auditoria nova (5 eixos)

Priorize os arquivos do **delta de código** apurado na Fase 0 — é onde os achados novos rendem
mais. O restante da árvore entra em amostragem, **exceto o Eixo A, que é sempre integral**.
Os eixos podem rodar em paralelo; cada um produz um arquivo próprio.

### Eixo A — Agnosticismo de stack (prioridade máxima, varredura integral)

Regra do projeto: agentes e comandos devem ser **agnósticos a linguagem, framework, ferramenta e
plataforma** no seu comportamento central. Skills de referência específicas
(`skills/devops/*`, `skills/ui-libraries/*`, `skills/integrations/*`, `skills/legacy/*`,
`skills/mobile/*`) são exceções legítimas por design — não as reporte.

**Varredura semente obrigatória, antes de qualquer leitura:**

```bash
rg -in 'laravel|symfony|django|rails|spring|express|nest|next\.js|react|vue|angular|svelte|\
tailwind|bootstrap|eloquent|prisma|hibernate|sequelize|typeorm|phpunit|jest|vitest|pytest|\
rspec|composer|npm|yarn|pnpm|pip|maven|gradle|docker|kubernetes|terraform|aws|gcp|azure|\
mysql|postgres|mongodb|redis|php|python|ruby|golang|typescript|javascript' agents/ commands/
```

Cada hit é **candidato**, não achado. Promova a violação apenas se estiver sob uma seção de
comportamento — e **cite o heading da seção** junto do trecho. Descarte hits sob "Example",
"Reference", tabelas de detecção e listas de skills condicionais.

Reporte: `N candidatos → M violações`, por que os `N−M` caíram, e para cada violação: arquivo,
linha, heading da seção, trecho literal, tecnologia acoplada, motivo e a reescrita agnóstica
sugerida em uma linha.

### Eixo B — Referências e consistência

- Skills referenciadas por agentes que não existem no caminho citado.
- Skills sem nenhum agente/comando que as carregue (órfãs).
- `name:` divergente do basename do diretório; nomes duplicados entre categorias.
- Templates referenciados por caminho que não resolve a partir da raiz do projeto instalado.
- Divergência entre `CLAUDE.md` / `README.md` / `README.pt-BR.md` / `docs/*.md` e a árvore real.
- Rode e interprete: `helpers/orphan-skill-scan.sh`, `helpers/orphan-template-scan.sh`,
  `helpers/agent-lint.sh`, `helpers/size-limits.sh`.

### Eixo C — Fluxos, comandos e automação

Melhorias em `commands/*.md`, hooks e scripts de install/update/render: etapas redundantes,
gates ausentes, ordem de spawn subótima, paralelismo não explorado, condicionais implícitas que
deveriam ser explícitas.

### Eixo D — Agentes e skills

Regra duplicada entre agentes que deveria ter casa canônica única, skill grande demais pedindo
`references/`, agente acima do limite de linhas, cobertura faltante, sobreposição de
responsabilidades.

### Eixo E — Economia de tokens

Contexto carregado sem necessidade, conteúdo duplicado lido duas vezes, leitura de arquivo
inteiro onde `grep`/`head` bastaria, output verboso de comando, skill sempre-carregada que
poderia ser condicional. **Quantifique**: linhas/bytes atuais → estimados após a mudança, e em
quais fluxos incide.

---

## Protocolo Anti-Duplicação

Todo achado passa por estas portas, **em ordem**:

**1. Porta literal.** O slug já existe?

```bash
grep -F "<slug>" docs/reports/_index.md docs/reports/_index-archive-*.md 2>/dev/null
```

**2. Pré-filtro mecânico por alvo** (barato, roda antes da comparação semântica):

```bash
grep -i "<basename-do-arquivo-alvo>" docs/reports/_index.md docs/reports/_index-archive-*.md
```

Sem resultado → território novo, siga direto para a porta 4. Com resultado → aplique a porta 3
**somente contra essas linhas**, nunca contra o banco inteiro.

**3. Porta semântica.** Compare o candidato com as linhas filtradas por três atributos:
**(a)** arquivo/alvo, **(b)** causa raiz, **(c)** remediação proposta.
**Dois dos três coincidindo ⇒ duplicata. Descarte.**

**4. Porta de escopo menor.** Um tema registrado só volta se o novo achado cobrir sub-escopo
**estritamente contido** e ainda não descrito. Nesse caso declare `**Refina:** <fingerprint-pai>`
e explique em uma linha o que o pai não cobria.

**5. Porta de estado.** O achado não pode pertencer ao **conjunto aberto** — reapresentar item já
registrado e não implementado é ruído, não descoberta.

**Convenção de slug:** prefixo de categoria (`ref-`, `docs-sync-`, `flow-`, `agent-`, `skill-`,
`token-`, `auto-`, `gov-`) + tema. **Máximo 80 caracteres**, kebab-case, descrevendo o tema — não
uma frase inteira.

Ao final, anexe ao `index.md` a seção **"Descartados por duplicação"** listando os candidatos
rejeitados e por qual porta. Isso torna o filtro auditável e impede que o próximo pass
redescubra os mesmos becos sem saída.

---

## Rubrica de severidade (fixa — não improvise)

| Severidade | Critério |
|---|---|
| **HIGH** | Quebra ou corrompe um fluxo em uso, ou documenta como verdade algo factualmente falso |
| **MEDIUM-HIGH** | Degrada um fluxo em uso, ou cria risco real de drift sem gate que o pegue |
| **MEDIUM** | Duplicação, inconsistência ou lacuna com custo de manutenção concreto |
| **LOW-MEDIUM** | Imprecisão localizada, sem consequência funcional |
| **LOW** | Cosmético, ou melhoria opcional |

---

## Saída

Crie `docs/reports/<YYYY-MM-DD>/` com — **nesta ordem de escrita**:

| Ordem | Arquivo | Conteúdo |
|---|---|---|
| 1 | `00-guardiao-verificacao.md` | Fases 1 e 1b, item a item |
| 2 | `01-agnosticismo-de-stack.md` | Eixo A |
| 3 | `02-referencias-e-consistencia.md` | Eixo B |
| 4 | `03-fluxos-e-comandos.md` | Eixo C |
| 5 | `04-agentes-e-skills.md` | Eixo D |
| 6 | `05-economia-tokens.md` | Eixo E |
| 7 | `index.md` | Sumário executivo |
| 8 | `_index.md` (raiz de reports) | Banco de fingerprints |

**Cabeçalho obrigatório do `index.md`:**

```markdown
**Data:** <YYYY-MM-DD> · **Baseline:** `HEAD` = `<sha>` · **Baseline anterior:** `<sha>`
```

Sem isso o pass seguinte perde a capacidade de calcular o delta.

O `index.md` traz: método, cobertura da Fase 1 (`N de M`), placar ✅/🟡/🔴, mortalidade da Fase 1b,
contagem por eixo, tabela de severidade e "Descartados por duplicação".

**Template por achado** (dentro de cada eixo, agrupado por `## HIGH`, `## MEDIUM-HIGH`, …):

```markdown
### <Título do achado em uma frase>

- **Fingerprint:** `<slug>`
- **Alvo:** `path/do/arquivo`
- **Evidência:** `path:linha` — "<trecho literal>"; (…demais ocorrências)
- **Problema:** o que está errado, objetivamente.
- **Por que importa:** consequência prática no HEAD atual.
- **Proposta:** a mudança concreta, em 1–3 linhas.
- **Impacto positivo:** ganho esperado (quantifique quando possível).
- **Impacto negativo / risco:** o que piora, quebra ou passa a exigir manutenção.
- **Esforço:** Baixo | Médio | Alto
- **Refina:** `<fingerprint-pai>`  ← apenas quando aplicável
```

Toda proposta **precisa** ter impacto negativo declarado. "Nenhum" só é aceitável com
justificativa explícita — se você não consegue nomear o custo, você não entendeu a mudança.

---

## Atualização do banco

1. Anexe ao `docs/reports/_index.md`, sob `## Registered Fingerprints`, a seção
   `## <YYYY-MM-DD> — <título do pass>` com sub-seções por eixo. **Novo formato de linha**,
   com o campo `alvo:` que alimenta o pré-filtro mecânico:

   ```
   - `<slug>` — **SEVERIDADE** — alvo: `path` — <descrição> — [report](<YYYY-MM-DD>/<arquivo>.md)
   ```

   Entradas legadas sem `alvo:` permanecem como estão; o pré-filtro cai para busca por substring
   nelas. Não faça retrofit em massa.
2. Atualize a tabela **Estatísticas** com a linha do dia: data, publicados, originais acumulados,
   placar de execução verificado na Fase 1 e mortalidade da Fase 1b.
3. Aplique as correções de marcação das Fases 1 e 1b (🔴 reaberto / 🟡 parcial / 🟢 resolvido /
   ⚰️ obsoleto).
4. Rode os gates e reporte a saída:

   ```bash
   bash helpers/check-fingerprint-uniqueness.sh
   bash helpers/archive-index.sh --dry-run     # execute sem --dry-run se houver seção >90 dias
   ```

5. Commit no padrão do histórico (`git log --oneline -10`), sem atribuição de IA, e push na
   branch designada.

## Encerramento

Responda no chat apenas com: cobertura da Fase 1 (`N de M`), placar ✅/🟡/🔴, mortalidade da
Fase 1b, achados originais por eixo, candidatos descartados por duplicação, e os 3 achados mais
graves. Nada além disso.
