# Terraform — CI/CD Workflows Reference

## Core Rule

- **PR**: plan only — never apply
- **Merge to main**: apply with manual approval gate for production
- **Scheduled**: drift detection

---

## GitHub Actions — PR Plan Workflow

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
        id: plan
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

---

## GitHub Actions — Apply Workflow (merge to main)

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

## GitLab CI — Plan + Apply

```yaml
stages:
  - validate
  - plan
  - apply

variables:
  TF_ROOT: infra/environments/production

terraform:validate:
  stage: validate
  image: hashicorp/terraform:1.8.0
  script:
    - terraform init
    - terraform validate
  only:
    - merge_requests
    - main

terraform:plan:
  stage: plan
  image: hashicorp/terraform:1.8.0
  script:
    - terraform init
    - terraform plan -no-color -out=tfplan
  artifacts:
    paths:
      - $TF_ROOT/tfplan
  only:
    - merge_requests

terraform:apply:
  stage: apply
  image: hashicorp/terraform:1.8.0
  script:
    - terraform init
    - terraform apply -auto-approve tfplan
  when: manual
  only:
    - main
```

---

## Drift Detection (Scheduled)

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

## Environment Promotion Pattern

```
feature branch → PR → plan (staging) → merge → apply (staging) → tag → apply (production, manual approval)
```

Keep separate `terraform.tfvars` per environment in git. Use separate state keys per environment in the backend config.
