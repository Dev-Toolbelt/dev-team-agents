# Eixo C — Fluxos, Comandos e Automação — 2026-10-10

**Baseline:** `HEAD` = `349f18c` · **2 achados originais** · 1 candidato descartado.

Prioridade de varredura: o delta (62 commits) concentra-se em `app/` (52 arquivos),
`scripts/lib` (23) e `.github/` (8). As duas primeiras subárvores têm **uma única menção** no
banco de 287 fingerprints — território novo, e é de lá que vêm os dois achados.

---

## MEDIUM-HIGH

### A regra de sender confiável para canais IPC é cumprida só por grep humano

- **Fingerprint:** `auto-ipc-trusted-sender-rule-has-no-gate-only-a-wiki-note-to-grep`
- **Alvo:** `app/src/main/security.ts`
- **Evidência:**
  - `app/src/main/security.ts:244` — `export function trustedHandler<Args extends unknown[], R>(…)`;
    `:249-252` recusa a chamada quando `!isTrustedSender(event, target)`.
  - As quatro casas de registro hoje passam por ele:
    `app/src/main/ipc.ts:393-394` — "The one door to `ipcMain.handle`: every channel in this file
    goes through it, so a new handler cannot forget the sender check by being written the plain
    way"; `app/src/main/notificationIpc.ts:28-29`; `app/src/main/taskBoardIpc.ts:74-75`;
    `app/src/main/accountIpc.ts:123` (recebe o `handle` já embrulhado por injeção).
  - `docs/wiki/electron/ipc-channels-need-the-trusted-sender-check.md:3` —
    "**Origin:** A rebased app branch added IPC channels that passed linting and tests without
    the security check; **found by grep only** | 2026-09-30"; `:43` — "**Linting and tests do not
    catch unguarded channels.**"; `:45` — "**After rebasing app work on main, grep for new
    `ipcMain.handle` calls.** The pattern is not enforced at lint time."
  - `.github/scripts/ci/05-app.sh` roda, nesta ordem: `preflight`, `node pin`,
    `npm script contract`, `npm ci`, `typecheck`, `lint`, `build`, `unit tests`. Nenhum passo lê
    `ipcMain.handle`.
- **Problema:** a única invariante de segurança do processo principal — todo canal IPC atrás do
  `trustedHandler` — é verificada por um ser humano lembrando de rodar um `grep` depois de um
  rebase. O repositório sabe disso: escreveu uma entrada de wiki cuja seção *Gotchas* é
  literalmente um recado para rodar o grep à mão, porque o incidente já ocorreu uma vez.
- **Por que importa:** o `app/` é um cliente puro do CLI (ADR-0015) e o IPC do renderer é,
  nas palavras da própria entrada de wiki, "the only path from user input into the app". Um canal
  registrado com `ipcMain.handle('x', async (…) => …)` em vez do `handle` local compila, passa
  `npm run lint`, passa `vitest` e vai para `main` — foi exatamente o que aconteceu em 2026-09-30.
  Os quatro arquivos de IPC usam **dois padrões diferentes** (três declaram o `handle` local,
  `accountIpc.ts` recebe por injeção), então "escrever igual ao vizinho" não protege.
- **Proposta:** um check determinístico em `05-app.sh`:
  `grep -rn 'ipcMain\.handle' app/src --include='*.ts' | grep -v 'trustedHandler'` deve sair
  vazio, salvo a linha de definição do `handle` local em cada arquivo — ou, mais robusto, proibir
  `ipcMain.handle` fora de `security.ts` e expor só o wrapper. Registrar como `blocking`.
- **Impacto positivo:** fecha a última porta de entrada não verificada do processo principal e
  elimina uma instrução de processo manual. Pela própria ENFORCEMENT POLICY de
  `.github/scripts/ci/01-lint.sh:11-13`, o check qualifica como `blocking` hoje: é
  determinístico, tem zero violações na árvore e uma violação é um bug de correção.
- **Impacto negativo / risco:** um grep sobre `ipcMain.handle` é sintático e pode produzir falso
  positivo em comentário ou string (a própria linha de doc em `security.ts:241` casaria);
  o check precisa de uma exclusão, que é mais um padrão para manter. Se o app passar a registrar
  canais por uma fábrica própria, o grep deixa de ver — e um check que não vê mais nada é pior do
  que nenhum, porque dá confiança falsa. Mitigação: o check falha quando **nenhuma** ocorrência é
  encontrada, a mesma técnica de não-vacuidade que `05-app.sh:run_tests` já usa.
- **Esforço:** Baixo.

---

## MEDIUM

### `stamp-code-signed.cjs` fica fora de todos os gates de JS do repositório

- **Fingerprint:** `auto-stamp-code-signed-cjs-outside-every-js-gate-in-the-tree`
- **Alvo:** `.github/scripts/release/stamp-code-signed.cjs`
- **Evidência:**
  - O arquivo tem 30 linhas e reescreve código-fonte: `:29` —
    `writeFileSync(target, source.replace(pattern, 'export const CODE_SIGNED = true;'))`
    sobre `app/src/main/build-info.ts`.
  - É executado duas vezes num release: `.github/workflows/release.yml:768` (job
    `app-build-mac`) e `:835` (job `app-build-win`), **antes** do `npm ci` e do build de cada
    plataforma.
  - Nenhum gate o alcança: `app/package.json:15` — `"lint": "eslint ."` — e `05-app.sh` roda esse
    script com `cwd = app/`, então `eslint` nunca sai de `app/`;
    `.github/scripts/ci/01-lint.sh:139` — `SHELLCHECK_TARGETS=(scripts helpers .github/scripts packaging)`
    só aplica a `-name '*.sh'`; `03-python.sh:16-17` só compila python.
    `grep -rn stamp-code-signed` fora de `.github/` e de `docs/reports/` devolve uma linha, em
    `packaging/README.md:158`, que registra: "The positive path needs a notarised build and
    **has never run**".
  - É o **único** arquivo JS/TS da árvore sem gate algum. Os outros fora de `app/` têm um:
    `infra/supabase/functions/**/*.ts` (22 arquivos) passam por
    `.github/scripts/ci/07-edge-functions.sh:30-31` (`deno check --frozen`, `deno test --frozen`);
    `opencode/plugin/dev-team-agents.ts` é exercitado por `tests/js/opencode-plugin.test.mjs` via
    `tests/test_opencode_plugin.py`; os dois renderizadores de release em python têm
    `tests/test_release_render.py`, que — como o próprio docstring diz — existe porque "they run
    only inside the release workflow, so without these tests the first execution would be a real
    tag".
- **Problema:** o repositório reconheceu esse risco para os renderizadores python do mesmo
  diretório e escreveu testes que os dirigem por `subprocess`. O `.cjs` vizinho, que faz uma coisa
  mais frágil (um `replace` ancorado em uma linha literal de outro arquivo), não ganhou nem
  `node --check`.
- **Por que importa:** o `pattern` de `:21` é
  `/^export const CODE_SIGNED = false;$/gm` e `:23` aborta quando não há exatamente uma
  ocorrência. Qualquer reformatação de `app/src/main/build-info.ts:14` — um `as const`, um
  prettier, uma quebra de linha — faz o release **morrer no meio**, depois do build assinado do
  macOS, com as credenciais já exportadas para o ambiente do job. A falha é alta e barulhenta, que
  é o design correto; o que falta é alguém notar antes do `git push --tags`. E como
  `build-info.ts` é um arquivo que `05-app.sh` typechecka, um refactor dele passa verde no CI que
  existe.
- **Proposta:** uma linha em `01-lint.sh` —
  `blocking "node --check (JS outside app/)" node --check .github/scripts/release/stamp-code-signed.cjs`
  — ou, melhor, um teste no mesmo molde de `test_release_render.py`: rodar o script contra uma
  cópia de `build-info.ts` e afirmar o antes/depois e o exit 1 na forma inesperada.
- **Impacto positivo:** o contrato entre o script e a linha que ele procura passa a ser verificado
  no PR em vez de na tag. Custo de execução desprezível.
- **Impacto negativo / risco:** `node --check` só pega sintaxe, e o risco real aqui é
  semântico (a linha-alvo mudar de forma) — um gate que só checa sintaxe dá a sensação de cobertura
  sem a cobertura, que é o padrão que `05-app.sh` combate explicitamente. O teste de verdade
  precisa de uma fixture e passa a ser mais um arquivo a manter quando `build-info.ts` ganhar
  constantes novas. Além disso, `01-lint.sh` roda sem node no PATH (o `setup-node` é do job `app`),
  então o check precisa ir para o job `app` ou o job `lint` precisa de node — uma dependência nova
  entre jobs.
- **Esforço:** Baixo.

---

## Descartados por duplicação — 1

- **Nenhum job de CI executa o `release.yml` nem valida seus placeholders.** Já é
  `auto-release-workflow-has-no-guard-for-auth-config-placeholders` (MEDIUM-HIGH, aberto), e
  `grep 'REPLACE-ME\|auth-config\|gate_mode' .github/workflows/release.yml` segue vazio depois de
  `a2933cd` ter reescrito o workflow. Porta 5 (estado).

## Hipóteses levantadas e refutadas por evidência

Registradas para que o próximo pass não as redescubra:

1. **`batchScript` quebraria com um caminho terminando em `\`.** `app/src/main/firstTaskLauncher.ts:70`
   emite `cd /d "C:\dir\"`; o `cd` do `cmd.exe` não usa `CommandLineToArgvW`, e o regex de
   segurança de `quoteCmd` (`app/src/shared/shellQuote.ts:62-65`) devolve a raiz de drive (`C:\`)
   sem aspas. Não reproduz.
2. **Algum canal IPC novo do delta estaria sem `trustedHandler`.** Rodado o grep que a entrada de
   wiki pede: os quatro arquivos passam. O achado acima é a **ausência do gate**, não uma violação.
3. **O job Windows não verificaria a assinatura Authenticode** que o comentário de
   `stamp-code-signed.cjs:12-13` promete. `release.yml:846-866` faz
   `Get-AuthenticodeSignature` em cada instalador e lança quando `EXPECT_SIGNED` é `true` e algum
   não está `Valid`. A promessa é cumprida nas duas plataformas.
4. **`scripts/lib/codex_hooks_merge.py` e `scripts/lib/permission_rules.py` ficariam fora do
   `compileall`** de `03-python.sh:16` (que recebe `scripts/lib/devteam` e
   `scripts/lib/render_provider.py`, não `scripts/lib`). Ficam — mas os dois são importados por
   `tests/test_permission_rules.py`, `tests/test_delegated_installers.py` e
   `tests/test_hook_project_root.py`, que o mesmo gate roda. Um erro de sintaxe é pego. Não
   sustenta achado.
