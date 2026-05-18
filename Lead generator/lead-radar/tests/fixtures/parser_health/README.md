# Parser-health fixtures

Captured live samples per source, used for offline parser regression testing.

## Redaction policy

Before committing a fixture, scan for:
- Email addresses → replace with `[REDACTED-EMAIL]`
- Phone numbers → replace with `[REDACTED-PHONE]`
- Full names of identifiable individuals → replace with `[REDACTED-NAME]`

Public forum titles, body text, and usernames are generally fine to keep.
When in doubt, redact.

## Re-capturing

When a parser test fails because the source's DOM drifted, capture a fresh
fixture from the same URL pattern and re-run the test. See the test docstring
for the URL pattern per source.

URL patterns per source:

| source         | type | URL pattern |
|----------------|------|-------------|
| reddit         | json | https://www.reddit.com/search.json?q=warmtepomp&sort=new&limit=10 |
| reddit_new     | json | https://www.reddit.com/r/DIYNL/new.json?limit=10 |
| tweakers       | html | https://gathering.tweakers.net/forum/find?keywords=warmtepomp |
| bouwinfo       | html | https://www.bouwinfo.be/?s=warmtepomp |
| bouwinfo_forum | html | https://www.bouwinfo.be/categories/technieken/verwarming-en-koeling/warmtepompen |
| klusidee_forum | html | https://www.klusidee.nl/Forum/forum/cv-ketels-gaskachels-en-geisers.33/ |
| ouders_forum   | html | https://www.ouders.nl/forum/huis-tuin-en-keuken |
| google         | json | Synthetic DDG result list — update manually if _parse_results logic changes |
| marktplaats    | html | https://www.marktplaats.nl/q/warmtepomp+installateur/ |
| 2dehands       | html | https://www.2dehands.be/q/aannemer+renovatie+antwerpen/ |

## CI note

Sites with aggressive bot-detection (marktplaats, 2dehands, tweakers) may
return captcha or redirect pages in CI. These tests use pre-captured fixtures
so they remain offline-runnable without live network access. If a fixture
becomes stale, re-capture locally and commit the updated file.
