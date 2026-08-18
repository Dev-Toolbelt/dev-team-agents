# Referência de Credentials

Referência de `.dev-team-agents/user-data/credentials.local.json`: para que serve cada seção, quem a utiliza e como preenchê-la com segurança.

---

## Índice

- [Resumo](#resumo)
- [Local do Arquivo](#local-do-arquivo)
- [Template Completo](#template-completo)
- [Estrutura de Topo](#estrutura-de-topo)
- [Seção DevOps](#seção-devops)
- [Seção App](#seção-app)
- [Referência Campo a Campo](#referência-campo-a-campo)
- [Notas de Uso](#notas-de-uso)
- [Orientações de Segurança](#orientações-de-segurança)

---

## Resumo

`credentials.local.json` é o arquivo local, ignorado pelo git, de credenciais e referências de ambiente criado pelo instalador. Ele dá a agentes selecionados informação estruturada suficiente para acessar staging ou produção quando uma task exige validação operacional ou suporte a deploy.

Ele não é um gerenciador de segredos. É um arquivo local de conveniência com schema previsível.

---

## Local do Arquivo

```text
.dev-team-agents/user-data/credentials.local.json
```

O instalador o cria na primeira instalação e aplica permissões restritivas com `chmod 600`.

---

## Template Completo

```json
{
  "work_feedback_active": true,
  "work_feedback_interval_minutes": 5,
  "devops": {
    "agents": ["software-architect", "devops-specialist", "security-specialist"],
    "staging": {
      "ssh": {
        "user": "",
        "host": "",
        "privateKeyPath": "",
        "path": ""
      },
      "database": [
        {
          "type": "",
          "host": "",
          "port": "",
          "database": "",
          "username": "",
          "password": ""
        }
      ]
    },
    "production": {
      "ssh": {
        "user": "",
        "host": "",
        "privateKeyPath": "",
        "path": ""
      },
      "docker": {},
      "database": [
        {
          "type": "",
          "host": "",
          "port": "",
          "database": "",
          "username": "",
          "password": ""
        }
      ]
    }
  },
  "app": {
    "agents": [
      "software-architect",
      "backend-developer",
      "frontend-developer",
      "code-reviewer",
      "backend-reviewer",
      "frontend-reviewer",
      "qa-specialist",
      "security-specialist",
      "backend-test-specialist",
      "frontend-test-specialist"
    ],
    "staging": {
      "appUrl": "",
      "username": "",
      "password": ""
    },
    "production": {
      "appUrl": "",
      "username": "",
      "password": ""
    }
  }
}
```

---

## Estrutura de Topo

| Chave | Propósito |
|-------|-----------|
| `work_feedback_active` | Habilita/desabilita o check-in periódico em tabela de status enquanto sub-agents trabalham em segundo plano (`skills/shared/work-feedback/SKILL.md`). Padrão `true` |
| `work_feedback_interval_minutes` | Intervalo, em minutos, entre os check-ins de status. Padrão `5` |
| `devops` | Acesso de nível de infraestrutura para servidores, bancos e tarefas operacionais |
| `app` | Acesso de nível de aplicação para login em ambientes de staging ou produção |

Cada seção define:

- Quais agentes podem usar aquele bloco
- Ambientes separados de staging e produção
- Credenciais estruturadas em vez de notas soltas

---

## Seção DevOps

`devops` é voltada para tarefas de infraestrutura.

### Resumo

| Chave | Significado |
|-------|-------------|
| `agents` | Allowlist de agentes para credenciais de infraestrutura |
| `staging.ssh` | Dados de acesso SSH para staging |
| `staging.database` | Um ou mais bancos de staging |
| `production.ssh` | Dados de acesso SSH para produção |
| `production.docker` | Metadados opcionais de Docker específicos do ambiente |
| `production.database` | Um ou mais bancos de produção |

### Uso esperado

Esse bloco é mais relevante quando a task envolve:

- diagnóstico de deploy
- inspeção de servidor
- revisão operacional
- validação de banco
- auditoria de segurança

---

## Seção App

`app` é voltada para cenários de navegador ou login na aplicação.

### Resumo

| Chave | Significado |
|-------|-------------|
| `agents` | Allowlist de agentes para credenciais da aplicação |
| `staging.appUrl` | URL base da aplicação em staging |
| `staging.username` | Usuário de login em staging |
| `staging.password` | Senha de login em staging |
| `production.appUrl` | URL base da aplicação em produção |
| `production.username` | Usuário de login em produção |
| `production.password` | Senha de login em produção |

### Uso esperado

Esse bloco é mais relevante quando a task envolve:

- validação de QA em staging
- agentes de review verificando comportamento vivo
- validação de segurança em ambientes acessíveis
- reprodução de bug em ambiente deployado

---

## Referência Campo a Campo

### `devops.agents`

Lista de nomes de agentes autorizados a consumir credenciais de infraestrutura.

Use para limitar acessos de maior risco ao menor conjunto de papéis que realmente precisa deles.

### `devops.staging.ssh.user`

Usuário SSH do servidor de staging.

Exemplo:

```json
"user": "deploy"
```

### `devops.staging.ssh.host`

Hostname ou IP do servidor de staging.

Exemplo:

```json
"host": "staging.example.com"
```

### `devops.staging.ssh.privateKeyPath`

Caminho absoluto ou relativo ao usuário para a chave privada SSH usada no staging.

Exemplo:

```json
"privateKeyPath": "~/.ssh/id_ed25519"
```

### `devops.staging.ssh.path`

Caminho remoto da aplicação após o login.

Exemplo:

```json
"path": "/var/www/my-app"
```

### `devops.staging.database[]`

É um array porque staging pode ter mais de um banco ou serviço.

Cada entrada contém:

| Campo | Significado |
|-------|-------------|
| `type` | Engine do banco, como `postgres`, `mysql`, `mongodb` |
| `host` | Host do banco |
| `port` | Porta do banco |
| `database` | Nome do banco |
| `username` | Usuário de login no banco |
| `password` | Senha do banco |

### `devops.production.ssh.*`

Mesmo schema e significado do SSH de staging, mas para produção.

Use com disciplina mais rígida e apenas quando a task realmente exigir acesso a produção.

### `devops.production.docker`

Objeto aberto reservado para metadados Docker específicos do deploy.

Como layouts de infraestrutura variam, esse bloco é propositalmente flexível. Usos comuns podem incluir:

- nomes de projetos compose
- labels de containers
- nomes de serviços
- referências de registry

Se não for usado, deixe como `{}`.

### `devops.production.database[]`

Mesmo schema dos bancos de staging, mas para sistemas de produção.

Se a produção tiver réplicas de leitura, bancos analíticos ou múltiplos serviços, adicione múltiplas entradas no array.

### `app.agents`

Lista de nomes de agentes autorizados a consumir credenciais de aplicação.

Ela é separada de `devops.agents` porque acesso em nível de navegador e acesso em nível de servidor não têm a mesma fronteira de confiança.

### `app.staging.appUrl`

URL base usada para abrir o ambiente de staging.

Exemplo:

```json
"appUrl": "https://staging.example.com"
```

### `app.staging.username`

Usuário ou e-mail usado para login em staging.

### `app.staging.password`

Senha da conta de staging.

### `app.production.appUrl`

URL base da aplicação em produção.

### `app.production.username`

Usuário ou e-mail usado para login em produção.

### `app.production.password`

Senha da conta de produção.

---

## Notas de Uso

- Preencha apenas as seções que você realmente usa.
- Você pode manter campos não utilizados como strings vazias.
- Prefira credenciais de staging sempre que a task não exigir produção explicitamente.
- Se existirem múltiplos ambientes, mantenha o schema consistente em vez de adicionar notas ad hoc.

Exemplo mínimo só com staging:

```json
{
  "app": {
    "agents": ["qa-specialist"],
    "staging": {
      "appUrl": "https://staging.example.com",
      "username": "qa@example.com",
      "password": "..."
    },
    "production": {
      "appUrl": "",
      "username": "",
      "password": ""
    }
  }
}
```

---

## Orientações de Segurança

- Não commite este arquivo.
- Mantenha permissões restritivas no arquivo.
- Prefira chaves SSH em vez de senhas para acesso a servidor.
- Prefira usuários de banco com menor privilégio possível.
- Use contas dedicadas e não pessoais na aplicação quando possível.
- Trate credenciais de produção como exceção, não como padrão.
