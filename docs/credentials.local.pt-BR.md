# Referência de Credentials

Referência de `.dev-team-agents/credentials.local.json`: como criar e editar o arquivo, as duas chaves reservadas, e como preenchê-lo com segurança.

---

## Índice

- [Resumo](#resumo)
- [Local do Arquivo](#local-do-arquivo)
- [Criando e Editando](#criando-e-editando)
- [Estrutura](#estrutura)
- [Notas de Uso](#notas-de-uso)
- [Orientações de Segurança](#orientações-de-segurança)

---

## Resumo

`credentials.local.json` é o arquivo local, ignorado pelo git, de credenciais e referências de ambiente. Ele dá a agentes selecionados informação estruturada suficiente para acessar staging ou produção quando uma task exige validação operacional ou suporte a deploy.

Ele não é um gerenciador de segredos. É um arquivo local de conveniência cuja forma você escolhe.

---

## Local do Arquivo

```text
.dev-team-agents/credentials.local.json
```

O arquivo é específico da máquina (nunca exportado ou commitado) e ignorado pelo bloco `.gitignore` gerenciado pelo bind. Ele fica no `.dev-team-agents/` do checkout principal; todas as worktrees do git compartilham o mesmo arquivo, e um subprojeto de monorepo tem o seu.

---

## Criando e Editando

O arquivo não existe por padrão. Crie-o de uma das três formas:

### Via Aplicativo Desktop

Abra a aba **Credentials** na visão do projeto. Clique em **Create file** para criar o `credentials.local.json` a partir do exemplo inicial. A aba é um editor em árvore: adicione, renomeie, aninhe, mova entre grupos e remova grupos e campos, marque um campo como segredo ou um grupo como produção, e pesquise por chaves e valores visíveis.

Segredos são somente escrita: um valor marcado em `$secrets`, ou que parece segredo, aparece só como definido / não definido, com Substituir.

### Via CLI

```bash
devteam cred local init
```

Cria o arquivo com o template canônico. Sai com erro (código 4) se o arquivo já existe.

### Manualmente

Rode `devteam cred local init` e edite o resultado, ou escreva o arquivo seguindo a estrutura abaixo, e depois execute:

```bash
chmod 600 .dev-team-agents/credentials.local.json
```

---

## Estrutura

O arquivo é livre. Nomeie, aninhe e remova grupos e campos como fizer sentido para o projeto: não existe lista fixa de categorias, ambientes ou agentes. `devteam cred local init` grava um grupo `example` para começar; edite-o ou apague-o.

Duas chaves reservadas podem aparecer em **qualquer** objeto. Todas as outras chaves são suas:

| Chave | Valor | Significado |
|-------|-------|-------------|
| `$production` | `true` | O objeto e tudo o que está aninhado abaixo dele é produção. Os agentes perguntam antes de cada ação que altera estado ali, uma ação por vez |
| `$secrets` | lista de nomes de chaves irmãs | Essas chaves guardam segredos. O app as mantém somente escrita, e `devteam cred local show` nunca as imprime |

Duas chaves de topo são configurações, não credenciais: `work_feedback_active` (padrão `true`) e `work_feedback_interval_minutes` (padrão `5`), lidas pelos check-ins periódicos de progresso dos agentes.

Exemplo:

```json
{
  "work_feedback_active": true,
  "work_feedback_interval_minutes": 5,
  "api": {
    "staging": {
      "url": "https://staging.example.com",
      "username": "qa@example.com",
      "password": "...",
      "$secrets": ["password"]
    },
    "production": {
      "$production": true,
      "url": "https://example.com",
      "db": { "host": "db.internal", "dsn": "...", "$secrets": ["dsn"] }
    }
  },
  "jira": { "site": "acme.atlassian.net", "token": "...", "$secrets": ["token"] }
}
```

Um valor continua oculto mesmo sem entrada em `$secrets` quando a chave parece segredo (`password`, `token`, `secret`, `apiKey`…) ou o valor parece (uma URL com `usuario:senha@`, uma URL com query string, uma chave colada). Isso é uma rede de segurança, não um substituto: marque seus segredos para que um valor com nome inocente (`conn`, `dsn2`) também fique protegido.

---

## Notas de Uso

- Mantenha só o que os agentes realmente precisam.
- Marque todo grupo de produção com `$production`. Um grupo chamado `production` sem a flag não está marcado.
- Prefira credenciais de staging sempre que a task não exigir produção explicitamente.
- Renomear um segredo, ou movê-lo para outro grupo, mantém o valor e a marcação de segredo: a mudança acontece no arquivo, e o valor nunca chega ao app.

---

## Orientações de Segurança

- Não commite este arquivo.
- Mantenha as permissões do arquivo restritas.
- Prefira chaves SSH a senhas para acesso a servidores.
- Prefira usuários de banco com o mínimo de privilégio.
- Use contas de aplicação dedicadas e não pessoais quando possível.
- Trate credenciais de produção como exceção, não como padrão.
