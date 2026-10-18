# Terraform — Module Structure & Patterns Reference

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
│   ├── app-service/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── shared/
    └── backend.tf
```

---

## Remote State Backends

### AWS S3 + DynamoDB

```hcl
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

Bootstrap once:

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

## Modules — When and How

Create a module when the same set of resources is used in more than one environment.

```hcl
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

## Variable Patterns

```hcl
# variables.tf — always include type and description
variable "environment" {
  type        = string
  description = "Deployment environment (staging | production)"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be staging or production."
  }
}
```

---

## Secrets — Never in tfvars or State

| Cloud | Data source pattern |
|-------|-------------------|
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

> Never pass secrets via `-var` flags in CI — they appear in logs.

---

## Importing Existing Resources

```bash
terraform import aws_s3_bucket.my_bucket my-existing-bucket-name
terraform import aws_instance.web i-1234567890abcdef0
```

After import, run `terraform plan` to verify state matches real infrastructure before any changes.

---

## Anti-Patterns

- `terraform apply` without `terraform plan` review in production
- Secrets in `terraform.tfvars` — use secret manager data sources
- Local state file — always use remote backend with locking
- `count` for resources that differ significantly — use `for_each` with maps instead
- `latest` as a module version — pin to a specific git tag
- Running apply directly from a developer machine against production — always use CI
