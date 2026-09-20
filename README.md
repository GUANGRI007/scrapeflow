# ScrapeFlow

A config-driven web scraper. Describe the site in a YAML file, get clean CSV or JSON out.
No code changes needed per site.

Built for the kind of job that shows up constantly in freelance work:
*"here's a site, here are the fields I need, give me a spreadsheet."*

## Why this exists

Most scraping jobs are the same shape: walk a list of pages, pull a fixed set of
fields off each one, write them to a file. Rewriting that loop per client wastes
time and hides bugs. ScrapeFlow puts the site-specific part in a config file and
keeps the crawling, retrying, throttling and exporting in one tested place.
## Install

```bash
pip install -r requirements.txt
```

Python 3.9+.

## Quick start

```bash
python -m scrapeflow examples/books.yaml -o books.csv
```

That config scrapes books.toscrape.com, a sandbox site published specifically for
scraper practice, and writes title, price, availability and rating for every book
across all 50 listing pages.

## Field options

| Key | Meaning |
|---|---|
| `selector` | CSS selector, resolved relative to the row element |
| `attr` | Read this attribute instead of the text (`href`, `src`, `class`, ...) |
| `regex` | Apply to the extracted value and keep capture group 1 |
| `default` | Value to use when the selector matches nothing |
| `required` | If true, a row missing this field is dropped and counted |

Relative URLs pulled from `href` / `src` are resolved against the page they came from.

## CLI

```
python -m scrapeflow CONFIG [-o OUTPUT] [--format csv|json] [--limit N] [--dry-run] [-v]
```

Always start with `--dry-run`. It costs one request and tells you whether your
selectors are right before you hammer a site for ten minutes.

## Behaviour worth knowing

- **Throttling is on by default** (0.5s). The default is deliberately polite.
- **Retries** use exponential backoff and only fire on connection errors and 5xx
  responses. A 404 is a real answer, not a failure to retry.
- **Pagination stops** when the next-link disappears, `max_pages` is hit, or a
  page yields zero rows, whichever comes first.
- **Partial results are kept.** If page 31 of 50 dies, the 30 pages already
  collected are still written, and the exit code is non-zero.
- **Encoding is resolved explicitly**: HTTP header, then HTML meta charset, then
  UTF-8. This avoids the usual mojibake in currency symbols and non-ASCII text.
## Scope and limits

Honest about what this does not do:

- **No JavaScript.** This fetches HTML over HTTP and parses it. Sites that render
  content client-side need a browser engine (Playwright/Selenium); that is a
  different tool and a different price.
- **No login or session handling.** Public pages only.
- **No CAPTCHA handling, no proxy rotation, no anti-bot evasion.** If a site
  actively does not want to be scraped, this tool respects that by failing.

Check the target site's Terms of Service and robots.txt before scraping it.
Being technically able to fetch a page is not the same as being allowed to.

## Tests

```bash
python -m pytest tests/ -v
```

39 tests cover config validation, field extraction (attributes, regex, defaults,
required-field dropping), URL resolution, response decoding and both exporters.
They use local HTML fixtures and hit no network.

## Licence

MIT
