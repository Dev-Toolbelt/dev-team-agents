---
name: cicd-gitlab
description: GitLab CI/CD — .gitlab-ci.yml patterns for build, test, lint, and deploy.
---

# GitLab CI/CD

## File Location

```
.gitlab-ci.yml   ← root of repository
```

## Standard Pipeline

```yaml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  POSTGRES_DB: test
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  POSTGRES_HOST_AUTH_METHOD: trust

default:
  image: node:20-alpine
  cache:
    key: $CI_COMMIT_REF_SLUG
    paths:
      - node_modules/
  before_script:
    - npm ci

lint:
  stage: lint
  script:
    - npm run lint

test:
  stage: test
  services:
    - postgres:16-alpine
  variables:
    DATABASE_URL: postgres://postgres:postgres@postgres:5432/test
  script:
    - npm test
  artifacts:
    reports:
      junit: test-results.xml
    when: always

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
  only:
    - main

deploy:
  stage: deploy
  environment:
    name: production
    url: https://myapp.example.com
  before_script: []
  script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$DEPLOY_KEY" | ssh-add -
    - ssh -o StrictHostKeyChecking=no $DEPLOY_USER@$DEPLOY_HOST "
        cd /opt/myapp &&
        IMAGE_TAG=$CI_COMMIT_SHA docker compose pull app &&
        IMAGE_TAG=$CI_COMMIT_SHA docker compose up -d &&
        docker image prune -f"
  only:
    - main
  when: manual   # remove for auto-deploy
```

## Secrets Management

- Store secrets in **Settings → CI/CD → Variables**
- Mark as **Masked** to prevent log exposure
- Mark as **Protected** to restrict to protected branches
- Use variable groups for shared secrets across projects (requires GitLab Premium)

## Rules — Replacing `only`/`except`

```yaml
deploy:
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: on_success
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: never
```

## Reusable Templates

```yaml
# .gitlab/ci/test.gitlab-ci.yml
.test-template: &test-template
  stage: test
  services:
    - postgres:16-alpine
  script:
    - npm test

unit-test:
  <<: *test-template
  variables:
    SUITE: unit

integration-test:
  <<: *test-template
  variables:
    SUITE: integration
```

## Best Practices

- Use `stages` to control execution order and parallelism
- Use `needs:` for DAG-based pipeline — skip waiting for entire stage
- Cache `node_modules`/`vendor` with branch-scoped keys
- Use `artifacts: reports:` for test results, coverage, and SAST reports
- Use `environment:` for deploy jobs — enables GitLab's deployment tracking
- GitLab has built-in SAST/DAST — enable in Security & Compliance settings
