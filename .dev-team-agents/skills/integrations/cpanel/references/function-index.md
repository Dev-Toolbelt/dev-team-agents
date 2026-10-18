<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI Function Index

Every UAPI function in the spec (695 operations). Grep this file by keyword (`grep -i "dns" function-index.md`) and open the linked module file.

## Groups

| Group | File | Functions | Modules |
|---|---|---|---|
| Account Security | [account-security.md](modules/account-security.md) | 1 | `ActiveSessions` |
| API Development Tools | [api-development-tools.md](modules/api-development-tools.md) | 9 | `Batch`, `Integration`, `Parser`, `Tokens`, `UserTasks` |
| Authentication | [authentication.md](modules/authentication.md) | 9 | `ExternalAuthentication`, `TwoFactorAuth` |
| Backup Information | [backup-information.md](modules/backup-information.md) | 3 | `BackupInfo` |
| Block Ip Addresses | [block-ip-addresses.md](modules/block-ip-addresses.md) | 2 | `BlockIP` |
| Commerce Integration | [commerce-integration.md](modules/commerce-integration.md) | 19 | `Market` |
| Contact Information | [contact-information.md](modules/contact-information.md) | 7 | `ContactInformation`, `Contactus` |
| cPanel Account | [cpanel-account.md](modules/cpanel-account.md) | 51 | `AccountEnhancements`, `DomainRecommendations`, `Features`, `Personalization`, `Quota`, `Resellers`, `ResourceUsage`, `StatsBar`, `Team`, `TeamRoles`, `UserManager`, `Users`, `Variables` |
| cPanel Account Backups | [cpanel-account-backups.md](modules/cpanel-account-backups.md) | 13 | `Backup`, `Restore` |
| cPanel Plugin Framework | [cpanel-plugin-framework.md](modules/cpanel-plugin-framework.md) | 2 | `Plugins` |
| cPanel Theme Management | [cpanel-theme-management.md](modules/cpanel-theme-management.md) | 14 | `Branding`, `CacheBuster`, `Chrome`, `Locale`, `Themes` |
| Directory Management | [directory-management.md](modules/directory-management.md) | 10 | `DirectoryIndexes`, `DirectoryPrivacy`, `DirectoryProtection` |
| DNS | [dns.md](modules/dns.md) | 45 | `DNS`, `DNSSEC`, `DynamicDNS`, `Email`, `EmailAuth`, `ZoneEdit` |
| Domain | [domain.md](modules/domain.md) | 4 | `Domain` |
| Domain Management | [domain-management.md](modules/domain-management.md) | 29 | `AddonDomain`, `DomainInfo`, `DomainLookup`, `Mime`, `Park`, `SubDomain`, `WebVhosts` |
| Domains | [domains.md](modules/domains.md) | 1 | `SubDomain` |
| Email | [email.md](modules/email.md) | 147 | `BoxTrapper`, `CSVImport`, `Chkservd`, `Email`, `GPG`, `Mailboxes`, `Session`, `SpamAssassin`, `WebmailApps`, `cPGreyList` |
| Extract Information | [extract-information.md](modules/extract-information.md) | 3 | `ExtractInfo` |
| File Manager | [file-manager.md](modules/file-manager.md) | 2 | `Trash` |
| Files | [files.md](modules/files.md) | 42 | `Fileman`, `Ftp`, `ImageManager`, `WebDisk` |
| GIT Management | [git-management.md](modules/git-management.md) | 7 | `VersionControl`, `VersionControlDeployment` |
| InProductSurvey | [inproductsurvey.md](modules/inproductsurvey.md) | 1 | `InProductSurvey` |
| MySQL and MariaDB | [mysql-and-mariadb.md](modules/mysql-and-mariadb.md) | 25 | `Mysql` |
| Notifications | [notifications.md](modules/notifications.md) | 1 | `Pushbullet` |
| Optional Applications | [optional-applications.md](modules/optional-applications.md) | 32 | `CCS`, `CPDAVD`, `ClamScanner`, `DAV`, `WordPressBackup`, `WordPressRestore` |
| PostgreSQL | [postgresql.md](modules/postgresql.md) | 14 | `Postgresql` |
| Retrieve bandwidth information | [retrieve-bandwidth-information.md](modules/retrieve-bandwidth-information.md) | 3 | `Bandwidth` |
| Security | [security.md](modules/security.md) | 6 | `KnownHosts`, `LastLogin`, `Variables` |
| Server Information | [server-information.md](modules/server-information.md) | 8 | `Notifications`, `PasswdStrength`, `SSH`, `ServerInformation`, `Variables`, `WebProsMCP` |
| ServiceProxy | [serviceproxy.md](modules/serviceproxy.md) | 3 | `ServiceProxy` |
| Site Quality Monitoring | [site-quality-monitoring.md](modules/site-quality-monitoring.md) | 13 | `SiteQuality` |
| SSL Certificates | [ssl-certificates.md](modules/ssl-certificates.md) | 53 | `DCV`, `SSL` |
| Statistics | [statistics.md](modules/statistics.md) | 7 | `Stats`, `StatsManager` |
| UserData | [userdata.md](modules/userdata.md) | 2 | `UserData` |
| Web Server Configuration | [web-server-configuration.md](modules/web-server-configuration.md) | 2 | `EA4` |
| Web Server Management | [web-server-management.md](modules/web-server-management.md) | 43 | `LangPHP`, `ModSecurity`, `NginxCaching`, `PassengerApps`, `WebApp` |
| Website Backups | [website-backups.md](modules/website-backups.md) | 8 | `WebsiteBackup` |
| Website Configuration | [website-configuration.md](modules/website-configuration.md) | 54 | `LogManager`, `Mime`, `Nova`, `Sitejet`, `WPX`, `WordPressSite` |

## Functions

| Function | Summary | RO/RW | File |
|---|---|---|---|
| `AccountEnhancements::has_enhancement` | Validate Account Enhancement assignment | RO | [cpanel-account](modules/cpanel-account.md#accountenhancements-has-enhancement) |
| `AccountEnhancements::list` | Return all cPanel account's Account Enhancements | RO | [cpanel-account](modules/cpanel-account.md#accountenhancements-list) |
| `ActiveSessions::list_active_sessions` | Return active cPanel sessions | ? | [account-security](modules/account-security.md#activesessions-list-active-sessions) |
| `AddonDomain::addaddondomain` | Create an addon domain | RW | [domain-management](modules/domain-management.md#addondomain-addaddondomain) |
| `AddonDomain::deladdondomain` | Remove an addon domain | RW | [domain-management](modules/domain-management.md#addondomain-deladdondomain) |
| `AddonDomain::listaddondomains` | List the addon domains | RO | [domain-management](modules/domain-management.md#addondomain-listaddondomains) |
| `Backup::fullbackup_to_ftp` | Back up cPanel account via FTP | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-fullbackup-to-ftp) |
| `Backup::fullbackup_to_homedir` | Back up cPanel account to home directory | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-fullbackup-to-homedir) |
| `Backup::fullbackup_to_scp_with_key` | Back up cPanel account via SCP with SSH key | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-fullbackup-to-scp-with-key) |
| `Backup::fullbackup_to_scp_with_password` | Back up cPanel account via SCP with password | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-fullbackup-to-scp-with-password) |
| `Backup::list_backups` | Return backup files | RO | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-list-backups) |
| `Backup::restore_databases` | Restore databases | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-restore-databases) |
| `Backup::restore_email_filters` | Restore email filters | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-restore-email-filters) |
| `Backup::restore_email_forwarders` | Restore email forwarders | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-restore-email-forwarders) |
| `Backup::restore_files` | Restore files | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#backup-restore-files) |
| `BackupInfo::list` | Return cPanel account backups | ? | [backup-information](modules/backup-information.md#backupinfo-list) |
| `BackupInfo::progress` | Return account backup progress | ? | [backup-information](modules/backup-information.md#backupinfo-progress) |
| `BackupInfo::reset` | Remove backup progress record | ? | [backup-information](modules/backup-information.md#backupinfo-reset) |
| `Bandwidth::get_enabled_protocols` | Return services monitored in bandwidth data | RO | [retrieve-bandwidth-information](modules/retrieve-bandwidth-information.md#bandwidth-get-enabled-protocols) |
| `Bandwidth::get_retention_periods` | Return bandwidth retention period | RO | [retrieve-bandwidth-information](modules/retrieve-bandwidth-information.md#bandwidth-get-retention-periods) |
| `Bandwidth::query` | Return cPanel account's bandwidth usage report | RO | [retrieve-bandwidth-information](modules/retrieve-bandwidth-information.md#bandwidth-query) |
| `Batch::strict` | Run multiple UAPI functions in order | RW | [api-development-tools](modules/api-development-tools.md#batch-strict) |
| `BlockIP::add_ip` | Add IP address to cPanel account's block list | RW | [block-ip-addresses](modules/block-ip-addresses.md#blockip-add-ip) |
| `BlockIP::remove_ip` | Remove IP address from cPanel account's block list | RW | [block-ip-addresses](modules/block-ip-addresses.md#blockip-remove-ip) |
| `BoxTrapper::blacklist_messages` | Add email address to BoxTrapper blocked senders | RW | [email](modules/email.md#boxtrapper-blacklist-messages) |
| `BoxTrapper::delete_messages` | Delete messages in the BoxTrapper queue | RW | [email](modules/email.md#boxtrapper-delete-messages) |
| `BoxTrapper::deliver_messages` | Send messages in the BoxTrapper queue | RW | [email](modules/email.md#boxtrapper-deliver-messages) |
| `BoxTrapper::get_allowlist` | Return account BoxTrapper allowlist rules | RO | [email](modules/email.md#boxtrapper-get-allowlist) |
| `BoxTrapper::get_blocklist` | Return account BoxTrapper blocklist rules | RO | [email](modules/email.md#boxtrapper-get-blocklist) |
| `BoxTrapper::get_configuration` | Return email account's BoxTrapper configuration | RO | [email](modules/email.md#boxtrapper-get-configuration) |
| `BoxTrapper::get_email_template` | Return specified BoxTrapper email template | RO | [email](modules/email.md#boxtrapper-get-email-template) |
| `BoxTrapper::get_forwarders` | Return all BoxTrapper forwarders | RO | [email](modules/email.md#boxtrapper-get-forwarders) |
| `BoxTrapper::get_ignorelist` | Return account BoxTrapper ignorelist rules | RO | [email](modules/email.md#boxtrapper-get-ignorelist) |
| `BoxTrapper::get_log` | Return BoxTrapper log file and contents | RO | [email](modules/email.md#boxtrapper-get-log) |
| `BoxTrapper::get_message` | Return message's top 200 lines in BoxTrapper queue | RO | [email](modules/email.md#boxtrapper-get-message) |
| `BoxTrapper::get_status` | Return whether email account uses BoxTrapper | RO | [email](modules/email.md#boxtrapper-get-status) |
| `BoxTrapper::ignore_messages` | Add email account to Exim ignore list | RW | [email](modules/email.md#boxtrapper-ignore-messages) |
| `BoxTrapper::list_email_templates` | Return BoxTrapper email templates | RO | [email](modules/email.md#boxtrapper-list-email-templates) |
| `BoxTrapper::list_queued_messages` | Return email account's BoxTrapper queued messages | RO | [email](modules/email.md#boxtrapper-list-queued-messages) |
| `BoxTrapper::process_messages` | Run a specific BoxTrapper action for a message | RW | [email](modules/email.md#boxtrapper-process-messages) |
| `BoxTrapper::reset_email_template` | Restore default BoxTrapper email message template | RW | [email](modules/email.md#boxtrapper-reset-email-template) |
| `BoxTrapper::save_configuration` | Update email account's BoxTrapper configuration | RW | [email](modules/email.md#boxtrapper-save-configuration) |
| `BoxTrapper::save_email_template` | Save BoxTrapper message template contents | RW | [email](modules/email.md#boxtrapper-save-email-template) |
| `BoxTrapper::set_allowlist` | Update account BoxTrapper allowlist | RW | [email](modules/email.md#boxtrapper-set-allowlist) |
| `BoxTrapper::set_blocklist` | Update account BoxTrapper blocklist | RW | [email](modules/email.md#boxtrapper-set-blocklist) |
| `BoxTrapper::set_forwarders` | Add email address to BoxTrapper forwarders | RW | [email](modules/email.md#boxtrapper-set-forwarders) |
| `BoxTrapper::set_ignorelist` | Update account BoxTrapper ignorelist | RW | [email](modules/email.md#boxtrapper-set-ignorelist) |
| `BoxTrapper::set_status` | Enable or disable BoxTrapper for email account | RW | [email](modules/email.md#boxtrapper-set-status) |
| `BoxTrapper::whitelist_messages` | Add email address to BoxTrapper allowed senders | RW | [email](modules/email.md#boxtrapper-whitelist-messages) |
| `Branding::get_application_information` | Return single app's info from dynamicui.conf | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#branding-get-application-information) |
| `Branding::get_applications` | Return multiple apps' info from dynamicui.conf | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#branding-get-applications) |
| `Branding::get_available_applications` | Return current user's cPanel application details | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#branding-get-available-applications) |
| `Branding::get_information_for_applications` | Return app's info from sitemap.json | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#branding-get-information-for-applications) |
| `Branding::include` | Return branding file content from the active theme | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#branding-include) |
| `CacheBuster::read` | Return web browser cached file override ID | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#cachebuster-read) |
| `CacheBuster::update` | Create web browser cached file override ID | RW | [cpanel-theme-management](modules/cpanel-theme-management.md#cachebuster-update) |
| `CCS::add_delegate` | Add calendar delegation | RW | [optional-applications](modules/optional-applications.md#ccs-add-delegate) |
| `CCS::list_delegates` | List cPanel account's calendar delegates | RO | [optional-applications](modules/optional-applications.md#ccs-list-delegates) |
| `CCS::list_users` | List cPanel account's calendar users | RO | [optional-applications](modules/optional-applications.md#ccs-list-users) |
| `CCS::remove_delegate` | Remove calendar delegation | RW | [optional-applications](modules/optional-applications.md#ccs-remove-delegate) |
| `CCS::update_delegate` | Update calendar delegation | RW | [optional-applications](modules/optional-applications.md#ccs-update-delegate) |
| `Chkservd::get_exim_ports` | Return outgoing (SMTP) mail port | RO | [email](modules/email.md#chkservd-get-exim-ports) |
| `Chkservd::get_exim_ports_ssl` | Return outgoing mail (SMTP) SSL-secured port | RO | [email](modules/email.md#chkservd-get-exim-ports-ssl) |
| `Chrome::get_dom` | Return cPanel theme header and footer HTML | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#chrome-get-dom) |
| `ClamScanner::check_disinfection_status` | Request disinfection process status | RO | [optional-applications](modules/optional-applications.md#clamscanner-check-disinfection-status) |
| `ClamScanner::disinfect_files` | Start disinfecting files with viruses | RW | [optional-applications](modules/optional-applications.md#clamscanner-disinfect-files) |
| `ClamScanner::get_scan_paths` | Return virus scan types | RO | [optional-applications](modules/optional-applications.md#clamscanner-get-scan-paths) |
| `ClamScanner::get_scan_status` | Request virus scan status | RO | [optional-applications](modules/optional-applications.md#clamscanner-get-scan-status) |
| `ClamScanner::list_infected_files` | Return infected file list | RO | [optional-applications](modules/optional-applications.md#clamscanner-list-infected-files) |
| `ClamScanner::start_scan` | Start virus scan | RW | [optional-applications](modules/optional-applications.md#clamscanner-start-scan) |
| `ContactInformation::get_notification_preferences` | Return the account's notification preferences. | RO | [contact-information](modules/contact-information.md#contactinformation-get-notification-preferences) |
| `ContactInformation::get_pushbullet_access_token` | Return Pushbullet access token | RW | [contact-information](modules/contact-information.md#contactinformation-get-pushbullet-access-token) |
| `ContactInformation::set_email_addresses` | Set contact email address(es) | RW | [contact-information](modules/contact-information.md#contactinformation-set-email-addresses) |
| `ContactInformation::set_notification_preferences` | Set the account's notification preferences. | RW | [contact-information](modules/contact-information.md#contactinformation-set-notification-preferences) |
| `ContactInformation::set_pushbullet_access_token` | Update Pushbullet access token | RW | [contact-information](modules/contact-information.md#contactinformation-set-pushbullet-access-token) |
| `ContactInformation::unset_email_addresses` | Unset contact email addresses | RW | [contact-information](modules/contact-information.md#contactinformation-unset-email-addresses) |
| `Contactus::is_enabled` | Return whether contact option is enabled | RO | [contact-information](modules/contact-information.md#contactus-is-enabled) |
| `CPDAVD::add_delegate` | Share a calendar | RW | [optional-applications](modules/optional-applications.md#cpdavd-add-delegate) |
| `CPDAVD::list_delegates` | List calendar sharing. | RO | [optional-applications](modules/optional-applications.md#cpdavd-list-delegates) |
| `CPDAVD::list_users` | List CalDAV and CardDAV users | RO | [optional-applications](modules/optional-applications.md#cpdavd-list-users) |
| `CPDAVD::manage_collection` | Manage a calendar, task list, or address book | RW | [optional-applications](modules/optional-applications.md#cpdavd-manage-collection) |
| `CPDAVD::remove_delegate` | Remove a share. | RW | [optional-applications](modules/optional-applications.md#cpdavd-remove-delegate) |
| `CPDAVD::update_delegate` | Update calendar sharing. | RW | [optional-applications](modules/optional-applications.md#cpdavd-update-delegate) |
| `cPGreyList::disable_all_domains` | Disable Greylisting for all domains | RW | [email](modules/email.md#cpgreylist-disable-all-domains) |
| `cPGreyList::disable_domains` | Disable Greylisting for specified domains | RW | [email](modules/email.md#cpgreylist-disable-domains) |
| `cPGreyList::enable_all_domains` | Enable Greylisting for all domains | RW | [email](modules/email.md#cpgreylist-enable-all-domains) |
| `cPGreyList::enable_domains` | Enable Greylisting for specified domains | RW | [email](modules/email.md#cpgreylist-enable-domains) |
| `cPGreyList::has_greylisting_enabled` | Return whether Greylisting is enabled | RO | [email](modules/email.md#cpgreylist-has-greylisting-enabled) |
| `cPGreyList::list_domains` | Return Greylisting status for domains | RO | [email](modules/email.md#cpgreylist-list-domains) |
| `CSVImport::doimport` | Import email accounts from CSV file | RW | [email](modules/email.md#csvimport-doimport) |
| `DAV::disable_shared_global_addressbook` | Disable global address book | RW | [optional-applications](modules/optional-applications.md#dav-disable-shared-global-addressbook) |
| `DAV::enable_shared_global_addressbook` | Enable global address book | RW | [optional-applications](modules/optional-applications.md#dav-enable-shared-global-addressbook) |
| `DAV::get_calendar_contacts_config` | Return CalDAV and CardDAV connection information | RO | [optional-applications](modules/optional-applications.md#dav-get-calendar-contacts-config) |
| `DAV::has_shared_global_addressbook` | Return whether global address book is enabled | RO | [optional-applications](modules/optional-applications.md#dav-has-shared-global-addressbook) |
| `DAV::is_dav_service_enabled` | Return whether DAV is enabled | RO | [optional-applications](modules/optional-applications.md#dav-is-dav-service-enabled) |
| `DAV::is_horde_enabled` | Return whether Horde is enabled | RO | [optional-applications](modules/optional-applications.md#dav-is-horde-enabled) |
| `DCV::check_domains_via_dns` | Verify domain ownership via DNS | RW | [ssl-certificates](modules/ssl-certificates.md#dcv-check-domains-via-dns) |
| `DCV::check_domains_via_http` | Verify domain ownership via HTTP | RW | [ssl-certificates](modules/ssl-certificates.md#dcv-check-domains-via-http) |
| `DCV::ensure_domains_can_pass_dcv` | Verify domain ownership **(deprecated)** | RW | [ssl-certificates](modules/ssl-certificates.md#dcv-ensure-domains-can-pass-dcv) |
| `DirectoryIndexes::get_indexing` | Return directory indexing settings | RO | [directory-management](modules/directory-management.md#directoryindexes-get-indexing) |
| `DirectoryIndexes::list_directories` | Return subdirectories directory indexing settings | RO | [directory-management](modules/directory-management.md#directoryindexes-list-directories) |
| `DirectoryIndexes::set_indexing` | Update directory indexing settings | RW | [directory-management](modules/directory-management.md#directoryindexes-set-indexing) |
| `DirectoryPrivacy::add_user` | Add authorized user for protected directory | RW | [directory-management](modules/directory-management.md#directoryprivacy-add-user) |
| `DirectoryPrivacy::configure_directory_protection` | Enable or disable protected directory | RW | [directory-management](modules/directory-management.md#directoryprivacy-configure-directory-protection) |
| `DirectoryPrivacy::delete_user` | Delete authorized user for protected directory | RW | [directory-management](modules/directory-management.md#directoryprivacy-delete-user) |
| `DirectoryPrivacy::is_directory_protected` | Return whether directory uses password protection | RO | [directory-management](modules/directory-management.md#directoryprivacy-is-directory-protected) |
| `DirectoryPrivacy::list_directories` | Return privacy status of subdirectories | RO | [directory-management](modules/directory-management.md#directoryprivacy-list-directories) |
| `DirectoryPrivacy::list_users` | Return authorized users for protected directory | RO | [directory-management](modules/directory-management.md#directoryprivacy-list-users) |
| `DirectoryProtection::list_directories` | Return Directory Protection settings | RO | [directory-management](modules/directory-management.md#directoryprotection-list-directories) |
| `DNS::ensure_domains_reside_only_locally` | Return whether domains only resolve locally | RO | [dns](modules/dns.md#dns-ensure-domains-reside-only-locally) |
| `DNS::ensure_domains_use_recognized_nameservers` | Return whether domains use recognized nameservers | RO | [dns](modules/dns.md#dns-ensure-domains-use-recognized-nameservers) |
| `DNS::fetch_cpanel_generated_domains` | Retrieve cPanel-generated subdomains for a domain | RO | [dns](modules/dns.md#dns-fetch-cpanel-generated-domains) |
| `DNS::has_local_authority` | Return whether local DNS server is authoritative | RO | [dns](modules/dns.md#dns-has-local-authority) |
| `DNS::is_alias_available` | Return `ALIAS` DNS record availability & resolver | RO | [dns](modules/dns.md#dns-is-alias-available) |
| `DNS::is_https_available` | Return DNS HTTPS record support information | RO | [dns](modules/dns.md#dns-is-https-available) |
| `DNS::is_svcb_available` | Return DNS SVCB record support information | RO | [dns](modules/dns.md#dns-is-svcb-available) |
| `DNS::lookup` | Return domain's DNS information | RO | [dns](modules/dns.md#dns-lookup) |
| `DNS::mass_edit_zone` | Update a DNS zone | RW | [dns](modules/dns.md#dns-mass-edit-zone) |
| `DNS::parse_zone` | Return a parsed DNS zone | RO | [dns](modules/dns.md#dns-parse-zone) |
| `DNS::swap_ip_in_zones` | Update IP addresses in zone files | RW | [dns](modules/dns.md#dns-swap-ip-in-zones) |
| `DNSSEC::activate_zone_key` | Enable DNSSEC security key | RW | [dns](modules/dns.md#dnssec-activate-zone-key) |
| `DNSSEC::add_zone_key` | Create DNSSEC security key | RW | [dns](modules/dns.md#dnssec-add-zone-key) |
| `DNSSEC::deactivate_zone_key` | Disable DNSSEC security key | RW | [dns](modules/dns.md#dnssec-deactivate-zone-key) |
| `DNSSEC::disable_dnssec` | Disable DNSSEC | RW | [dns](modules/dns.md#dnssec-disable-dnssec) |
| `DNSSEC::enable_dnssec` | Enable DNSSEC | RW | [dns](modules/dns.md#dnssec-enable-dnssec) |
| `DNSSEC::export_zone_dnskey` | Export DNSKEY record value | RO | [dns](modules/dns.md#dnssec-export-zone-dnskey) |
| `DNSSEC::export_zone_key` | Export DNSSEC security key | RW | [dns](modules/dns.md#dnssec-export-zone-key) |
| `DNSSEC::fetch_ds_records` | Return domain's DS records | RO | [dns](modules/dns.md#dnssec-fetch-ds-records) |
| `DNSSEC::import_zone_key` | Add DNSSEC security key | RW | [dns](modules/dns.md#dnssec-import-zone-key) |
| `DNSSEC::remove_zone_key` | Remove DNSSEC security key | RW | [dns](modules/dns.md#dnssec-remove-zone-key) |
| `DNSSEC::set_nsec3` | Update domain to use NSEC3 | RW | [dns](modules/dns.md#dnssec-set-nsec3) |
| `DNSSEC::unset_nsec3` | Update domain to use NSEC | RW | [dns](modules/dns.md#dnssec-unset-nsec3) |
| `Domain::convert_temporary_to_registered` | Convert a temporary domain to a registered domain | RW | [domain](modules/domain.md#domain-convert-temporary-to-registered) |
| `Domain::is_temporary_domain` | Return whether a domain is temporary | RO | [domain](modules/domain.md#domain-is-temporary-domain) |
| `Domain::rename_domain` | Rename a primary, addon, or alias domain | RW | [domain](modules/domain.md#domain-rename-domain) |
| `Domain::temporary_domain_is_disabled` | Return whether temporary domains are disabled | RO | [domain](modules/domain.md#domain-temporary-domain-is-disabled) |
| `DomainInfo::domains_data` | Return all domains' hosting configuration | RO | [domain-management](modules/domain-management.md#domaininfo-domains-data) |
| `DomainInfo::list_domains` | Return cPanel account's domains | RO | [domain-management](modules/domain-management.md#domaininfo-list-domains) |
| `DomainInfo::main_domain_builtin_subdomain_aliases` | Return built-in subdomain aliases | RO | [domain-management](modules/domain-management.md#domaininfo-main-domain-builtin-subdomain-aliases) |
| `DomainInfo::primary_domain` | Return the cPanel account's primary domain | RO | [domain-management](modules/domain-management.md#domaininfo-primary-domain) |
| `DomainInfo::single_domain_data` | Return domain's hosting configuration | RO | [domain-management](modules/domain-management.md#domaininfo-single-domain-data) |
| `DomainLookup::countbasedomains` | Count the domains that have their own DNS zone | RO | [domain-management](modules/domain-management.md#domainlookup-countbasedomains) |
| `DomainLookup::getbasedomains` | List the domains that have their own DNS zone | RO | [domain-management](modules/domain-management.md#domainlookup-getbasedomains) |
| `DomainLookup::getdocroot` | Return a domain's document root | RO | [domain-management](modules/domain-management.md#domainlookup-getdocroot) |
| `DomainLookup::getdocroots` | Return every domain's document root | RO | [domain-management](modules/domain-management.md#domainlookup-getdocroots) |
| `DomainRecommendations::domain_availability` | Check whether a domain is available for registration | RO | [cpanel-account](modules/cpanel-account.md#domainrecommendations-domain-availability) |
| `DomainRecommendations::domain_suggestions` | Search for available domain names and pricing | RO | [cpanel-account](modules/cpanel-account.md#domainrecommendations-domain-suggestions) |
| `DomainRecommendations::get_store_config` | Retrieve the sanitized domain store configuration | RO | [cpanel-account](modules/cpanel-account.md#domainrecommendations-get-store-config) |
| `DomainRecommendations::is_enabled` | Check whether Domain Recommendations is enabled | RO | [cpanel-account](modules/cpanel-account.md#domainrecommendations-is-enabled) |
| `DomainRecommendations::purchase_domain` | Get a URL to purchase a domain | RW | [cpanel-account](modules/cpanel-account.md#domainrecommendations-purchase-domain) |
| `DomainRecommendations::supported_tlds` | List the TLDs supported by the domain store | RO | [cpanel-account](modules/cpanel-account.md#domainrecommendations-supported-tlds) |
| `DynamicDNS::create` | Create Dynamic DNS domain | RW | [dns](modules/dns.md#dynamicdns-create) |
| `DynamicDNS::delete` | Delete Dynamic DNS domain | RW | [dns](modules/dns.md#dynamicdns-delete) |
| `DynamicDNS::list` | Return Dynamic DNS domains | RO | [dns](modules/dns.md#dynamicdns-list) |
| `DynamicDNS::recreate` | Update Dynamic DNS domain ID | RW | [dns](modules/dns.md#dynamicdns-recreate) |
| `DynamicDNS::set_description` | Update Dynamic DNS domain description | RW | [dns](modules/dns.md#dynamicdns-set-description) |
| `EA4::get_php_recommendations` | Get custom PHP recommendations. | RO | [web-server-configuration](modules/web-server-configuration.md#ea4-get-php-recommendations) |
| `EA4::get_recommendations` | Get EA4 configuration recommendations | RO | [web-server-configuration](modules/web-server-configuration.md#ea4-get-recommendations) |
| `Email::account_name` | Return current user's account name | RO | [email](modules/email.md#email-account-name) |
| `Email::add_auto_responder` | Create email account's autoresponder | RW | [email](modules/email.md#email-add-auto-responder) |
| `Email::add_domain_forwarder` | Create domain-level forwarder | RW | [email](modules/email.md#email-add-domain-forwarder) |
| `Email::add_forwarder` | Create email account forwarder | RW | [email](modules/email.md#email-add-forwarder) |
| `Email::add_list` | Create mailing list | RW | [email](modules/email.md#email-add-list) |
| `Email::add_mailman_delegates` | Add administrators to mailing list | RW | [email](modules/email.md#email-add-mailman-delegates) |
| `Email::add_mx` | Create mail exchanger record | RW | [dns](modules/dns.md#email-add-mx) |
| `Email::add_pop` | Create email account | RW | [email](modules/email.md#email-add-pop) |
| `Email::add_spam_filter` | Update minimum spam score threshold value | RW | [email](modules/email.md#email-add-spam-filter) |
| `Email::browse_mailbox` | Return mail directory's subdirectories and files | RO | [email](modules/email.md#email-browse-mailbox) |
| `Email::change_mx` | Update mail exchanger record | RW | [dns](modules/dns.md#email-change-mx) |
| `Email::check_fastmail` | Return BlackBerry FastMail support status | RO | [email](modules/email.md#email-check-fastmail) |
| `Email::count_auto_responders` | Return cPanel account's autoresponders total | RO | [email](modules/email.md#email-count-auto-responders) |
| `Email::count_filters` | Return cPanel account's email filters total | RO | [email](modules/email.md#email-count-filters) |
| `Email::count_forwarders` | Return cPanel account's mail forwarder total | RO | [email](modules/email.md#email-count-forwarders) |
| `Email::count_lists` | Return cPanel account's mailing list total | RO | [email](modules/email.md#email-count-lists) |
| `Email::count_pops` | Return cPanel account's email account total | RO | [email](modules/email.md#email-count-pops) |
| `Email::delete_auto_responder` | Delete email account's autoresponder | RW | [email](modules/email.md#email-delete-auto-responder) |
| `Email::delete_domain_forwarder` | Delete domain-level forwarder | RW | [email](modules/email.md#email-delete-domain-forwarder) |
| `Email::delete_filter` | Delete email account's email filter | RW | [email](modules/email.md#email-delete-filter) |
| `Email::delete_forwarder` | Delete email account's email forwarder | RW | [email](modules/email.md#email-delete-forwarder) |
| `Email::delete_held_messages` | Delete email account's outgoing messages | RW | [email](modules/email.md#email-delete-held-messages) |
| `Email::delete_list` | Delete mailing list | RW | [email](modules/email.md#email-delete-list) |
| `Email::delete_mx` | Delete mail exchanger record | RW | [dns](modules/dns.md#email-delete-mx) |
| `Email::delete_pop` | Delete email account | RW | [email](modules/email.md#email-delete-pop) |
| `Email::disable_filter` | Disable email filter for email account | RW | [email](modules/email.md#email-disable-filter) |
| `Email::disable_mailbox_autocreate` | Disable cPanel account mailbox autocreation | RW | [email](modules/email.md#email-disable-mailbox-autocreate) |
| `Email::disable_spam_assassin` | Disable Apache SpamAssassin for cPanel account | RW | [email](modules/email.md#email-disable-spam-assassin) |
| `Email::disable_spam_autodelete` | Disable spam box filtering auto-delete | RW | [email](modules/email.md#email-disable-spam-autodelete) |
| `Email::disable_spam_box` | Disable spam box filtering for cPanel account | RW | [email](modules/email.md#email-disable-spam-box) |
| `Email::dispatch_client_settings` | Send email client settings to an email address | RW | [email](modules/email.md#email-dispatch-client-settings) |
| `Email::edit_pop_quota` | Update email account's quota | RW | [email](modules/email.md#email-edit-pop-quota) |
| `Email::enable_filter` | Enable email filter for email account | RW | [email](modules/email.md#email-enable-filter) |
| `Email::enable_mailbox_autocreate` | Enable cPanel account mailbox autocreation | RW | [email](modules/email.md#email-enable-mailbox-autocreate) |
| `Email::enable_spam_assassin` | Enable Apache SpamAssassin for cPanel account | RW | [email](modules/email.md#email-enable-spam-assassin) |
| `Email::enable_spam_box` | Enable spam box filtering for cPanel account | RW | [email](modules/email.md#email-enable-spam-box) |
| `Email::export_lists` | Export cPanel account's Mailman mailing lists to a file | RW | [email](modules/email.md#email-export-lists) |
| `Email::fetch_charmaps` | Return server's supported character encodings | RO | [email](modules/email.md#email-fetch-charmaps) |
| `Email::fts_rescan_mailbox` | Start IMAP Full-Text Search scan for email account | RW | [email](modules/email.md#email-fts-rescan-mailbox) |
| `Email::generate_mailman_otp` | Create one-time password for a mailing list | RW | [email](modules/email.md#email-generate-mailman-otp) |
| `Email::get_auto_responder` | Return email account's autoresponder information | RO | [email](modules/email.md#email-get-auto-responder) |
| `Email::get_charsets` | Return mail server's supported character encodings | RO | [email](modules/email.md#email-get-charsets) |
| `Email::get_client_settings` | Return email account's client settings | RO | [email](modules/email.md#email-get-client-settings) |
| `Email::get_default_email_quota` | Return email account's default email quota | RO | [email](modules/email.md#email-get-default-email-quota) |
| `Email::get_default_email_quota_mib` | Return email account's default email quota in MiB | RO | [email](modules/email.md#email-get-default-email-quota-mib) |
| `Email::get_disk_usage` | Return email account's disk usage | RO | [email](modules/email.md#email-get-disk-usage) |
| `Email::get_filter` | Return email filter's information | RO | [email](modules/email.md#email-get-filter) |
| `Email::get_held_message_count` | Return email account's outgoing message count | RO | [email](modules/email.md#email-get-held-message-count) |
| `Email::get_lists_total_disk_usage` | Return cPanel account's mailing list disk usage | RO | [email](modules/email.md#email-get-lists-total-disk-usage) |
| `Email::get_mailbox_autocreate` | Return cPanel account's mailbox autocreate status | RO | [email](modules/email.md#email-get-mailbox-autocreate) |
| `Email::get_mailman_delegates` | Return mailing list administrators | RO | [email](modules/email.md#email-get-mailman-delegates) |
| `Email::get_main_account_disk_usage` | Return primary email account's disk usage | RO | [email](modules/email.md#email-get-main-account-disk-usage) |
| `Email::get_main_account_disk_usage_bytes` | Return primary email account's disk usage in bytes | RO | [email](modules/email.md#email-get-main-account-disk-usage-bytes) |
| `Email::get_max_email_quota` | Return email account's max quota size | RO | [email](modules/email.md#email-get-max-email-quota) |
| `Email::get_max_email_quota_mib` | Return email account's max quota size in MiB | RO | [email](modules/email.md#email-get-max-email-quota-mib) |
| `Email::get_pop_quota` | Return email account's quota | RO | [email](modules/email.md#email-get-pop-quota) |
| `Email::get_spam_settings` | Return email account Apache SpamAssassin settings | RO | [email](modules/email.md#email-get-spam-settings) |
| `Email::get_webmail_settings` | Return email account's Webmail settings | RO | [email](modules/email.md#email-get-webmail-settings) |
| `Email::has_delegated_mailman_lists` | Return email account's mailing list privileges | RO | [email](modules/email.md#email-has-delegated-mailman-lists) |
| `Email::has_plaintext_authentication` | Return whether plaintext authentication is enabled | RO | [email](modules/email.md#email-has-plaintext-authentication) |
| `Email::hold_outgoing` | Stop email account's outgoing mail | RW | [email](modules/email.md#email-hold-outgoing) |
| `Email::list_auto_responders` | Return domain's autoresponders | RO | [email](modules/email.md#email-list-auto-responders) |
| `Email::list_default_address` | Return domain's default email address | RO | [email](modules/email.md#email-list-default-address) |
| `Email::list_domain_forwarders` | Return domain-level forwarders | RO | [email](modules/email.md#email-list-domain-forwarders) |
| `Email::list_filters` | Return account-level email filters | RO | [email](modules/email.md#email-list-filters) |
| `Email::list_filters_backups` | Return domains with domain-level email filters | RO | [email](modules/email.md#email-list-filters-backups) |
| `Email::list_forwarders` | Return domain's forwarders | RO | [email](modules/email.md#email-list-forwarders) |
| `Email::list_forwarders_backups` | Return domains with domain-level forwarders | RO | [email](modules/email.md#email-list-forwarders-backups) |
| `Email::list_lists` | Return cPanel account's mailing lists | RO | [email](modules/email.md#email-list-lists) |
| `Email::list_mail_domains` | Return cPanel account's mail domains | RO | [email](modules/email.md#email-list-mail-domains) |
| `Email::list_mxs` | Return mail exchanger records | RO | [dns](modules/dns.md#email-list-mxs) |
| `Email::list_pops` | Return email accounts | RO | [email](modules/email.md#email-list-pops) |
| `Email::list_pops_with_disk` | Return email accounts with disk information | RO | [email](modules/email.md#email-list-pops-with-disk) |
| `Email::list_system_filter_info` | Return system-level email filter file information | RO | [email](modules/email.md#email-list-system-filter-info) |
| `Email::passwd_list` | Update mailing list password | RW | [email](modules/email.md#email-passwd-list) |
| `Email::passwd_pop` | Update email account password | RW | [email](modules/email.md#email-passwd-pop) |
| `Email::release_outgoing` | Start email account outgoing mail | RW | [email](modules/email.md#email-release-outgoing) |
| `Email::remove_mailman_delegates` | Remove account mailing list admin privileges | RW | [email](modules/email.md#email-remove-mailman-delegates) |
| `Email::reorder_filters` | Update email address's email filter order | RW | [email](modules/email.md#email-reorder-filters) |
| `Email::set_always_accept` | Update Mail Exchanger type | RW | [email](modules/email.md#email-set-always-accept) |
| `Email::set_default_address` | Create default email address | RW | [email](modules/email.md#email-set-default-address) |
| `Email::set_list_privacy_options` | Update mailing list privacy options | RW | [email](modules/email.md#email-set-list-privacy-options) |
| `Email::set_manual_mx_redirects` | Add manual MX redirection | RW | [email](modules/email.md#email-set-manual-mx-redirects) |
| `Email::stats_db_status` | Return eximstats SQLite database status | RO | [email](modules/email.md#email-stats-db-status) |
| `Email::store_filter` | Create email filter | RW | [email](modules/email.md#email-store-filter) |
| `Email::suspend_incoming` | Suspend email account incoming (SMTP) mail | RW | [email](modules/email.md#email-suspend-incoming) |
| `Email::suspend_login` | Suspend email account login | RW | [email](modules/email.md#email-suspend-login) |
| `Email::suspend_outgoing` | Suspend email account outgoing mail | RW | [email](modules/email.md#email-suspend-outgoing) |
| `Email::terminate_mailbox_sessions` | Stop cPanel account IMAP and POP3 connections | RW | [email](modules/email.md#email-terminate-mailbox-sessions) |
| `Email::trace_delivery` | Run email delivery route trace | RO | [email](modules/email.md#email-trace-delivery) |
| `Email::trace_filter` | Run test for main domain email filters | RO | [email](modules/email.md#email-trace-filter) |
| `Email::unset_manual_mx_redirects` | Remove manual MX redirection | RW | [email](modules/email.md#email-unset-manual-mx-redirects) |
| `Email::unsuspend_incoming` | Unsuspend email account incoming mail | RW | [email](modules/email.md#email-unsuspend-incoming) |
| `Email::unsuspend_login` | Unsuspend email account login | RW | [email](modules/email.md#email-unsuspend-login) |
| `Email::unsuspend_outgoing` | Unsuspend email account outgoing mail | RW | [email](modules/email.md#email-unsuspend-outgoing) |
| `Email::verify_password` | Validate email account password | RW | [email](modules/email.md#email-verify-password) |
| `EmailAuth::apply_dmarc` | Apply DMARC records to domains. | RW | [dns](modules/dns.md#emailauth-apply-dmarc) |
| `EmailAuth::disable_dkim` | Remove domains' DKIM records | RW | [dns](modules/dns.md#emailauth-disable-dkim) |
| `EmailAuth::enable_dkim` | Enable domains' DKIM records | RW | [dns](modules/dns.md#emailauth-enable-dkim) |
| `EmailAuth::ensure_dkim_keys_exist` | Validate domains' DKIM private keys | RW | [dns](modules/dns.md#emailauth-ensure-dkim-keys-exist) |
| `EmailAuth::fetch_dkim_private_keys` | Return domains' DKIM private keys | RW | [dns](modules/dns.md#emailauth-fetch-dkim-private-keys) |
| `EmailAuth::install_dkim_private_keys` | Add domains' DKIM record keys | RW | [dns](modules/dns.md#emailauth-install-dkim-private-keys) |
| `EmailAuth::install_spf_records` | Add domains' SPF records | RW | [dns](modules/dns.md#emailauth-install-spf-records) |
| `EmailAuth::remove_dmarc` | Remove DMARC record from domain(s) | RW | [dns](modules/dns.md#emailauth-remove-dmarc) |
| `EmailAuth::validate_current_dkims` | Validate domains' DKIM records | RO | [dns](modules/dns.md#emailauth-validate-current-dkims) |
| `EmailAuth::validate_current_dmarcs` | Validate domains' DMARC records | RO | [dns](modules/dns.md#emailauth-validate-current-dmarcs) |
| `EmailAuth::validate_current_ptrs` | Validate domains' PTR records | RO | [dns](modules/dns.md#emailauth-validate-current-ptrs) |
| `EmailAuth::validate_current_spfs` | Validate domains' SPF records | RO | [dns](modules/dns.md#emailauth-validate-current-spfs) |
| `ExternalAuthentication::configured_modules` | Return server's external authentication providers | RO | [authentication](modules/authentication.md#externalauthentication-configured-modules) |
| `ExternalAuthentication::get_authn_links` | Return external authentication links | RO | [authentication](modules/authentication.md#externalauthentication-get-authn-links) |
| `ExternalAuthentication::has_external_auth_modules_configured` | Return external authentication user status | RO | [authentication](modules/authentication.md#externalauthentication-has-external-auth-modules-configured) |
| `ExternalAuthentication::remove_authn_link` | Remove external authentication link | RW | [authentication](modules/authentication.md#externalauthentication-remove-authn-link) |
| `ExtractInfo::finish` | Remove extract progress record | ? | [extract-information](modules/extract-information.md#extractinfo-finish) |
| `ExtractInfo::progress` | Return archive extraction progress | ? | [extract-information](modules/extract-information.md#extractinfo-progress) |
| `ExtractInfo::start` | Start extract progress tracking | ? | [extract-information](modules/extract-information.md#extractinfo-start) |
| `Features::get_feature_metadata` | Return cPanel account's features' metadata | RO | [cpanel-account](modules/cpanel-account.md#features-get-feature-metadata) |
| `Features::has_feature` | Validate cPanel account's feature access | RO | [cpanel-account](modules/cpanel-account.md#features-has-feature) |
| `Features::has_features_like` | Return whether queried features are enabled | RO | [cpanel-account](modules/cpanel-account.md#features-has-features-like) |
| `Features::list_features` | Return cPanel account's features | RO | [cpanel-account](modules/cpanel-account.md#features-list-features) |
| `Features::list_features_like` | Return queried cPanel account features | RO | [cpanel-account](modules/cpanel-account.md#features-list-features-like) |
| `Fileman::autocompletedir` | Return autocomplete file and directory names | RO | [files](modules/files.md#fileman-autocompletedir) |
| `Fileman::copy_file` | Copy a file | RW | [files](modules/files.md#fileman-copy-file) |
| `Fileman::delete_file` | Delete a file permanently | RW | [files](modules/files.md#fileman-delete-file) |
| `Fileman::empty_trash` | Delete .trash folder content | RW | [files](modules/files.md#fileman-empty-trash) |
| `Fileman::get_file_content` | Return file content | RO | [files](modules/files.md#fileman-get-file-content) |
| `Fileman::get_file_information` | Return file or directory information | RO | [files](modules/files.md#fileman-get-file-information) |
| `Fileman::list_files` | Return directory content | RO | [files](modules/files.md#fileman-list-files) |
| `Fileman::move_file` | Move a file | RW | [files](modules/files.md#fileman-move-file) |
| `Fileman::rename_file` | Rename a file | RW | [files](modules/files.md#fileman-rename-file) |
| `Fileman::restore_from_trash` | Restore a file from the trash | RW | [files](modules/files.md#fileman-restore-from-trash) |
| `Fileman::save_file_content` | Save file | RW | [files](modules/files.md#fileman-save-file-content) |
| `Fileman::transcode` | Update buffer encoding | RW | [files](modules/files.md#fileman-transcode) |
| `Fileman::trash_file` | Move a file to the trash | RW | [files](modules/files.md#fileman-trash-file) |
| `Fileman::upload_files` | Upload files | RW | [files](modules/files.md#fileman-upload-files) |
| `Ftp::add_ftp` | Create FTP account | RW | [files](modules/files.md#ftp-add-ftp) |
| `Ftp::allows_anonymous_ftp` | Return if anonymous FTP connections allowed | RO | [files](modules/files.md#ftp-allows-anonymous-ftp) |
| `Ftp::allows_anonymous_ftp_incoming` | Return if anonymous FTP transfers allowed | RO | [files](modules/files.md#ftp-allows-anonymous-ftp-incoming) |
| `Ftp::delete_ftp` | Delete FTP account | RW | [files](modules/files.md#ftp-delete-ftp) |
| `Ftp::ftp_exists` | Return whether an FTP account exists | RO | [files](modules/files.md#ftp-ftp-exists) |
| `Ftp::get_ftp_daemon_info` | Return FTP server's information | RO | [files](modules/files.md#ftp-get-ftp-daemon-info) |
| `Ftp::get_port` | Return FTP server's port | RO | [files](modules/files.md#ftp-get-port) |
| `Ftp::get_quota` | Return FTP account's quota | RO | [files](modules/files.md#ftp-get-quota) |
| `Ftp::get_welcome_message` | Return FTP account's welcome message | RO | [files](modules/files.md#ftp-get-welcome-message) |
| `Ftp::kill_session` | Stop FTP session | RW | [files](modules/files.md#ftp-kill-session) |
| `Ftp::list_ftp` | Return FTP accounts | RO | [files](modules/files.md#ftp-list-ftp) |
| `Ftp::list_ftp_with_disk` | Return FTP accounts and disk usage | RO | [files](modules/files.md#ftp-list-ftp-with-disk) |
| `Ftp::list_sessions` | Return FTP server's active sessions | RO | [files](modules/files.md#ftp-list-sessions) |
| `Ftp::passwd` | Update FTP account's password | RW | [files](modules/files.md#ftp-passwd) |
| `Ftp::server_name` | Return whether server uses ProFTPD or Pure-FTPd | RO | [files](modules/files.md#ftp-server-name) |
| `Ftp::set_anonymous_ftp` | Enable or disable anonymous FTP logins | RW | [files](modules/files.md#ftp-set-anonymous-ftp) |
| `Ftp::set_anonymous_ftp_incoming` | Enable or disable anonymous incoming FTP transfers | RW | [files](modules/files.md#ftp-set-anonymous-ftp-incoming) |
| `Ftp::set_homedir` | Update FTP account's home directory | RW | [files](modules/files.md#ftp-set-homedir) |
| `Ftp::set_quota` | Update FTP account's quota | RW | [files](modules/files.md#ftp-set-quota) |
| `Ftp::set_welcome_message` | Update FTP welcome message | RW | [files](modules/files.md#ftp-set-welcome-message) |
| `GPG::delete_keypair` | Delete GnuPG key pair | RW | [email](modules/email.md#gpg-delete-keypair) |
| `GPG::export_public_key` | Export GnuPG public key | RO | [email](modules/email.md#gpg-export-public-key) |
| `GPG::export_secret_key` | Export GnuPG secret key | RW | [email](modules/email.md#gpg-export-secret-key) |
| `GPG::generate_key` | Create GnuPG key | RW | [email](modules/email.md#gpg-generate-key) |
| `GPG::import_key` | Import GnuPG key | RW | [email](modules/email.md#gpg-import-key) |
| `GPG::list_public_keys` | Return current user's GnuPG public keys | RO | [email](modules/email.md#gpg-list-public-keys) |
| `GPG::list_secret_keys` | Return current user's GnuPG secret keys | RO | [email](modules/email.md#gpg-list-secret-keys) |
| `ImageManager::convert_file` | Create image with new format | RW | [files](modules/files.md#imagemanager-convert-file) |
| `ImageManager::create_thumbnails` | Create image thumbnails | RW | [files](modules/files.md#imagemanager-create-thumbnails) |
| `ImageManager::get_dimensions` | Return image dimensions | RO | [files](modules/files.md#imagemanager-get-dimensions) |
| `ImageManager::resize_image` | Save resized image | RW | [files](modules/files.md#imagemanager-resize-image) |
| `InProductSurvey::get_in_product_survey_url` | Return in-product survey banner data | RW | [inproductsurvey](modules/inproductsurvey.md#inproductsurvey-get-in-product-survey-url) |
| `Integration::fetch_url` | Return integrated application URL | RW | [api-development-tools](modules/api-development-tools.md#integration-fetch-url) |
| `KnownHosts::create` | Create host | RW | [security](modules/security.md#knownhosts-create) |
| `KnownHosts::delete` | Delete host | RW | [security](modules/security.md#knownhosts-delete) |
| `KnownHosts::update` | Update host in the known_hosts file | RW | [security](modules/security.md#knownhosts-update) |
| `KnownHosts::verify` | Validate host | RO | [security](modules/security.md#knownhosts-verify) |
| `LangPHP::php_get_domain_handler` | Return PHP version's handler | RO | [web-server-management](modules/web-server-management.md#langphp-php-get-domain-handler) |
| `LangPHP::php_get_impacted_domains` | Return domains that shared PHP configuration | RO | [web-server-management](modules/web-server-management.md#langphp-php-get-impacted-domains) |
| `LangPHP::php_get_installed_versions` | Return installed PHP versions | RO | [web-server-management](modules/web-server-management.md#langphp-php-get-installed-versions) |
| `LangPHP::php_get_system_default_version` | Return default PHP version | RO | [web-server-management](modules/web-server-management.md#langphp-php-get-system-default-version) |
| `LangPHP::php_get_vhost_versions` | Return virtual host's PHP version | RO | [web-server-management](modules/web-server-management.md#langphp-php-get-vhost-versions) |
| `LangPHP::php_ini_get_user_basic_directives` | Return basic PHP directives | RO | [web-server-management](modules/web-server-management.md#langphp-php-ini-get-user-basic-directives) |
| `LangPHP::php_ini_get_user_content` | Return virtual host's php.ini content | RO | [web-server-management](modules/web-server-management.md#langphp-php-ini-get-user-content) |
| `LangPHP::php_ini_get_user_paths` | Return php.ini file paths | RO | [web-server-management](modules/web-server-management.md#langphp-php-ini-get-user-paths) |
| `LangPHP::php_ini_set_user_basic_directives` | Update basic PHP directives | RW | [web-server-management](modules/web-server-management.md#langphp-php-ini-set-user-basic-directives) |
| `LangPHP::php_ini_set_user_content` | Update virtual host's php.ini content | RW | [web-server-management](modules/web-server-management.md#langphp-php-ini-set-user-content) |
| `LangPHP::php_set_vhost_versions` | Update virtual host's PHP version | RW | [web-server-management](modules/web-server-management.md#langphp-php-set-vhost-versions) |
| `LastLogin::get_last_or_current_logged_in_ip` | Return last authenticated login IP address | RO | [security](modules/security.md#lastlogin-get-last-or-current-logged-in-ip) |
| `Locale::get_attributes` | Return current locale settings | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#locale-get-attributes) |
| `Locale::list_locales` | Return available locales | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#locale-list-locales) |
| `Locale::set_locale` | Update cPanel account locale | RW | [cpanel-theme-management](modules/cpanel-theme-management.md#locale-set-locale) |
| `LogManager::delete_archive` | Delete a log archive file | RW | [website-configuration](modules/website-configuration.md#logmanager-delete-archive) |
| `LogManager::get_settings` | Retrieve cPanel account's log archival settings | RO | [website-configuration](modules/website-configuration.md#logmanager-get-settings) |
| `LogManager::list_archives` | Return cPanel account's archive files list | RO | [website-configuration](modules/website-configuration.md#logmanager-list-archives) |
| `LogManager::list_error_logs` | Return domain's PHP error logs | RO | [website-configuration](modules/website-configuration.md#logmanager-list-error-logs) |
| `LogManager::set_settings` | Save cPanel account's log archive settings | RW | [website-configuration](modules/website-configuration.md#logmanager-set-settings) |
| `LogManager::view_error_log` | Return PHP error log for a domain | RO | [website-configuration](modules/website-configuration.md#logmanager-view-error-log) |
| `Mailboxes::expunge_mailbox_messages` | Delete selected messages in mailbox | RW | [email](modules/email.md#mailboxes-expunge-mailbox-messages) |
| `Mailboxes::expunge_messages_for_mailbox_guid` | Delete selected messages in mailbox by GUID | RW | [email](modules/email.md#mailboxes-expunge-messages-for-mailbox-guid) |
| `Mailboxes::get_mailbox_status_list` | Return cPanel account's mailbox status | RO | [email](modules/email.md#mailboxes-get-mailbox-status-list) |
| `Mailboxes::has_utf8_mailbox_names` | Return if cPanel account's mailboxes use UTF-8 | RO | [email](modules/email.md#mailboxes-has-utf8-mailbox-names) |
| `Mailboxes::set_utf8_mailbox_names` | Enable or disable Webmail mailbox UTF-8 encoding | RW | [email](modules/email.md#mailboxes-set-utf8-mailbox-names) |
| `Market::cancel_pending_ssl_certificate` | Delete an order | RW | [commerce-integration](modules/commerce-integration.md#market-cancel-pending-ssl-certificate) |
| `Market::create_shopping_cart` | Create shopping cart | RW | [commerce-integration](modules/commerce-integration.md#market-create-shopping-cart) |
| `Market::create_shopping_cart_non_ssl` | Create shopping cart for non-SSL products | RW | [commerce-integration](modules/commerce-integration.md#market-create-shopping-cart-non-ssl) |
| `Market::get_all_products` | Return provider's available products | RO | [commerce-integration](modules/commerce-integration.md#market-get-all-products) |
| `Market::get_build_cart_url` | Build cart URL for a product | RW | [commerce-integration](modules/commerce-integration.md#market-get-build-cart-url) |
| `Market::get_certificate_status_details` | Return provider's SSL certificate request status | RO | [commerce-integration](modules/commerce-integration.md#market-get-certificate-status-details) |
| `Market::get_completion_url` | Get product purchase completion URL | RO | [commerce-integration](modules/commerce-integration.md#market-get-completion-url) |
| `Market::get_license_info` | Retrieve license information for a domain | RW | [commerce-integration](modules/commerce-integration.md#market-get-license-info) |
| `Market::get_login_url` | Return provider's login URL | RO | [commerce-integration](modules/commerce-integration.md#market-get-login-url) |
| `Market::get_pending_ssl_certificates` | Return provider's pending SSL certificates | RO | [commerce-integration](modules/commerce-integration.md#market-get-pending-ssl-certificates) |
| `Market::get_product_info` | Retrieve product information | RO | [commerce-integration](modules/commerce-integration.md#market-get-product-info) |
| `Market::get_provider_specific_dcv_constraints` | Return provider's DCV filename requirements | RO | [commerce-integration](modules/commerce-integration.md#market-get-provider-specific-dcv-constraints) |
| `Market::get_providers_list` | Return enabled providers | RO | [commerce-integration](modules/commerce-integration.md#market-get-providers-list) |
| `Market::get_ssl_certificate_if_available` | Return provider's available SSL certificates | RO | [commerce-integration](modules/commerce-integration.md#market-get-ssl-certificate-if-available) |
| `Market::process_ssl_pending_queue` | Start processing pending queue's SSL certificates | RW | [commerce-integration](modules/commerce-integration.md#market-process-ssl-pending-queue) |
| `Market::request_ssl_certificates` | Request SSL certificate order | RW | [commerce-integration](modules/commerce-integration.md#market-request-ssl-certificates) |
| `Market::set_status_of_pending_queue_items` | Update status of items in pending queue | RW | [commerce-integration](modules/commerce-integration.md#market-set-status-of-pending-queue-items) |
| `Market::set_url_after_checkout` | Update URL after checkout | RW | [commerce-integration](modules/commerce-integration.md#market-set-url-after-checkout) |
| `Market::validate_login_token` | Validate login token | RW | [commerce-integration](modules/commerce-integration.md#market-validate-login-token) |
| `Mime::add_handler` | Add web server MIME type handler | RW | [website-configuration](modules/website-configuration.md#mime-add-handler) |
| `Mime::add_hotlink` | Enable hotlink protection | RW | [domain-management](modules/domain-management.md#mime-add-hotlink) |
| `Mime::add_mime` | Add MIME type to web server | RW | [website-configuration](modules/website-configuration.md#mime-add-mime) |
| `Mime::add_redirect` | Add redirect to domain | RW | [domain-management](modules/domain-management.md#mime-add-redirect) |
| `Mime::delete_handler` | Remove web server MIME type handler | RW | [website-configuration](modules/website-configuration.md#mime-delete-handler) |
| `Mime::delete_hotlink` | Disable hotlink protection | RW | [domain-management](modules/domain-management.md#mime-delete-hotlink) |
| `Mime::delete_mime` | Remove MIME type from web server | RW | [website-configuration](modules/website-configuration.md#mime-delete-mime) |
| `Mime::delete_redirect` | Remove redirect from domain | RW | [domain-management](modules/domain-management.md#mime-delete-redirect) |
| `Mime::get_redirect` | Return redirect URL for domain | RO | [domain-management](modules/domain-management.md#mime-get-redirect) |
| `Mime::list_handlers` | Return web server's MIME handlers | RO | [website-configuration](modules/website-configuration.md#mime-list-handlers) |
| `Mime::list_hotlinks` | Return domains with hotlink protection | RO | [domain-management](modules/domain-management.md#mime-list-hotlinks) |
| `Mime::list_mime` | Return web server's MIME types | RO | [website-configuration](modules/website-configuration.md#mime-list-mime) |
| `Mime::list_redirects` | Return .htaccess files' redirects | RO | [domain-management](modules/domain-management.md#mime-list-redirects) |
| `Mime::redirect_info` | Return redirect information | RO | [website-configuration](modules/website-configuration.md#mime-redirect-info) |
| `ModSecurity::disable_all_domains` | Disable ModSecurity for all domains | RW | [web-server-management](modules/web-server-management.md#modsecurity-disable-all-domains) |
| `ModSecurity::disable_domains` | Disable ModSecurity for selected domains | RW | [web-server-management](modules/web-server-management.md#modsecurity-disable-domains) |
| `ModSecurity::enable_all_domains` | Enable ModSecurity for all domains | RW | [web-server-management](modules/web-server-management.md#modsecurity-enable-all-domains) |
| `ModSecurity::enable_domains` | Enable ModSecurity for selected domains | RW | [web-server-management](modules/web-server-management.md#modsecurity-enable-domains) |
| `ModSecurity::has_modsecurity_installed` | Return ModSecurity installation status | RO | [web-server-management](modules/web-server-management.md#modsecurity-has-modsecurity-installed) |
| `ModSecurity::list_domains` | Return ModSecurity domains' status | RO | [web-server-management](modules/web-server-management.md#modsecurity-list-domains) |
| `Mysql::add_host` | Enable remote MySQL host access | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-add-host) |
| `Mysql::add_host_note` | Add remote MySQL host note | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-add-host-note) |
| `Mysql::check_database` | Validate MySQL database integrity | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-check-database) |
| `Mysql::create_database` | Create MySQL database | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-create-database) |
| `Mysql::create_user` | Create MySQL user | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-create-user) |
| `Mysql::delete_database` | Delete MySQL database | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-delete-database) |
| `Mysql::delete_host` | Disable remote MySQL host access | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-delete-host) |
| `Mysql::delete_user` | Delete MySQL user | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-delete-user) |
| `Mysql::dump_database_schema` | Return MySQL database schema | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-dump-database-schema) |
| `Mysql::get_host_notes` | Return remote MySQL host notes | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-get-host-notes) |
| `Mysql::get_privileges_on_database` | Return MySQL user privileges | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-get-privileges-on-database) |
| `Mysql::get_restrictions` | Return MySQL name length restrictions | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-get-restrictions) |
| `Mysql::get_server_information` | Return MySQL server host information and version | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-get-server-information) |
| `Mysql::list_databases` | Return MySQL databases | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-list-databases) |
| `Mysql::list_routines` | Return MySQL user routines | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-list-routines) |
| `Mysql::list_users` | Return MySQL users | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-list-users) |
| `Mysql::locate_server` | Return MySQL server host information | RO | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-locate-server) |
| `Mysql::rename_database` | Update MySQL database name | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-rename-database) |
| `Mysql::rename_user` | Update MySQL username | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-rename-user) |
| `Mysql::repair_database` | Repair MySQL database tables | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-repair-database) |
| `Mysql::revoke_access_to_database` | Remove MySQL user privileges | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-revoke-access-to-database) |
| `Mysql::set_password` | Update MySQL user password | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-set-password) |
| `Mysql::set_privileges_on_database` | Update MySQL user privileges | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-set-privileges-on-database) |
| `Mysql::setup_db_and_user` | Create a randomly named MySQL username/database set. | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-setup-db-and-user) |
| `Mysql::update_privileges` | Update MySQL® privileges | RW | [mysql-and-mariadb](modules/mysql-and-mariadb.md#mysql-update-privileges) |
| `NginxCaching::clear_cache` | Delete NGINX cache contents. | RW | [web-server-management](modules/web-server-management.md#nginxcaching-clear-cache) |
| `NginxCaching::disable_cache` | Disable the user's NGINX cache | RW | [web-server-management](modules/web-server-management.md#nginxcaching-disable-cache) |
| `NginxCaching::enable_cache` | Enable the user's NGINX cache | RW | [web-server-management](modules/web-server-management.md#nginxcaching-enable-cache) |
| `NginxCaching::reset_cache_config` | Reset the user's NGINX cache configuration | RW | [web-server-management](modules/web-server-management.md#nginxcaching-reset-cache-config) |
| `Notifications::get_notifications_count` | Return server notifications total | RO | [server-information](modules/server-information.md#notifications-get-notifications-count) |
| `Nova::account_exists` | Return Nova account status | RO | [website-configuration](modules/website-configuration.md#nova-account-exists) |
| `Nova::add_api_token` | Add an existing AI App Builder API token | ? | [website-configuration](modules/website-configuration.md#nova-add-api-token) |
| `Nova::can_create_domains` | Return domain creation availability | RO | [website-configuration](modules/website-configuration.md#nova-can-create-domains) |
| `Nova::create_account` | Create AI App Builder API key | ? | [website-configuration](modules/website-configuration.md#nova-create-account) |
| `Nova::disk_quota_check` | Return disk quota information | RO | [website-configuration](modules/website-configuration.md#nova-disk-quota-check) |
| `Nova::ensure_account` | Return Nova account SSO URL | ? | [website-configuration](modules/website-configuration.md#nova-ensure-account) |
| `Nova::get_all_user_nova_info` | Return AI App Builder domains | RO | [website-configuration](modules/website-configuration.md#nova-get-all-user-nova-info) |
| `Nova::get_sso_link` | Return AI App Builder SSO URL | ? | [website-configuration](modules/website-configuration.md#nova-get-sso-link) |
| `Nova::get_tier` | Return the user's Nova tier snapshot | RO | [website-configuration](modules/website-configuration.md#nova-get-tier) |
| `Nova::poll_publish` | Return AI App Builder publication process | ? | [website-configuration](modules/website-configuration.md#nova-poll-publish) |
| `Nova::publish` | Run AI App Builder domain publication | ? | [website-configuration](modules/website-configuration.md#nova-publish) |
| `Park::listparkeddomains` | List the parked (aliased) domains | RO | [domain-management](modules/domain-management.md#park-listparkeddomains) |
| `Park::park` | Park an alias domain on an existing domain | RW | [domain-management](modules/domain-management.md#park-park) |
| `Park::unpark` | Remove a parked (aliased) domain | RW | [domain-management](modules/domain-management.md#park-unpark) |
| `Parser::firstfile_relative_uri` | Return session relative URI | RO | [api-development-tools](modules/api-development-tools.md#parser-firstfile-relative-uri) |
| `PassengerApps::disable_application` | Disable Passenger application | RW | [web-server-management](modules/web-server-management.md#passengerapps-disable-application) |
| `PassengerApps::edit_application` | Update Passenger application settings | RW | [web-server-management](modules/web-server-management.md#passengerapps-edit-application) |
| `PassengerApps::enable_application` | Enable Passenger application | RW | [web-server-management](modules/web-server-management.md#passengerapps-enable-application) |
| `PassengerApps::ensure_deps` | Install Passenger application dependencies | RW | [web-server-management](modules/web-server-management.md#passengerapps-ensure-deps) |
| `PassengerApps::list_applications` | Return Passenger applications | RO | [web-server-management](modules/web-server-management.md#passengerapps-list-applications) |
| `PassengerApps::register_application` | Register Passenger application | RW | [web-server-management](modules/web-server-management.md#passengerapps-register-application) |
| `PassengerApps::unregister_application` | Unregister Passenger application | RW | [web-server-management](modules/web-server-management.md#passengerapps-unregister-application) |
| `PasswdStrength::get_required_strength` | Return minimum required password strength | RO | [server-information](modules/server-information.md#passwdstrength-get-required-strength) |
| `Personalization::get` | Retrieve NVData data from file | RO | [cpanel-account](modules/cpanel-account.md#personalization-get) |
| `Personalization::set` | Save NVData data to file | RW | [cpanel-account](modules/cpanel-account.md#personalization-set) |
| `Plugins::can_show_promotions` | Enable plugin promotions | ? | [cpanel-plugin-framework](modules/cpanel-plugin-framework.md#plugins-can-show-promotions) |
| `Plugins::create_user` | Create third-party user | ? | [cpanel-plugin-framework](modules/cpanel-plugin-framework.md#plugins-create-user) |
| `Postgresql::create_database` | Create PostgreSQL database | RW | [postgresql](modules/postgresql.md#postgresql-create-database) |
| `Postgresql::create_user` | Create PostgreSQL user | RW | [postgresql](modules/postgresql.md#postgresql-create-user) |
| `Postgresql::delete_database` | Delete PostgreSQL database | RW | [postgresql](modules/postgresql.md#postgresql-delete-database) |
| `Postgresql::delete_user` | Delete PostgreSQL user | RW | [postgresql](modules/postgresql.md#postgresql-delete-user) |
| `Postgresql::get_restrictions` | Return PostgreSQL name length restrictions | RO | [postgresql](modules/postgresql.md#postgresql-get-restrictions) |
| `Postgresql::grant_all_privileges` | Enable all user privileges on PostgreSQL database | RW | [postgresql](modules/postgresql.md#postgresql-grant-all-privileges) |
| `Postgresql::list_databases` | Return PostgreSQL databases | RO | [postgresql](modules/postgresql.md#postgresql-list-databases) |
| `Postgresql::list_users` | Return PostgreSQL users | RO | [postgresql](modules/postgresql.md#postgresql-list-users) |
| `Postgresql::rename_database` | Update PostgreSQL database name | RW | [postgresql](modules/postgresql.md#postgresql-rename-database) |
| `Postgresql::rename_user` | Update PostgreSQL username | RW | [postgresql](modules/postgresql.md#postgresql-rename-user) |
| `Postgresql::rename_user_no_password` | Update PostgreSQL username without password | RW | [postgresql](modules/postgresql.md#postgresql-rename-user-no-password) |
| `Postgresql::revoke_all_privileges` | Remove PostgreSQL user privileges | RW | [postgresql](modules/postgresql.md#postgresql-revoke-all-privileges) |
| `Postgresql::set_password` | Update PostgreSQL user password | RW | [postgresql](modules/postgresql.md#postgresql-set-password) |
| `Postgresql::update_privileges` | Update PostgreSQL® privileges | RW | [postgresql](modules/postgresql.md#postgresql-update-privileges) |
| `Pushbullet::send_test_message` | Validate Pushbullet token | RW | [notifications](modules/notifications.md#pushbullet-send-test-message) |
| `Quota::get_local_quota_info` | Return local disk quota information | RO | [cpanel-account](modules/cpanel-account.md#quota-get-local-quota-info) |
| `Quota::get_quota_info` | Return disk quota information | RO | [cpanel-account](modules/cpanel-account.md#quota-get-quota-info) |
| `Resellers::list_accounts` | Return reseller's cPanel accounts | RO | [cpanel-account](modules/cpanel-account.md#resellers-list-accounts) |
| `ResourceUsage::get_usages` | Return resource usage and custom statistics | RO | [cpanel-account](modules/cpanel-account.md#resourceusage-get-usages) |
| `Restore::directory_listing` | Return backups in home directory | RO | [cpanel-account-backups](modules/cpanel-account-backups.md#restore-directory-listing) |
| `Restore::get_users` | Return cPanel accounts with backup metadata | RO | [cpanel-account-backups](modules/cpanel-account-backups.md#restore-get-users) |
| `Restore::query_file_info` | Return backup storage locations | RO | [cpanel-account-backups](modules/cpanel-account-backups.md#restore-query-file-info) |
| `Restore::restore_file` | Restore file or directory | RW | [cpanel-account-backups](modules/cpanel-account-backups.md#restore-restore-file) |
| `ServerInformation::get_information` | Return service and device status | RO | [server-information](modules/server-information.md#serverinformation-get-information) |
| `ServiceProxy::get_service_proxy_backends` | Return a cPanel account’s service proxying setup | RO | [serviceproxy](modules/serviceproxy.md#serviceproxy-get-service-proxy-backends) |
| `ServiceProxy::set_service_proxy_backends` | Add cPanel account service proxying | RW | [serviceproxy](modules/serviceproxy.md#serviceproxy-set-service-proxy-backends) |
| `ServiceProxy::unset_all_service_proxy_backends` | Remove cPanel account service proxying | RW | [serviceproxy](modules/serviceproxy.md#serviceproxy-unset-all-service-proxy-backends) |
| `Session::create_temp_user` | Create user session with existing session | RW | [email](modules/email.md#session-create-temp-user) |
| `Session::create_webmail_session_for_mail_user` | Create Webmail session | RW | [email](modules/email.md#session-create-webmail-session-for-mail-user) |
| `Session::create_webmail_session_for_mail_user_check_password` | Create Webmail session with credentials | RW | [email](modules/email.md#session-create-webmail-session-for-mail-user-check-password) |
| `Session::create_webmail_session_for_self` | Create Webmail session for current user | RW | [email](modules/email.md#session-create-webmail-session-for-self) |
| `Sitejet::add_api_token` | Add an existing Sitejet API token. | ? | [website-configuration](modules/website-configuration.md#sitejet-add-api-token) |
| `Sitejet::can_create_domains` | Return Domain Availability | RO | [website-configuration](modules/website-configuration.md#sitejet-can-create-domains) |
| `Sitejet::create_account` | Generate a Sitejet API key. | ? | [website-configuration](modules/website-configuration.md#sitejet-create-account) |
| `Sitejet::create_restore_point` | Create a restore point. | ? | [website-configuration](modules/website-configuration.md#sitejet-create-restore-point) |
| `Sitejet::create_website` | Create Sitejet domain ID | ? | [website-configuration](modules/website-configuration.md#sitejet-create-website) |
| `Sitejet::get_all_user_sitejet_info` | Return Sitejet domains | ? | [website-configuration](modules/website-configuration.md#sitejet-get-all-user-sitejet-info) |
| `Sitejet::get_api_token` | Return Sitejet API token | ? | [website-configuration](modules/website-configuration.md#sitejet-get-api-token) |
| `Sitejet::get_preview_url` | Return Sitejet preview URL | ? | [website-configuration](modules/website-configuration.md#sitejet-get-preview-url) |
| `Sitejet::get_sso_link` | Return Sitejet SSO URL | ? | [website-configuration](modules/website-configuration.md#sitejet-get-sso-link) |
| `Sitejet::get_templates` | Return Sitejet templates **(deprecated)** | ? | [website-configuration](modules/website-configuration.md#sitejet-get-templates) |
| `Sitejet::is_publish_in_progress` | Check whether a Sitejet publish is running | ? | [website-configuration](modules/website-configuration.md#sitejet-is-publish-in-progress) |
| `Sitejet::restore_document_root` | Restore a domain from the restore point. | ? | [website-configuration](modules/website-configuration.md#sitejet-restore-document-root) |
| `Sitejet::set_template` | Update Sitejet template **(deprecated)** | ? | [website-configuration](modules/website-configuration.md#sitejet-set-template) |
| `Sitejet::start_publish` | Publish Sitejet domain | ? | [website-configuration](modules/website-configuration.md#sitejet-start-publish) |
| `SiteQuality::create_project` | Add domain to monitoring | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-create-project) |
| `SiteQuality::create_site_quality_user` | Register cPanel user for monitoring | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-create-site-quality-user) |
| `SiteQuality::delete_site_quality_user` | Delete Site Quality Monitoring account | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-delete-site-quality-user) |
| `SiteQuality::get_all_scores` | Return all projects' monitoring results | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-get-all-scores) |
| `SiteQuality::get_app_token` | Return koality authentication token | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-get-app-token) |
| `SiteQuality::get_monitored_domains` | Return the user's monitored domains. | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-get-monitored-domains) |
| `SiteQuality::get_monitored_system_scores` | Return status for a user's monitored domains. | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-get-monitored-system-scores) |
| `SiteQuality::has_site_quality_user` | Validate monitoring account existence | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-has-site-quality-user) |
| `SiteQuality::is_site_quality_user_enabled` | Validate monitoring account enablement | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-is-site-quality-user-enabled) |
| `SiteQuality::reset_config` | Remove monitoring user from cPanel configuration | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-reset-config) |
| `SiteQuality::send_activation_email` | Request activation email | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-send-activation-email) |
| `SiteQuality::update_domain` | Update domain name in Site Quality Monitoring project | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-update-domain) |
| `SiteQuality::verify_code` | Validate activation code | ? | [site-quality-monitoring](modules/site-quality-monitoring.md#sitequality-verify-code) |
| `SpamAssassin::clear_spam_box` | Delete spam box contents | RW | [email](modules/email.md#spamassassin-clear-spam-box) |
| `SpamAssassin::get_symbolic_test_names` | Return SpamAssassin™ symbolic test scores | RO | [email](modules/email.md#spamassassin-get-symbolic-test-names) |
| `SpamAssassin::get_user_preferences` | Return SpamAssassin™ settings | RO | [email](modules/email.md#spamassassin-get-user-preferences) |
| `SpamAssassin::update_user_preference` | Update SpamAssassin™ settings | RW | [email](modules/email.md#spamassassin-update-user-preference) |
| `SSH::get_port` | Return SSH port | RO | [server-information](modules/server-information.md#ssh-get-port) |
| `SSH::get_shell` | Return whether cPanel account has shell access | RO | [server-information](modules/server-information.md#ssh-get-shell) |
| `SSL::add_autossl_excluded_domains` | Disable AutoSSL for domains | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-add-autossl-excluded-domains) |
| `SSL::can_ssl_redirect` | Return whether domains can redirect to secure URL | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-can-ssl-redirect) |
| `SSL::check_shared_cert` | Return whether shared SSL certificate exists **(deprecated)** | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-check-shared-cert) |
| `SSL::delete_cert` | Delete SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-delete-cert) |
| `SSL::delete_csr` | Delete certificate signing request | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-delete-csr) |
| `SSL::delete_key` | Delete private key | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-delete-key) |
| `SSL::delete_ssl` | Remove SSL for domain | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-delete-ssl) |
| `SSL::disable_mail_sni` | Disable SNI mail services for domain | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-disable-mail-sni) |
| `SSL::enable_mail_sni` | Enable SNI mail services for domain | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-enable-mail-sni) |
| `SSL::fetch_best_for_domain` | Request best SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-fetch-best-for-domain) |
| `SSL::fetch_cert_info` | Return SSL certificate information | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-fetch-cert-info) |
| `SSL::fetch_certificates_for_fqdns` | Return SSL certificate information for all FQDN | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-fetch-certificates-for-fqdns) |
| `SSL::fetch_key_and_cabundle_for_certificate` | Return private key and CA bundle | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-fetch-key-and-cabundle-for-certificate) |
| `SSL::find_certificates_for_key` | Return SSL certificate for private key | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-find-certificates-for-key) |
| `SSL::find_csrs_for_key` | Return private key's certificate signing requests | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-find-csrs-for-key) |
| `SSL::generate_cert` | Create self-signed SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-generate-cert) |
| `SSL::generate_csr` | Create certificate signing request | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-generate-csr) |
| `SSL::generate_key` | Create private key | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-generate-key) |
| `SSL::get_autossl_excluded_domains` | Return AutoSSL disabled domains | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-get-autossl-excluded-domains) |
| `SSL::get_autossl_problems` | Return domains with AutoSSL problems | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-get-autossl-problems) |
| `SSL::get_autossl_renewal_status` | Return AutoSSL renewal status for a domain | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-get-autossl-renewal-status) |
| `SSL::get_cabundle` | Return certificate's CA bundle and hostname | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-get-cabundle) |
| `SSL::get_cn_name` | Request best SSL domain for service | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-get-cn-name) |
| `SSL::install_ssl` | Install SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-install-ssl) |
| `SSL::installed_host` | Return SSL certificate's info for dedicated IP | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-installed-host) |
| `SSL::installed_hosts` | Return domains with SSL certificate information | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-installed-hosts) |
| `SSL::is_autossl_check_in_progress` | Return whether AutoSSL check in progress | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-is-autossl-check-in-progress) |
| `SSL::is_mail_sni_supported` | Return whether mail SNI is enabled | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-is-mail-sni-supported) |
| `SSL::is_sni_supported` | Return whether Apache web server supports mail SNI | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-is-sni-supported) |
| `SSL::list_certs` | Return all SSL certificates | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-list-certs) |
| `SSL::list_csrs` | Return all certificate signing requests | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-list-csrs) |
| `SSL::list_keys` | Return all private keys | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-list-keys) |
| `SSL::list_ssl_items` | Return SSL-related items | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-list-ssl-items) |
| `SSL::mail_sni_status` | Return status of domain's SNI mail services | RO | [ssl-certificates](modules/ssl-certificates.md#ssl-mail-sni-status) |
| `SSL::rebuild_mail_sni_config` | Start SNI configuration files rebuild | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-rebuild-mail-sni-config) |
| `SSL::rebuildssldb` | Start SSL database rebuild | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-rebuildssldb) |
| `SSL::remove_autossl_excluded_domains` | Enable AutoSSL for specifed domains | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-remove-autossl-excluded-domains) |
| `SSL::set_autossl_excluded_domains` | Disable AutoSSL for specifed domains | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-autossl-excluded-domains) |
| `SSL::set_cert_friendly_name` | Update SSL certificate's friendly name | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-cert-friendly-name) |
| `SSL::set_csr_friendly_name` | Update certificate signing request's friendly name | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-csr-friendly-name) |
| `SSL::set_default_key_type` | Update SSL TLS key type | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-default-key-type) |
| `SSL::set_key_friendly_name` | Update private key's friendly name | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-key-friendly-name) |
| `SSL::set_primary_ssl` | Update SSL website for dedicated IP address | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-set-primary-ssl) |
| `SSL::show_cert` | Export SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-show-cert) |
| `SSL::show_csr` | Export certificate signing request | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-show-csr) |
| `SSL::show_key` | Export private key | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-show-key) |
| `SSL::start_autossl_check` | Start AutoSSL for current user | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-start-autossl-check) |
| `SSL::toggle_ssl_redirect_for_domains` | Enable or disable secure redirects | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-toggle-ssl-redirect-for-domains) |
| `SSL::upload_cert` | Import SSL certificate | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-upload-cert) |
| `SSL::upload_key` | Import private key | RW | [ssl-certificates](modules/ssl-certificates.md#ssl-upload-key) |
| `Stats::get_bandwidth` | Return bandwidth statistics for all domains | RO | [statistics](modules/statistics.md#stats-get-bandwidth) |
| `Stats::get_site_errors` | Return specified domain access log | RO | [statistics](modules/statistics.md#stats-get-site-errors) |
| `Stats::get_stats_daily` | Return daily AwStats statistics for a domain | RO | [statistics](modules/statistics.md#stats-get-stats-daily) |
| `Stats::list_sites` | Return Analog statistics for all domains | RO | [statistics](modules/statistics.md#stats-list-sites) |
| `Stats::list_stats_by_domain` | Return Analog statistics for specified domain | RO | [statistics](modules/statistics.md#stats-list-stats-by-domain) |
| `StatsBar::get_stats` | Return cPanel account statistics | RO | [cpanel-account](modules/cpanel-account.md#statsbar-get-stats) |
| `StatsManager::get_configuration` | Returns weblog analyzers' configuration | RO | [statistics](modules/statistics.md#statsmanager-get-configuration) |
| `StatsManager::save_configuration` | Save current user's weblog analyzers configuration | RW | [statistics](modules/statistics.md#statsmanager-save-configuration) |
| `SubDomain::addsubdomain` | Create subdomain | RW | [domain-management](modules/domain-management.md#subdomain-addsubdomain) |
| `SubDomain::changedocroot` | Change a subdomain or addon domain document root | RW | [domains](modules/domains.md#subdomain-changedocroot) |
| `SubDomain::delsubdomain` | Remove a subdomain | RW | [domain-management](modules/domain-management.md#subdomain-delsubdomain) |
| `SubDomain::getreservedsubdomains` | List the reserved subdomain names | RO | [domain-management](modules/domain-management.md#subdomain-getreservedsubdomains) |
| `SubDomain::listsubdomains` | List the subdomains | RO | [domain-management](modules/domain-management.md#subdomain-listsubdomains) |
| `SubDomain::validregex` | Return the subdomain validation pattern | RO | [domain-management](modules/domain-management.md#subdomain-validregex) |
| `Team::add_roles` | Add roles to a team user | RW | [cpanel-account](modules/cpanel-account.md#team-add-roles) |
| `Team::add_team_user` | Add a team user | RW | [cpanel-account](modules/cpanel-account.md#team-add-team-user) |
| `Team::cancel_expire` | Stop a team user from expiring | RW | [cpanel-account](modules/cpanel-account.md#team-cancel-expire) |
| `Team::edit_team_user` | Edit a team user | RW | [cpanel-account](modules/cpanel-account.md#team-edit-team-user) |
| `Team::get_team_users_with_roles_count` | Get number of team users with roles | RO | [cpanel-account](modules/cpanel-account.md#team-get-team-users-with-roles-count) |
| `Team::list_team` | List Team Users | RO | [cpanel-account](modules/cpanel-account.md#team-list-team) |
| `Team::password_reset_request` | Sends a password reset request link to team user. | RW | [cpanel-account](modules/cpanel-account.md#team-password-reset-request) |
| `Team::reinstate_team_user` | Reinstate a team user | RW | [cpanel-account](modules/cpanel-account.md#team-reinstate-team-user) |
| `Team::remove_roles` | Remove roles from a team user | RW | [cpanel-account](modules/cpanel-account.md#team-remove-roles) |
| `Team::remove_team_user` | Remove a team user | RW | [cpanel-account](modules/cpanel-account.md#team-remove-team-user) |
| `Team::set_contact_email` | Set a contact email address for a team user | RW | [cpanel-account](modules/cpanel-account.md#team-set-contact-email) |
| `Team::set_expire` | Set a team user to expire | RW | [cpanel-account](modules/cpanel-account.md#team-set-expire) |
| `Team::set_locale` | Set locale for a team user | RW | [cpanel-account](modules/cpanel-account.md#team-set-locale) |
| `Team::set_notes` | Set notes for a team user | RW | [cpanel-account](modules/cpanel-account.md#team-set-notes) |
| `Team::set_password` | Set password for a team user | RW | [cpanel-account](modules/cpanel-account.md#team-set-password) |
| `Team::set_roles` | Set roles for a team user | RW | [cpanel-account](modules/cpanel-account.md#team-set-roles) |
| `Team::suspend_team_user` | Suspend a team user | RW | [cpanel-account](modules/cpanel-account.md#team-suspend-team-user) |
| `TeamRoles::list_feature_descriptions` | List all role feature descriptions | RO | [cpanel-account](modules/cpanel-account.md#teamroles-list-feature-descriptions) |
| `Themes::get_theme_base` | Return current theme **(deprecated)** | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#themes-get-theme-base) |
| `Themes::list` | Return available themes | RO | [cpanel-theme-management](modules/cpanel-theme-management.md#themes-list) |
| `Themes::update` | Update current theme | RW | [cpanel-theme-management](modules/cpanel-theme-management.md#themes-update) |
| `Tokens::create_full_access` | Create cPanel API token | RW | [api-development-tools](modules/api-development-tools.md#tokens-create-full-access) |
| `Tokens::list` | Return cPanel API tokens | RO | [api-development-tools](modules/api-development-tools.md#tokens-list) |
| `Tokens::rename` | Update cPanel API token's name | RW | [api-development-tools](modules/api-development-tools.md#tokens-rename) |
| `Tokens::revoke` | Remove cPanel API token | RW | [api-development-tools](modules/api-development-tools.md#tokens-revoke) |
| `Trash::remove` | Delete item from Trash | ? | [file-manager](modules/file-manager.md#trash-remove) |
| `Trash::usage` | Report the disk space used by the trash directory | ? | [file-manager](modules/file-manager.md#trash-usage) |
| `TwoFactorAuth::generate_user_configuration` | Create 2FA authentication code | RW | [authentication](modules/authentication.md#twofactorauth-generate-user-configuration) |
| `TwoFactorAuth::get_team_user_configuration` | Return team user 2FA config | RW | [authentication](modules/authentication.md#twofactorauth-get-team-user-configuration) |
| `TwoFactorAuth::get_user_configuration` | Return cPanel account 2FA config | RO | [authentication](modules/authentication.md#twofactorauth-get-user-configuration) |
| `TwoFactorAuth::remove_user_configuration` | Remove 2FA config | RW | [authentication](modules/authentication.md#twofactorauth-remove-user-configuration) |
| `TwoFactorAuth::set_user_configuration` | Save 2FA config | RW | [authentication](modules/authentication.md#twofactorauth-set-user-configuration) |
| `UserData::get_scoped_userdata` | Return scoped userdata mapping | RW | [userdata](modules/userdata.md#userdata-get-scoped-userdata) |
| `UserData::set_scoped_userdata` | Set scoped userdata key/value | RW | [userdata](modules/userdata.md#userdata-set-scoped-userdata) |
| `UserManager::change_password` | Update cPanel account password (User Manager) | RW | [cpanel-account](modules/cpanel-account.md#usermanager-change-password) |
| `UserManager::check_account_conflicts` | Return Subaccounts and service accounts conflicts | RO | [cpanel-account](modules/cpanel-account.md#usermanager-check-account-conflicts) |
| `UserManager::create_user` | Create Subaccount | RW | [cpanel-account](modules/cpanel-account.md#usermanager-create-user) |
| `UserManager::delete_user` | Delete Subaccount | RW | [cpanel-account](modules/cpanel-account.md#usermanager-delete-user) |
| `UserManager::dismiss_merge` | Remove service account link request | RW | [cpanel-account](modules/cpanel-account.md#usermanager-dismiss-merge) |
| `UserManager::edit_user` | Update Subaccount settings | RW | [cpanel-account](modules/cpanel-account.md#usermanager-edit-user) |
| `UserManager::list_users` | Return cPanel account's Subaccounts | RO | [cpanel-account](modules/cpanel-account.md#usermanager-list-users) |
| `UserManager::lookup_service_account` | Return service account's information | RO | [cpanel-account](modules/cpanel-account.md#usermanager-lookup-service-account) |
| `UserManager::lookup_user` | Return Subaccount's information | RO | [cpanel-account](modules/cpanel-account.md#usermanager-lookup-user) |
| `UserManager::merge_service_account` | Register service account to Subaccount | RW | [cpanel-account](modules/cpanel-account.md#usermanager-merge-service-account) |
| `UserManager::unlink_service_account` | Unregister service account from Subaccount | RW | [cpanel-account](modules/cpanel-account.md#usermanager-unlink-service-account) |
| `Users::change_password` | Update cPanel account password | RW | [cpanel-account](modules/cpanel-account.md#users-change-password) |
| `UserTasks::delete` | Remove item from task queue | RW | [api-development-tools](modules/api-development-tools.md#usertasks-delete) |
| `UserTasks::retrieve` | Return task queue information | RO | [api-development-tools](modules/api-development-tools.md#usertasks-retrieve) |
| `Variables::get_server_information` | Return server's configuration settings | RO | [server-information](modules/server-information.md#variables-get-server-information) |
| `Variables::get_session_information` | Return web server's hostname | RO | [security](modules/security.md#variables-get-session-information) |
| `Variables::get_user_information` | Return cPanel account's configuration settings | RO | [cpanel-account](modules/cpanel-account.md#variables-get-user-information) |
| `VersionControl::create` | Create Git repository | RW | [git-management](modules/git-management.md#versioncontrol-create) |
| `VersionControl::delete` | Delete Git repository | RW | [git-management](modules/git-management.md#versioncontrol-delete) |
| `VersionControl::retrieve` | Return Git repositories | RW | [git-management](modules/git-management.md#versioncontrol-retrieve) |
| `VersionControl::update` | Update Git repository settings | RW | [git-management](modules/git-management.md#versioncontrol-update) |
| `VersionControlDeployment::create` | Create Git deployment task | RW | [git-management](modules/git-management.md#versioncontroldeployment-create) |
| `VersionControlDeployment::delete` | Delete Git deployment task | RW | [git-management](modules/git-management.md#versioncontroldeployment-delete) |
| `VersionControlDeployment::retrieve` | Return Git deployment task status | RW | [git-management](modules/git-management.md#versioncontroldeployment-retrieve) |
| `WebApp::configure` | Update an application's configuration. | ? | [web-server-management](modules/web-server-management.md#webapp-configure) |
| `WebApp::delete` | Delete an application. | ? | [web-server-management](modules/web-server-management.md#webapp-delete) |
| `WebApp::deploy` | Deploy an application. | ? | [web-server-management](modules/web-server-management.md#webapp-deploy) |
| `WebApp::fetch_logs` | Fetch an application's runtime or build logs. | ? | [web-server-management](modules/web-server-management.md#webapp-fetch-logs) |
| `WebApp::get_available` | List available application runtimes and limits. | ? | [web-server-management](modules/web-server-management.md#webapp-get-available) |
| `WebApp::has_feature` | Report whether the Web Apps feature is available. | ? | [web-server-management](modules/web-server-management.md#webapp-has-feature) |
| `WebApp::list` | List the account's web applications. | ? | [web-server-management](modules/web-server-management.md#webapp-list) |
| `WebApp::redeploy` | Redeploy an application, pulling source updates first. | ? | [web-server-management](modules/web-server-management.md#webapp-redeploy) |
| `WebApp::redeploy` | Redeploy an application, pulling source updates first. | ? | [web-server-management](modules/web-server-management.md#webapp-redeploy) |
| `WebApp::restart` | Restart an application's server process. | ? | [web-server-management](modules/web-server-management.md#webapp-restart) |
| `WebApp::set_mode` | Set an application's run mode. | ? | [web-server-management](modules/web-server-management.md#webapp-set-mode) |
| `WebApp::stage` | Register a new web application. | ? | [web-server-management](modules/web-server-management.md#webapp-stage) |
| `WebApp::stage` | Register a new web application. | ? | [web-server-management](modules/web-server-management.md#webapp-stage) |
| `WebApp::start` | Start an application's server process. | ? | [web-server-management](modules/web-server-management.md#webapp-start) |
| `WebApp::stop` | Stop an application's server process. | ? | [web-server-management](modules/web-server-management.md#webapp-stop) |
| `WebDisk::delete_user` | Delete Web Disk account | RW | [files](modules/files.md#webdisk-delete-user) |
| `WebDisk::set_homedir` | Update Web Disk home directory location | RW | [files](modules/files.md#webdisk-set-homedir) |
| `WebDisk::set_password` | Update Web Disk account password | RW | [files](modules/files.md#webdisk-set-password) |
| `WebDisk::set_permissions` | Update Web Disk home directory permissions | RW | [files](modules/files.md#webdisk-set-permissions) |
| `WebmailApps::list_webmail_apps` | Return available webmail clients | RO | [email](modules/email.md#webmailapps-list-webmail-apps) |
| `WebProsMCP::get_connection_config` | Get the WebPros MCP connection configuration | ? | [server-information](modules/server-information.md#webprosmcp-get-connection-config) |
| `WebProsMCP::unlink_webpros_account` | Unlink the WebPros Account from this cPanel account | RW | [server-information](modules/server-information.md#webprosmcp-unlink-webpros-account) |
| `WebsiteBackup::create_backup` | Start a backup of a website's files and databases | ? | [website-backups](modules/website-backups.md#websitebackup-create-backup) |
| `WebsiteBackup::delete_backup` | Delete one or more website backups | ? | [website-backups](modules/website-backups.md#websitebackup-delete-backup) |
| `WebsiteBackup::disk_quota_check` | Validate website backup disk quota | ? | [website-backups](modules/website-backups.md#websitebackup-disk-quota-check) |
| `WebsiteBackup::extract_backup` | Start extracting a backup's files to a folder | ? | [website-backups](modules/website-backups.md#websitebackup-extract-backup) |
| `WebsiteBackup::list_backups` | Return website backups | ? | [website-backups](modules/website-backups.md#websitebackup-list-backups) |
| `WebsiteBackup::list_operations` | Return running backup operations | ? | [website-backups](modules/website-backups.md#websitebackup-list-operations) |
| `WebsiteBackup::operation_status` | Return backup operation status | ? | [website-backups](modules/website-backups.md#websitebackup-operation-status) |
| `WebsiteBackup::restore_backup` | Start an in-place restore of a website backup | ? | [website-backups](modules/website-backups.md#websitebackup-restore-backup) |
| `WebVhosts::list_domains` | Return virtual host names for domains | RO | [domain-management](modules/domain-management.md#webvhosts-list-domains) |
| `WebVhosts::list_ssl_capable_domains` | Return domains that allow SSL certificate purchase | RO | [domain-management](modules/domain-management.md#webvhosts-list-ssl-capable-domains) |
| `WordPressBackup::any_running` | Return all WordPress sites' backup status | RO | [optional-applications](modules/optional-applications.md#wordpressbackup-any-running) |
| `WordPressBackup::cancel` | Stop WordPress site backup | RW | [optional-applications](modules/optional-applications.md#wordpressbackup-cancel) |
| `WordPressBackup::cleanup` | Delete WordPress backup temporary files | RW | [optional-applications](modules/optional-applications.md#wordpressbackup-cleanup) |
| `WordPressBackup::get_available_backups` | Return WordPress site backups | RO | [optional-applications](modules/optional-applications.md#wordpressbackup-get-available-backups) |
| `WordPressBackup::is_running` | Return WordPress site backup status | RO | [optional-applications](modules/optional-applications.md#wordpressbackup-is-running) |
| `WordPressBackup::start` | Backup WordPress site | RW | [optional-applications](modules/optional-applications.md#wordpressbackup-start) |
| `WordPressRestore::any_running` | Return WordPress site restore status | RO | [optional-applications](modules/optional-applications.md#wordpressrestore-any-running) |
| `WordPressRestore::cleanup` | Delete restored WordPress site's temporary files | RW | [optional-applications](modules/optional-applications.md#wordpressrestore-cleanup) |
| `WordPressRestore::start` | Restore WordPress site | RW | [optional-applications](modules/optional-applications.md#wordpressrestore-start) |
| `WordPressSite::create` | Install WordPress site | RW | [website-configuration](modules/website-configuration.md#wordpresssite-create) |
| `WordPressSite::retrieve` | Return WordPress site information | RO | [website-configuration](modules/website-configuration.md#wordpresssite-retrieve) |
| `WPX::change_admin_password` | Update WordPress administrator password | ? | [website-configuration](modules/website-configuration.md#wpx-change-admin-password) |
| `WPX::create_nova_for_wordpress_website` | Start a Nova for WordPress walkthrough | ? | [website-configuration](modules/website-configuration.md#wpx-create-nova-for-wordpress-website) |
| `WPX::create_website` | Start a new WordPress installation on a domain | ? | [website-configuration](modules/website-configuration.md#wpx-create-website) |
| `WPX::get_admin_account` | Return WordPress administrator account | ? | [website-configuration](modules/website-configuration.md#wpx-get-admin-account) |
| `WPX::get_credentials` | Return single-use WordPress login URL | ? | [website-configuration](modules/website-configuration.md#wpx-get-credentials) |
| `WPX::get_site_activity` | Return WordPress installation activity | ? | [website-configuration](modules/website-configuration.md#wpx-get-site-activity) |
| `WPX::get_task_progress` | Return WordPress task progress | ? | [website-configuration](modules/website-configuration.md#wpx-get-task-progress) |
| `WPX::get_task_status` | Return background task status | ? | [website-configuration](modules/website-configuration.md#wpx-get-task-status) |
| `WPX::get_website` | Return WordPress installation | ? | [website-configuration](modules/website-configuration.md#wpx-get-website) |
| `WPX::has_reached_quota` | Return WordPress disk quota status | ? | [website-configuration](modules/website-configuration.md#wpx-has-reached-quota) |
| `WPX::import_website` | Import an existing WordPress site | ? | [website-configuration](modules/website-configuration.md#wpx-import-website) |
| `WPX::list_websites` | Return WordPress installations | ? | [website-configuration](modules/website-configuration.md#wpx-list-websites) |
| `WPX::remove_installation` | Delete a WordPress installation permanently | ? | [website-configuration](modules/website-configuration.md#wpx-remove-installation) |
| `WPX::set_language` | Update WordPress installation language | ? | [website-configuration](modules/website-configuration.md#wpx-set-language) |
| `ZoneEdit::resetzone` | Reset a DNS zone to the server defaults | RW | [dns](modules/dns.md#zoneedit-resetzone) |
