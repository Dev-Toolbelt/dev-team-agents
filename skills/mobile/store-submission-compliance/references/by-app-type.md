# Rules by App Type

Pick every row that matches the app, then check its items on top of `apple.md` and `google-play.md`. An app usually matches several rows.

| App type | Apple | Google Play | Check |
|---|---|---|---|
| **Every app** | 2.1, 2.3, 5.1.1 | User Data, Target API | Privacy policy in the app and the listing; no staging backend; screenshots of this build; age or content rating answered |
| **Account-based** (sign-up or sign-in) | 2.1(a), 4.8, 5.1.1(v) | Account deletion, app access | Demo account in the review notes; in-app deletion that really deletes; privacy-focused login option when a social login is the main one (Apple); web deletion link (Play) |
| **Subscriptions or in-app purchase** | 3.1.1, 3.1.2 | Payments, Subscriptions | Store billing for digital goods; restore control; benefits, billed amount and period shown before purchase; terms and privacy links on the paywall; purchase reachable by the reviewer |
| **User-generated content** (posts, chat, profiles, comments) | 1.2 | User Generated Content | Filtering of objectionable content; report action with a timely response; block abusive users; published contact info; moderation that covers non-consensual intimate imagery, including AI-generated |
| **Generative AI features** | 1.2, 5.1.2 | AI-Generated Content | Users can report or flag offensive output inside the app; safeguards against prohibited output; consent before personal data reaches a third-party AI provider; reviewer can reach the feature without a paid tier or written instructions |
| **Children as audience** | 1.3, 5.1.4 | Families | No third-party analytics or ads in Apple's Kids category; parental gate before links, purchases and outside content; on Play only Families self-certified ad SDKs for ads shown to children or users of unknown age, and a neutral age screen in mixed-audience apps |
| **Health, fitness or medical** | 5.1.3, 1.4.1 | Health apps, Health Connect | Health data never used for ads or stored in iCloud without need; medical claims backed by evidence or regulatory clearance; Health Connect permissions declared for each data type |
| **Finance, banking, crypto, lending** | 3.1.5, 5.1.1(ix) | Financial services | Submitted by the regulated legal entity, not an individual account; licences for the regions offered; crypto exchange or wallet rules for the region |
| **Paid random items** (loot boxes, gacha) | 3.1.1 | Payments, Monetization | Odds of each item type disclosed before purchase |
| **Gambling or betting** | 5.3 | Real-money gambling | Licence for every region offered; geo-restriction; Apple requires the app to be free and use no in-app purchase for credits |
| **VPN or network proxy** | 5.4 | VpnService | Uses the platform VPN API; submitted by an organisation account (Apple); no selling or sharing of traffic data; disclosure in the listing |
| **Thin web wrapper** (Capacitor, Cordova, WebView shell) | 4.2 | Minimum functionality | Native value beyond the website: offline, push, device features, native navigation. Treat as a manual item; it is a reviewer judgement |
| **Location-based** | 5.1.1, 5.1.5 | Location permissions | Foreground location unless a core feature needs background; purpose string names the feature; prominent disclosure before background access on Play |
