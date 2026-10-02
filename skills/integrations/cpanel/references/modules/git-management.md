<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — GIT Management

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Repository Management**: [`VersionControl::create`](#versioncontrol-create), [`VersionControl::delete`](#versioncontrol-delete), [`VersionControl::retrieve`](#versioncontrol-retrieve), [`VersionControl::update`](#versioncontrol-update)
- **Deployment Settings**: [`VersionControlDeployment::create`](#versioncontroldeployment-create), [`VersionControlDeployment::delete`](#versioncontroldeployment-delete), [`VersionControlDeployment::retrieve`](#versioncontroldeployment-retrieve)

## Repository Management

<a id="versioncontrol-create"></a>
### `VersionControl::create` — Create Git repository

`GET /execute/VersionControl/create` · RW · rollback: none · since cPanel 72

This function creates a new Git™ repository on a cPanel account.; For more information about support for version control in cPanel & WHM, read our [Git Version Control](https://go.cpanel.net/GitVersionControl) and [Guide to Git](https://go.cpanel.net/GitDeployment) documentation.; For a list of configuration changes, repository restrictions, and troubleshooting steps, read our [Guide to Git - For System Administrators](https://go.cpanel.net/GuidetoGitForSystemAdministrators) documentation. Important: The system logs errors for this function in the `~/.cpanel/logs/vc_TIMESTAMP_git_create.log` file, where `TIMESTAMP` represents the time of the error in Unix epoch time.

**Parameters**

- `name` · **required** · string · e.g. `example` — The new repository's display name.
- `repository_root` · **required** · string <path> · e.g. `/home/user/public_html/example` — The absolute path to the directory in which to store the repository, relative to the user's `home` directory. Note:  If the directory does **not** exist, the system will create it.; If the specified directory already contains a repository, the system will automatically add it to the list of cPanel-managed repositories.; This feature enforces several restrictions on repository paths. For more information, read our [Guide to Git - For System Administrators](https://go.cpanel.net/GuidetoGitForSystemAdministrators) documentation.
- `type` · **required** · string (`git`) · e.g. `git` — The repository type.; `git` — A [Git](https://git-scm.com/) repository. Note: `git` is the only possible value.
- `source_repository` · optional · JSON-encoded · object — A JSON-formatted object containing information about the source repository that the system will clone. Note: If you do **not** include source repository data, the function creates an empty repository.
  - `remote_name` (string) — The source repository's name.
  - `url` (string) — The source repository's clone URL.

**Returns** `data`: object

- `available_branches` (array of string) — An list of available branches for the cloned or existing repository, if any exist.
- `branch` (string) — The repository's current branch.; `null` — The system has **not** finished the clone process for the repository, or no local branches exist.
- `clone_urls` (object) — An object containing URLs to use to clone the repository.
  - `read_only` (array of string <url>) — A list of clone URLs with read-only permissions.
  - `read_write` (array of string) — A list of of clone URLs with read-write permissions.
- `last_update` (any (`None`)) — Information about the most-recent (HEAD) commit for the current branch.
- `name` (string) — The repository's display name.
- `repository_root` (string <path>) — The absolute path of the directory that contains the repository in the user's `home` directory.
- `source_repository` (object) — A object containing information about a cloned repository's source repository.
  - `remote_name` (string) — The source repository's name.
  - `url` (string <url>) — The source repository's clone URL.
- `tasks` (array of object) — An array of objects containing information about the [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's process that will clone the repository.
  - *(array of objects)*
    - `action` (string (`create`)) — The task's action.; `create` Note: `create` is the only possible value.
    - `args` (object) — A list of arguments for the [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's process.
    - `id` (string) — The [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's task ID number.
    - `sse_url` (string) — The SSE interface to track the progress of the process.
    - `subsystem` (string (`VersionControl`)) — The [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) subsystem that will handle the task.; `VersionControl` Note: `VersionControl` is the only possible value.
- `type` (string) — The repository type.; `git` — A Git repostiory.

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControl \
  create \
  type='git' \
  name='example' \
  repository_root='/home/user/public_html/example'
```

<a id="versioncontrol-delete"></a>
### `VersionControl::delete` — Delete Git repository

`GET /execute/VersionControl/delete` · RW · rollback: none · since cPanel 72

This function deletes a cPanel account's Git™ repository. For more information about support for version control in cPanel & WHM, read our [Git Version Control](https://go.cpanel.net/GitVersionControl) and [Guide to Git](https://go.cpanel.net/GitDeployment) documentation. Warning:  When you call this function, the system **permanently deletes** the entire contents of the specified directory. You **cannot** recover this data after deletion.; You **cannot** use this function to delete any repositories that do not appear in the cache of repositories (for example, repositories that contain invalid characters or exist within cPanel-controlled directories).

**Parameters**

- `repository_root` · **required** · string · e.g. `/home/user/example` — The absolute directory path in the user's `home` directory containing the repository to delete.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControl \
  delete \
  repository_root='/home/user/example'
```

<a id="versioncontrol-retrieve"></a>
### `VersionControl::retrieve` — Return Git repositories

`GET /execute/VersionControl/retrieve` · RW · rollback: none · since cPanel 72

This function lists Git™ repositories on a cPanel account. For more information about support for version control in cPanel & WHM, read our [Git Version Control](https://go.cpanel.net/GitVersionControl) and [Guide to Git](https://go.cpanel.net/GitDeployment) documentation. Important:  This feature does **not** allow the following characters in repository paths: ``\ * \| " ' < > & @ ` $ { } [ ] ( ) ; ? : = % #``; This function does **not** allow repositories that exist in the following cPanel-controlled directories: `.cpanel`; `.htpasswds`; `.ssh`; `.trash`; `access-logs`; `cgi-bin`; `etc`; `logs`; `perl5`; `mail`; `spamassassin`; `ssl`; `tmp`; `var` Users can create repositories in some of these directories on the command line. They may appear in the list of repositories in Gitweb, but users may see an error message if they try to access them.

**Parameters**

- `fields` · optional · string · default `*` · e.g. `name,type,branch,last_update` — A comma-separated list of desired return values. Note: Use a wildcard (`*`) to list all possible return values.

**Returns** `data`: array of object — An array of objects containing repository data.

- *(array of objects)*
  - `available_branches` (array of string) — A list of available local and remote branches for the cloned or existing repository.; An empty array — No branches exist.; `null` — The repository is a bare repository.
  - `branch` (string) — The repository's current branch.; `null` — The system has not finished the clone process for the repository, no local branches exist, or the repository is a bare repository.
  - `clone_urls` (object) — An array of objects containing URLS to use to clone the repository.
    - `read_only` (array of string) — A list of clone URLs with read-only permissions.
    - `read_write` (array of string) — A list of clone URLs with read-write permissions.
  - `deployable` (integer (`1`, `0`)) — Whether the system could deploy the repository.; `1` — Can deploy.; `0` — Cannot deploy.
  - `last_deployment` (object) — An object containing information about the commit that the system most recently deployed.
    - `deployment_date` (integer <unix_timestamp>) — The timestamp for the most-recent deployment.
    - `repository_state` (object) — A object containing information about the state of the repository at the time of the most recent deployment.
  - `last_update` (object) — An object containing information about the most-recent (HEAD) commit for the current branch.
    - `author` (string) — The most-recent commit's author's name and email address.
    - `date` (integer <unix_timestamp>) — The timestamp for the most-recent commit.
    - `identifier` (string) — The identifier (SHA-1 value) for the most-recent commit.
    - `message` (string) — The commit message.
  - `name` (string) — The repository's display name.
  - `repository_root` (string <path>) — The absolute directory path in the user's `home` directory containing the repository.
  - `source_repository` (object) — An object containing information about the source repository.
    - `remote_name` (string) — The source repository's name.
    - `url` (string) — The source repository's clone URL.
  - `tasks` (array of object) — An array of objects containing information about the [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's process that will clone the repository.
    - *(array of objects)*
      - `action` (string (`create`, `deploy`)) — The task's action.; `create` — Create the repository.; `deploy` — Deploy the repository.
      - `args` (object) — A list of arguments for the Task Queue system's process.
      - `id` (string) — The Task Queue system's task ID number.
      - `sse_url` (string) — The Secure Server Events (SSE) interface URL to track the progress of the process.
      - `subsystem` (string (`VersionControl`)) — The Task Queue subsystem that will handle the task.; `VersionControl` is the only possible value.
  - `type` (string (`git`)) — The repository type.; `git` is the only possible value.

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControl \
  retrieve
```

<a id="versioncontrol-update"></a>
### `VersionControl::update` — Update Git repository settings

`GET /execute/VersionControl/update` · RW · rollback: none · since cPanel 72

This function modifies a Git™ repository's basic settings. For more information about support for version control in cPanel & WHM, read our [Git Version Control](https://go.cpanel.net/GitVersionControl) and [Guide to Git](https://go.cpanel.net/GitDeployment) documentation. Note:  This function **only** pulls changes from the remote repository if you specify a `branch` value.; You **cannot** modify the `type`, `repository_root`, or `url` values for existing repositories.; You **must** include the `repository_root` parameter in order to identify the repository to update.; All other input parameters are **optional**. Use them to assign the **new** values to the account. If you do not include a parameter or specify its existing value, no change will occur.

**Parameters**

- `repository_root` · **required** · string <path> · e.g. `/home/user/public_html/example` — The absolute directory path that contains the repository to update.
- `branch` · optional · string · e.g. `master` — The new branch to use. If you do not specify a value, the function does **not** update this parameter. **Remember:** This function **only** pulls changes from the remote repository if you specify this value.
- `name` · optional · string · e.g. `example` — The repository's new display name. If you do not specify a value, the function does **not** update this parameter.
- `source_repository` · optional · JSON-encoded · object · e.g. `{"remote_name": "origin"}` — A JSON-encoded object containing information about the source repository. If you do not specify a value, the function does **not** update this parameter. Important:  You **cannot** modify the source repository's URL.; You **must** JSON-encode the contents of this object.
  - `remote_name` (string) — The source repository's name.

**Returns** `data`: object

- `available_branches` (array of string) — A list of local and remote branches available for the cloned or existing repository.; An empty array, if no branches exist.; `null` — The repository is a bare repository.
- `branch` (string) — The repository's current branch.; `null` — The system has not finished the clone process for the repository, no local branches exist, or the repository is a bare repository.
- `clone_urls` (object) — An object containing the URLs to use to clone the repository.
  - `read_only` (array of string <url>) — A list of clone URLs with read-only permissions.
  - `read_write` (array of string) — A list of clone URLs with read-write permissions.
- `deployable` (integer (`1`, `0`)) — Whether the system could deploy the repository.; `1` — Can deploy.; `0` — Cannot deploy.
- `last_deployment` (object) — An object containing information about the commit that the system most recently deployed.
  - `deployment_date` (integer <unix_timestamp>) — The timestamp for the most recent deployment.
  - `repository_state` (object) — A object containing information about the state of the repository at the time of the most recent deployment.
- `last_update` (object) — An object containing information about the most recent (HEAD) commit for the current branch.
  - `author` (string) — The most recent commit's author name and email address.
  - `date` (integer <unix_timestamp>) — The timestamp for the most recent commit.
  - `identifier` (string) — The identifier (SHA-1 value) for the most recent commit.
  - `message` (string) — The commit message.
- `name` (string) — The repository's display name.
- `repository_root` (string) — The directory path that exists in the user's `home` directory containing the repository.
- `source_repository` (object) — An object containing information about the source repository.
  - `remote_name` (string) — The source repository's name.
  - `url` (string) — The source repository's clone URL.
- `tasks` (array of object) — An array of objects containing information about the [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's process that will clone the repository.
  - *(array of objects)*
    - `action` (string (`create`, `deploy`)) — The task's action.; `create` — Create the repository.; `deploy` — Deploy the repository.
    - `args` (object) — An object containing arguments for the Task Queue system's process.
    - `id` (string) — The Task Queue system's task ID number.
    - `subsystem` (string (`VersionControl`)) — The Task Queue subsystem that will handle the task.; `VersionControl` Note:  `VersionControl` is the only possible value.
- `type` (string (`git`)) — The repository type.; `git` — A [Git](https://git-scm.com/) repository.

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControl \
  update \
  repository_root='/home/user/public_html/example'
```

## Deployment Settings

<a id="versioncontroldeployment-create"></a>
### `VersionControlDeployment::create` — Create Git deployment task

`GET /execute/VersionControlDeployment/create` · RW · rollback: none · since cPanel 74

This function deploys the changes from a cPanel-managed repository. Important: The system logs messages for this function in the `~/.cpanel/logs/vc_TIMESTAMP_git_deploy.log` file, where TIMESTAMP represents the time in Unix epoch time. The system pulls changes with the `--ff-only` option and will only succeed if the branch's HEAD commit is up-to-date or Git can fast forward it. For more information about our suggested deployment configuration and how users can set it up, read our [Guide to Git™ - Deployment](https://go.cpanel.net/GitDeployment) documentation. Before deployment, repositories must meet the following requirements: A valid checked-in `.cpanel.yml` file in the top-level directory.; One or more local or remote branches.; A clean working tree. If a repository does **not** meet these requirements, the system will **not** display deployment information. Also, it will disable deployment functionality. For more information, read our [Guide to Git™ - Deployment](https://go.cpanel.net/GitDeployment) documentation.

**Parameters**

- `repository_root` · **required** · string <path> · e.g. `/home/user/public_html/example` — The repository's directory.

**Returns** `data`: object

- `deploy_id` (string) — The deployment ID number.
- `log_path` (string <path>) — The absolute path to the task's log file vc_TIMESTAMP_git_deploy.log, where TIMESTAMP represents the time in Unix epoch time.
- `repository_root` (string <path>) — The repository's directory.
- `sse_url` (string <url-path>) — The SSE interface to track the progress of the deployment process.
- `task_id` (string) — The Task Queue system's task ID number.
- `timestamps` (object <object>) — A hash of timestamps for the deployment process.
  - `queued` (string) — The time at which the deployment process.

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControlDeployment \
  create \
  repository_root='/home/user/public_html/example'
```

<a id="versioncontroldeployment-delete"></a>
### `VersionControlDeployment::delete` — Delete Git deployment task

`GET /execute/VersionControlDeployment/delete` · RW · rollback: none · since cPanel 74

This function deletes a deployment task. For more information, read our [Guide to Git - Deployment](https://go.cpanel.net/GitDeployment) documentation.

**Parameters**

- `deploy_id` · **required** · string · e.g. `13` — The [Task Queue system's](https://go.cpanel.net/whmdocsTaskQueueMonitor) task ID number.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControlDeployment \
  delete \
  deploy_id='13'
```

<a id="versioncontroldeployment-retrieve"></a>
### `VersionControlDeployment::retrieve` — Return Git deployment task status

`GET /execute/VersionControlDeployment/retrieve` · RW · rollback: none · since cPanel 74

This function retrieves the status of deployment tasks. Before deployment, repositories must meet the following requirements: A valid checked-in `.cpanel.yml` file in the top-level directory.; One or more local or remote branches.; A clean working tree. If a repository does **not** meet these requirements, the system will **not** display deployment information. Also, it will disable deployment functionality. For more information, read our [Guide to Git™ - Deployment](https://go.cpanel.net/GitDeployment) documentation. Important: The system logs messages for this function in the `~/.cpanel/logs/vc_TIMESTAMP_git_deploy.log` file, where `TIMESTAMP` represents the time in Unix epoch time.

**Returns** `data`: array of object — An array of objects containing deployment task data.

- *(array of objects)*
  - `deploy_id` (integer) — The deployment ID number.
  - `log_path` (string <path>) — The absolute path to the task's log file.
  - `repository_root` (string <path>) — The aboslute path to the cPanel-managed repository directory.
  - `repository_state` (object) — An object containing information about the repository's state at the time of deployment.
    - `author` (string) — The most-recent commit's author's name and email address as they exist in the user's Git configuration files.
    - `branch` (string) — The repository's current branch.
    - `date` (integer <unix_timestamp>) — The timestamp for the most-recent commit, in Unix time format.
    - `identifier` (string) — The identifier (SHA-1 value) for the most-recent commit.
    - `message` (string) — The commit message.
  - `sse_url` (string <url-path>) — The SSE interface to track the progress of the deployment process.
  - `task_id` (string) — The [Task Queue](https://go.cpanel.net/whmdocsTaskQueueMonitor) system's task ID number.
  - `timestamps` (object) — An object containing timestamps for the deployment process.
    - `active` (string) — The time at which the system started the deployment process, in Unix time format.
    - `canceled` (string) — The time at which the system cancelled the deployment process, in Unix time format.
    - `failed` (string) — The time at which the deployment process failed, in Unix time format.
    - `queued` (string) — The time at which the deployment process entered the task queue, in Unix time format.
    - `succeeded` (string) — The time at which the deployment process finished successfully, in Unix time format.

```bash
uapi --output=jsonpretty \
  --user=username \
  VersionControlDeployment \
  retrieve
```

