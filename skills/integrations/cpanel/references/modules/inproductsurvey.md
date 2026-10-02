<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — InProductSurvey

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **InProductSurvey**: [`InProductSurvey::get_in_product_survey_url`](#inproductsurvey-get-in-product-survey-url)

## InProductSurvey

<a id="inproductsurvey-get-in-product-survey-url"></a>
### `InProductSurvey::get_in_product_survey_url` — Return in-product survey banner data

`GET /execute/InProductSurvey/get_in_product_survey_url` · RW · rollback: none · since 11.32

This function returns whether the in-product survey banner should display for the current user and the survey link. Notes:  The function selects a link template based on whether the authenticated user is a webmail user or a cPanel/Team user.; A `display` value of `0` means you should not render the banner UI.

**Returns** `data`: object — The in-product survey banner data.

- `display` (string (`1`, `0`)) — Whether to display the in-product survey banner.; `1` — Display the banner.; `0` — Do not display the banner.
- `link` (string) — The fully resolved survey URL.
- `max_dismiss` (string) — Maximum number of dismissals allowed before the banner is suppressed.
- `new_user` (string (`1`, `0`)) — Whether the authenticated user is considered new.; `1` — New user experience.; `0` — Established user.
- `submit_event` (string) — Client-side analytics or event identifier emitted on successful survey submission.
- `server_type` (string) — Product/server type identifier (e.g., cpanel, whm).
- `user_type` (string (`cpanel`, `webmail`)) — Type of authenticated user context.

```bash
uapi --output=jsonpretty \
--user=username \
InProductSurvey \
get_in_product_survey_url
```

