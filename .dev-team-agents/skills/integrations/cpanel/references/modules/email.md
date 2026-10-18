<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Email

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Spam Prevention (BoxTrapper)**: [`BoxTrapper::blacklist_messages`](#boxtrapper-blacklist-messages), [`BoxTrapper::delete_messages`](#boxtrapper-delete-messages), [`BoxTrapper::deliver_messages`](#boxtrapper-deliver-messages), [`BoxTrapper::get_allowlist`](#boxtrapper-get-allowlist), [`BoxTrapper::get_blocklist`](#boxtrapper-get-blocklist), [`BoxTrapper::get_configuration`](#boxtrapper-get-configuration), [`BoxTrapper::get_email_template`](#boxtrapper-get-email-template), [`BoxTrapper::get_forwarders`](#boxtrapper-get-forwarders), [`BoxTrapper::get_ignorelist`](#boxtrapper-get-ignorelist), [`BoxTrapper::get_log`](#boxtrapper-get-log), [`BoxTrapper::get_message`](#boxtrapper-get-message), [`BoxTrapper::get_status`](#boxtrapper-get-status), [`BoxTrapper::ignore_messages`](#boxtrapper-ignore-messages), [`BoxTrapper::list_email_templates`](#boxtrapper-list-email-templates), [`BoxTrapper::list_queued_messages`](#boxtrapper-list-queued-messages), [`BoxTrapper::process_messages`](#boxtrapper-process-messages), [`BoxTrapper::reset_email_template`](#boxtrapper-reset-email-template), [`BoxTrapper::save_configuration`](#boxtrapper-save-configuration), [`BoxTrapper::save_email_template`](#boxtrapper-save-email-template), [`BoxTrapper::set_allowlist`](#boxtrapper-set-allowlist), [`BoxTrapper::set_blocklist`](#boxtrapper-set-blocklist), [`BoxTrapper::set_forwarders`](#boxtrapper-set-forwarders), [`BoxTrapper::set_ignorelist`](#boxtrapper-set-ignorelist), [`BoxTrapper::set_status`](#boxtrapper-set-status), [`BoxTrapper::whitelist_messages`](#boxtrapper-whitelist-messages)
- **Email Accounts**: [`CSVImport::doimport`](#csvimport-doimport), [`Email::account_name`](#email-account-name), [`Email::add_auto_responder`](#email-add-auto-responder), [`Email::add_pop`](#email-add-pop), [`Email::browse_mailbox`](#email-browse-mailbox), [`Email::count_auto_responders`](#email-count-auto-responders), [`Email::count_pops`](#email-count-pops), [`Email::delete_auto_responder`](#email-delete-auto-responder), [`Email::delete_held_messages`](#email-delete-held-messages), [`Email::delete_pop`](#email-delete-pop), [`Email::dispatch_client_settings`](#email-dispatch-client-settings), [`Email::edit_pop_quota`](#email-edit-pop-quota), [`Email::get_auto_responder`](#email-get-auto-responder), [`Email::get_client_settings`](#email-get-client-settings), [`Email::get_default_email_quota`](#email-get-default-email-quota), [`Email::get_default_email_quota_mib`](#email-get-default-email-quota-mib), [`Email::get_disk_usage`](#email-get-disk-usage), [`Email::get_held_message_count`](#email-get-held-message-count), [`Email::get_main_account_disk_usage`](#email-get-main-account-disk-usage), [`Email::get_main_account_disk_usage_bytes`](#email-get-main-account-disk-usage-bytes), [`Email::get_max_email_quota`](#email-get-max-email-quota), [`Email::get_max_email_quota_mib`](#email-get-max-email-quota-mib), [`Email::get_pop_quota`](#email-get-pop-quota), [`Email::get_webmail_settings`](#email-get-webmail-settings), [`Email::hold_outgoing`](#email-hold-outgoing), [`Email::list_auto_responders`](#email-list-auto-responders), [`Email::list_default_address`](#email-list-default-address), [`Email::list_mail_domains`](#email-list-mail-domains), [`Email::list_pops`](#email-list-pops), [`Email::list_pops_with_disk`](#email-list-pops-with-disk), [`Email::passwd_pop`](#email-passwd-pop), [`Email::release_outgoing`](#email-release-outgoing), [`Email::set_default_address`](#email-set-default-address), [`Email::set_manual_mx_redirects`](#email-set-manual-mx-redirects), [`Email::terminate_mailbox_sessions`](#email-terminate-mailbox-sessions), [`Email::trace_delivery`](#email-trace-delivery), [`Email::unset_manual_mx_redirects`](#email-unset-manual-mx-redirects), [`Email::verify_password`](#email-verify-password)
- **Mail Server Information**: [`Chkservd::get_exim_ports`](#chkservd-get-exim-ports), [`Chkservd::get_exim_ports_ssl`](#chkservd-get-exim-ports-ssl)
- **Email Forwarding**: [`Email::add_domain_forwarder`](#email-add-domain-forwarder), [`Email::add_forwarder`](#email-add-forwarder), [`Email::count_forwarders`](#email-count-forwarders), [`Email::delete_domain_forwarder`](#email-delete-domain-forwarder), [`Email::delete_forwarder`](#email-delete-forwarder), [`Email::list_domain_forwarders`](#email-list-domain-forwarders), [`Email::list_forwarders`](#email-list-forwarders), [`Email::list_forwarders_backups`](#email-list-forwarders-backups)
- **Mailing Lists**: [`Email::add_list`](#email-add-list), [`Email::add_mailman_delegates`](#email-add-mailman-delegates), [`Email::count_lists`](#email-count-lists), [`Email::delete_list`](#email-delete-list), [`Email::export_lists`](#email-export-lists), [`Email::generate_mailman_otp`](#email-generate-mailman-otp), [`Email::get_lists_total_disk_usage`](#email-get-lists-total-disk-usage), [`Email::get_mailman_delegates`](#email-get-mailman-delegates), [`Email::has_delegated_mailman_lists`](#email-has-delegated-mailman-lists), [`Email::list_lists`](#email-list-lists), [`Email::passwd_list`](#email-passwd-list), [`Email::remove_mailman_delegates`](#email-remove-mailman-delegates), [`Email::set_list_privacy_options`](#email-set-list-privacy-options)
- **Spam Management**: [`Email::add_spam_filter`](#email-add-spam-filter), [`Email::disable_spam_assassin`](#email-disable-spam-assassin), [`Email::disable_spam_autodelete`](#email-disable-spam-autodelete), [`Email::disable_spam_box`](#email-disable-spam-box), [`Email::enable_spam_assassin`](#email-enable-spam-assassin), [`Email::enable_spam_box`](#email-enable-spam-box), [`Email::get_spam_settings`](#email-get-spam-settings), [`SpamAssassin::clear_spam_box`](#spamassassin-clear-spam-box), [`SpamAssassin::get_symbolic_test_names`](#spamassassin-get-symbolic-test-names), [`SpamAssassin::get_user_preferences`](#spamassassin-get-user-preferences), [`SpamAssassin::update_user_preference`](#spamassassin-update-user-preference)
- **Email Server Information**: [`Email::check_fastmail`](#email-check-fastmail), [`Email::disable_mailbox_autocreate`](#email-disable-mailbox-autocreate), [`Email::enable_mailbox_autocreate`](#email-enable-mailbox-autocreate), [`Email::fetch_charmaps`](#email-fetch-charmaps), [`Email::fts_rescan_mailbox`](#email-fts-rescan-mailbox), [`Email::get_charsets`](#email-get-charsets), [`Email::get_mailbox_autocreate`](#email-get-mailbox-autocreate), [`Email::has_plaintext_authentication`](#email-has-plaintext-authentication), [`Email::set_always_accept`](#email-set-always-accept), [`Email::stats_db_status`](#email-stats-db-status)
- **Email Filtering**: [`Email::count_filters`](#email-count-filters), [`Email::delete_filter`](#email-delete-filter), [`Email::disable_filter`](#email-disable-filter), [`Email::enable_filter`](#email-enable-filter), [`Email::get_filter`](#email-get-filter), [`Email::list_filters`](#email-list-filters), [`Email::list_filters_backups`](#email-list-filters-backups), [`Email::list_system_filter_info`](#email-list-system-filter-info), [`Email::reorder_filters`](#email-reorder-filters), [`Email::store_filter`](#email-store-filter), [`Email::trace_filter`](#email-trace-filter)
- **Email Suspensions**: [`Email::suspend_incoming`](#email-suspend-incoming), [`Email::suspend_login`](#email-suspend-login), [`Email::suspend_outgoing`](#email-suspend-outgoing), [`Email::unsuspend_incoming`](#email-unsuspend-incoming), [`Email::unsuspend_login`](#email-unsuspend-login), [`Email::unsuspend_outgoing`](#email-unsuspend-outgoing)
- **Signing and Encryption (GnuPG Keys)**: [`GPG::delete_keypair`](#gpg-delete-keypair), [`GPG::export_public_key`](#gpg-export-public-key), [`GPG::export_secret_key`](#gpg-export-secret-key), [`GPG::generate_key`](#gpg-generate-key), [`GPG::import_key`](#gpg-import-key), [`GPG::list_public_keys`](#gpg-list-public-keys), [`GPG::list_secret_keys`](#gpg-list-secret-keys)
- **Mailbox Management**: [`Mailboxes::expunge_mailbox_messages`](#mailboxes-expunge-mailbox-messages), [`Mailboxes::expunge_messages_for_mailbox_guid`](#mailboxes-expunge-messages-for-mailbox-guid), [`Mailboxes::get_mailbox_status_list`](#mailboxes-get-mailbox-status-list), [`Mailboxes::has_utf8_mailbox_names`](#mailboxes-has-utf8-mailbox-names), [`Mailboxes::set_utf8_mailbox_names`](#mailboxes-set-utf8-mailbox-names)
- **Webmail Sessions**: [`Session::create_temp_user`](#session-create-temp-user), [`Session::create_webmail_session_for_mail_user`](#session-create-webmail-session-for-mail-user), [`Session::create_webmail_session_for_mail_user_check_password`](#session-create-webmail-session-for-mail-user-check-password), [`Session::create_webmail_session_for_self`](#session-create-webmail-session-for-self)
- **Webmail Applications**: [`WebmailApps::list_webmail_apps`](#webmailapps-list-webmail-apps)
- **Spam Filtering (Greylisting)**: [`cPGreyList::disable_all_domains`](#cpgreylist-disable-all-domains), [`cPGreyList::disable_domains`](#cpgreylist-disable-domains), [`cPGreyList::enable_all_domains`](#cpgreylist-enable-all-domains), [`cPGreyList::enable_domains`](#cpgreylist-enable-domains), [`cPGreyList::has_greylisting_enabled`](#cpgreylist-has-greylisting-enabled), [`cPGreyList::list_domains`](#cpgreylist-list-domains)

## Spam Prevention (BoxTrapper)

<a id="boxtrapper-blacklist-messages"></a>
### `BoxTrapper::blacklist_messages` — Add email address to BoxTrapper blocked senders

`GET /execute/BoxTrapper/blacklist_messages` · RW · rollback: none · since cPanel 82

This function blacklists email message senders. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system disables this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The email address for which to blacklist messages. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated user.
- `queuefile` · **required** · string · e.g. `example.msg` — The filename of the email message to blacklist.

**Returns** `data`: array of object — An array of objects of blacklisted email information.

- *(array of objects)*
  - `email` (string <email>) — The email address that sent the blacklisted message.
  - `failed` (integer (`1`)) — Whether the system failed to blacklist the message.
  - `matches` (array of string) — An array of messages that the system deleted.
  - `operator` (string (`blacklist`)) — The action that the function performed.
  - `reason` (string) — A message about the failure or the warning.
  - `warning` (integer (`1`)) — Whether the system experienced issues when it blacklisted the message.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  blacklist_messages \
  email='user@example.com' \
  queuefile='file1'
```

<a id="boxtrapper-delete-messages"></a>
### `BoxTrapper::delete_messages` — Delete messages in the BoxTrapper queue

`GET /execute/BoxTrapper/delete_messages` · RW · rollback: none · since cPanel 82

This function deletes messages in the BoxTrapper queue. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system disables this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.
- `queuefile` · **required** · string · e.g. `example.msg` — The filename of the email message who's sender to delete. Warning: To delete multiple email message senders, duplicate the parameter name.
- `all_like` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to delete all messages that resemble the `queuefile` parameter's value.; `1` - Delete all messages resembling the `queuefile` parameter.; `0` - Do **not** delete all messages resembling the `queuefile` parameter.

**Returns** `data`: array of object — An array of objects that contain information about the messages that matched the requested pattern.

- *(array of objects)*
  - `email` (string <email>) — The deleted email message's sender.
  - `failed` (integer (`1`)) — Whether the system failed to delete the messages.
  - `matches` (array of string) — An array of messages that the system deleted.
  - `operator` (string (`delete`)) — The operation that the system performed.
  - `reason` (string) — A message about the failure or the warning.
  - `warning` (integer (`1`)) — Whether the system experienced issues when it deleted the message.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  delete_messages \
  email='user@example.com' \
  queuefile='file1.msg'
```

<a id="boxtrapper-deliver-messages"></a>
### `BoxTrapper::deliver_messages` — Send messages in the BoxTrapper queue

`GET /execute/BoxTrapper/deliver_messages` · RW · rollback: none · since cPanel 82

This function delivers messages in the BoxTrapper queue. Important: When you disable the [*Receive Mail* role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The sender's cPanel account email address for which to deliver email messages. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.
- `queuefile` · **required** · string — The filename of the email messages to deliver. Note: To deliver multiple email messages, pass this parameter multiple times.
- `all_like` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to deliver all messages that resemble the `queuefile` parameter's value.; `1` - Deliver all similar messages.; `0` - Don't deliver all similar messages.

**Returns** `data`: array of object — The delivered email message information.

- *(array of objects)*
  - `email` (string <email>) — The delivered email message's sender.
  - `failed` (integer (`1`)) — Whether the system could not deliver the message.
  - `matches` (array of string) — A list of delivered email messages.
  - `operator` (string (`deliver`, `deliverall`)) — The action that the function performed.; `deliver`; `deliverall`
  - `reason` (string) — A message about the failure or the warning.
  - `warning` (integer (`1`)) — Whether the system experienced issues when it delivered the message.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  deliver_messages \
  email='user@example.com' \
  queuefile='example.msg'
```

<a id="boxtrapper-get-allowlist"></a>
### `BoxTrapper::get_allowlist` — Return account BoxTrapper allowlist rules

`GET /execute/BoxTrapper/get_allowlist` · RO · since cPanel 94

This function retrieves a list of BoxTrapper allowlist configuration rules. BoxTrapper will deliver emails that match these rules. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.

**Returns** `data`: array of string — The allowlist configuration rules.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_allowlist \
  email='user@example.com'
```

<a id="boxtrapper-get-blocklist"></a>
### `BoxTrapper::get_blocklist` — Return account BoxTrapper blocklist rules

`GET /execute/BoxTrapper/get_blocklist` · RO · since cPanel 94

This function retrieves a list of BoxTrapper blocklist configuration rules. BoxTrapper will delete messages that match these rules and send a notification to the sender. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.

**Returns** `data`: array of string — The blocklist configuration rules.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_blocklist \
  email='user@example.com'
```

<a id="boxtrapper-get-configuration"></a>
### `BoxTrapper::get_configuration` — Return email account's BoxTrapper configuration

`GET /execute/BoxTrapper/get_configuration` · RO · since cPanel 82

This function retrieves an account's BoxTrapper configuration. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system disables this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.

**Returns** `data`: object

- `enable_auto_whitelist` (integer (`0`, `1`)) — Whether whitelisting is enabled.; 1 - Enabled.; 0 - Disabled.
- `from_addresses` (string) — The email addresses that send emails from the account.
- `from_name` (string) — The name of the person who owns the email account.
- `queue_days` (integer) — The number of days that the system retains log files and queued messages.
- `spam_score` (number) — The account's [Apache SpamAssassin](https://go.cpanel.net/cpaneldocsSpamFilters) threshold score.
- `whitelist_by_association` (integer (`0`, `1`)) — Whether the system whitelisted the email addresses in a message's `To` and `From` sections, including carbon-copied (CC) recipients.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_configuration \
  email='user@example.com'
```

<a id="boxtrapper-get-email-template"></a>
### `BoxTrapper::get_email_template` — Return specified BoxTrapper email template

`GET /execute/BoxTrapper/get_email_template` · RO · rollback: none · since cPanel 84

This function retrieves a BoxTrapper email message template. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.
- `template` · **required** · string (`blacklist`, `returnverify`, `verifyreleased`, `verify`) · e.g. `verify` — The message template.; `blacklist`; `returnverify`; `verifyreleased`; `verify` Note: For more information on each template, read our [BoxTrapper](https://go.cpanel.net/cpaneldocsBoxTrapper) documentation.

**Returns** `data`: string — The template file's contents.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_email_template \
  email='user@example.com' \
  template='verify'
```

<a id="boxtrapper-get-forwarders"></a>
### `BoxTrapper::get_forwarders` — Return all BoxTrapper forwarders

`GET /execute/BoxTrapper/get_forwarders` · RO · since cPanel 86

This function retrieves a list of email addresses to which BoxTrapper forwards email messages. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Important: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.

**Returns** `data`: array of string — The email addresses to which BoxTrapper forwards email.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_forwarders \
  email='user@example.com'
```

<a id="boxtrapper-get-ignorelist"></a>
### `BoxTrapper::get_ignorelist` — Return account BoxTrapper ignorelist rules

`GET /execute/BoxTrapper/get_ignorelist` · RO · since cPanel 94

This function retrieves a list of BoxTrapper ignorelist configuration rules. BoxTrapper will delete messages that match these rules without sending a notification to the sender. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.

**Returns** `data`: array of string — The ignorelist configuration rules.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_ignorelist \
  email='user@example.com'
```

<a id="boxtrapper-get-log"></a>
### `BoxTrapper::get_log` — Return BoxTrapper log file and contents

`GET /execute/BoxTrapper/get_log` · RO · since cPanel 82

This function returns the account's BoxTrapper log file and its contents. Important: When you disable the [Receive Mail role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Important: If you call this function in Webmail, the system ignores this parameter and defaults to the currently authenticated email address.
- `date` · optional · integer <unix_timestamp> · e.g. `1556812881` — The date for which to return the log file and its contents. Note: This parameter defaults to the current date.

**Returns** `data`: object

- `date` (integer <unix_timestamp>) — The date for which the system returned the log.
- `lines` (array of string) — An array of lines from the log file.
- `path` (string) — The log file's filepath.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_log \
  email='user@example.com'
```

<a id="boxtrapper-get-message"></a>
### `BoxTrapper::get_message` — Return message's top 200 lines in BoxTrapper queue

`GET /execute/BoxTrapper/get_message` · RO · since cPanel 82

This function returns the first 200 lines of an email in the BoxTrapper queue. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> or string <username> — The account’s name, either an email address or the cPanel user’s username. Important: If you call this function in Webmail, the system ignores this parameter.
- `queuefile` · **required** · string · e.g. `example.msg` — The message's filename.

**Returns** `data`: object

- `content` (string) — The email message's contents.
- `contents` (any) — 
- `queuefile` (string) — The message's filename.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_message \
  email='user@example.com' \
  queuefile='example.msg'
```

<a id="boxtrapper-get-status"></a>
### `BoxTrapper::get_status` — Return whether email account uses BoxTrapper

`GET /execute/BoxTrapper/get_status` · RO · since cPanel 82

This function checks whether BoxTrapper is enabled for an email account. Important: When you disable the [Receive Mail role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Important: If you call this function in Webmail, the system ignores this parameter.

**Returns** `data`: integer (`0`, `1`) — Whether BoxTrapper is enabled for the email account.; `1` — Enabled.; `0` — Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  get_status \
  email='user@example.com'
```

<a id="boxtrapper-ignore-messages"></a>
### `BoxTrapper::ignore_messages` — Add email account to Exim ignore list

`GET /execute/BoxTrapper/ignore_messages` · RW · rollback: none · since cPanel 82

This function marks email message senders for Exim to ignore. Important: When you disable the [Receive Mail role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The cPanel email account from which to ignore messages. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.
- `queuefile` · **required** · string — The filename of the email message to ignore. Note: To ignore multiple email messages, duplicate this parameter.

**Returns** `data`: array of object — An array of objects containing ignored email message information.

- *(array of objects)*
  - `email` (string <email>) — The ignored email message's sender.
  - `failed` (integer (`1`)) — Whether the system failed to ignore the messages.; `1` - Failed to ignore the message.; `1` - Failed to ignore the message.; `1` - Failed to ignore the message.; `1` - Failed to ignore the message.; `1` - Failed to ignor
  - `matches` (array of string) — An array containing ignored message files.
  - `operator` (string (`ignore`)) — The operation that the system performed.; `ignore` — The system ignored this email message.
  - `reason` (string) — A message that describes the failure or the warning.
  - `warning` (integer (`1`)) — Whether the system experienced issues when it ignored the message.; `1` — The system encountered a problem.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  ignore_messages \
  email='user@example.com' \
  queuefile='example.msg'
```

<a id="boxtrapper-list-email-templates"></a>
### `BoxTrapper::list_email_templates` — Return BoxTrapper email templates

`GET /execute/BoxTrapper/list_email_templates` · RO · since cPanel 84

This function lists the BoxTrapper email templates. Important: When you **disable** the [Receive Mail](https://go.cpanel.net/serverroles) role, the system disables this function.

**Returns** `data`: array of string (`blacklist`, `verify`, `verifyreleased`, `returnverify`) — An array of strings representing BoxTrapper message templates.; `blacklist` - BoxTrapper responds with this message when a blacklisted address sends an email.; `verify` - BoxTrapper responds with this message when an add

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  list_email_templates
```

<a id="boxtrapper-list-queued-messages"></a>
### `BoxTrapper::list_queued_messages` — Return email account's BoxTrapper queued messages

`GET /execute/BoxTrapper/list_queued_messages` · RO · since cPanel 82

This function returns a list of messages in the account's BoxTrapper queue. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The email account for which to retrieve queued messages. Important: If you call this function in Webmail, the system ignores this parameter and defaults to the currently authenticated email address.
- `date` · optional · integer <unix_timestamp> · e.g. `1556812881` — The date for which to return queued messages.

**Returns** `data`: array of object — Information about each queued message.

- *(array of objects)*
  - `from` (string <email>) — The sender's email address.
  - `queuefile` (string) — The message's unique ID.
  - `subject` (string) — The message's subject.
  - `time` (integer <unix_timestamp>) — The message's creation time.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  list_queued_messages \
  email='user@example.com'
```

<a id="boxtrapper-process-messages"></a>
### `BoxTrapper::process_messages` — Run a specific BoxTrapper action for a message

`GET /execute/BoxTrapper/process_messages` · RW · rollback: none · since cPanel 82

This function performs a specified action on messages in the BoxTrapper queue. Important: When you disable the [*Receive Mail*](https://go.cpanel.net/serverroles#roles) role, the system **disables** this function.

**Parameters**

- `action` · **required** · string (`deliver`, `deliverall`, `delete`, `deleteall`, `blacklist`, `whitelist`, `ignore`) · e.g. `blacklist` — The action to perform on the email message file. To perform multiple actions on the specified email messages, pass this parameter multiple times.; `deliver` — Deliver a specific message.; `deliverall` — Deliver all messages from a sender.; `delete` — Delete a message.; `deleteall` — Delete all messages from a sender.; `blacklist` — Blacklist the sender of an email message.; `whitelist` — Whitelist the sender of an email message.; `ignore` — Ignore email messages from a sender. Note: The function performs the actions on the email messages files in the order that you pass each action.
- `queuefile` · **required** · string · e.g. `example.msg` — The filename of the email message to process. To process multiple email messages, pass this parameter multiple times.
- `email` · optional · string <email> · e.g. `user@example.com` — The account's email address. Warning:  The `email` parameter is required when this function is called **outside** of Webmail.; If you call this function in Webmail, the `email` parameter is **not** required, and the system overrides this parameter with the current authenticated user's email address.

**Returns** `data`: array of object — An array of objects containing processed email message information.

- *(array of objects)*
  - `email` (string <email>) — The email address for which the system processed an email message.
  - `failed` (integer (`1`)) — Whether the system failed to process the message.; `1` - The function failed to process the message.
  - `matches` (array of string) — An array of email messages that the system processed.
  - `operator` (string (`deliver`, `deliverall`, `delete`, `deleteall`, `blacklist`, `whitelist`, `ignore`)) — The operation that the system performed.; `deliver` - Delivered a specific message.; `deliverall` - Delivered all messages from a sender.; `delete` - Deleted a message.; `deleteall` - Deleted all messages from a sender.;
  - `reason` (string) — A message about the failure or the warning.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  process_messages \
  queuefile='example.msg' \
  action='blacklist'
```

<a id="boxtrapper-reset-email-template"></a>
### `BoxTrapper::reset_email_template` — Restore default BoxTrapper email message template

`GET /execute/BoxTrapper/reset_email_template` · RW · rollback: clean · since cPanel 84

This function restores the BoxTrapper email message templates to the system default setting. Important: When you **disable** the [Receive Mail](https://go.cpanel.net/serverroles) role, the system disables this function.

**Parameters**

- `template` · **required** · string (`blacklist`, `verify`, `verifyreleased`, `returnverify`) · e.g. `verify` — The message template. Possible values: `blacklist` - BoxTrapper responds with this message when a blacklisted address sends an email.; `verify` - BoxTrapper responds with this message when an address that does not exist on the whitelist or blacklist sends an email. This message requests a response to confirm that the sender is legitimate.; `verifyreleased` - BoxTrapper responds with this message when a person responds to the verify message with an email or a click on the verification link.; `returnverify` - BoxTrapper responds with this message when the verification process fails.
- `email` · optional · string <email> · e.g. `user@example.com` — The account's email address. Warning: The `email` parameter is required when this function is called outside of webmail. If you call this function in Webmail, the `email` parameter is not required, and the system overrides this parameter with the current authenticated user's email address.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  reset_email_template \
  template='verify'
```

<a id="boxtrapper-save-configuration"></a>
### `BoxTrapper::save_configuration` — Update email account's BoxTrapper configuration

`GET /execute/BoxTrapper/save_configuration` · RW · rollback: clean · since cPanel 82

This function modifies an account's BoxTrapper configuration. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.
- `enable_auto_whitelist` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to enable automatic whitelisting for the account.; `1` - Enable.; `0` - Disable.
- `from_addresses` · **required** · string <email-csv> · e.g. `sender1@test.com,sender2@test.com` — A comma-separated list of email addresses that the system uses when it sends messages back to the original message senders.
- `queue_days` · **required** · integer · e.g. `14` — The number of days to retain log files and queued messages.
- `whitelist_by_association` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to whitelist the email addresses in a message's *To* and *From* sections, including carbon-copied (CC) recipients.; `1` - Whitelist.; `0` - Do **not** whitelist.
- `from_name` · optional · string · e.g. `User` — The name of the person who owns the email account.
- `spam_score` · optional · number · e.g. `2.5` — The account's Apache SpamAssassin™ threshold score. For more information about Apache SpamAssassin threshold scores, read our [Spam Filters](https://go.cpanel.net/cpaneldocsSpamFilters) documentation. Note: This parameter defaults to the account's current configuration.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  save_configuration \
  email='user@example.com' \
  from_addresses='sender1@test.com,sender2@test.com' \
  queue_days='14' \
  enable_auto_whitelist='1' \
  whitelist_by_association='1'
```

<a id="boxtrapper-save-email-template"></a>
### `BoxTrapper::save_email_template` — Save BoxTrapper message template contents

`GET /execute/BoxTrapper/save_email_template` · RW · rollback: clean · since cPanel 84

This function saves the contents of a BoxTrapper message template. Important: When you disable the [_Receive Mail_ role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `contents` · **required** · string — The template file's contents. You can use [variables](https://go.cpanel.net/cpaneldocsBoxTrapper) in the template to include details about the original message. Important:  You **must** include `To: %email%` in this parameter's value.; If you use the `verify` template, you **must** include `Subject: verify#%msgid%` in this parameter's value.; This value cannot exceed four kilobytes (KB).; You **must** URI-encode this parameter's value when using the CLI.
- `email` · **required** · string <email> · e.g. `user@example.com` — The account's email address. Warning: If you call this function in Webmail, the system overrides this parameter. Note: This parameter defaults to the current email address.
- `template` · **required** · string (`blacklist`, `returnverify`, `verifyreleased`, `verify`) · e.g. `blacklist` — The message template.; `blacklist`; `returnverify`; `verifyreleased`; `verify` Important: If you use the `verify` template, you **must** include `Subject: verify#%msgid%` in this parameter's value. Note: For more information about each template, read our [BoxTrapper documentation](https://go.cpanel.net/cpaneldocsBoxTrapper).

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  save_email_template \
  email='user@example.com' \
  template='blacklist' \
  contents='To: %25email%25
Subject: Re: %25subject%25

The user %25acct%25 does not accept mail from your address.

The headers of the message sent from your address are shown below:

%25headers%25'
```

<a id="boxtrapper-set-allowlist"></a>
### `BoxTrapper::set_allowlist` — Update account BoxTrapper allowlist

`GET /execute/BoxTrapper/set_allowlist` · RW · rollback: clean · since cPanel 94

This function sets the BoxTrapper allowlist configuration rules. BoxTrapper will deliver emails that match these rules. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.
- `rules` · **required** · array of string — An array of allowlist rules. Note: You can set multiple allowlist rules, duplicate or increment the parameter name. For example, `rules-1`, `rules-2`, and `rules-3`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty --user=username BoxTrapper set_allowlist email='user@example.com' rules-1='allowlisted-email\@domain\.com' rules-2='from allowlisted-email2\@domain\.com' rules-3='to domain2\.com'
```

<a id="boxtrapper-set-blocklist"></a>
### `BoxTrapper::set_blocklist` — Update account BoxTrapper blocklist

`GET /execute/BoxTrapper/set_blocklist` · RW · rollback: clean · since cPanel 94

This function sets the BoxTrapper blocklist configuration rules. BoxTrapper will delete messages that match these rules and send a notification to the sender. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.
- `rules` · **required** · array of string — An array of blocklist rules. Note: You can set multiple block rules, duplicate or increment the parameter name. For example, `rules-1`, `rules-2`, and `rules-3`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty --user=username BoxTrapper set_blocklist email='user@example.com' rules-1='blocklisted-email\@domain\.com' rules-2='from blocklisted-email2\@domain\.com' rules-3='to domain2\.com'
```

<a id="boxtrapper-set-forwarders"></a>
### `BoxTrapper::set_forwarders` — Add email address to BoxTrapper forwarders

`GET /execute/BoxTrapper/set_forwarders` · RW · rollback: clean · since cPanel 86

This function adds a list of email addresses to which BoxTrapper forwards email messages. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string · e.g. `user@example.com` — The account's email address. Warning: If you call this function in Webmail, the system ignores this parameter and uses the currently-authenticated email address.
- `forwarder` · **required** · array of any <email> — The email addresses to which to forward email messages.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  set_forwarders \
  email='user@example.com' \
  forwarder='user1@example.com'
```

<a id="boxtrapper-set-ignorelist"></a>
### `BoxTrapper::set_ignorelist` — Update account BoxTrapper ignorelist

`GET /execute/BoxTrapper/set_ignorelist` · RW · rollback: clean · since cPanel 94

This function sets the BoxTrapper ignorelist configuration rules. BoxTrapper will delete messages that match these rules without sending a notification to the sender. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — A valid email address on the cPanel account. Warning: If you call this function in Webmail, the system overrides this parameter. This parameter defaults to the current email address.
- `rules` · **required** · array of string — An array of ignorelist rules. Note: You can set multiple ignore rules, duplicate or increment the parameter name. For example, `rules-1`, `rules-2`, and `rules-3`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty --user=username BoxTrapper set_ignorelist email='user@example.com' rules-1='ignored-email\@domain\.com' rules-2='from ignored-email2\@domain\.com' rules-3='to domain2\.com'
```

<a id="boxtrapper-set-status"></a>
### `BoxTrapper::set_status` — Enable or disable BoxTrapper for email account

`GET /execute/BoxTrapper/set_status` · RW · rollback: none · since cPanel 82

This function enables or disables BoxTrapper for an email account. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> or string <username> — The account's name. This can be an email address or the cPanel user’s username. Warning: If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.
- `enabled` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to enable or disable BoxTrapper for the email account.; `1` - Enable BoxTrapper.; `0` - **Disable** BoxTrapper.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  set_status \
  email='user@example.com' \
  enabled='1'
```

<a id="boxtrapper-whitelist-messages"></a>
### `BoxTrapper::whitelist_messages` — Add email address to BoxTrapper allowed senders

`GET /execute/BoxTrapper/whitelist_messages` · RW · rollback: none · since cPanel 82

This function whitelists email messages. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function. Note: To retrieve email messages in the BoxTrapper queue from senders that you did not previously whitelist, use the UAPI `BoxTrapper::deliver_messages` function.

**Parameters**

- `queuefile` · **required** · string · e.g. `example.msg` — The filename of the email message to whitelist. Note: To get a list of filenames in an account's BoxTrapper queue, use the UAPI `BoxTrapper::list_queued_messages` function. Note: To whitelist multiple email messages, duplicate this parameter.
- `email` · optional · string <email> · e.g. `user@example.com` — The cPanel account email address for which to whitelist messages. **Warning** If you call this function in Webmail, the system ignores this parameter and defaults to the currently-authenticated email address.

**Returns** `data`: array of object — An array of one or more objects, depending on how many queuefiles were passed as parameters.

- *(array of objects)*
  - `email` (string <email>) — A whitelisted email address.
  - `failed` (string (`1`)) — The system failed to whitelist the message.; `1` — The function failed to whitelist the message.
  - `matches` (array of string) — An array of message files that the system whitelisted.
  - `operator` (string (`whitelist`)) — The action that the system performed.
  - `reason` (string) — The reason the function skipped the message during whitelisting.
  - `warning` (integer (`1`)) — Whether the system experienced issues when it whitelisted the message.; `1` — There was an issue whitelisting the message.

```bash
uapi --output=jsonpretty \
  --user=username \
  BoxTrapper \
  whitelist_messages \
  queuefile='example.msg'
```

## Email Accounts

<a id="csvimport-doimport"></a>
### `CSVImport::doimport` — Import email accounts from CSV file

`GET /execute/CSVImport/doimport` · RW · rollback: none · since cPanel 94

This function imports email accounts from an already uploaded CSV file.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain under which to add the email accounts.
- `id` · **required** · string · e.g. `Leq58oid3sF3Moye3_YbJGqoMvCb7M4j` — The unique ID of the import operation. The cPanel API 2 CSVImport::uploadimport function generates this ID and stores it in the `CPVAR` attribute named `csvimportid`.
- `type` · **required** · string (`email`, `fwd`) · e.g. `email` — The type of email address to add.; `email` — A regular email account.; `fwd` — A forwarder.

**Returns** `data`: object

- `results` (array of object) — The results for each attempted add operation.
  - *(array of objects)*
    - `email` (string <email>) — The email address or forwarder.
    - `fwd` (string <email>) — The destination of the forwarder (if applicable).
    - `reason` (string) — The explanation of the outcome for each operation.
    - `status` (integer (`0`, `1`)) — The outcome of each operation.; `1` — Success.; `0` — Failed.
    - `type` (string (`email`, `fwd`)) — The type of email address.; `email` — A regular email account.; `fwd` — A forwarder.

```bash
uapi --output=jsonpretty \
  --user=username \
  CSVImport \
  doimport \
  id='Leq58oid3sF3Moye3_YbJGqoMvCb7M4j' \
  type='email' \
  domain='example.com'
```

<a id="email-account-name"></a>
### `Email::account_name` — Return current user's account name

`GET /execute/Email/account_name` · RO · since cPanel 11.42

This function returns the provided value. This function works with other functions to display form data within a user interface. Note: If you call this function from a Webmail session URL, the system will **only** access data for that email account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · optional · string · e.g. `user` — The function will return this value in the data return. If you do **not** include this parameter, the function returns `All Mail On The Account` or a blank value.; A valid string.; An empty value. Note: The function does **not** validate this parameter's value.
- `display` · optional · string · e.g. `any_value` — Include this parameter to cause the function to return `All Mail On The Account` if the account parameter is blank or does not exist. If you do **not** include this parameter and the account value is blank or does not exist, the function returns a blank data value.

**Returns** `data`: string <email> — The account parameter's value.; A valid string.; `All Mail On The Account`; An empty value.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  account_name
```

<a id="email-add-auto-responder"></a>
### `Email::add_auto_responder` — Create email account's autoresponder

`GET /execute/Email/add_auto_responder` · RW · rollback: none · since cPanel 11.42

This function creates an autoresponder for an email account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `body` · **required** · string · e.g. `This is an autoresponder message.` — The contents of the autoresponder message's `Body` section.
- `domain` · **required** · string <domain> · e.g. `example.com` — The email account's domain. For example, `example.com` if the email address is `user@example.com`.
- `email` · **required** · string · e.g. `user` — The email account name. For example, `user` if the email address is `user@example.com`.
- `from` · **required** · string · e.g. `User Name` — The contents of the autoresponder message's `From:` field.
- `interval` · **required** · integer · e.g. `24` — The amount of time, in hours, that the server waits between autoresponder messages to the same address. Note: If you specify `0`, the system sends a message for each received email.
- `is_html` · **required** · integer (`0`, `1`) · e.g. `1` — Whether the body of the autoresponder message begins with an [HTML Content-Type declaration](https://en.wikipedia.org/wiki/Character_encodings_in_HTML#Specifying_the_document.27s_character_encoding).; `1` — Include an HTML content type declaration.; `0` — Do **not** include an HTML content type declaration.
- `start` · **required** · integer <unix_timestamp> · e.g. `1410277881` — When to enable the autoresponder.
- `stop` · **required** · integer <unix_timestamp> · e.g. `1410300000` — When to disable the autoresponder. A time that is after the `start` time.
- `subject` · **required** · string · e.g. `Autoresponder Subject` — The contents of the autoresponder message's `Subject:` field.
- `charset` · optional · string · default `utf-8` · e.g. `UTF-8` — The [character set](https://en.wikipedia.org/wiki/Character_encoding).

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_auto_responder \
  email='user' \
  from='User Name' \
  subject='Autoresponder Subject' \
  body='This is an autoresponder message.' \
  domain='example.com' \
  is_html='1' \
  interval='24' \
  start='1410277881' \
  stop='1410300000'
```

<a id="email-add-pop"></a>
### `Email::add_pop` — Create email account

`GET /execute/Email/add_pop` · RW · rollback: clean · since cPanel 11.42

This function creates an email address. Important:  When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.; We recommend that you use the UAPI `UserManager::create_user` function to create an email address instead of this function. This function is incompatible with [the *Reset Password* feature](https://go.cpanel.net/resetpassdocs).; You **must** URI-encode values when using the CLI.

**Parameters**

- `email` · **required** · string or string <email> · e.g. `user` — The email account username or address.; A valid email account username. For example, `user` to create `user@example.com`.; A valid email address. Note: You **cannot** enter `cpanel` as an account name when you create an email account.
- `password` · **required** · string · e.g. `123456luggage` — The email account password.
- `domain` · optional · string <domain> · default `The cPanel account's main domain.` · e.g. `example.com` — The email account's domain. For example, `example.com` to create `user@example.com`.
- `password_hash` · optional · string — The account's password hash. Notes:  You can use this parameter instead of the `password` parameter. However, you cannot use both `password` and `password_hash` parameters in the same request.; You can find your server's hash type in the `/etc/sysconfig/authconfig` file.
- `quota` · optional · integer or string (`unlimited`) · default `The defined system value.` · e.g. `500` — The maximum amount of disk space that the new email account may use.; A positive integer that represents the maximum amount of disk space, in megabytes (MB).; `0` or `unlimited` — The account possesses unlimited disk space. Note:  The positive integer value **cannot** exceed the maximum email quota.; The `0` or `unlimited` value is **only** available to users **without** a maximum email account quota.
- `send_welcome_email` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to send client configuration instructions to the account.; `1` — Send the instructions.; `0` — Do **not** send the instructions.
- `skip_update_db` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to skip the update of the email accounts database's cache.; `1` — Skip the update.; `0` — Perform the update.

**Returns** `data`: string — The email address.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_pop \
  email='user' \
  password='123456luggage'
```

<a id="email-browse-mailbox"></a>
### `Email::browse_mailbox` — Return mail directory's subdirectories and files

`GET /execute/Email/browse_mailbox` · RO · since cPanel 11.42

This function lists the mail directory's subdirectories (boxes) and files. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function. Notes: If you do not use any input parameters, the function returns a list of items in the cPanel account's main mail directory.

**Parameters**

- `account` · optional · string <email> · e.g. `user@example.com` — An email address, to limit the function's results.
- `dir` · optional · string · e.g. `maildir` — A mail directory name, to limit results to specific directories. Note: If you pass the `default` or `mail` values, the function lists information for all mail directories.
- `showdotfiles` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to include hidden files and directories.; `1` — Include hidden items.; `0` — Do **not** include hidden items.

**Returns** `data`: array of object

- *(array of objects)*
  - `depth` (integer) — The directory depth of the item's path.
  - `file` (string) — The item's base name.
  - `fullpath` (string <path>) — The item's absolute path.
  - `isleaf` (integer (`0`, `1`)) — Whether the item is a file or a directory.; `1` - File.; `0` - Directory.
  - `ismailbox` (integer (`0`, `1`)) — Whether the item is a mailbox.; `1` - Mailbox.; `0` - **Not** a mailbox.
  - `mtime` (integer <unix_timestamp>) — The item's modification time.
  - `path` (string <path>) — The item's directory's path.
  - `relpath` (string <path>) — The item's relative path.
  - `type` (string (`dir`, `file`)) — The item type.; `dir` - The item is a directory.; `file` - The item is a file.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  browse_mailbox
```

<a id="email-count-auto-responders"></a>
### `Email::count_auto_responders` — Return cPanel account's autoresponders total

`GET /execute/Email/count_auto_responders` · RO · since cPanel 82

This function returns the number of [autoresponders](https://go.cpanel.net/Autoresponders) for every email address on a cPanel account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: integer — The number of email autoresponders.; `0`; A positive integer.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  count_auto_responders
```

<a id="email-count-pops"></a>
### `Email::count_pops` — Return cPanel account's email account total

`GET /execute/Email/count_pops` · RO · since cPanel 82

This function returns the number of [email accounts](https://go.cpanel.net/cpaneldocsEmailAccounts) for a cPanel account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: integer — The number of email accounts.; `0`; A positive integer.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  count_pops
```

<a id="email-delete-auto-responder"></a>
### `Email::delete_auto_responder` — Delete email account's autoresponder

`GET /execute/Email/delete_auto_responder` · RW · rollback: none · since cPanel 11.42

This function deletes an autoresponder. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The email account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_auto_responder \
  email='user@example.com'
```

<a id="email-delete-held-messages"></a>
### `Email::delete_held_messages` — Delete email account's outgoing messages

`GET /execute/Email/delete_held_messages` · RW · rollback: none · since cPanel 74

This function deletes all outbound email messages held in the mail queue for the specified email account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email address to query.

**Returns** `data`: integer — The number of held outbound email messages deleted from the mail queue.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_held_messages \
  email='username@example.com'
```

<a id="email-delete-pop"></a>
### `Email::delete_pop` — Delete email account

`GET /execute/Email/delete_pop` · RW · rollback: lossy · since cPanel 11.42

This function deletes an email address. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string or string <email> — The email account username or address.; A valid email account username. For example, `user` if the email address is `user@example.com`.; A valid email address.
- `domain` · optional · string <domain> · default `The cPanel account's main domain.` · e.g. `example.com` — The email account's domain. For example, `example.com` if the email address is `user@example.com`.
- `flags` · optional · string · e.g. `passwd` — Whether to remove the mail account's home mail directory. If you do not specify a value, the function removes the mail account's home directory.; `passwd` — Preserve the mail account's home directory.; Any other value — Remove the mail account's home directory.
- `skip_quota` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to modify the mail account's quota file.; `1` — Do **not** modify.; `0` — Modify.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_pop \
  email='user@domain.com'
```

<a id="email-dispatch-client-settings"></a>
### `Email::dispatch_client_settings` — Send email client settings to an email address

`GET /execute/Email/dispatch_client_settings` · RW · rollback: none · since cPanel 62

This function sends an email account's client settings to an email address. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · **required** · string <email> or string <username> — The email account username or address for which to send client settings.
- `to` · **required** · string <email> · e.g. `user@example.com` — The email address to send client settings.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  dispatch_client_settings \
  to='user@example.com' \
  account='username'
```

<a id="email-edit-pop-quota"></a>
### `Email::edit_pop_quota` — Update email account's quota

`GET /execute/Email/edit_pop_quota` · RW · rollback: clean · since cPanel 11.42

This function changes an email address's quota.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The email account's domain. Defaults to the cPanel account's main domain.
- `email` · **required** · string · e.g. `user` — The email account username.
- `quota` · optional · string · e.g. `500` — The maximum amount of disk space that the new email account may use. Defaults to the system value.; A positive integer that represents the maximum amount of disk space, in megabytes (MB). Note: You **cannot** enter a value that exceeds the maximum email quota.; `0` or `unlimited` — The account possesses unlimited disk space. If the email account's quota value is set higher (or unlimited) than the account's max quota, the account's max quota will be applied instead of the value entered. Note: This value is only available to users without a maximum email account quota.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  edit_pop_quota \
  email='user' \
  domain='example.com'
```

<a id="email-get-auto-responder"></a>
### `Email::get_auto_responder` — Return email account's autoresponder information

`GET /execute/Email/get_auto_responder` · RO · since cPanel 11.42

This function retrieves autoresponder information. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <username> · e.g. `user` — The email account name.
- `temp_charset` · optional · string · default `utf-8` · e.g. `utf-8` — The autoresponder's [character set](https://en.wikipedia.org/wiki/Character_encoding).

**Returns** `data`: object

- `body` (string) — The contents of the autoresponder message's `Body` section.
- `charset` (string) — The autoresponder's [character set](https://en.wikipedia.org/wiki/Character_encoding).
- `from` (string) — The contents of the autoresponder message's `From` field.
- `interval` (integer) — The amount of time, in hours, that the server waits between autoresponder messages to the same address.
- `is_html` (integer (`0`, `1`)) — Whether the body of the autoresponder message begins with an [HTML content type declaration](https://en.wikipedia.org/wiki/Character_encodings_in_HTML#Specifying_the_document.27s_character_encoding).; `1` - Includes an H
- `start` (integer <unix_timestamp>) — When the autoresponder becomes enabled in Unix time.
- `stop` (integer <unix_timestamp>) — When the autoresponder becomes disabled in Unix time.
- `subject` (string) — The contents of the autoresponder message's `Subject` field.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_auto_responder \
  email='user'
```

<a id="email-get-client-settings"></a>
### `Email::get_client_settings` — Return email account's client settings

`GET /execute/Email/get_client_settings` · RO · since cPanel 62

This function retrieves an email account's client settings. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · optional · string <email> · e.g. `username@example.com` — The email address for which to send client settings. Note: This parameter defaults to the [system default email account](https://go.cpanel.net/systemdefaultemailaccount).

**Returns** `data`: object

- `account` (string <email>) — The account's email address.
- `activesync_available` (integer (`1`, `0`)) — Whether the account supports ActiveSync.; `1` — Supported.; `0` — **Not** supported.
- `activesync_host` (string <domain>) — The account's ActiveSync hostname.
- `activesync_port` (integer) — The account's ActiveSync SSL/TLS port.
- `activesync_username` (string <email>) — The account's ActiveSync username.
- `display` (string <email>) — The account's display name.
- `domain` (string <domain>) — The account's domain name.
- `from_archiving` (integer (`1`, `0`)) — Whether the account is a mail archive.; `1` — The account is a mail archive.; `0` — The account is **not** a mail archive.
- `has_plaintext_authentication` (integer (`1`, `0`)) — Whether the account supports plaintext authentication.; `1` — Supported.; `0` — **Not** supported.
- `inbox_host` (string <domain>) — The account's hostname.
- `inbox_insecure_port` (integer) — The account's insecure inbound port.
- `inbox_port` (integer) — The account's secure inbound port.
- `inbox_service` (string (`imap`, `pop`)) — The service type that the account uses.; `imap`; `pop`
- `inbox_username` (string <email>) — The account's username.
- `mail_domain` (string <domain>) — The account's mail hostname.
- `smtp_host` (string <domain>) — The account's outbound SMTP hostname.
- `smtp_insecure_port` (integer) — The account's insecure outbound SMTP port.
- `smtp_port` (integer) — The account's secure outbound SMTP port.
- `smtp_username` (string <email>) — The account's SMTP username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_client_settings
```

<a id="email-get-default-email-quota"></a>
### `Email::get_default_email_quota` — Return email account's default email quota

`GET /execute/Email/get_default_email_quota` · RO · since cPanel 11.48

This function retrieves the account's default email quota size, in bytes format. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: integer — The default email quota in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_default_email_quota
```

<a id="email-get-default-email-quota-mib"></a>
### `Email::get_default_email_quota_mib` — Return email account's default email quota in MiB

`GET /execute/Email/get_default_email_quota_mib` · RO · since cPanel 11.48

This function retrieves the account's default email quota size in [mebibytes](https://en.wikipedia.org/wiki/Mebibyte) (MiB). Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: integer — The default email quota in [mebibytes](https://en.wikipedia.org/wiki/Mebibyte) (MiB).

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_default_email_quota_mib
```

<a id="email-get-disk-usage"></a>
### `Email::get_disk_usage` — Return email account's disk usage

`GET /execute/Email/get_disk_usage` · RO · since cPanel 11.42

This function retrieves the disk space that an email account uses. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The email account's domain.
- `user` · **required** · string <username> · e.g. `user` — The email account username.

**Returns** `data`: object

- `diskused` (number) — The disk space that the email account uses.; A positive floating-point value that represents the disk space, used in megabytes (MB).; `0` - The account posesses an unlimited disk quota.
- `domain` (string <domain>) — The email account's domain.
- `login` (string <email>) — The email address or the main account username.
- `user` (string) — The email account's username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_disk_usage \
  user='user' \
  domain='example.com'
```

<a id="email-get-held-message-count"></a>
### `Email::get_held_message_count` — Return email account's outgoing message count

`GET /execute/Email/get_held_message_count` · RO · since cPanel 74

This function returns the count of outbound email messages held in the mail queue for the specified email account. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · optional · string <email> · e.g. `username@example.com` — The email address to query.

**Returns** `data`: integer — The number of messages currently held in the mail queue.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_held_message_count
```

<a id="email-get-main-account-disk-usage"></a>
### `Email::get_main_account_disk_usage` — Return primary email account's disk usage

`GET /execute/Email/get_main_account_disk_usage` · RO · since cPanel 11.42

This function returns the disk space that the main account uses. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: string — The current amount of disk space that the main email account uses.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_main_account_disk_usage
```

<a id="email-get-main-account-disk-usage-bytes"></a>
### `Email::get_main_account_disk_usage_bytes` — Return primary email account's disk usage in bytes

`GET /execute/Email/get_main_account_disk_usage_bytes` · RO · since cPanel 64

This function returns the disk space that the cPanel account uses. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: integer — The current amount of disk space that the main email account uses, in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_main_account_disk_usage_bytes
```

<a id="email-get-max-email-quota"></a>
### `Email::get_max_email_quota` — Return email account's max quota size

`GET /execute/Email/get_max_email_quota` · RO · since cPanel 11.48

This function retrieves the account's maximum email quota size, in bytes format. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: integer — The account's maximum email quota, in bytes format.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_max_email_quota
```

<a id="email-get-max-email-quota-mib"></a>
### `Email::get_max_email_quota_mib` — Return email account's max quota size in MiB

`GET /execute/Email/get_max_email_quota_mib` · RO · since cPanel 11.48

This function retrieves the account's maximum email account quota size, in [Mebibytes (MiB)](https://en.wikipedia.org/wiki/Mebibyte) format. Important: When you disable the [Receive Mail role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: integer — The account's maximum email account quota size, in Mebibytes (MiB).

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_max_email_quota_mib
```

<a id="email-get-pop-quota"></a>
### `Email::get_pop_quota` — Return email account's quota

`GET /execute/Email/get_pop_quota` · RO · since cPanel 11.42

This function retrieves an email account's quota. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `email` · **required** · string · e.g. `user` — The email account username.  For example, user if the email address is user@example.com.
- `as_bytes` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return the quota as bytes.; `1` — Return the quota as bytes.; `0` — Return the quota as megabytes (MB).
- `domain` · optional · string <domain> · e.g. `example.com` — The email account's domain. This parameter defaults to the cPanel account's main domain.

**Returns** `data`: integer — The email account's quota.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_pop_quota \
  email='user'
```

<a id="email-get-webmail-settings"></a>
### `Email::get_webmail_settings` — Return email account's Webmail settings

`GET /execute/Email/get_webmail_settings` · RO · since cPanel 11.42

This function retrieves an email account's Webmail settings. Important: When you disable the [_Receive Mail_ role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · optional · string <email> or string <username> — The email account. Note: If you do **not** specify a value, the function retrieves settings for the cPanel account's default mail account.

**Returns** `data`: object

- `domain` (string <domain>) — The email account's mail server hostname.
- `has_maildir` (integer (`1`)) — Whether `Maildir` is enabled for the email account.; `1` — Enabled.
- `user` (string <email> or string <username>) — The email account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_webmail_settings
```

<a id="email-hold-outgoing"></a>
### `Email::hold_outgoing` — Stop email account's outgoing mail

`GET /execute/Email/hold_outgoing` · RW · rollback: none · since cPanel 70

This function sets Exim's queue to not send outgoing mail from an email account. Notes:  To send all mail from the queue, use the UAPI `Email::release_outgoing` function.; To reject outgoing mail and not place mail in a queue, use the UAPI `Email::suspend_outgoing` function.; This function does **not** hold local outgoing mail.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account's username.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  hold_outgoing \
  email='username@example.com'
```

<a id="email-list-auto-responders"></a>
### `Email::list_auto_responders` — Return domain's autoresponders

`GET /execute/Email/list_auto_responders` · RO · since cPanel 11.42

This function lists a domain's autoresponders. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.
- `regex` · optional · string · e.g. `user` — A [Perl Compatible Regular Expression (PCRE)](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) that filters the results.

**Returns** `data`: array of object

- *(array of objects)*
  - `email` (string <email>) — The autoresponder's email address.
  - `subject` (string) — The contents of the autoresponder message's `Subject:` field.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_auto_responders \
  domain='example.com'
```

<a id="email-list-default-address"></a>
### `Email::list_default_address` — Return domain's default email address

`GET /execute/Email/list_default_address` · RO · since cPanel 11.42

This function retrieves a domain's default address. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `user` · **required** · string <username> · e.g. `user` — The user whose default addresses to list.
- `domain` · optional · string <domain> · e.g. `example.com` — The domain. If you do not specify a value, the function lists default addresses for all of the cPanel account's domains.

**Returns** `data`: array of object — An object of data for a domain.

- *(array of objects)*
  - `defaultaddress` (string) — The domain's default address.; An email account username - The system forwards unroutable mail to this address.; `:fail:` - The system bounces unroutable mail back to the sender, and sends a failure message.; `:blackhole
  - `domain` (string <domain>) — The domain name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_default_address \
  user='user'
```

<a id="email-list-mail-domains"></a>
### `Email::list_mail_domains` — Return cPanel account's mail domains

`GET /execute/Email/list_mail_domains` · RO · since cPanel 11.42

This function lists the account's mail domains. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function. Note: This function **always** returns the account's main domain first. **Additional Note:** By default, temporary domains (*.cpanel.site) are excluded. Use the `return_temporary_domain` parameter to include them.

**Parameters**

- `add_www` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to list `www.` addresses.; `1` — List `www.` addresses.; `0` — Do **not** list `www.` addresses. For example, if you specify `1`, the function's output would include both `example.com` and `www.example.com`. If you specify `0`, the output would include **only** `example.com`.
- `include_wildcard` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to list wildcard addresses.; `1` — List wildcard addresses.; `0` — Do **not** list wildcard addresses. For example, if you specify `1`, the function's output would include both `example.com` and `*.example.com`. If you specify `0`, the output would include **only** `example.com`.
- `return_temporary_domain` · optional · boolean · default `False` — Whether to include temporary domains (*.cpanel.site) in the output. By default, temporary domains are excluded.
- `select` · optional · string <domain> · e.g. `example.com` — The name of the domain that the function returns with the `select `output parameter. If you do **not** use this parameter, the function will **not** return the `select` parameter with any domains.

**Returns** `data`: array of object

- *(array of objects)*
  - `domain` (string <domain>) — The domain name.
  - `select` (integer) — The domain that you specified in the `select` input parameter.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_mail_domains
```

<a id="email-list-pops"></a>
### `Email::list_pops` — Return email accounts

`GET /execute/Email/list_pops` · RO · since cPanel 11.42

This function lists the cPanel account's email accounts. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `no_validate` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to skip the email database's validation check.; `1` — Skip the validation check.; `0` — Run the validation check.
- `regex` · optional · string · e.g. `user` — A [Perl Compatible Regular Expression (PCRE)](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) that filters the results.
- `skip_main` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to exclude the cPanel account's main account from the results.; `1` — Exclude the main account.; `0` — Include the main account.

**Returns** `data`: array of object — An object of data for an email address on the cPanel account.

- *(array of objects)*
  - `email` (string <email> or string <username>) — An email address.; A valid email address on the cPanel account.; The cPanel account username, for the main account.
  - `login` (string (`Main Account`) or string <email>) — The email account login.; A valid email address on the cPanel account.; `Main Account`, for the main account.
  - `suspended_incoming` (integer (`0`, `1`)) — Whether incoming email for the email account is suspended.; `1` - Suspended.; `0` - Not suspended.
  - `suspended_login` (integer (`0`, `1`)) — Whether logins for the email account are suspended.; `1` - Suspended.; `0` - Not suspended.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_pops
```

<a id="email-list-pops-with-disk"></a>
### `Email::list_pops_with_disk` — Return email accounts with disk information

`GET /execute/Email/list_pops_with_disk` · RO · since cPanel 11.42

This function lists the cPanel account's email accounts with disk information. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — A domain name to filter the results by. If you do **not** use this parameter, the function returns **all** of the cPanel account's email addresses.
- `email` · optional · string <username> · e.g. `user` — The cPanel user account to query. If you do **not** use this parameter, the function returns the email addresses for **all** cPanel accounts that the user owns. Note: To retrieve information for a single email address, add the domain parameter. For example, `email=user&domain=example.com` will return information for the email address `user@example.com`.
- `get_restrictions` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to display restriction status for each of the email addresses.; `1` — Display.; `0` — Do **not** display.
- `infinityimg` · optional · string · e.g. `images/myimg.jpg` — An image to display for email addresses with an unlimited quota. If you specify an `infinityimg` value, the function returns HTML code to display that image as the `diskquota` parameter's value.
- `infinitylang` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to return the `∞` character for email addresses with an unlimited quota.; `1` — Return the `∞` character for unlimited `diskquota` values.; `0` — Return the string `unlimited` for unlimited `diskquota` values. Note: If you specify `1` for this parameter **and** the `infinityimg` parameter, the function ignores **this** parameter and returns HTML code for unlimited `diskquota` values.
- `maxaccounts` · optional · integer · e.g. `500` — The maximum number of email addresses to return. If you do not use this parameter, the function returns an unlimited number of email addresses.
- `no_disk` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to skip the collection of disk usage information.; `1` — Do **not** collect.; `0` — Collect.
- `no_validate` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to skip email database validation.; `1` — Skip validation.; `0` — Perform the validation.
- `regex` · optional · string · default `An empty string` · e.g. `/^[a-z0-9_-]{6,18}$/` — A [Perl Compatible Regular Expression (PCRE)](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) that filters the results. For example, `/^[a-z0-9_-]{6,18}$/` matches the local portion of an email address, if it contains between six and 18 characters.

**Returns** `data`: array of object — An array of objects containing data for each email address.

- *(array of objects)*
  - `_diskquota` (integer) — The disk quota.; A positive value that represents the disk quota, in bytes.; `0` - The account possesses an unlimited disk quota.
  - `_diskused` (integer) — The disk space that the email account uses.; A positive value that represents the used disk space, in bytes.; `0` - The account possesses an unlimited disk quota.
  - `diskquota` (integer or string) — The email account's disk quota.; A positive value that represents the email address's quota, in megabytes (MB).; `unlimited`, `∞`, or HTML code to display an infinity image - The email account has an unlimited quota.
  - `diskused` (integer) — The disk space that the email account uses.; A positive floating-point value that represents the used disk space, in megabytes (MB).; `0` - The account possesses an unlimited disk quota.
  - `diskusedpercent` (integer) — The percentage of disk space that the email account uses.; A positive value.; `0` - The account has an unlimited disk quota.
  - `diskusedpercent20` (integer) — The percentage of disk space that the email account uses.; A positive value.; `0` - The account possesses an unlimited disk quota.
  - `diskusedpercent_float` (number) — The floating-point value from which the function derives the `diskusedpercent` return.; A floating-point value.; `0` - Unlimited or disabled disk quota.
  - `domain` (string <domain>) — The email account's domain.
  - `email` (string (`Main Account`) or string <email>) — The email address, or the string `Main Account`.; A valid email address.; `Main Account`
  - `has_suspended` (integer (`0`, `1`)) — Whether the email account possesses one of the following suspension parameters: `suspended_login` `suspended_incoming` `suspended_outgoing` `hold_outgoing`; `1` - The email account has a suspension.; `0` - The email acco
  - `hold_outgoing` (integer (`0`, `1`)) — Whether the email account's outgoing email is held in Exim's queue.; `1` - Outgoing email is held in Exim's queue.; `0` - Outgoing email is **not** held in Exim's queue.
  - `humandiskquota` (integer or string (`None`)) — The disk quota, in human-readable format.; The disk quota and the unit of measure.; `None` - The account possesses an unlimited disk quota.
  - `humandiskused` (string) — The disk space that the email account uses, in human-readable format.; The disk space that the email account uses, a non-breaking space (`\u00a0`), and the unit of measure.; `None` - The account possesses an unlimited di
  - `login` (string <email> or string <username>) — The email address, or the main account username.; A valid email address.; The username for the main account.
  - `mtime` (integer <unix_timestamp>) — The email account's last modification time, in [Unix time](https://wikipedia.org/wiki/Unix_time) format.
  - `suspended_incoming` (integer (`0`, `1`)) — Whether the email account's incoming email is suspended.; `1` - Suspended.; `0` - **Not** suspended.
  - `suspended_login` (integer (`0`, `1`)) — Whether the user's ability to log in to, send mail from, and read their email account is suspended.; `1` - Suspended.; `0` - **Not** suspended.
  - `suspended_outgoing` (integer (`0`, `1`)) — Whether the email account's outgoing email is suspended.; `1` - Suspended.; `0` - **Not** suspended.
  - `txtdiskquota` (integer or string (`unlimited`)) — The email account's disk quota.; A positive value that represents the email address's quota, in megabytes (MB).; `unlimited` - The email account has an unlimited quota.
  - `user` (string) — The email account username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_pops_with_disk
```

<a id="email-passwd-pop"></a>
### `Email::passwd_pop` — Update email account password

`GET /execute/Email/passwd_pop` · RW · rollback: none · since cPanel 11.42

This function changes an email account's password. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> or string <username> — The email account username or address.
- `password` · **required** · string · e.g. `12345luggage` — The email account password.
- `domain` · optional · string <domain> · default `the cPanel account's main domain` · e.g. `example.com` — The email account's domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  passwd_pop \
  email='username@example.com' \
  password='12345luggage'
```

<a id="email-release-outgoing"></a>
### `Email::release_outgoing` — Start email account outgoing mail

`GET /execute/Email/release_outgoing` · RW · rollback: none · since cPanel 70

This function sends all of the outgoing mail from Exim's queue for an email account. Note: To set Exim to queue all outgoing mail for an email account, use the UAPI `Email::hold_outgoing` function.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account's username.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  release_outgoing \
  email='username@example.com'
```

<a id="email-set-default-address"></a>
### `Email::set_default_address` — Create default email address

`GET /execute/Email/set_default_address` · RW · rollback: none · since cPanel 11.42

This function configures a default (catchall) email address. **Important**: When you disable the [Mail Receive role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `fwdopt` · **required** · string (`fwd`, `fail`, `blackhole`, `pipe`) · e.g. `fwd` — The method to use to handle unroutable mail.; `fwd` — Forward messages to the `fwdemail` parameter’s address.; `fail` — Bounce messages back to the sender, and include the `failmsgs` parameter’s failure message.; `blackhole` — Send messages to the `/dev/null/` directory. This method does **not** generate a failure notice.; `pipe` — Pipe mail to the `pipefwd` parameter’s application. This parameter requires the [File Storage role](https://go.cpanel.net/serverroles).
- `domain` · optional · string <domain> · e.g. `example.com` — The domain whose default email behavior you want to configure. **Note**: This parameter defaults to the cPanel account’s main domain.
- `failmsgs` · optional · string · default `No such person at this address` — The failure message for the message’s sender. **Note**: Use this parameter if you used the `fail` method for the `fwdopt` parameter.
- `fwdemail` · optional · string <email> · e.g. `admin@example.com` — The email address to which the system forwards messages. **Note**: Use this parameter if you used the `fwd` method for the `fwdopt` parameter.
- `pipefwd` · optional · string · e.g. `mailscript.pl` — The application to which the system pipes messages. **Note**: Use this parameter if you used the `pipe` method for the `fwdopt` parameter. **Important**: This parameter requires the [File Storage role](https://go.cpanel.net/serverroles).

**Returns** `data`: array of object — An array of hashes of forwarder information.

- *(array of objects)*
  - `dest` (string) — The destination to which the system sends unroutable mail.; An email address  The system forwards mail to this address.; :fail:  The system bounces mail back to the sender, and sends a failure message.; :blackhole:  The 
  - `domain` (string) — The domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  set_default_address \
  fwdopt='fwd'
```

<a id="email-set-manual-mx-redirects"></a>
### `Email::set_manual_mx_redirects` — Add manual MX redirection

`GET /execute/Email/set_manual_mx_redirects` · RW · rollback: none · since cPanel 96

This function lets you create a manual Exim mail exchanger (MX) redirect for a domain. An MX redirection lets you bypass the domain's MX lookup via the Domain Name System (DNS). This function adds the manual redirect entries to the `/etc/manualmx` file. Note: To remove a domain's manual MX redirection, use the UAPI Email `unset_manual_mx_redirect` function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain for which to add a manual MX redirect entry. Note:  To add multiple domain entries, increment the parameter. For example, use the `domain`, `domain-1`, and `domain-2` parameters.; For multiple domains, you **must** include its corresponding `mx_host` value.
- `mx_host` · **required** · string <domain> or string <ipv4> or string <ipv6> — The domain, IPv4, or IPv6 address to redirect the domain value's emails to. Note:  To add multiple MX hosts, increment the parameter. For example, use the `mx_host`, `mx_host-1`, and `mx_host-2` parameters.; For multiple MX hosts, you **must** include its corresponding `domain` value.

**Returns** `data`: object — A list of domains and the replaced manual MX redirect entries.

- `additionalProperties` (string) — The domain for which the function replaced the manual MX redirect entry.; null — The domain did not have an existing manual MX redirect entry.

```bash
uapi --output=jsonpretty --user=username Email set_manual_mx_redirects domain='example.com' mx_host='mailhostexample.com'
```

<a id="email-terminate-mailbox-sessions"></a>
### `Email::terminate_mailbox_sessions` — Stop cPanel account IMAP and POP3 connections

`GET /execute/Email/terminate_mailbox_sessions` · RW · rollback: none · since cPanel 96

This function terminates all IMAP and POP3 connections for a cPanel account. Note: This function ends connections for every email address, which includes the [default address](https://go.cpanel.net/cpaneldocsDefaultAddress).

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  terminate_mailbox_sessions
```

<a id="email-trace-delivery"></a>
### `Email::trace_delivery` — Run email delivery route trace

`GET /execute/Email/trace_delivery` · RO · since cPanel 84

This function traces the email delivery route to an email account.

**Parameters**

- `recipient` · **required** · string · e.g. `username@example.com` — The email address to which to trace a message delivery path.

**Returns** `data`: object

- `address` (string <email>) — The email address of an email message recipient.
- `type` (string) — A type of trace node.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  trace_delivery \
  recipient='username@example.com'
```

<a id="email-unset-manual-mx-redirects"></a>
### `Email::unset_manual_mx_redirects` — Remove manual MX redirection

`GET /execute/Email/unset_manual_mx_redirects` · RW · rollback: none · since cPanel 96

This function lets you create a manual Exim mail exchanger (MX) redirect for a domain. An MX redirection lets you bypass the domain's MX lookup via the Domain Name System (DNS). This function adds the manual redirect entries to the `/etc/manualmx` file. Note: To remove a domain's manual MX redirection, use the UAPI Email `unset_manual_mx_redirect` function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain for which to add a manual MX redirect entry. Note:  To add multiple domain entries, increment the parameter. For example, use the `domain`, `domain-1`, and `domain-2` parameters.; For multiple domains, you **must** include its corresponding `mx_host` value.

**Returns** `data`: object — A list of domains and the removed manual MX redirect entries.

- `additionalProperties` (string) — The domain for which the function removed the manual MX redirect entry.; null — The domain did not have a manual MX redirect entry.

```bash
uapi --output=jsonpretty --user=username Email unset_manual_mx_redirects domain='example.com'
```

<a id="email-verify-password"></a>
### `Email::verify_password` — Validate email account password

`GET /execute/Email/verify_password` · RW · rollback: none · since cPanel 11.52

This function verifies the password for an email account. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account address.
- `password` · **required** · string · e.g. `123456luggage` — The email account password.

**Returns** `data`: integer (`0`, `1`) — Whether the password is valid for the email account.; `1` - The password is valid.; `0` - The password is **not** valid.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  verify_password \
  email='username@example.com' \
  password='123456luggage'
```

## Mail Server Information

<a id="chkservd-get-exim-ports"></a>
### `Chkservd::get_exim_ports` — Return outgoing (SMTP) mail port

`GET /execute/Chkservd/get_exim_ports` · RO · since cPanel 11.42

This function lists the ports on which Exim listens.

**Returns** `data`: object

- `ports` (array of integer) — An array of port numbers on which Exim listens.

```bash
uapi --output=jsonpretty \
  --user=username \
  Chkservd \
  get_exim_ports
```

<a id="chkservd-get-exim-ports-ssl"></a>
### `Chkservd::get_exim_ports_ssl` — Return outgoing mail (SMTP) SSL-secured port

`GET /execute/Chkservd/get_exim_ports_ssl` · RO · since cPanel 11.42

This function retrieves Exim's SSL port.

**Returns** `data`: object

- `ports` (array of integer) — An array of port numbers on which Exim listens for SSL/TLS connections.

```bash
uapi --output=jsonpretty \
  --user=username \
  Chkservd \
  get_exim_ports_ssl
```

## Email Forwarding

<a id="email-add-domain-forwarder"></a>
### `Email::add_domain_forwarder` — Create domain-level forwarder

`GET /execute/Email/add_domain_forwarder` · RW · rollback: none · since cPanel 11.42

This function creates a domain-level forwarder. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `destdomain` · **required** · string <domain> · e.g. `forwardtome.com` — The domain to receive forwarded mail.
- `domain` · **required** · string <domain> · e.g. `example.com` — The domain on the cPanel account from which to forward mail.

**Returns** `data`: string — A message of success, or a reason for failure.; A message of success that lists the updated `vdomainaliases` file.; A reason for failure.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_domain_forwarder \
  domain='example.com' \
  destdomain='forwardtome.com'
```

<a id="email-add-forwarder"></a>
### `Email::add_forwarder` — Create email account forwarder

`GET /execute/Email/add_forwarder` · RW · rollback: none · since cPanel 11.42

This function creates an email forwarder. Important: When you disable the MailReceive role, the system disables this function. For more information, read our [How to Use Server Profiles](https://go.cpanel.net/howtouseserverprofiles) documentation.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain.
- `email` · **required** · string · e.g. `forwardme@example.com` — The email address to forward.
- `fwdopt` · **required** · string · e.g. `fwd` — The method to use to handle the email address's mail.
- `failmsgs` · optional · string · default `No such person at this address` · e.g. `Nobody home.` — The failure message for the message's sender. Note: Use this parameter if you used the fail method for the fwdopt parameter.
- `fwdemail` · optional · string · e.g. `fwdtome@example.com` — The email address to which the system forwards messages. Note: You must use this parameter if you used the fwd method for the fwdopt parameter. You can pass multiple addresses to this parameter as a comma-separated list.
- `fwdsystem` · optional · string · e.g. `user` — The system user to whom the system forwards messages. Note: You must use this parameter if you used the system method for the fwdopt parameter.
- `pipefwd` · optional · string · e.g. `mailscript.pl` — The application to which the system pipes messages. Note: You must use this parameter if you used the pipe method for the fwdopt parameter. Important: This parameter requires the FileStorage role. For more information, read our [How to Use Server Profiles](https://go.cpanel.net/howtouseserverprofiles) documentation.

**Returns** `data`: array of object

- *(array of objects)*
  - `domain` (string) — The domain.
  - `email` (string) — The email address.
  - `forward` (string) — The method that the system will use to handle the address's mail.; An email address  The system forwards mail to this address.; :fail:  The system bounces mail back to the sender and sends a failure message.; :blackhole:

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_forwarder \
  domain='example.com' \
  email='forwardme@example.com' \
  fwdopt='fwd'
```

<a id="email-count-forwarders"></a>
### `Email::count_forwarders` — Return cPanel account's mail forwarder total

`GET /execute/Email/count_forwarders` · RO · since cPanel 82

This function returns the number of [forwarders](https://go.cpanel.net/Forwarders) for every email address on a cPanel account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: integer — The number of email forwarders.; `0`; A positive integer.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  count_forwarders
```

<a id="email-delete-domain-forwarder"></a>
### `Email::delete_domain_forwarder` — Delete domain-level forwarder

`GET /execute/Email/delete_domain_forwarder` · RW · rollback: none · since cPanel 11.42

This function deletes a domain-level forwarder. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_domain_forwarder \
  domain='example.com'
```

<a id="email-delete-forwarder"></a>
### `Email::delete_forwarder` — Delete email account's email forwarder

`GET /execute/Email/delete_forwarder` · RW · rollback: none · since cPanel 11.42

This function deletes an email forwarder. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `address` · **required** · string <email> · e.g. `user@example.com` — The forwarder's email address.
- `forwarder` · **required** · string · e.g. `fwdtome@example.com` — The forwarder's destination.; A valid email address.; A script location.; A system account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_forwarder \
  address='user@example.com' \
  forwarder='fwdtome@example.com'
```

<a id="email-list-domain-forwarders"></a>
### `Email::list_domain_forwarders` — Return domain-level forwarders

`GET /execute/Email/list_domain_forwarders` · RO · since cPanel 11.42

This function lists domain-level forwarders. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — The domain name to query. If you do not use this parameter, the function returns all domain-level forwarders on the cPanel account.

**Returns** `data`: array of object — An array of objects containing domain forwarder information.

- *(array of objects)*
  - `dest` (string <domain>) — The forwarded domain.
  - `forward` (string <domain>) — The destination domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_domain_forwarders
```

<a id="email-list-forwarders"></a>
### `Email::list_forwarders` — Return domain's forwarders

`GET /execute/Email/list_forwarders` · RO · since cPanel 11.42

This function lists a domain's forwarders. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain.
- `regex` · optional · string · e.g. `user` — A [Perl Compatible Regular Expression (PCRE)](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) that filters the forwarded address or destination. If you do **not** use this parameter, the function returns all of the account's forwarders.

**Returns** `data`: array of object

- *(array of objects)*
  - `dest` (string <email>) — The forwarded address.
  - `forward` (string <email>) — The forwarded mail's destination.
  - `html_dest` (string <email>) — The forwarded address in an HTML-compatible format.
  - `html_forward` (string <email>) — The forwarded mail's destination in an HTML-compatible format.
  - `uri_dest` (string) — The forwarded address in a URI-encoded format.
  - `uri_forward` (string) — The forwarded mail's destination in a URI-encoded format.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_forwarders \
  domain='example.com'
```

<a id="email-list-forwarders-backups"></a>
### `Email::list_forwarders_backups` — Return domains with domain-level forwarders

`GET /execute/Email/list_forwarders_backups` · RO · since cPanel 11.42

This function lists the domains with domain-level forwarders. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `domain` (string <domain>) — domain that uses a domain-level filter.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_forwarders_backups
```

## Mailing Lists

<a id="email-add-list"></a>
### `Email::add_list` — Create mailing list

`GET /execute/Email/add_list` · RW · rollback: none · since cPanel 11.42

This function creates a Mailman mailing list. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain.
- `list` · **required** · string · e.g. `newlist` — The mailing list name.
- `password` · **required** · string · e.g. `12345luggage` — The mailing list password.
- `private` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether the mailing list is private.; `1` — Private.; `0` — Public.
- `rebuildonly` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to rebuild the mailing list.; `1` — Rebuild the mailing list.; `0` — Do **not** rebuild the mailing list.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_list \
  list='newlist' \
  password='12345luggage' \
  domain='example.com'
```

<a id="email-add-mailman-delegates"></a>
### `Email::add_mailman_delegates` — Add administrators to mailing list

`GET /execute/Email/add_mailman_delegates` · RW · rollback: none · since cPanel 11.42

This function grants mailing list administrative privileges to users. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `delegates` · **required** · string — A list of the administrators to add. Note: Separate multiple email addresses with commas.
- `list` · **required** · string · e.g. `mylist` — The mailing list.

**Returns** `data`: object

- `delegates` (array of string) — An array of the mailing list's administrators.
- `metadata` (object) — 
  - `transformed` (any) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_mailman_delegates \
  list='mylist' \
  delegates='user@example.com'
```

<a id="email-count-lists"></a>
### `Email::count_lists` — Return cPanel account's mailing list total

`GET /execute/Email/count_lists` · RO · since cPanel 82

This function returns the number of [mailing lists](https://go.cpanel.net/MailingLists) for every email address on a cPanel account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: integer — The number of mailing lists.; `0`; A positive integer.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  count_lists
```

<a id="email-delete-list"></a>
### `Email::delete_list` — Delete mailing list

`GET /execute/Email/delete_list` · RW · rollback: none · since cPanel 11.42

This function deletes a Mailman mailing list. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `list` · **required** · string · e.g. `mylist` — The mailing list.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_list \
  list='mylist'
```

<a id="email-export-lists"></a>
### `Email::export_lists` — Export cPanel account's Mailman mailing lists to a file

`GET /execute/Email/export_lists` · RW · rollback: none · since cPanel 11.114

This function exports a cPanel account's Mailman mailing lists into a CSV file. This file is located in mail/exported_lists under the user's home directory.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  export_lists
```

<a id="email-generate-mailman-otp"></a>
### `Email::generate_mailman_otp` — Create one-time password for a mailing list

`GET /execute/Email/generate_mailman_otp` · RW · rollback: none · since cPanel 11.42

This function generates a one-time password (OTP) for a mailing list. Note: The generated password expires after one use. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `list` · **required** · string · e.g. `mylist` — The mailing list.

**Returns** `data`: string — The new one-time password.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  generate_mailman_otp \
  list='mylist'
```

<a id="email-get-lists-total-disk-usage"></a>
### `Email::get_lists_total_disk_usage` — Return cPanel account's mailing list disk usage

`GET /execute/Email/get_lists_total_disk_usage` · RO · since cPanel 82

This function returns the total disk usage for the [mailing lists](https://go.cpanel.net/cpaneldocsMailingLists) of a cPanel account. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: integer — The total disk usage for the [mailing lists](https://go.cpanel.net/MailingLists) of a cPanel account, in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_lists_total_disk_usage
```

<a id="email-get-mailman-delegates"></a>
### `Email::get_mailman_delegates` — Return mailing list administrators

`GET /execute/Email/get_mailman_delegates` · RO · since cPanel 11.42

This function lists a mailing list's administrators. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `list` · **required** · string · e.g. `mylist` — The name of a Mailman mailing list on the cPanel account.

**Returns** `data`: object

- `delegates` (array of string <email>) — An array of the mailing list's administrators.
- `metadata` (object) — 
  - `transformed` (any) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_mailman_delegates \
  list='mylist'
```

<a id="email-has-delegated-mailman-lists"></a>
### `Email::has_delegated_mailman_lists` — Return email account's mailing list privileges

`GET /execute/Email/has_delegated_mailman_lists` · RO · since cPanel 11.42

This function checks an account's administrative privileges on mailing lists. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `delegate` · **required** · string <email> · e.g. `user@example.com` — The email address.

**Returns** `data`: integer (`0`, `1`) — Whether the email address has administrative privileges on one or more mailing lists on the cPanel account.; `1` — The email address has administrative privileges.; `0` — The email address does **not** have administrativ

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  has_delegated_mailman_lists \
  delegate='user@example.com'
```

<a id="email-list-lists"></a>
### `Email::list_lists` — Return cPanel account's mailing lists

`GET /execute/Email/list_lists` · RO · since cPanel 11.42

This function lists the account's Mailman mailing lists.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — The domain to query. If you do **not** use this parameter, the function lists mailing lists for all of the cPanel account's domains.
- `regex` · optional · string · e.g. `user` — A [Perl Compatible Regular Expression (PCRE)](https://en.wikipedia.org/wiki/Perl_Compatible_Regular_Expressions) that filters the results.

**Returns** `data`: array of object

- *(array of objects)*
  - `accesstype` (string (`private`, `public`)) — The level of access that users have to the mailing list.; `private` - The list has **all** of the following settings: The list has private archives.; The administrator **must** approve subscriptions.; The Mailman directo
  - `advertised` (integer (`0`, `1`)) — Whether the Mailman directory page displays the list.; `1` - The Mailman directory page displays the list.; `0` - The Mailman directory page does not display the list.
  - `archive_private` (integer (`0`, `1`)) — Whether the mailing list archive is `private`.; `1` - The mailing list archive is `private`.; `0` - The mailing list archive is `public`.
  - `desthost` (string <domain> or string <ipv4>) — The IP address or domain name that handles mail for the mailing list's domain.; A valid hostname.; An IPv4 address.
  - `diskused` (integer) — The disk space that the mailing list currently uses, measured in megabytes (MB).
  - `humandiskused` (string) — The disk space that the mailing list uses, in human-readable format.
  - `list` (string <email>) — The mailing list name and domain.
  - `listadmin` (string) — The mailing list's administrators' email addresses.
  - `listid` (string) — The mailing list's name and domain.
  - `subscribe_policy` (integer (`1`, `2`, `3`)) — The level of control that the mailing list administrator has over new subscribers.; `1` - Anyone can subscribe.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_lists
```

<a id="email-passwd-list"></a>
### `Email::passwd_list` — Update mailing list password

`GET /execute/Email/passwd_list` · RW · rollback: none · since cPanel 11.42

This function changes a mailing list's password. Important: When you disable the [_Receive Mail_](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `list` · **required** · string · e.g. `mylist@example.com` — The full name (including the domain) of a Mailman mailing list on the cPanel account.
- `password` · **required** · string · e.g. `12345luggage` — The new password.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  passwd_list \
  list='mylist@example.com' \
  password='12345luggage'
```

<a id="email-remove-mailman-delegates"></a>
### `Email::remove_mailman_delegates` — Remove account mailing list admin privileges

`GET /execute/Email/remove_mailman_delegates` · RW · rollback: none · since cPanel 11.42

This function removes an account's mailing list administrative privileges.

**Parameters**

- `delegates` · **required** · string · e.g. `user@example.com,admin@example.com` — list of the administrators to remove.
- `list` · **required** · string · e.g. `mylist` — The mailing list.

**Returns** `data`: object

- `delegates` (array of string) — An array of the mailing list's administrators.
- `metadata` (object) — 
  - `transformed` (any) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  remove_mailman_delegates \
  list='mylist' \
  delegates='user@example.com,admin@example.com'
```

<a id="email-set-list-privacy-options"></a>
### `Email::set_list_privacy_options` — Update mailing list privacy options

`GET /execute/Email/set_list_privacy_options` · RW · rollback: none · since cPanel 11.42

This function modifies a Mailman mailing list's privacy options. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `advertised` · **required** · integer (`0`, `1`) · e.g. `1` — Whether the Mailman directory page displays the list.; `1` - Display.; `0` - Does **not** display.
- `archive_private` · **required** · integer (`0`, `1`) · e.g. `1` — Whether the mailing list archive is private.; `1` - Private.; `0` - Public.
- `list` · **required** · string · e.g. `mylist` — The mailing list name.
- `subscribe_policy` · **required** · integer (`1`, `2`, `3`) · e.g. `1` — The level of control that the mailing list administrator has over new subscribers.; `1` - Anyone can subscribe. The system sends a confirmation email.; `2` - The administrator **must** approve subscriptions. The system does **not** send a confirmation email.; `3` - The administrator **must** approve subscriptions. The system sends a confirmation email.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  set_list_privacy_options \
  list='mylist' \
  advertised='1' \
  archive_private='1' \
  subscribe_policy='1'
```

## Spam Management

<a id="email-add-spam-filter"></a>
### `Email::add_spam_filter` — Update minimum spam score threshold value

`GET /execute/Email/add_spam_filter` · RW · rollback: none · since cPanel 11.42

This function sets a new minimum Apache SpamAssassin™ spam score threshold value. Notes:  To disable spam filtering, use the UAPI `Email::disable_spam_autodelete` fuction.; For more information, read our [Spam Filters](https://go.cpanel.net/cpaneldocsSpamFilters) documentation. Important:  When you disable the [*Spam Filter* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `account` · optional · string <email> · e.g. `username@example.com` — The email account to apply a spam score threshold value. Note: If you do **not** specify a value, the function applies the new spam score threshold value to **all** accounts.
- `required_score` · optional · string · default `5` · e.g. `8` — Set a spam score threshold value. Notes:  You **must** specify a value greater than `0`, and lower than the domain owner's spam score threshold value.; You **cannot** enter `0` as a value for this parameter.; You can retrieve the domain owner‘s spam score threshold value via the `cpuser_spam_auto_delete_score` return from the UAPI `Email::get_spam_settings` function.; The default value, `5`, is an aggressive spam score.; The lower the spam score, the more likely that Apache SpamAssassin will label messages as spam and delete them.; Some systems may wish to use a more lenient spam score (for example, `8` or `10`).

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_spam_filter
```

<a id="email-disable-spam-assassin"></a>
### `Email::disable_spam_assassin` — Disable Apache SpamAssassin for cPanel account

`GET /execute/Email/disable_spam_assassin` · RW · rollback: none · since cPanel 11.42

This function disables Apache SpamAssassin™ for a cPanel account. Important: When you disable the [*Spam Filter* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  disable_spam_assassin
```

<a id="email-disable-spam-autodelete"></a>
### `Email::disable_spam_autodelete` — Disable spam box filtering auto-delete

`GET /execute/Email/disable_spam_autodelete` · RW · rollback: none · since cPanel 11.42

This function disables the Apache SpamAssassin™ auto-delete spam feature. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `spam_auto_delete` (integer (`0`)) — Whether the auto-delete spam feature is disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  disable_spam_autodelete
```

<a id="email-disable-spam-box"></a>
### `Email::disable_spam_box` — Disable spam box filtering for cPanel account

`GET /execute/Email/disable_spam_box` · RW · rollback: none · since cPanel 70

This function disables spam box filtering for a cPanel account. When you disable spam box filtering, the system sends all messages to the account's inbox. Notes:  This function **requires** that your hosting provider enables Apache SpamAssassin™ on the server.; To **enable** spam box filtering, use the UAPI `Email::enable_spam_box` function.; For more information, read our [Spam Filters](https://go.cpanel.net/cpaneldocsSpamFilters) documentation. Important: When you disable the [*Spam Filter* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  disable_spam_box
```

<a id="email-enable-spam-assassin"></a>
### `Email::enable_spam_assassin` — Enable Apache SpamAssassin for cPanel account

`GET /execute/Email/enable_spam_assassin` · RW · rollback: none · since cPanel 11.42

This function enables Apache SpamAssassin™ for the account. Important: When you disable the [Spam Filter role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  enable_spam_assassin
```

<a id="email-enable-spam-box"></a>
### `Email::enable_spam_box` — Enable spam box filtering for cPanel account

`GET /execute/Email/enable_spam_box` · RW · rollback: none · since cPanel 70

This function enables spam box filtering for a cPanel account. When you enable spam box filtering, the system sends messages marked as spam to a spam folder. Notes:  This function **requires** that your hosting provider enables Apache SpamAssassin on the server.; To **disable** spam box filtering, use the UAPI `Email::disable_spam_box` function.; For more information, read our [Spam Filters](https://go.cpanel.net/cpaneldocsSpamFilters) documentation. Important: When you disable the [Spam Filter](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  enable_spam_box
```

<a id="email-get-spam-settings"></a>
### `Email::get_spam_settings` — Return email account Apache SpamAssassin settings

`GET /execute/Email/get_spam_settings` · RO · since cPanel 11.42

This function retrieves the Apache SpamAssassin™ settings for the account. Important: When you disable the [SpamFilter role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · optional · string <email> · e.g. `username@example.com` — Retrieve a specific user account's SpamAssassin settings. Note: If you do **not** specify this parameter, the function returns the settings for [the default email account](https://go.cpanel.net/DefaultAddress).

**Returns** `data`: object

- `cpuser_spam_auto_delete` (integer (`0`, `1`)) — The cPanel user's account-wide spam filter setting; `1` - Enabled.; `0` - Not enabled.
- `cpuser_spam_auto_delete_score` (integer) — The cPanel user's account-wide spam filter threshold score.
- `rewrites_subjects` (integer (`0`, `1`)) — Whether the user's spam filter rewrites the subject lines of spam messages.; `1` -  Rewrite.; `0` -  No rewrites.
- `spam_as_acl` (integer (`1`)) — Whether the user's spam filter uses Apache SpamAssassin as an ACL.
- `spam_auto_delete` (integer (`0`, `1`)) — Whether the user's autodelete function is enabled.; `1` -  Enabled.; `0` -  Not enabled.
- `spam_auto_delete_score` (integer) — Displays the user's spam filter threshold.
- `spam_box_enabled` (integer (`0`, `1`)) — Whether the user's spam box is enabled.; `1` -  Enabled.; `0` -  Not enabled.
- `spam_enabled` (integer (`0`, `1`)) — Whether the server's global spam filtering is enabled.; `1` -  Enabled.; `0` -  Not enabled.
- `spam_status_changeable` (integer (`0`, `1`)) — Whether the server allows cPanel users to configure Apache SpamAssassin settings.; `1` -  Allowed.; `0` -  Not allowed.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_spam_settings
```

<a id="spamassassin-clear-spam-box"></a>
### `SpamAssassin::clear_spam_box` — Delete spam box contents

`GET /execute/SpamAssassin/clear_spam_box` · RW · rollback: none · since cPanel 70

This function clears the spam box of all its contents for all email accounts. Important: This function deletes the Spam Box folder contents for every email address on the account, which includes the system user email account.

```bash
uapi --output=jsonpretty \
  --user=username \
  SpamAssassin \
  clear_spam_box
```

<a id="spamassassin-get-symbolic-test-names"></a>
### `SpamAssassin::get_symbolic_test_names` — Return SpamAssassin™ symbolic test scores

`GET /execute/SpamAssassin/get_symbolic_test_names` · RO · since cPanel 70

This function lists the Apache SpamAssassin™ scores for each symbolic test.

**Returns** `data`: array of object

- *(array of objects)*
  - `key` (string) — The name of the test.
  - `rule_type` (string (`body_tests`, `full_evals`, `head_evals`, `head_tests`, `meta_tests`, `other_tests`, `rawbody_tests`, `uri_tests`)) — The type and section of the email that the SpamAssassin analyses.; `body_tests`; `full_evals`; `head_evals`; `head_tests`; `meta_tests`; `other_tests`; `rawbody_tests`; `uri_tests`
  - `score` (integer or number) — The score to assign to the email if the result of the test is true.

```bash
uapi --output=jsonpretty \
  --user=username \
  SpamAssassin \
  get_symbolic_test_names
```

<a id="spamassassin-get-user-preferences"></a>
### `SpamAssassin::get_user_preferences` — Return SpamAssassin™ settings

`GET /execute/SpamAssassin/get_user_preferences` · RO · since cPanel 70

This function lists the Apache SpamAssassin™ settings for the account. Note: Additional customizations may appear in the returns. Form more information read the [Apache SpamAssassin™ configuration file](https://spamassassin.apache.org/full/3.1.x/doc/Mail_SpamAssassin_Conf.html#user_preferences) documentation.

**Returns** `data`: object

- `blacklist_from` (array of string <email>) — The email addresses on the blacklist.
- `required_score` (array of number <float>) — The score to mark a message as spam.
- `score` (array of string) — The symbolic test name and score.
- `whitelist_from` (array of string <email>) — The email addresses on the whitelist.

```bash
uapi --output=jsonpretty \
  --user=username \
  SpamAssassin \
  get_user_preferences
```

<a id="spamassassin-update-user-preference"></a>
### `SpamAssassin::update_user_preference` — Update SpamAssassin™ settings

`GET /execute/SpamAssassin/update_user_preference` · RW · rollback: none · since cPanel 70

This function sets the Apache SpamAssassin™ settings for the account. Note: Additional customizations may appear in the function's return. For more information, read the [Apache SpamAssassin configuration file documentation](https://spamassassin.apache.org/full/3.1.x/doc/Mail_SpamAssassin_Conf.html#user_preferences).

**Parameters**

- `preference` · **required** · string — The variable that you want to manipulate.; `score`; `required_score`; `whitelist_from`; `blacklist_from`; A [custom SpamAssassin variable](https://spamassassin.apache.org/full/3.1.x/doc/Mail_SpamAssassin_Conf.html#user_preferences). Important:  You can **only** choose one of these possible values per call.; If you enter a value for the `preference` parameter, but you do **not** define a value for the `value` parameter, the function will remove any previous settings.
- `value` · optional · string · e.g. `ACT_NOW_CAPS 5.0` — The value for the preference of the variable that you want to manipulate.; A valid SpamAssassin "`TEST_NAME SCORE`" value when the value of the `preference` parameter is `score`, where: `TEST_NAME` represents the symbolic name of the test. For list of symbolic test names, run the UAPI `SpamAssassin::get_symbolic_test_names` function.; `SCORE` represents the floating-point value that SpamAssassin assigns to the mail when the test result is true. The score value must be greater than `0`, and less than `1000`.; A valid floating-point number if the value of the `preference` parameter is `required_score`.; A valid email address if the value of the `preference` parameter is `whitelist_from` or `blacklist_from`.; A [custom SpamAssassin variable](https://spamassassin.apache.org/full/3.1.x/doc/Mail_SpamAssassin_Conf.html#user_preferences) value. Note: To enter multiple values, increment the parameter name. For example, use the `value-0` and `value-1` parameters.

**Returns** `data`: object

- `additionalProperties` (any) — An array containing custom SpamAssassin variable values.
- `blacklist_from` (array of string <email>) — An array of email addresses on the blacklist.
- `required_score` (array of number <float>) — An array containing the score at which the system will mark a message as spam.
- `score` (array of string) — An array of the symbolic test names and their scores.
- `whitelist_from` (array of string <email>) — An array of the email addresses on the whitelist.

```bash
uapi --output=jsonpretty \
  --user=username \
  SpamAssassin \
  update_user_preference \
  preference='score'
```

## Email Server Information

<a id="email-check-fastmail"></a>
### `Email::check_fastmail` — Return BlackBerry FastMail support status

`GET /execute/Email/check_fastmail` · RO · since cPanel 11.42

This function checks whether [BlackBerry® FastMail](https://go.cpanel.net/blackberryfastmail) support is enabled. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: string — The contents of the server's `/var/cpanel/fastmail` file.; A positive value that represents a BlackBerry FastMail version number if it is enabled on the server.; A `null` value if BlackBerry FastMail is not enabled on th

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  check_fastmail
```

<a id="email-disable-mailbox-autocreate"></a>
### `Email::disable_mailbox_autocreate` — Disable cPanel account mailbox autocreation

`GET /execute/Email/disable_mailbox_autocreate` · RW · rollback: none · since cPanel 78

This function disables the system's ability to automatically create mailboxes for a cPanel account. Note: When you **enable** the UAPI's `Email::enable_mailbox_autocreate` function, the system automatically creates mailboxes. The system creates a new mailbox when it receives an email address in [plus address format](https://en.wikipedia.org/wiki/Email_address#Sub-addressing) and that mailbox does **not** exist. For example, receiving an email from the `user+newmailbox@example.com` address creates the `newmailbox` mailbox if the `newmailbox` mailbox does not exist.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account address for which to disable mailbox autocreation.

**Returns** `data`: integer (`0`, `1`) — Whether the function disabled mailbox autocreation for the cPanel account.; `1` - Mailbox autocreation disabled.; `0` - Mailbox autocreation is **not** disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  disable_mailbox_autocreate \
  email='username@example.com'
```

<a id="email-enable-mailbox-autocreate"></a>
### `Email::enable_mailbox_autocreate` — Enable cPanel account mailbox autocreation

`GET /execute/Email/enable_mailbox_autocreate` · RW · rollback: none · since cPanel 78

This function allows the system to automatically create mailboxes for a cPanel account. The system will create a new mailbox when it receives an email address in plus address format and that mailbox does not exist. For example, receiving an email from the user+newmailbox@example.com address creates the newmailbox mailbox if the newmailbox mailbox does not exist. Note: To disable this functionality, use the UAPI Email::disable_mailbox_autocreate function.

**Parameters**

- `email` · **required** · string · e.g. `username@example.com` — The email account for which to enable mailbox autocreation.

**Returns** `data`: integer (`0`, `1`) — Whether the function enabled mailbox autocreation for the cPanel account.; 1  Mailbox autocreation enabled.; 0  Mailbox autocreation is not enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  enable_mailbox_autocreate \
  email='username@example.com'
```

<a id="email-fetch-charmaps"></a>
### `Email::fetch_charmaps` — Return server's supported character encodings

`GET /execute/Email/fetch_charmaps` · RO · since cPanel 11.42

This function lists the available character encodings. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `map` (string) — A [character encoding](https://en.wikipedia.org/wiki/Character_encoding) that cPanel supports.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  fetch_charmaps
```

<a id="email-fts-rescan-mailbox"></a>
### `Email::fts_rescan_mailbox` — Start IMAP Full-Text Search scan for email account

`GET /execute/Email/fts_rescan_mailbox` · RW · rollback: none · since cPanel 70

This function requests that the IMAP Full-Text Search Indexing (powered by Apache Solr™) plugin rescan an email account. Note: To enable this function, you **must** install the *IMAP Full-Text Search Indexing (powered by Apache Solr™)* plugin in WHM's [*Manage Plugins*](https://go.cpanel.net/whmdocsManagePlugins) interface (*WHM >> Home >> cPanel >> Manage Plugins*). For more information, read our [install_dovecot_fts script](https://go.cpanel.net/installdovecotftsscript) documentation. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `account` · **required** · string <email> · e.g. `username@example.com` — The email user's account name. Note: If you do not enter an email address, the function rescans the default email account.

**Returns** `data`: integer (`0`, `1`) — Whether the system started the rescan.; `1` - Success.; `0` - Failure.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  fts_rescan_mailbox \
  account='username@example.com'
```

<a id="email-get-charsets"></a>
### `Email::get_charsets` — Return mail server's supported character encodings

`GET /execute/Email/get_charsets` · RO · since cPanel 11.42

This function lists character encodings that the mail server supports. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of string — An array of [character encodings](https://en.wikipedia.org/wiki/Character_encoding) that the mail server supports.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_charsets
```

<a id="email-get-mailbox-autocreate"></a>
### `Email::get_mailbox_autocreate` — Return cPanel account's mailbox autocreate status

`GET /execute/Email/get_mailbox_autocreate` · RO · since cPanel 78

This function checks whether a cPanel account will automatically create mailboxes when it receives an email address in [plus address format](https://en.wikipedia.org/wiki/Email_address#Sub-addressing). Note: To enable or disable this functionality, use the UAPI's `Email::enable_mailbox_autocreate` and `Email::disable_mailbox_autocreate` functions.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account address to query.

**Returns** `data`: integer (`0`, `1`) — Whether the cPanel account can automatically create mailboxes.; `1` — The cPanel account can automatically create mailboxes.; `0` — The cPanel account **cannot** automatically create mailboxes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_mailbox_autocreate \
  email='username@example.com'
```

<a id="email-has-plaintext-authentication"></a>
### `Email::has_plaintext_authentication` — Return whether plaintext authentication is enabled

`GET /execute/Email/has_plaintext_authentication` · RO · since cPanel 56

This function checks whether plaintext authentication is enabled on the Dovecot mail server. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: integer (`0`, `1`) — Whether plaintext authentication is enabled on the Dovecot mail server.; `1` - Enabled.; `0` - Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  has_plaintext_authentication
```

<a id="email-set-always-accept"></a>
### `Email::set_always_accept` — Update Mail Exchanger type

`GET /execute/Email/set_always_accept` · RW · rollback: none · since cPanel 11.42

This function sets the Mail Exchanger (MX) type. Note: This function **only** affects the cPanel configuration. You **must** configure the mail exchanger's DNS entry separately. Important: When you disable the [DNS role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The mail exchanger's domain.
- `alwaysaccept` · optional · string (`auto`, `local`, `secondary`, `remote`) · default `auto` · e.g. `auto` — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do **not** accept mail. Note: This parameter is redundant with the `mxcheck` parameter. Do **not** enter the `mxcheck` and `alwaysaccept` parameters at the same time. [Undefined behavior](https://en.wikipedia.org/wiki/Undefined_behavior) may occur if this happens.
- `mxcheck` · optional · string (`auto`, `local`, `secondary`, `remote`) · default `auto` · e.g. `auto` — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do **not** accept mail. Note: This parameter is redundant with the `alwaysaccept` parameter. Do **not** enter the `mxcheck` and `alwaysaccept` parameters at the same time. [Undefined behavior](https://en.wikipedia.org/wiki/Undefined_behavior) may occur if this happens.

**Returns** `data`: object

- `checkmx` (object) — An object containing the mail exchanger's data.
  - `changed` (integer (`0`, `1`)) — Whether a change occurred during the function.; `1` — Change occurred.; `0` — **No** change.
  - `detected` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do *
  - `isprimary` (integer (`0`, `1`)) — Whether the mail exchanger is the primary mail exchanger.; `1` —  Primary.; `0` — **Not** primary.
  - `issecondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` — Secondary.; `0` — **Not** secondary.
  - `local` (integer (`0`, `1`)) — Whether the mail exchanger is a local exchanger.; `1` — Local.; `0` — **Not** local.
  - `mxcheck` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do *
  - `remote` (integer (`0`, `1`)) — Whether the mail exchanger is a remote exchanger.; `1` — Remote.; `0` — **Not** remote.
  - `secondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` — Secondary.; `0` — **Not** secondary.
  - `warnings` (array of string) — An array of warning messages, if any exist.
- `detected` (string) — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do *
- `local` (integer (`0`, `1`)) — Whether the mail exchanger is a local exchanger.; `1` — Local.; `0` — **Not** local.
- `mxcheck` (string) — The mail exchanger type.; `auto` — Allow cPanel to determine the appropriate role.; `local` — Always accept the domain's mail.; `secondary` — Accept mail until a higher priority mail server is available.; `remote` — Do *
- `remote` (integer (`0`, `1`)) — Whether the mail exchanger is a remote exchanger.; `1` — Remote.; `0` — **Not** remote.
- `results` (string) — A message of success or a reason for failure.; A message of success that includes the new type.; A string that describes an error.
- `secondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` — Secondary.; `0` — **Not** secondary.
- `status` (integer (`0`, `1`)) — Whether the function succeeded.; `1` — Success.; `0` — Failure.
- `statusmsg` (string) — A message of success or a reason for failure.; A message of success that includes the new type.; A string that describes an error.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  set_always_accept \
  domain='example.com'
```

<a id="email-stats-db-status"></a>
### `Email::stats_db_status` — Return eximstats SQLite database status

`GET /execute/Email/stats_db_status` · RO · since cPanel 64

This function returns the status of the eximstats SQLite Database. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: string (`active`, `importing`, `upcp`) — The disk space that the email account uses.; `active` - The database is available and up-to-date.; `importing` - The database is available, but a data import is currently in progress.; `upcp` - The database is unavailabl

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  stats_db_status
```

## Email Filtering

<a id="email-count-filters"></a>
### `Email::count_filters` — Return cPanel account's email filters total

`GET /execute/Email/count_filters` · RO · since cPanel 82

This function returns the number of [email filters](https://go.cpanel.net/cpaneldocsEmailFilters) for every email address on a cPanel account. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles) or the [*IP Blocker*](https://go.cpanel.net/whmdocsFeatureManager) feature, the system **disables** this function. For more information, read our [How to Use Server Profiles](https://go.cpanel.net/howtouseserverprofiles) documentation.

**Returns** `data`: integer — The number of email filters.; `0`; A positive integer.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  count_filters
```

<a id="email-delete-filter"></a>
### `Email::delete_filter` — Delete email account's email filter

`GET /execute/Email/delete_filter` · RW · rollback: none · since cPanel 11.42

This function deletes an email filter. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · **required** · string <email> · e.g. `user@example.com` — The email address that owns the filter.
- `filtername` · **required** · string · e.g. `coffee` — The filter's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_filter \
  account='user@example.com' \
  filtername='coffee'
```

<a id="email-disable-filter"></a>
### `Email::disable_filter` — Disable email filter for email account

`GET /execute/Email/disable_filter` · RW · rollback: none · since cPanel 11.42

This function disables an email filter. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · **required** · string <email> · e.g. `user@example.com` — The email address that owns the filter.
- `filtername` · **required** · string · e.g. `coffee` — The filter's name.

**Returns** `data`: object

- `filtername` (string) — The filter's name.
- `updated` (integer (`0`, `1`)) — Whether the function updated the filter.; `1` - Updated,; `0` - Did **not** update.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  disable_filter \
  account='user@example.com' \
  filtername='coffee'
```

<a id="email-enable-filter"></a>
### `Email::enable_filter` — Enable email filter for email account

`GET /execute/Email/enable_filter` · RW · rollback: none · since cPanel 11.42

This function enables an email filter. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · **required** · string <email> · e.g. `username@example.com` — The email address that owns the filter.
- `filtername` · **required** · string · e.g. `coffee` — The filter's name.

**Returns** `data`: object

- `filtername` (string) — The filter's name.
- `updated` (integer (`0`, `1`)) — Whether the function updated the filter.; `1` - Updated.; `0` - Did **not** update.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  enable_filter \
  account='username@example.com' \
  filtername='coffee'
```

<a id="email-get-filter"></a>
### `Email::get_filter` — Return email filter's information

`GET /execute/Email/get_filter` · RO · since cPanel 11.42

This function retrieves an email filter's information. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `account` · **required** · string <email> · e.g. `user@example.com` — The email address that owns the filter.
- `filtername` · **required** · string · e.g. `coffee` — The filter's name.

**Returns** `data`: object

- `actions` (array of object) — An array of objects that contains the filter's actions.
  - *(array of objects)*
    - `action` (string (`deliver`, `fail`, `finish`, `save`, `pipe`)) — The filter's action.; `deliver` -  The filter sends mail to the destination address.; `fail` -  The filter forces a delivery failure.; `finish` -  The filter stops message processing.; `save` -  The filter saves mail to 
    - `dest` (string <email> or string <path>) — The destination to which the filter sends mail.
    - `number` (integer) — The filter's position in the order of the account's filters.
- `filtername` (string) — The filter's name.
- `metadata` (object) — 
  - `transformed` (integer (`1`)) — Post-processing may have transformed the data.
- `rules` (array of object) — An array of objects that contains the filter's rules.
  - *(array of objects)*
    - `match` (string (`is`, `matches`, `contains`, `does not contain`, `begins`, `does not begin`, `ends`, `does not end`, `does not match`, `is above`, `is not above`, `is below`, …)) — The filter's match type.; `is`; `matches`; `contains`; `does not contain`; `begins`; `does not begin`; `ends`; `does not end`; `does not match`; `is above`; `is not above`; `is below`; `is not below`
    - `number` (integer) — The filter's position in the order of the account's filters.
    - `opt` (string (`and`, `or`, `null`)) — The connection between multiple conditions.; `and` -  Match both conditions.; `or` -  Match either condition.; `null` -  There is only one condition.
    - `part` (string (`$header_from:`, `$header_subject:`, `$header_to:`, `$reply_address:`, `$message_body`, `$message_headers`, `foranyaddress $h_to:,$h_cc:,$h_bcc:`, `not delivered`, `error_message`)) — The queried email section.; `$header_from:` -  Matches against the From: section.; `$header_subject:` -  Matches against the Subject: section.; `$header_to:` -  Matches against the To: section.; `$reply_address:` -  Matc
    - `val` (string) — The matched value.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  get_filter \
  account='user@example.com' \
  filtername='coffee'
```

<a id="email-list-filters"></a>
### `Email::list_filters` — Return account-level email filters

`GET /execute/Email/list_filters` · RO · since cPanel 11.42

This function lists account-level mail filters. For more information about Exim filters, read [Exim’s documentation](http://www.exim.org/exim-html-3.30/doc/html/filter.html). **Important**: When you disable the [Mail Receive role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `account` · optional · string <email> or string <username> — The email address or cPanel account username for which to return a list of filters. If you do not specify this value, the function lists all of the cPanel account’s account-level filters.

**Returns** `data`: array of object

- *(array of objects)*
  - `actions` (array of object) — An array of objects that descibe each of the filter’s actions.
    - *(array of objects)*
      - `action` (string) — The filter’s action.
      - `dest` (string) — The destination to which the filter sends mail.; A file path.; An application path.; A valid email address.
  - `enabled` (integer) — Whether the filter is enabled.
  - `filtername` (string) — The filter’s name.
  - `rules` (array of object) — An array of objects that descibe each of the filter’s rules.
    - *(array of objects)*
      - `match` (string (`is`, `matches`, `contains`, `does not contain`, `begins`, `does not begin`, `ends`, `does not end`, `does not match`, `is above`, `is not above`, `is below`, …)) — The filter’s match type.
      - `opt` (string (`and`, `or`, `null`)) — The connection between multiple conditions.; `and` — Match both conditions.; `or` — Match either condition.; `null` — Only one condition exists.
      - `part` (string) — The queried email section.
      - `val` (string) — The matched value.
  - `unescaped` (boolean) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_filters
```

<a id="email-list-filters-backups"></a>
### `Email::list_filters_backups` — Return domains with domain-level email filters

`GET /execute/Email/list_filters_backups` · RO · since cPanel 11.42

This function lists all of the cPanel account's domains that use domain-level filters. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object — An array of objects that contains information about domains with domain-level filters.

- *(array of objects)*
  - `domain` (string <domain>) — A domain with a domain-level filter.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_filters_backups
```

<a id="email-list-system-filter-info"></a>
### `Email::list_system_filter_info` — Return system-level email filter file information

`GET /execute/Email/list_system_filter_info` · RO · since cPanel 11.42

This function retrieves a `.yaml.gz` file that contains system-level filter information. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `filter_info` (string) — The file that contains the account's system-level filter information.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_system_filter_info
```

<a id="email-reorder-filters"></a>
### `Email::reorder_filters` — Update email address's email filter order

`GET /execute/Email/reorder_filters` · RW · rollback: none · since cPanel 11.42

This function modifies the filter order for an email address. For more information about Exim filters, read [Exim's documentation](http://www.exim.org/exim-html-3.30/doc/html/filter.html). Important: When you disable the [_Receive Mail_ role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `filter*` · **required** · string · e.g. `coffee` — A mail filter name. For each mail filter to reorder, supply a `filter*` parameter, where `*` is a number that represents the filter's order. For example, to set `coffee` as the first email filter and `cheesecloth` as the second, set `coffee` as the `filter1` parameter's value, and `cheesecloth` as the value for the `filter2` parameter.
- `mailbox` · **required** · string · e.g. `user@example.com` — The email address.

**Returns** `data`: object (`None`)

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  reorder_filters \
  mailbox='user@example.com' \
  filter*='coffee'
```

<a id="email-store-filter"></a>
### `Email::store_filter` — Create email filter

`GET /execute/Email/store_filter` · RW · rollback: none · since cPanel 11.42

This function creates a new email filter. For more information about Exim filters, read [Exim's documentation](http://www.exim.org/exim-html-3.30/doc/html/filter.html). Important: When you disable the [*Receive Mail* role](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/#roles), the system **disables** this function. ### Create multiple rules You may create up to 4,096 separate sets of conditions in one filter. To do this, append numbers to the parameter names. To create a filter with two sets of actions and conditions, use the following parameters: Assign the information for the first filter rule to the `action1`, `dest1`, `match1`, `opt1`, `part1`, and `val1` parameters.; Assign the information for the second filter rule to the `action2`, `dest2`, `match2`, `opt2`, `part2`, and `val2` parameters. To create a filter that uses one set of actions but two sets of conditions, use the following parameters: Assign the actions to the `action1` and `dest1` parameters.; Assign the first set of conditions to the `match1`, `opt1`, `part1`, and `val1` parameters.; Assign the second set of conditions to the `match2`, `opt2`, `part2`, and `val2` parameters.

**Parameters**

- `action*` · **required** · string (`deliver`, `fail`, `finish`, `save`, `pipe`) — The filter's action.; `deliver` - Deliver the message to the `dest*` address.; `fail` - Force a delivery failure.; `finish` - Stop processing the message.; `save` - Save the message to the `dest*` file.; `pipe` - Pipe the message to the `dest*` application. Important:  You **must** increment each action. For example, pass the first action as `action1` and the second action as `action2`.; This value **requires** the `FileStorage` role. For more information, read our [How to Use Server Profiles](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles) documentation.
- `filtername` · **required** · string · e.g. `coffee` — The filter name.
- `match*` · **required** · string (`is`, `matches`, `contains`, `does not contain`, `begins`, `does not begin`, `ends`, `does not end`, `does not match`, `is above`, `is not above`, `is below`, …) — The filter's [match type](http://www.exim.org/exim-html-current/doc/html/spec_html/filter_ch-exim_filter_files.html).; If the `val*` parameter is a string, use a string operator.; If the `val*` parameter is an integer, use a numeric operator. String operators: `is`; `matches`; `contains`; `does not contain`; `begins`; `does not begin`; `ends`; `does not end`; `does not match` Numeric operators: `is above`; `is not above`; `is below`; `is not below` Important: You **must** increment each match type. For example, pass the first match type as `match1` and the second match type as `match2`.
- `part*` · **required** · string (`$h_x-Spam-Bar`, `$h_x-Spam-Score`, `$h_X-Spam-Status`, `$h_List-id`, `$header_from`, `$header_subject`, `$header_to`, `$reply_address`, `$message_body`, `$message_headers`, `$h_to, $h_cc`, `not delivered`, …) — The email section to query.; `$h_x-Spam-Bar:` - Match against the message's spam score value, measured in plus(`+`) characters.; `$h_x-Spam-Score:` - Match against the message's spam score value.; `$h_X-Spam-Status:` - Match against whether the system detected the message as spam.; `$h_List-Id:` - Match against the message's `List-ID` header value.; `$header_from:` - Match against the `From:` section.; `$header_subject:` - Match against the `Subject:` section.; `$header_to:` - Match against the `To:` section.; `$reply_address:` - Match against the `Reply To:` section.; `$message_body:` - Match against the message's body.; `$message_headers:` - Match against the message's headers.; `foranyaddress $h_to:, $h_cc:` - Match against all message recipients.; `not delivered` - Match if the message is not queued for delivery.; `error_message` - Match if the incoming message is bounced. Important: You **must** increment each section. For example, pass the first section as `part1` and the second section as `part2`. Note: Generally, the recipient does **not** receive the `BCC` field in an email's header. For this reason you **cannot** use the `BCC` field in a filter.
- `val*` · **required** · integer or string — The value to match. Important: You **must** increment each value. For example, pass the first value as `val1` and the second value as `val2`.
- `account` · optional · string <email> · e.g. `user@example.com` — The email address, for user-level filters. If you do not use this parameter, the function creates an account-level filter.
- `dest*` · optional · string <email> or string <path> · default `` — The destination for filtered mail. Important:  This parameter is **required** if the action value is `deliver`, `save`, or `pipe`.; You **must** increment each destination. For example, pass the first destination as `dest1` and the second destination as `dest2`.
- `oldfiltername` · optional · string · e.g. `pool` — The name of an existing filter, to rename it. If you do not use this parameter, the function creates a new filter.
- `opt*` · optional · string (`and`, `or`) · default `and` — The connection between multiple conditions. Important: You **must** increment each connection. For example, pass the first connection as `opt1` and the second connection as `opt2`.

**Returns** `data`: object

- `account` (string <email>) — The filter's email address.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  store_filter \
  filtername='coffee' \
  action*='deliver' \
  match*='contains' \
  part*='$header_from' \
  val*='coconut'
```

<a id="email-trace-filter"></a>
### `Email::trace_filter` — Run test for main domain email filters

`GET /execute/Email/trace_filter` · RO · since cPanel 11.42

This function tests mail filters. The function **only** tests filters for the cPanel account's main domain, and only tests against the message's body. For more information about Exim filters, read [Exim's documentation](http://www.exim.org/exim-html-3.30/doc/html/filter.html). Note: If the domain or account does not contain a filter file, this function will fail. Important: When you disable the [Receive Mail](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `msg` · **required** · string · e.g. `Test` — The string to test. The function uses this string as the body of an email message, to check whether filters would match the string.
- `account` · optional · string <email> · e.g. `user@example.com` — The email address, to test legacy cPanel filters in the filters directory. If you do not use this parameter, the function tests the main domain's filters in the `/etc/vfilters` directory.

**Returns** `data`: object

- `trace` (string) — A series of messages that describe the trace results.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  trace_filter \
  msg='Test'
```

## Email Suspensions

<a id="email-suspend-incoming"></a>
### `Email::suspend_incoming` — Suspend email account incoming (SMTP) mail

`GET /execute/Email/suspend_incoming` · RW · rollback: none · since cPanel 54

This function suspends incoming email for an account. The system will reject incoming email while the account is suspended. Notes:  The user can still log in to the email account. To suspend a user's ability to log in to, send mail from, and read their account, use the UAPI `Email::suspend_login` function.; Use the UAPI `Email::unsuspend_incoming` function to allow the account to receive email. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · optional · string <email> · e.g. `user@example.com` — The email user's account name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  suspend_incoming
```

<a id="email-suspend-login"></a>
### `Email::suspend_login` — Suspend email account login

`GET /execute/Email/suspend_login` · RW · rollback: none · since cPanel 54

This function suspends a user's ability to log in to their email account. This function immediately suspends the user's login credentials and prevents future authenticated connections to the email account. Notes:  When you suspend an account, the user's account still receives email.; To suspend incoming email for an account, use the UAPI `Email::suspend_incoming` function.; To remove the login suspension for an account, use the UAPI `Email::unsuspend_login` function. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The email user's account name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  suspend_login \
  email='user@example.com'
```

<a id="email-suspend-outgoing"></a>
### `Email::suspend_outgoing` — Suspend email account outgoing mail

`GET /execute/Email/suspend_outgoing` · RW · rollback: none · since cPanel 70

This function rejects outgoing mail for a suspended email account. This function does **not** disable a user's login credentials or access permissions to their email account. Notes:  To suspend a user's login credentials and prevent authenticated connections to the email account, use the UAPI `Email::suspend_login` function.; To allow an email account to send mail, use the UAPI `Email::unsuspend_outgoing` function.; To hold outgoing mail in Exim's queue, use the UAPI `Email::hold_outgoing` function. Important: When you disable the [Send Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · **required** · string <email> · e.g. `username@example.com` — The email account's username.

**Returns** `data`: integer (`0`, `1`) — Whether the function succeeded.; `1` — The function succeeded.; `0` — The function failed.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  suspend_outgoing \
  email='username@example.com'
```

<a id="email-unsuspend-incoming"></a>
### `Email::unsuspend_incoming` — Unsuspend email account incoming mail

`GET /execute/Email/unsuspend_incoming` · RW · rollback: none · since cPanel 54

This function unsuspends incoming email for an email account. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `email` · optional · string <email> · e.g. `user@example.com` — The email user's account name.

**Returns** `data`: integer (`0`, `1`) — Whether the function succeeded.; `1` — The function succeeded.; `0` — The function failed.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  unsuspend_incoming
```

<a id="email-unsuspend-login"></a>
### `Email::unsuspend_login` — Unsuspend email account login

`GET /execute/Email/unsuspend_login` · RW · rollback: none · since cPanel 54

This function restores a user's ability to log in to their email account. Note:  To suspend a user's ability to log in, use the UAPI `Email::suspend_login` function.; To suspend incoming email for an account, use the UAPI `Email::suspend_incoming` function. Important: When you disable the [Receive Mail role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `email` · optional · string <email> · e.g. `username@example.com` — The email user's account name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  unsuspend_login
```

<a id="email-unsuspend-outgoing"></a>
### `Email::unsuspend_outgoing` — Unsuspend email account outgoing mail

`GET /execute/Email/unsuspend_outgoing` · RW · rollback: none · since cPanel 70

This function cancels the suspension action put in place by the UAPI `Email::suspend_outgoing` function for outgoing mail for an email account. Note: To suspend an email account and reject all outgoing mail, use the UAPI `Email::suspend_outgoing` function.

**Parameters**

- `email` · **required** · string · e.g. `username@example.com` — The email account's username.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  unsuspend_outgoing \
  email='username@example.com'
```

## Signing and Encryption (GnuPG Keys)

<a id="gpg-delete-keypair"></a>
### `GPG::delete_keypair` — Delete GnuPG key pair

`GET /execute/GPG/delete_keypair` · RW · rollback: none · since cPanel 82

This function deletes a GnuPG (GPG) key pair.

**Parameters**

- `key_id` · **required** · string · e.g. `ACFFDB37176B680D` — The ID of the GPG key that you wish to delete. Note:  The function will delete **all** keys that match this ID.; If you set this parameter to a public key, the function will delete the public key. ; If you set this parameter to a public and private key pair, the function will delete the public and private keys.; To obtain the desired key, call the UAPI `GPG::list_secret_keys` function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  delete_keypair \
  key_id='ACFFDB37176B680D'
```

<a id="gpg-export-public-key"></a>
### `GPG::export_public_key` — Export GnuPG public key

`GET /execute/GPG/export_public_key` · RO · since cPanel 82

This function exports a GnuPG (GPG) public key.

**Parameters**

- `key_id` · **required** · string · e.g. `48BEA5A16FCA746E` — The ID of the GPG key.

**Returns** `data`: object

- `key_data` (string) — The GPG public key's contents.

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  export_public_key \
  key_id='48BEA5A16FCA746E'
```

<a id="gpg-export-secret-key"></a>
### `GPG::export_secret_key` — Export GnuPG secret key

`GET /execute/GPG/export_secret_key` · RW · rollback: none · since cPanel 82

This function exports a GnuPG (GPG) secret key.

**Parameters**

- `key_id` · **required** · string · e.g. `48BEA5A16FCA746E` — The ID of the GPG secret key that you wish to retrieve.
- `passphrase` · optional · string · e.g. `whatever` — The passphrase of the GPG secret key that you wish to retrieve.

**Returns** `data`: object

- `key_data` (string) — The GPG key's contents.

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  export_secret_key \
  key_id='48BEA5A16FCA746E'
```

<a id="gpg-generate-key"></a>
### `GPG::generate_key` — Create GnuPG key

`GET /execute/GPG/generate_key` · RW · rollback: none · since cPanel 82

This function generates a GnuPG (GPG) key. The system saves the key in the user's `.gnupg` directory. Note: This function uses [the system's entropy](https://en.wikipedia.org/wiki/Entropy_(computing)) to generate the key. Systems with low entropy levels may cause long generation times or timeouts.

**Parameters**

- `email` · **required** · string <email> · e.g. `user@example.com` — The user's email address.
- `name` · **required** · string <username> · e.g. `username` — The name of the user for whom to generate the key.
- `passphrase` · **required** · string · e.g. `123456luggage` — The key's password.
- `comment` · optional · string · e.g. `Username's Key` — A comment about the key.
- `expire` · optional · string · e.g. `1560363242` — The desired expiration date of the key as a timestamp in [Unix time format](http://en.wikipedia.org/wiki/Unix_time). Note: This will default to one year from the current date.
- `keysize` · optional · integer (`1024`, `2048`, `3072`, `4096`) · default `2048` · e.g. `2048` — The new key's size, in bytes. Note: Large keys require more time to generate.
- `no_expire` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to generate the key without an expiration date.; `0` - The key will expire.; `1` - The key will **not** expire.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  generate_key \
  name='username' \
  email='user@example.com'
  passphrase='123456luggage'
```

<a id="gpg-import-key"></a>
### `GPG::import_key` — Import GnuPG key

`GET /execute/GPG/import_key` · RW · rollback: none · since cPanel 82

This function imports a GnuPG (GPG) key.

**Parameters**

- `key_data` · **required** · string — The key to import. Note: You must URI-encode this value.

**Returns** `data`: object

- `key_id` (string) — The key's ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  import_key \
  key_data='%0A-----BEGIN%20PGP%20PUBLIC%20KEY%20BLOCK-----%0AVersion%3A%20GnuPG%20v2.0.14%20(GNU%2FLinux)%0A%0AmQENBFN0%2BOsBCADoFvyf8gHIKZ%2F%2B5KwbWb3Ht%2Fz1ukyQqFNGpBVIqHossmjmyF9e%0APn6iiZ0fHnt7r6XGGXaP%2BKKjIxAcqOTiFiP%2BHIx6GQubzVih6Ol0YNjzmK%2Ft4f%2B4%0AfSElEVnyzeyJa4LmC%2Fui%2FvvtptJ8JX6su7f11BwUTSyuqnk204AfN5uVpAcZNPT0%0A0qNNky1bxYvPUxU6Imvi1q3NtpFzqsQ4u%2FyZuLpUe7uwmgMPeO0lAms1kCa3Guot%0A3mfSt0vrUAMdcV4drY1FGtYZdYSa4rSTzpFuB7o9Ze%2BE3fUbCWs1%2B0FiN3JQNGO1%0AS2lnqjEqbpz2nHtA50elJRGqxZLEi8zkFqlTABEBAAG0Z2NQYW5lbCBTZWN1cml0%0AeSBUZWFtIC0gVEVTVCAoVEhJUyBJUyBBIFRFU1QgS0VZOyBETyBOT1QgVVNFIEZP%0AUiBBTllUSElORyBSRUFMISkgPHNlY3RlYW1zaXhAY3BhbmVsLm5ldD6JAT4EEwEC%0AACgFAlN0%2BOsCGwMFCQHhM4AGCwkIBwMCBhUIAgkKCwQWAgMBAh4BAheAAAoJEOhU%0A60c9RtoRkhMIAIe2yDKj55mGD3zbuGqxx6NNNIyiuEujw31N8yOS9BKTqGtIiK9i%0AGu4lzrzmHISKi0rjKmJdbckap7OouUoo9WR3ewjN6S5EHyjKfrrMwMzTWMPZOkTj%0A7A698X0vGc9yZ6KyBj8mM8J9duvNtRS285hfXfQxYO%2FuiyrJGBedI%2FWVZ3a7mcfq%0A7FhC8t6jU6sz9uIvYHAzywcVdmhEK5rS%2FuE%2F9e37h46jn2%2BkzlIWEe%2FYgpa%2BuWdT%0AO%2BOyqteW51LEjXLWMyP8AJEq8EoqbqKnm4Q1g0etOQ9trrkLUnPxaSwD5R6i4KLH%0AMR%2Fh7m%2FOoz8yOhUlrCGJwX7v9qDEdaYYFLQ%3D%0A%3DMEFZ%0A-----END%20PGP%20PUBLIC%20KEY%20BLOCK-----%0A'
```

<a id="gpg-list-public-keys"></a>
### `GPG::list_public_keys` — Return current user's GnuPG public keys

`GET /execute/GPG/list_public_keys` · RO · since cPanel 82

This function lists the GnuPG (GPG) public keys for the currently-authenticated account.

**Returns** `data`: array of object

- *(array of objects)*
  - `algorithm` (string (`RSA`, `DSA`)) — The key's algorithm.; RSA; DSA
  - `bits` (integer (`1024`, `2048`, `3072`, `4096`)) — The length of the key, in bits.
  - `created` (string) — The creation time for the key, in [Unix time format](http://en.wikipedia.org/wiki/Unix_time).
  - `expires` (string) — When the key will expire, in [Unix time format](http://en.wikipedia.org/wiki/Unix_time).
  - `id` (string) — The key's ID.
  - `type` (string (`pub`)) — The type of key.
  - `user_id` (string) — The user ID of the key which consists of the following space-separated values: The username.; The key's comment in parentheses.; The key's email address in angle brackets (<>).

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  list_public_keys
```

<a id="gpg-list-secret-keys"></a>
### `GPG::list_secret_keys` — Return current user's GnuPG secret keys

`GET /execute/GPG/list_secret_keys` · RO · since cPanel 82

This function lists the GnuPG (GPG) secret keys for the currently-authenticated account.

**Returns** `data`: array of object

- *(array of objects)*
  - `algorithm` (string (`RSA`, `DSA`)) — The key's algorithm.; `RSA`; `DSA`
  - `bits` (integer) — The key's length.
  - `created` (integer <unix_timestamp>) — When the function created the key.
  - `expires` (integer <unix_timestamp>) — When the key will expire.
  - `id` (string) — The key's ID.
  - `type` (string (`sec`)) — The type of key.; `sec` is the only possible value.
  - `user_id` (string) — The user ID of the key.

```bash
uapi --output=jsonpretty \
  --user=username \
  GPG \
  list_secret_keys
```

## Mailbox Management

<a id="mailboxes-expunge-mailbox-messages"></a>
### `Mailboxes::expunge_mailbox_messages` — Delete selected messages in mailbox

`GET /execute/Mailboxes/expunge_mailbox_messages` · RW · rollback: none · since cPanel 64

This function marks the selected mail messages as deleted.

**Parameters**

- `account` · **required** · string <email> or string <username> — The email account's name.
- `mailbox` · **required** · string · e.g. `INBOX.user@example_com` — The mailbox to operate on. Note:  Use the `Mailboxes::get_mailbox_status_list` function to list possible values for the mailbox parameter.; Because you cannot escape wildcard characters such as (`*`), we recommend that you use functions that use the `mailbox_guid` parameter instead. For example, the `Mailboxes::expunge_messages_for_mailbox_guid` function.
- `query` · **required** · string · e.g. `savedbefore 52w` — The Dovecot query to execute. Note: The query parameter prevents accidental removal of all messages in the mailbox. For more information, read Dovecot's [Search Query](http://wiki2.dovecot.org/Tools/Doveadm/SearchQuery) documentation.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mailboxes \
  expunge_mailbox_messages \
  account='_mainaccount@example.com' \
  mailbox='INBOX.user@example_com' \
  query='savedbefore 52w'
```

<a id="mailboxes-expunge-messages-for-mailbox-guid"></a>
### `Mailboxes::expunge_messages_for_mailbox_guid` — Delete selected messages in mailbox by GUID

`GET /execute/Mailboxes/expunge_messages_for_mailbox_guid` · RW · rollback: none · since cPanel 64

This function marks the selected mailbox's messages as deleted.

**Parameters**

- `account` · **required** · string <email> or string <username> — The email account's name.
- `mailbox_guid` · **required** · string · e.g. `2550860f0c58d158c92a000044f0d230` — The mailbox's globally unique identifier (GUID). Use the `Mailboxes::get_mailbox_status_list` function to list possible values for the `mailbox_guid` parameter.
- `query` · **required** · string · e.g. `savedbefore 52w` — The query to select which messages you wish to remove from the mailbox.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mailboxes \
  expunge_messages_for_mailbox_guid \
  account='_mainaccount@example.com' \
  mailbox_guid='2550860f0c58d158c92a000044f0d230' \
  query='savedbefore 52w'
```

<a id="mailboxes-get-mailbox-status-list"></a>
### `Mailboxes::get_mailbox_status_list` — Return cPanel account's mailbox status

`GET /execute/Mailboxes/get_mailbox_status_list` · RO · since cPanel 64

This function lists the account's mailbox size and globally unique identifier (GUID) by folder.

**Parameters**

- `account` · **required** · string · e.g. `user@example.com` — The email account for which you you wish to request the status.

**Returns** `data`: array of object

- *(array of objects)*
  - `guid` (string) — The mailbox GUID.
  - `mailbox` (string) — The mailbox name.
  - `messages` (integer) — The number of messages in the folder.
  - `vsize` (integer <bytes>) — The size of the folder, in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mailboxes \
  get_mailbox_status_list \
  account='user@example.com'
```

<a id="mailboxes-has-utf8-mailbox-names"></a>
### `Mailboxes::has_utf8_mailbox_names` — Return if cPanel account's mailboxes use UTF-8

`GET /execute/Mailboxes/has_utf8_mailbox_names` · RO · since cPanel 78

This function determines whether a cPanel user currently uses UTF-8 character-encoded mailbox names.

**Parameters**

- `user` · optional · string <username> · e.g. `user` — The user for whom to determine whether they currently use UTF-8 character-encoded mailbox names. Note: This parameter defaults to the currently-logged in user.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether the user currently uses UTF-8 character-encoded mailbox names.; `1` - Uses UTF-8 character-encoded mailbox names.; `0` - Does **not** use UTF-8 character-encoded mailbox names.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mailboxes \
  has_utf8_mailbox_names
```

<a id="mailboxes-set-utf8-mailbox-names"></a>
### `Mailboxes::set_utf8_mailbox_names` — Enable or disable Webmail mailbox UTF-8 encoding

`GET /execute/Mailboxes/set_utf8_mailbox_names` · RW · rollback: none · since cPanel 78

This function enables or disables UTF-8-encoded mailbox names on Roundcube webmail for a cPanel user's email accounts.

**Parameters**

- `enabled` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to enable or disable UTF-8 character-encoded mailbox names.; `1` - Enable UTF-8 encoded mailbox names.; `0` - Disable UTF-8 encoded mailbox names.

**Returns** `data`: object

- `success` (integer (`0`, `1`)) — Whether the system changed mailbox name setting's status.; `1` - Success.; `0` - Failure.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mailboxes \
  set_utf8_mailbox_names \
  enabled='1'
```

## Webmail Sessions

<a id="session-create-temp-user"></a>
### `Session::create_temp_user` — Create user session with existing session

`GET /execute/Session/create_temp_user` · RW · rollback: none · since cPanel 54.0.16 · CLI support: False

This function creates a temporary user session. Important:  Because this function requires a valid cPanel session ID, you **must** call it via a cPanel or Webmail session URL. If you call this function via the command line or Template Toolkit, it will **not** create a temporary user session. You **must** use the WHM API 1 `create_user_session` function to create a temporary user session.; Third-party plugins that require access to temporary MySQL users **must** call this function via the URL. It will create the temporary users before they are available. You can find these users in the `$ENV{'REMOTE_DBOWNER'}` environment variable.; If you **cannot** update your system, update your scripts to call the `Cgi::phpmyadminlink` function. This will create a temporary user session for you.

**Returns** `data`: object

- `created` (integer (`0`, `1`)) — Whether the function successfully created the temporary user session.; `1` - Success.; `0` - Failure.
- `session_temp_user` (string) — The temporary user's session ID.

<a id="session-create-webmail-session-for-mail-user"></a>
### `Session::create_webmail_session_for_mail_user` — Create Webmail session

`GET /execute/Session/create_webmail_session_for_mail_user` · RW · rollback: none · since cPanel 86

Create a temporary session for a cPanel user to connect to Webmail. Note: The cPanel user must own the Webmail account. ### How to use this API After you successfully call this API, you will need to log in to [Webmail](https://go.cpanel.net/webmailinterface). To do this, send an HTTP POST to `https://$URL_AUTHTY:2096$token/login` with a message body of `session=$session` where: `$URL_AUTHTY` represents the value from the `hostname` return.; If the `hostname` return value is `null`, enter the hostname of the server that answered the API function.; `$token` represents the value from the token return.; `$session` represents the value of the session return. For example, an HTTP POST may resemble the following: ```https://hostname.example.com:2096/cpsess2462418786/login``` With a message body of: ```session=username:D7NiAZv1nf4bXeg9:CREATE_WEBMAIL_SESSION_FOR_MAIL_USER,728fb86a7df1cf20690c65f349ac3137```

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain for the Webmail account.
- `login` · **required** · string · e.g. `username` — The Webmail account's username.
- `locale` · optional · string · e.g. `en` — The [locale](https://go.cpanel.net/localedocs) that the new session will use. Note:  You must **only** enter lowercase characters.; This parameter defaults to the cPanel user's locale.
- `remote_address` · optional · string <ipv4> · e.g. `192.168.0.1` — The session's client IP address. Note:  If you run this function from the command line, this parameter is **required**.; This parameter defaults to the API caller's IP address.

**Returns** `data`: object

- `hostname` (string) — The Webmail server's hostname.
- `session` (string) — The session ID to submit via POST to begin using the new session.
- `token` (string) — A new security token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Session \
  create_webmail_session_for_mail_user \
  login='username' \
  domain='example.com'
```

<a id="session-create-webmail-session-for-mail-user-check-password"></a>
### `Session::create_webmail_session_for_mail_user_check_password` — Create Webmail session with credentials

`GET /execute/Session/create_webmail_session_for_mail_user_check_password` · RW · rollback: none · since cPanel 86

This function creates a temporary session with a password for the calling cPanel user to connect to Webmail. Note:  The cPanel user must own the Webmail account.; This function works like the UAPI Session::create_webmail_session_for_mail_user function with one exception. This function requires a correct password to create the Webmail session. If you use an incorrect password or attempt to connect to a suspended account, the login will fail. ### How to use this API After you successfully call this API, you will need to log in to [Webmail](https://go.cpanel.net/webmailinterface). To do this, send an HTTP POST to `https://$URL_AUTHTY:2096$token/login` with a message body of `session=$session` where: `$URL_AUTHTY` represents the value from the `hostname` return.; If the `hostname` return value is `null`, enter the hostname of the server that answered the API function.; `$token` represents the value from the token return.; `$session` represents the value of the session return. For example, an HTTP POST may resemble the following: ```https://hostname.example.com:2096/cpsess2462418786/login``` With a message body of: ```session=username:D7NiAZv1nf4bXeg9:CREATE_WEBMAIL_SESSION_FOR_MAIL_USER,728fb86a7df1cf20690c65f349ac3137```

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain for the Webmail account.
- `login` · **required** · string · e.g. `username` — The Webmail account's username.
- `password` · **required** · string · e.g. `luggage12345` — The password for the Webmail account.
- `locale` · optional · string · e.g. `en` — The [locale](https://go.cpanel.net/localedocs) that the new session will use. Note:  You must **only** enter lowercase characters.; This parameter defaults to the cPanel user's locale.
- `remote_address` · optional · string <ipv4> · e.g. `192.168.0.1` — The session's account's client IP address. Note:  If you run this function from the command line, this parameter is **required**.; This parameter defaults to the API caller's IP address.

**Returns** `data`: object

- `hostname` (string) — The Webmail server's hostname.
- `session` (string) — The session value to submit via POST to begin using the new session.
- `token` (string) — A new security token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Session \
  create_webmail_session_for_mail_user_check_password \
  login='username' \
  domain='example.com' \
  password='luggage12345'
```

<a id="session-create-webmail-session-for-self"></a>
### `Session::create_webmail_session_for_self` — Create Webmail session for current user

`GET /execute/Session/create_webmail_session_for_self` · RW · rollback: none · since cPanel 86

Create a temporary session to connect to Webmail for the authenticated cPanel user. ### How to use this API After you successfully call this API, you will need to log in to [Webmail](https://go.cpanel.net/webmailinterface). To do this, send an HTTP POST to `https://$URL_AUTHTY:2096$token/login` with a message body of `session=$session` where: `$URL_AUTHTY` represents the value from the `hostname` return.; If the `hostname` return value is `null`, enter the hostname of the server that answered the API function.; `$token` represents the value from the token return.; `$session` represents the value of the session return. For example, an HTTP POST may resemble the following: ```https://hostname.example.com:2096/cpsess2462418786/login``` With a message body of: ```session=username:D7NiAZv1nf4bXeg9:CREATE_WEBMAIL_SESSION_FOR_MAIL_USER,728fb86a7df1cf20690c65f349ac3137```

**Parameters**

- `locale` · optional · string · e.g. `en` — The [locale](https://go.cpanel.net/localedocs) that the new session will use. Use UAPI `Locale::list_locales` to see a list of valid locales. Note:  You must **only** enter lowercase characters.; This parameter defaults to the cPanel user's locale.
- `remote_address` · optional · string <ipv4> · e.g. `192.168.0.1` — The session's client IP address. Note:  If you run this function from the command line, this parameter is **required**.; This parameter defaults to the API caller's IP address.

**Returns** `data`: object

- `hostname` (string <domain>) — The Webmail server's hostname.
- `session` (string) — The session value to submit via POST to begin using the new session.
- `token` (string) — A new security token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Session \
  create_webmail_session_for_self
```

## Webmail Applications

<a id="webmailapps-list-webmail-apps"></a>
### `WebmailApps::list_webmail_apps` — Return available webmail clients

`GET /execute/WebmailApps/list_webmail_apps` · RO · since cPanel 11.48

This function lists the account's available webmail clients. Important: When you disable the [Receive Mail role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `theme` · optional · string · default `the server's default theme` · e.g. `jupiter` — The webmail theme.

**Returns** `data`: array of object

- *(array of objects)*
  - `displayname` (string) — The webmail client name, as it will display in the interface.
  - `icon` (string) — An icon file's path, relative to the `/usr/local/cpanel/base/frontend` directory.
  - `id` (string) — The webmail client's ID.
  - `url` (string <url-path>) — The webmail client's URL.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebmailApps \
  list_webmail_apps
```

## Spam Filtering (Greylisting)

<a id="cpgreylist-disable-all-domains"></a>
### `cPGreyList::disable_all_domains` — Disable Greylisting for all domains

`GET /execute/cPGreyList/disable_all_domains` · RW · rollback: none · since cPanel 11.50

This function disables Greylisting on a cPanel account's domains.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string) — The domains that your changes will affect.
  - `domain` (string) — The domain.
  - `enabled` (integer (`0`, `1`)) — Whether Greylisting is enabled.; `1` — Enabled.; `0` — Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `addon`, `parked`)) — The domain type.; `main` — A main domain.; `addon` — An addon domain.; `parked` — A parked domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  disable_all_domains
```

<a id="cpgreylist-disable-domains"></a>
### `cPGreyList::disable_domains` — Disable Greylisting for specified domains

`GET /execute/cPGreyList/disable_domains` · RW · rollback: none · since cPanel 11.50

This function disables Greylisting on a cPanel account's selected domains.

**Parameters**

- `domains` · **required** · string — The domain on which to disable Greylisting. Note: To disable Greylisting on multiple domains, use the `domains` parameter multiple times.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string) — An array of domains that your changes will affect.
  - `domain` (string) — The domain.
  - `enabled` (integer (`0`, `1`)) — Whether Greylisting is disabled.; `1` — Enabled.; `0` — Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` — A main domain.; `sub` — A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  disable_domains \
  domains='example.com'
```

<a id="cpgreylist-enable-all-domains"></a>
### `cPGreyList::enable_all_domains` — Enable Greylisting for all domains

`GET /execute/cPGreyList/enable_all_domains` · RW · rollback: none · since cPanel 11.50

This function enables Greylisting on all of the cPanel account's domains.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string) — An array of domains that your changes will affect.
  - `domain` (string) — The domain.
  - `enabled` (integer (`0`, `1`)) — Whether Greylisting is enabled.; `1` — Enabled.; `0` — Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string) — The domain type.; `main` — A main domain.; `sub` — A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  enable_all_domains
```

<a id="cpgreylist-enable-domains"></a>
### `cPGreyList::enable_domains` — Enable Greylisting for specified domains

`GET /execute/cPGreyList/enable_domains` · RW · rollback: none · since cPanel 11.50

This function enables Greylisting on a cPanel account's selected domains.

**Parameters**

- `domains` · **required** · string — The domain on which to enable Greylisting. Note: To enable Greylisting on multiple domains, use the `domains` parameter multiple times.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string <domain>) — An array of domains that your changes will affect.
  - `domain` (string) — The domain.
  - `enabled` (integer (`0`, `1`)) — Whether Greylisting is disabled.; `1` — Enabled.; `0` — Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` — A main domain.; `sub` — A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  enable_domains \
  domains='example.com'
```

<a id="cpgreylist-has-greylisting-enabled"></a>
### `cPGreyList::has_greylisting_enabled` — Return whether Greylisting is enabled

`GET /execute/cPGreyList/has_greylisting_enabled` · RO · since cPanel 11.50

This function checks whether Greylisting is enabled for the cPanel account.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether Greylisting is enabled.; `1` — Enabled.; `0` — Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  has_greylisting_enabled
```

<a id="cpgreylist-list-domains"></a>
### `cPGreyList::list_domains` — Return Greylisting status for domains

`GET /execute/cPGreyList/list_domains` · RO · since cPanel 11.50

This function returns Greylisting's status for a cPanel account's domains.

**Returns** `data`: array of object

- *(array of objects)*
  - `cPGreyList` (object) — An object that contains the number of domains with Greylisting enabled or disabled.
    - `total_disabled` (integer) — The number of domains with Greylisting disabled.
    - `total_enabled` (integer) — The number of domains with Greylisting enabled.
  - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain will affect.
  - `domain` (string <domain>) — The domain.
  - `enabled` (integer (`0`, `1`)) — Whether Greylisting is enabled.; `1` — Enabled.; `0` — Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` — A main domain.; `sub` — A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  cPGreyList \
  list_domains
```

