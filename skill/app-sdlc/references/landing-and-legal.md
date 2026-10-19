# Landing site and legal pages

## Site
- Use the `app-landing-seo` skill to build it. The setup that worked:
  - Vite + React, prerendered to static pages.
  - Served by a Cloudflare Worker on a custom domain (`npx wrangler deploy`).
  - One dictionary per locale under `src/i18n/dictionaries/<locale>.ts`, with `/de/…`-style prefixes.
  - Guides per locale, and an SEO check script in the build.
- Store screenshots on the site come from the FrameCraft exports (an import script).
- The store listings point at localized URLs: support, privacy, terms and delete-account.

## Legal pages (the stores reject or flag these when they're wrong)
The privacy policy, terms and delete-account page must cover **every shipped platform**:
- **Sign-in per platform:** Apple (with Hide My Email) and Google (shares the account email). The identifiers stored.
- **Push:** the token stored for notifications, and the providers (Apple Push Notification service, Firebase Cloud Messaging). Notification text never includes private content.
- **Billing:** App Store / Google Play. RevenueCat as processor, and what it receives. No card data.
- **Cancellation per platform:**
  - iPhone: Settings > your name > Subscriptions.
  - Android: Google Play > Payments & subscriptions > Subscriptions.
  - Deleting the account doesn't cancel the subscription.
- **Refunds:** Apple at reportaproblem.apple.com, or Google Play.
- **Requirements:** iOS version + Apple ID; Android version + Google account.
- **The Apple EULA clause** limited to the iPhone app, plus Google Play's terms for Android.
- **Account deletion:** in-app path, email path, what gets deleted for owner vs partner, and backup retention.
- **Processors:** hosting, RevenueCat, Apple, Google. "We don't sell data or use ads/analytics SDKs", only if that's true.

Update the "last updated" date. Then translate the **changed paragraphs** into every locale. In each locale, match the existing register (du/Sie, tu/vous) and use the stores' localized menu names. Fan out by locale group to parallel subagents, each editing only its own files. Give each one the English diff, and have it confirm that type checks pass.

## Verify
- `npm run build` passes, including prerender and the SEO checks.
- After deploying, `curl` the live English privacy page and one translated locale, and grep for the new wording (for example the Google Play cancellation path).
- Sanity check: every locale's legal section has the same count of "Google Play" mentions and `<h3>` headings as English.
