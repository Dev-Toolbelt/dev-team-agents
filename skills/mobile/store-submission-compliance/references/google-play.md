# Google Play — Signals and Rules

Rules come from the Play Developer Policy Center, the Play Console Help Center and developer.android.com. Policy names are cited so a finding can be matched to a rejection email. Every row is a lead to confirm in the merged manifest and the release build, not a verdict.

## Volatile Facts

Re-read the source when `verified` is more than 60 days old (SKILL.md § Procedure, step 3). Paths under `support.google.com` are `/googleplay/android-developer/answer/<id>`.

| Fact | Value | Source | Verified |
|---|---|---|---|
| Target API level | New apps and updates: API 36 (Android 16) since 2026-08-31 (extension ended 2026-11-01). Wear OS and Android Automotive: API 35. Android TV and XR: API 34 | answer/11926878 | 2026-11-25 |
| Play Billing Library | v7 deadline passed (2026-08-31, extension 2026-11-01); v8 accepted until 2027-08-31; v9 until 2028-08-31 | https://developer.android.com/google/play/billing/deprecation-faq | 2026-11-25 |
| Closed test for new personal accounts | Accounts created after 2023-11-13: 12 or more testers opted in for 14 days in a row before production access | answer/14151465 | 2026-11-25 |
| Android App Bundle | Required for new apps since August 2021; TV apps since 2023-06-30 | answer/9844279 | 2026-11-25 |
| 64-bit | Every 32-bit native ABI shipped needs its 64-bit counterpart | https://developer.android.com/google/play/requirements/64-bit | 2026-11-25 |
| Developer verification | Install protection from 2026-09-30 in Brazil, Indonesia, Singapore and Thailand; global rollout in 2027. Play registers most apps automatically; the rest are registered in Play Console | https://developer.android.com/developer-verification | 2026-11-25 |
| Changes on 2027-01-27 (apps targeting Android 17) | One-time location through the location button; phone-call account verification no longer a permitted use of `READ_CALL_LOG` | answer/9888170 · answer/10208820 | 2026-11-25 |

## Build and Release

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `AND-TARGET-API` | CRITICAL | Target API level | `targetSdk` / `targetSdkVersion` below § Volatile Facts for the form factor | Raise it and test the behaviour changes |
| `AND-AAB` | CRITICAL | App Bundle | Release pipeline uploads an APK for a new app | Build and upload an `.aab`; enrol in Play App Signing |
| `AND-64BIT` | CRITICAL | 64-bit | `abiFilters` or bundled `.so` files with `armeabi-v7a` / `x86` but no `arm64-v8a` / `x86_64` | Build the 64-bit ABIs |
| `AND-DEBUGGABLE` | CRITICAL | Release build | `android:debuggable="true"` or `debuggable true` in the release build type | Remove it |
| `AND-STAGING-BACKEND` | CRITICAL | Minimum functionality | A staging, dev or localhost base URL compiled into the release flavour | Point release at production |
| `AND-BILLING-VERSION` | CRITICAL | Play Billing | `com.android.billingclient:billing` (or a wrapper that pins it) older than § Volatile Facts | Upgrade the library |
| `AND-R8` | MEDIUM | App quality | Release build type without `minifyEnabled` / `isMinifyEnabled` | Enable R8 and test the release build |
| `AND-DYNAMIC-CODE` | HIGH | Device and network abuse | `DexClassLoader`, downloaded `.dex` / `.jar`, or code loaded from outside the APK | Ship code through Play only |

## Permissions

Read the **merged** manifest (`app/build/intermediates/merged_manifests/` or `processReleaseManifest`): SDKs add permissions the source manifest does not show.

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `AND-BACKGROUND-LOCATION` | CRITICAL | Location permissions | `ACCESS_BACKGROUND_LOCATION` | Remove unless a core feature needs it; then prominent disclosure, consent and the Console declaration |
| `AND-SMS-CALLLOG` | CRITICAL | SMS and Call Log | `READ_SMS`, `SEND_SMS`, `RECEIVE_SMS`, `READ_CALL_LOG`, `PROCESS_OUTGOING_CALLS` | Only as the default handler or a listed exception, with the declaration form; use the SMS Retriever / User Consent API for OTP |
| `AND-ALL-FILES` | CRITICAL | All files access | `MANAGE_EXTERNAL_STORAGE` | Use the Storage Access Framework or MediaStore; declare only for a qualifying core use |
| `AND-MEDIA-PERMISSIONS` | HIGH | Photo and video permissions | `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` where a system picker would do | Use a system picker; declare only when it cannot support the core feature |
| `AND-FGS-TYPE` | HIGH | Foreground services | A `<service>` started in the foreground without `android:foregroundServiceType`, or `specialUse` without a subtype | Declare the type in the manifest and in Play Console |
| `AND-QUERY-ALL-PACKAGES` | HIGH | Package visibility | `QUERY_ALL_PACKAGES` | Use `<queries>` for the specific packages |
| `AND-ACCESSIBILITY-SERVICE` | CRITICAL | Accessibility API | An `AccessibilityService` in an app that is not a disability tool, or `isAccessibilityTool="true"` on one that is not | Remove it, or disclose and declare a permitted use |
| `AND-OVERLAY` | HIGH | Device and network abuse | `SYSTEM_ALERT_WINDOW` | Remove unless a core feature needs it |
| `AND-ADVERTISING-ID` | HIGH | Advertising ID | `com.google.android.gms.permission.AD_ID` present (often added by an SDK) with no ads or analytics declared | Remove it with `tools:node="remove"`, or declare the use |

## User Data

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `AND-PRIVACY-POLICY` | CRITICAL | User Data | No privacy-policy link inside the app | Link it in the app and in Play Console; every app needs one |
| `AND-PROMINENT-DISCLOSURE` | CRITICAL | User Data | Sensitive data collected (location in background, contacts, installed apps, SMS) with no in-app disclosure screen before the permission request | Show what is collected and why, then ask for affirmative consent |
| `AND-DATA-SAFETY` | HIGH | Data safety | Analytics, ads, crash, attribution or AI SDKs in the dependencies | Check the Data safety form against every SDK; manual check `privacy_labels_match_runtime` |
| `AND-ACCOUNT-DELETION` | CRITICAL | Account deletion | Sign-up exists with no in-app delete-account path or no web deletion page | Add both, put the web link in Play Console and the Data safety form |
| `AND-BACKUP` | MEDIUM | Security | `android:allowBackup="true"` with tokens or personal data in `SharedPreferences` / databases and no backup rules | Exclude sensitive files or disable backup |

## Payments

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `AND-PLAY-BILLING` | CRITICAL | Payments | Digital content, features or subscriptions unlocked through Stripe, PayPal, Pix or a web checkout without Play Billing | Use Play Billing; physical goods, donations and alternative-billing programmes in eligible countries are the exceptions |
| `AND-SUBSCRIPTION-TERMS` | HIGH | Subscriptions | The offer does not show price, period, renewal and how to cancel | State them before purchase |

## Listing

| ID | Severity | Rule | Signal | Fix |
|---|---|---|---|---|
| `AND-META-MISLEADING` | HIGH | Metadata | The listing claims features the build lacks, or uses other apps' names and icons | Describe only what ships |
| `AND-CONTENT-RATING` | HIGH | Content ratings | No completed content-rating questionnaire | Complete it before release |
| `AND-CLOSED-TEST` | HIGH | Testing requirements | New personal account without the closed test in § Volatile Facts | Manual check `closed_test_done` |
