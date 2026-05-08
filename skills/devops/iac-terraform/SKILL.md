---
name: iac-terraform
description: Terraform/OpenTofu IaC — structure, remote state, modules, CI/CD, drift detection.
---

# Infrastructure as Code — Terraform / OpenTofu

## Core Principle

IaC is code. It lives in git, gets reviewed in PRs, runs in CI, and never has secrets hardcoded in it. State is shared and locked.

> OpenTofu is a drop-in open-source alternative to Terraform. All patterns here apply to both.

---

## Project Structure

```
infra/
├── environments/
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars      # non-secret values only; in git
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── app-service/              # reusable module per component
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── shared/
    └── backend.tf                # remote state config (shared across envs)
```

---

## Remote State — Never Use Local State in Teams

### AWS S3 + DynamoDB (recommended for AWS projects)

```hcl
# infra/environments/production/main.tf
terraform {
  backend "s3" {
    bucket         = "my-project-tf-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "my-project-tf-lock"
    encrypt        = true
  }
}
```

Bootstrap the S3 bucket and DynamoDB table once:

```bash
aws s3api create-bucket --bucket my-project-tf-state --region us-east-1
aws s3api put-bucket-versioning --bucket my-project-tf-state \
  --versioning-configuration Status=Enabled
aws dynamodb create-table \
  --table-name my-project-tf-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### GCP GCS

```hcl
terraform {
  backend "gcs" {
    bucket = "my-project-tf-state"
    prefix = "production"
  }
}
```

### Azure Blob Storage

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "tf-state-rg"
    storage_account_name = "myprojecttfstate"
    container_name       = "tfstate"
    key                  = "production.terraform.tfstate"
  }
}
```

---

## Secrets — Never in tfvars or State

Secrets must come from the secret manager of the target cloud, not from Terraform variables.

| Cloud | Pattern |
|-------|---------|
| AWS | `data "aws_ssm_parameter"` or `data "aws_secretsmanager_secret_version"` |
| GCP | `data "google_secret_manager_secret_version"` |
| Azure | `data "azurerm_key_vault_secret"` |

```hcl
data "aws_ssm_parameter" "db_password" {
  name            = "/myapp/production/db_password"
  with_decryption = true
}

resource "aws_db_instance" "main" {
  password = data.aws_ssm_parameter.db_password.value
}
```

> Never pass secrets via `-var` flags in CI — they appear in logs. Always use the data source pattern above.

---

## Modules — When and How

Create a module when the same set of resources is used in more than one environment.

```hcl
# infra/environments/production/main.tf
module "app" {
  source = "../../modules/app-service"

  name        = "myapp"
  environment = "production"
  image_tag   = var.image_tag
  cpu         = 1024
  memory      = 2048
}
```

Module rules:
- `variables.tf` declares all inputs with types and descriptions
- `outputs.tf` exposes only what callers need
- No hard-coded environment names or region strings inside modules
- Modules are versioned via git tags when shared across repos

---

## CI/CD Integration

### PR Workflow (plan only, never apply on PR)

```yaml
# .github/workflows/terraform-plan.yml
name: Terraform Plan

on:
  pull_request:
    paths:
      - "infra/**"

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.8.0"

      - name: Terraform Init
        run: terraform init
        working-directory: infra/environments/production

      - name: Terraform Validate
        run: terraform validate
        working-directory: infra/environments/production

      - name: Terraform Plan
        run: terraform plan -no-color -out=tfplan
        working-directory: infra/environments/production
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Post plan to PR
        uses: actions/github-script@v7
        with:
          script: |
            const output = `#### Terraform Plan 📖
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\``;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });
```

### Apply Workflow (merge to main only, with manual approval for prod)

```yaml
# .github/workflows/terraform-apply.yml
name: Terraform Apply

on:
  push:
    branches: [main]
    paths:
      - "infra/**"

jobs:
  apply:
    runs-on: ubuntu-latest
    environment: production          # requires manual approval in GitHub Environments
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.8.0"
      - run: terraform init
        working-directory: infra/environments/production
      - run: terraform apply -auto-approve
        working-directory: infra/environments/production
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Drift Detection

Run `terraform plan` in CI on a schedule. Alert if drift is detected.

```yaml
# .github/workflows/drift-detection.yml
name: Drift Detection

on:
  schedule:
    - cron: "0 8 * * 1-5"    # weekdays at 8am

jobs:
  detect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
        working-directory: infra/environments/production
      - name: Plan (detect drift)
        id: plan
        run: terraform plan -detailed-exitcode -no-color
        working-directory: infra/environments/production
        continue-on-error: true
      - name: Alert on drift
        if: steps.plan.outputs.exitcode == '2'
        run: |
          echo "::error::Infrastructure drift detected. Review the plan output above."
          exit 1
```

Exit codes: `0` = no changes, `1` = error, `2` = changes detected (drift).

---

## Importing Existing Resources

When infrastructure already exists and needs to be brought under Terraform management:

```bash
terraform import aws_s3_bucket.my_bucket my-existing-bucket-name
terraform import aws_instance.web i-1234567890abcdef0
```

After import, run `terraform plan` to verify state matches real infrastructure before any changes.

---

## Anti-Patterns to Avoid

- `terraform apply` without `terraform plan` review in production
- Secrets in `terraform.tfvars` — use secret manager data sources
- Local state file — always use remote backend with locking
- `count` for resources that differ significantly — use `for_each` with maps instead
- `latest` as a module version — pin to a specific git tag
- Running apply directly from a developer machine against production — always use CI

---

## Before Declaring Done

- [ ] Remote backend configured with state locking (S3+DynamoDB, GCS, or Azure Blob)
- [ ] State bucket has versioning enabled (allows rollback)
- [ ] No secrets in `.tfvars` or passed via `-var` — all secrets use data sources
- [ ] `terraform validate` passes in CI on every PR
- [ ] `terraform plan` output posted to PR for review
- [ ] `terraform apply` requires manual approval for production environment
- [ ] Drift detection scheduled (weekly minimum)
- [ ] `.gitignore` includes: `*.tfstate`, `*.tfstate.backup`, `.terraform/`, `*.tfplan`
- [ ] Modules versioned via git tags if shared across repos
