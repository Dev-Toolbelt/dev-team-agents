---
name: wordpress
description: WordPress core, plugin/theme development, and security hardening reference.
---

## Detection Signals

- `wp-config.php`, `wp-content/`, `wp-includes/` in the project tree
- `functions.php` inside a `wp-content/themes/<theme>/` directory
- A plugin main file with a `Plugin Name:` header comment in `wp-content/plugins/<plugin>/`
- `composer.json` requiring `johnpbloch/wordpress` or `roots/wordpress`
- `wp` CLI usage in scripts (`wp-cli.yml`, `wp plugin`, `wp db`)

## Core Development Rules

| Rule | Detail |
|------|--------|
| Never edit WordPress core | Core files are overwritten on update. Extend via plugins/themes/hooks only. |
| Use hooks, not core patches | `add_action()` / `add_filter()` for all behavior changes. Never modify `wp-includes/` or `wp-admin/`. |
| Prefix everything | Functions, classes, options, hooks, transients, and DB tables must use a unique prefix (`myplugin_`) — avoids collisions with other plugins/themes. |
| Enqueue, never hardcode | Load CSS/JS via `wp_enqueue_script()` / `wp_enqueue_style()` with proper dependency arrays and version strings (cache busting). Never `<script>`/`<link>` directly in templates. |
| Use the `$wpdb` API or WP_Query | Avoid raw `mysql_*`/PDO connections outside WordPress's abstraction — breaks multisite/table-prefix portability. |
| Internationalize strings | Wrap user-facing text in `__()`/`_e()`/`esc_html__()` with a text domain matching the plugin/theme slug. |
| Child themes for customization | Never edit a parent/purchased theme directly — create a child theme (`style.css` with `Template:` header) so updates don't wipe changes. |
| Autoloader / namespaces for larger plugins | PSR-4 via Composer autoload for plugins beyond a few files; avoid giant single-file plugins. |

## Security — Non-Negotiable Rules

WordPress's attack surface is dominated by plugins/themes, not core. Apply these on every piece of code touching user input, output, or the database.

| Vulnerability class | Rule |
|---|---|
| **SQL Injection** | Never concatenate variables into SQL. Use `$wpdb->prepare()` for every query with a variable, always with placeholders (`%s`, `%d`, `%f`) — never manual string interpolation. |
| **XSS (stored/reflected)** | Escape ALL output at the point of echo: `esc_html()`, `esc_attr()`, `esc_url()`, `esc_js()`, `wp_kses_post()` for rich content. Never trust `$_GET`/`$_POST`/`$_REQUEST` directly in HTML. |
| **CSRF** | Every state-changing action (form, AJAX, admin-post) must verify a nonce: `wp_nonce_field()` / `wp_verify_nonce()` or `check_admin_referer()`. Never rely on `is_admin()` alone as protection. |
| **Broken access control** | Gate every privileged action with `current_user_can( 'capability' )` — never trust `is_admin()`, role names, or hidden UI as the only barrier. Check capability on every AJAX/REST callback too, not just page load. |
| **Unauthenticated AJAX/REST exposure** | `wp_ajax_nopriv_*` hooks and public REST routes (`permission_callback`) must independently validate input and, if privileged, must not exist — don't assume "no menu link" is protection. |
| **File upload / arbitrary file write** | Validate MIME type and extension against an allowlist (`wp_check_filetype`), never trust the client `Content-Type`. Disable PHP execution in the uploads directory when possible. Never let user input build a filesystem path unsanitized (path traversal via `../`). |
| **Insecure deserialization** | Never `unserialize()` user-controlled data — use `maybe_unserialize()` only on trusted stored data, prefer `json_decode()` for anything from the client. |
| **SSRF via `wp_remote_*`** | Validate/allowlist destination hosts before calling `wp_remote_get/post()` with user-supplied URLs. |
| **Hardcoded secrets** | API keys, DB credentials, salts belong in `wp-config.php` (outside webroot when possible) or environment variables — never committed in plugin/theme code. |
| **Object injection via magic methods** | Avoid `__wakeup()`/`__destruct()` gadget chains — audit any class that could be unserialized from user input. |
| **Directory listing / info disclosure** | Ensure `index.php` stub files exist in plugin/theme subdirectories; never expose `debug.log`, `.env`, or `wp-config.php.bak` in the webroot. |
| **User enumeration** | Don't build custom endpoints that leak usernames/emails via ID iteration (`?author=1`) beyond what core already restricts. |
| **Outdated dependencies** | Flag plugins/themes with no updates in 2+ years or below the "tested up to" WP version — these are the top real-world compromise vector, not custom code. |

**Review checklist to run before shipping any plugin/theme code:**
1. Every SQL query with a variable uses `$wpdb->prepare()`
2. Every echoed value is escaped with the correct `esc_*()` function for its context
3. Every form/AJAX/REST write action has nonce verification AND a capability check
4. Every file upload validates type/extension server-side
5. No `eval()`, `create_function()`, `unserialize()` on untrusted input, or dynamic `include`/`require` built from user input

## Plugin/Theme Structure Baseline

```
wp-content/plugins/my-plugin/
├── my-plugin.php          ← main file with Plugin Name header, minimal bootstrap only
├── includes/               ← classes, hooks, business logic
├── admin/                  ← admin-only screens, enqueued only on admin
├── assets/                 ← css/js/images, enqueued via wp_enqueue_*
├── languages/               ← .pot/.po/.mo for i18n
└── uninstall.php            ← cleans up options/tables on deletion (not deactivation)
```

## Performance

- Use transients (`set_transient()`/`get_transient()`) to cache expensive queries/API calls, not custom cron-based caching unless transients don't fit.
- Avoid `WP_Query` with `posts_per_page => -1` on large sites — paginate.
- Load scripts/styles conditionally (`is_page()`, `is_singular()`) — don't enqueue plugin assets site-wide.
- Prefer REST API / `admin-ajax.php` with proper caching headers over polling.

## Multisite Awareness

If `is_multisite()` is relevant: use `switch_to_blog()`/`restore_current_blog()` correctly (always paired), site-specific options via `get_blog_option()`, and never assume a single `wp_options` table.

## When Not to Use WordPress Idioms

If the project only borrows WordPress data (headless via REST/GraphQL, e.g. WPGraphQL) and the actual application is a separate frontend, apply this skill only to the WordPress backend/plugin code — the frontend consuming the API follows its own framework's skill (e.g. `skills/ui-libraries/*`).
