# Reader platform setup (M9)

The pen name gets a website and a mailing list. Readers of one book then hear about the next
without relying on Amazon. The factory builds the pages, the free bonus story and a launch email
for each book. You own the accounts and send every email yourself.

## What the factory does

| Part | Command or step | Output |
|---|---|---|
| Free bonus story | Runs automatically after book 1's summary (`reader.magnet: true`) | `series/<id>/magnet/bonus.md` and `bonus.epub` |
| Back-matter sign-up | Added to every book once `reader.signup_url` is set | "Free bonus story" page with your link |
| Launch email | Written at packaging; the Amazon link is filled in by `factory published` | `review/<id>/launch-email-ready.md` |
| Website | `factory site` | `site/dist/` (books by series, Kindle links, bonus page, about page) |

## Your steps

1. **Domain.** `maravellacourt.com` showed as available on GoDaddy on 19 Oct 2026, at ₹1 for the
   first year on a 3-year term.
   - Check the renewal price before paying.
   - Decline the .info/.net/.shop bundle.
   - Make sure **domain privacy** is on, so WHOIS doesn't show your name or address.
   - Clear the pen name on Amazon and Goodreads first (`pen-name-check` skill), so you don't buy
     a domain for a name you then drop.
2. **Newsletter provider.** Pick one with a free tier that can deliver a file on sign-up.
   - Kit (formerly ConvertKit) is a good fit. Its free plan includes landing pages and an
     "incentive email" that sends a download. Check the subscriber limit when you sign up.
   - Create a sign-up form for "Free bonus story", attach `bonus.epub` as the incentive, and
     copy the form's public URL.
   - Set the sender to an address on the domain, e.g. `hello@maravellacourt.com`. The provider
     walks you through the DNS records (SPF/DKIM) to add at GoDaddy.
3. **Postal address.** Marketing-email law requires a physical postal address in every email.
   Use a virtual mailbox or PO box, never your home address. Enter it in the provider's settings.
4. **Tell the factory.** In `config.yaml`, set:
   - `reader.signup_url`: the form URL
   - `reader.site_url`: `https://maravellacourt.com`
5. **Website.** Run `factory site`, then deploy:
   - `npm i -g vercel`, then `vercel deploy site/dist --prod`. The first time, it asks you to
     create a project.
   - In Vercel, under Project → Domains, add `maravellacourt.com`.
   - At GoDaddy, point DNS to Vercel: an A record for `@` to `76.76.21.21` and a CNAME for
     `www` to `cname.vercel-dns.com`. Use the values Vercel shows if they differ.
6. **After each book goes live:** run `factory published <id> --asin <ASIN>`, then
   `factory site` and redeploy. Paste `review/<id>/launch-email-ready.md` into the provider,
   check it, and send it.

## Done when (PRD section 12)

- The domain resolves and WHOIS shows a privacy service.
- Lighthouse score 90+, and every book page links to Amazon.
- A test sign-up receives the welcome email with the bonus EPUB.
- Every package has the sign-up page in its back matter.
- The email footer shows a non-home postal address.
