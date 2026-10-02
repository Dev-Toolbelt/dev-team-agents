<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — cPanel Theme Management

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Application Information**: [`Branding::get_application_information`](#branding-get-application-information), [`Branding::get_applications`](#branding-get-applications), [`Branding::get_available_applications`](#branding-get-available-applications), [`Branding::get_information_for_applications`](#branding-get-information-for-applications)
- **Branding Files**: [`Branding::include`](#branding-include)
- **Browser Cache Management**: [`CacheBuster::read`](#cachebuster-read), [`CacheBuster::update`](#cachebuster-update)
- **Brand Management**: [`Chrome::get_dom`](#chrome-get-dom)
- **Language**: [`Locale::get_attributes`](#locale-get-attributes), [`Locale::list_locales`](#locale-list-locales), [`Locale::set_locale`](#locale-set-locale)
- **Theme Settings**: [`Themes::get_theme_base`](#themes-get-theme-base), [`Themes::list`](#themes-list), [`Themes::update`](#themes-update)

## Application Information

<a id="branding-get-application-information"></a>
### `Branding::get_application_information` — Return single app's info from dynamicui.conf

`GET /execute/Branding/get_application_information` · RO · since cPanel 11.42

This function retrieves an application's information from the `dynamicui.conf` file.

**Parameters**

- `app_key` · **required** · string · e.g. `boxtrapper` — The application's feature name. This value **must** match a feature's `app_key` value. For a list of app_key values, read our [Guide to cPanel Interface Customization - Appkeys](https://go.cpanel.net/appkey) documentation.

**Returns** `data`: object

- `feature` (string) — The application's feature name.
- `file` (string) — The application's icon's filename.
- `group` (string) — The application's group.
- `height` (integer) — The application's icon's height, in pixels.
- `if` (string) — Conditional arguments that determine whether to display the item, if any exist.
- `imgtype` (string (`icon`)) — The item's image type.
- `itemdesc` (string) — The application's display name.
- `itemorder` (integer) — The application's order in the `dynamicui.conf` file representing the application's display order in cPanel's Home interface.
- `module` (string) — The application's module.
- `searchtext` (string) — One or more search terms.
- `subtype` (string (`img`)) — The item's subtype.
- `type` (string (`image`)) — The application's type.
- `url` (string) — The location to which the application's icon links.
- `width` (integer) — The application's icon's width representing an image width, in pixels.

```bash
uapi --output=jsonpretty \
  --user=username \
  Branding \
  get_application_information \
  app_key='boxtrapper'
```

<a id="branding-get-applications"></a>
### `Branding::get_applications` — Return multiple apps' info from dynamicui.conf

`GET /execute/Branding/get_applications` · RO · since cPanel 11.52

This function retrieves an application's information from a specific theme's `dynamicui.conf` file.

**Parameters**

- `app_keys` · optional · string · e.g. `addon_domains,ftp_accounts,anonymous_ftp` — A comma-separated list of an application feature names. If you do not specify this parameter, the output will include all of the applications that the `dynamicui.conf` file contains. Note:  This value must match an application's `feature` value in the `dynamicui.conf` file.; For more information, read our [Guide to cPanel Interface Customization - Appkeys](https://go.cpanel.net/appkey) documentation.

**Returns** `data`: any

```bash
uapi --output=jsonpretty \
  --user=username \
  Branding \
  get_applications
```

<a id="branding-get-available-applications"></a>
### `Branding::get_available_applications` — Return current user's cPanel application details

`GET /execute/Branding/get_available_applications` · RO · since cPanel 54

This function retrieves information about the groups and applications in the authenticated user's cPanel interface.

**Parameters**

- `nvarglist` · optional · string · e.g. `pref|software|domains` — A pipe-separated list of group names denoting the order in which to sort the groups. If you do not supply a value, the function does not sort the groups. Note: `arglist` is an alias for this parameter.

**Returns** `data`: object

- `default_group_order` (object) — An object that defines the default order of applications in cPanel.
- `grouporder` (array of string) — A list of group IDs, in the order in which the groups appear.
- `groups` (array of object) — Information about each group in the cPanel interface.
  - *(array of objects)*
    - `desc` (string) — The group's description.
    - `group` (string) — The group's ID.
    - `items` (array of object) — The groups and their application details.
- `implements` (object) — An object mapping the `implements` names to Appkey values for applications in cPanel.
- `index` (object) — The applications and the order in which they appear in the cPanel interface.

```bash
uapi --output=jsonpretty \
  --user=username \
  Branding \
  get_available_applications
```

<a id="branding-get-information-for-applications"></a>
### `Branding::get_information_for_applications` — Return app's info from sitemap.json

`GET /execute/Branding/get_information_for_applications` · RO · since cPanel 11.52

This function retrieves an application's information from a specific theme's `sitemap.json` file.

**Parameters**

- `docroot` · **required** · string <path> · e.g. `/usr/local/cpanel/base/webmail/jupiter` — The absolute path to the directory containing the `sitemap.json` file. This is the path to your theme's document root.
- `app_keys` · optional · string · e.g. `email_filters` — A comma-separated list of Appkey names. If you do **not** specify this parameter, the output will include all of the applications that the `sitemap.json` file contains. Note: This value **must** match an application's `key` value in the `sitemap.json` file. For more information, read our [Guide to cPanel Interface Customization - Appkeys](https://go.cpanel.net/appkey) documentation.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Branding \
  get_information_for_applications \
  docroot='/usr/local/cpanel/base/webmail/jupiter'
```

## Branding Files

<a id="branding-include"></a>
### `Branding::include` — Return branding file content from the active theme

`GET /execute/Branding/include` · RO · since cPanel 11.42

This function retrieves and renders a branding file from the active theme. The file may be a Template Toolkit (`.tt`) file or a standard HTML/image file. When the file is a Template Toolkit file, the system processes it and returns the rendered output. Otherwise, the system returns the file's raw or HTML-encoded content.

**Parameters**

- `file` · **required** · string · e.g. `header.tt` — The relative path to the branding file within the theme directory.
- `data` · optional · string <json> · e.g. `{"logoColor":"blue","showBanner":1}` — A JSON-encoded object containing additional variables to pass to the Template Toolkit template when rendering a `.tt` file. This parameter is ignored for non-template files.
- `raw` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to return the raw file content without HTML encoding.; `1` — Return the raw file content.; `0` — Return HTML-encoded content. This is the default behavior. This parameter has no effect when the file is a Template Toolkit (`.tt`) file.
- `skip_default` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to skip the default branding fallback.; `1` — Do not fall back to the default branding file if the theme-specific file does not exist. This parameter has no effect for accounts that do not have a branding package assigned; the theme fallback is always applied in that case.; `0` — Fall back to the default branding file. This is the default behavior.

**Returns** `data`: string — The rendered or retrieved content of the requested branding file.

```bash
uapi --output=jsonpretty \
  --user=username \
  Branding \
  include \
  file='header.tt'
```

## Browser Cache Management

<a id="cachebuster-read"></a>
### `CacheBuster::read` — Return web browser cached file override ID

`GET /execute/CacheBuster/read` · RO · since cPanel 11.46

This function returns the current `CacheBuster` id. The system uses this ID to force the browser to fetch a new resource when that resource already exists in the web browser cache. This is useful when an application has updated the resource on the server. You should append this ID to the end of the url in the query-string. For example, if you are accessing a url like: `https://example.com/styled/basic/sprites/icon_spritemap.css` To force the browser to fetch the updated version, you would append the following: `https://example.com/styled/basic/sprites/icon_spritemap.css?<CacheBusterID>` **Note** The application that updates the resource at this url on the server **must** call the `CacheBuster::update` function when it updates the resource to signify that update.

**Returns** `data`: object

- `cache_id` (integer) — An eight-digit random integer that the system uses to work around a browser's caching mechanism.

```bash
uapi --output=jsonpretty \
  --user=username \
  CacheBuster \
  read
```

<a id="cachebuster-update"></a>
### `CacheBuster::update` — Create web browser cached file override ID

`GET /execute/CacheBuster/update` · RW · rollback: none · since cPanel 11.46

This function generates a random integer (the CacheBuster ID). Use this ID to work with and around a browser's caching mechanism.

**Returns** `data`: object

- `cache_id` (integer) — random integer that the system uses to work with and around a browser's caching mechanism.

```bash
uapi --output=jsonpretty \
  --user=username \
  CacheBuster \
  update
```

## Brand Management

<a id="chrome-get-dom"></a>
### `Chrome::get_dom` — Return cPanel theme header and footer HTML

`GET /execute/Chrome/get_dom` · RO · since cPanel 11.42

This function returns header and footer HTML. You can use this HTML to create a page with the same visual appearance as your cPanel theme.

**Parameters**

- `page_title` · **required** · string · e.g. `Test` — The title of the page to wrap in the theme's headers and footers.

**Returns** `data`: object

- `footer` (string) — The pages' footer.
- `header` (string) — The pages' header.

```bash
uapi --output=jsonpretty \
  --user=username \
  Chrome \
  get_dom \
  page_title='Test'
```

## Language

<a id="locale-get-attributes"></a>
### `Locale::get_attributes` — Return current locale settings

`GET /execute/Locale/get_attributes` · RO · since cPanel 11.42

This function retrieves information about the user's current locale setting.

**Returns** `data`: object

- `direction` (string (`ltr`, `rtl`)) — The locale's text direction.; `ltr` - left to right.; `rtl` - right to left.
- `encoding` (string) — The user's character set.
- `locale` (string <ISO-3166-1 (alpha-2)>) — The locale's two-letter ISO-3166 code.
- `name` (string) — The locale's full name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Locale \
  get_attributes
```

<a id="locale-list-locales"></a>
### `Locale::list_locales` — Return available locales

`GET /execute/Locale/list_locales` · RO · since cPanel 82

This function lists an account's available interface languages.

**Returns** `data`: array of object

- *(array of objects)*
  - `direction` (string (`ltr`, `rtl`)) — The locale's text direction.; `ltr` - Left to right.; `rtl` - Right to left.
  - `local_name` (string) — The locale's full name, in the locale's language.
  - `locale` (string <ISO-3166-1 (alpha-2)>) — The locale's two-letter [ISO-3166 code](http://www.iso.org/iso/country_codes.htm).
  - `name` (string) — The locale's full name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Locale \
  list_locales
```

<a id="locale-set-locale"></a>
### `Locale::set_locale` — Update cPanel account locale

`GET /execute/Locale/set_locale` · RW · rollback: none · since cPanel 82

This function sets the account's locale.

**Parameters**

- `locale` · **required** · string · e.g. `en` — The locale's abbreviated name according to UAPI's `Locale::list_locales` function.

```bash
uapi --output=jsonpretty \
  --user=username \
  Locale \
  set_locale \
  locale='en'
```

## Theme Settings

<a id="themes-get-theme-base"></a>
### `Themes::get_theme_base` — Return current theme

`GET /execute/Themes/get_theme_base` · RO · since cPanel 11.50 · **DEPRECATED**

This function is deprecated and does not return useful output.

**Returns** `data`: string (`jupiter`, `unknown`) — The cPanel account's base theme.

```bash
uapi --output=jsonpretty \
  --user=username \
  Themes \
  get_theme_base
```

<a id="themes-list"></a>
### `Themes::list` — Return available themes

`GET /execute/Themes/list` · RO · since cPanel 11.42

This function lists available themes. Note: The `/usr/local/cpanel/scripts/modify_accounts` script allows you to modify the style and theme for many or all accounts on the server. For more information, read our [The modify_accounts Script](https://go.cpanel.net/modifyaccounts) documentation.

**Parameters**

- `show_mail_themes` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to list the account's mail themes.; `1` — List mail themes.; `0` — Do **not** list mail themes.

**Returns** `data`: array of string — An array that contains the account's themes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Themes \
  list
```

<a id="themes-update"></a>
### `Themes::update` — Update current theme

`GET /execute/Themes/update` · RW · rollback: none · since cPanel 11.42

This function applies a new theme to the cPanel interface. Note: The `/usr/local/cpanel/scripts/modify_accounts` script allows you to modify the theme for many or all accounts on the server. For more information, read our [The modify_accounts Script](https://go.cpanel.net/modifyaccounts) documentation.

**Parameters**

- `theme` · **required** · string · e.g. `jupiter` — The theme name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Themes \
  update \
  theme='jupiter'
```

