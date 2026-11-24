# RFC Trail

A browser explorer for the Internet's specifications: search the complete retained RFC Editor metadata index, follow updates and replacements, inspect original draft links, and compare dated index captures.

**Public app:** https://coolcode.ca/rfctrail/

<!-- coolcode:guide -->
Search **9110** for HTTP Semantics, **DNS** for a topic, or an author's name. Select an RFC, then follow **Obsoletes**, **Obsoleted by**, **Updates** and **Updated by**. The timeline is ordered by publication month, not by the date a status changed. Extend the trail to two or three connections to inspect a wider family. RFC status and replacement are separate facts: an obsolete document is not automatically Historic, and not every RFC is a standard. Save trail JSON or export filtered CSV to retain the evidence. A first capture establishes the baseline; later changed index captures enable comparisons.
<!-- /coolcode:guide -->

## What is included

- The official RFC Editor XML index, including all published `rfc-entry` records, rather than a fixed list of example specifications.
- Exact RFC-number search; text search across titles, authors, keywords, working-group acronyms, subseries and original draft names.
- Current-status, stream and publication-year filters; pagination and optional topic presets.
- Directed update/replacement relationships, including inverse fields. Repeated declarations are deduplicated. Missing referenced records remain explicit gaps.
- An interactive direct-relationship diagram and a bounded one-to-three-connection trail with a publication timeline, source details, original draft and official Datatracker history links.
- Dated captures, metadata changes, full search-result CSV and selected-trail JSON.

The bundled first capture contains **9,868 RFC entries**, retrieved **23 November 2026**. These are real source records. Publication dates are reported at month precision; the source includes a February 1968 date for RFC 31, which is retained without editorial correction. This metadata index is not the full RFC text, a complete citation graph, or a mirror of every Internet-Draft revision.

## Sources and use

- [RFC Editor XML index](https://www.rfc-editor.org/rfc-index.xml) is the authoritative source for the metadata and relations used here.
- [IETF open records](https://www.ietf.org/about/open-records/) documents public data access.
- [IETF RFC overview](https://www.ietf.org/process/rfcs/) explains statuses, publication streams, updates and obsolescence.
- [Datatracker API documentation](https://datatracker.ietf.org/api/) confirms public read-only access and a simplified document API without a key. This app links to Datatracker records; it does not request each one per visitor.
- [IETF Trust legal provisions](https://trustee.ietf.org/documents/trust-legal-provisions/) apply to source material. RFC titles and metadata are attributed to RFC Editor / IETF. This is an independent, unaffiliated explorer; source documents remain authoritative.

The official index returned `Access-Control-Allow-Origin: *` during source verification, but this app uses a retained compact copy rather than downloading the full XML for every visitor. No registration or API key is required. Searches and exports run locally. Only first-party app/data files are loaded; opening an official link contacts its publisher. Inputs are not stored in local storage.

## Expand or customize

Edit [`web/config.json`](web/config.json). The full index is already searchable; presets only provide starting points. For example, append this to `presets`:

```json
{"label":"IPv6", "query":"IPv6", "rfc":8200}
```

`defaultRfc` selects the initial document. `pageSize` controls result pagination (1–100). `maximumTrailNodes` bounds graph exploration (1–300; default 80). These are performance limits, not coverage limits. `retainedCaptures` controls retained changed index editions (1–52; default 8). `minimumRecords`, `maximumRecords`, `maximumSourceBytes` and `maximumDropFraction` protect against truncated or malformed source responses. The current producer deliberately accepts only the documented official `sourceUrl`; a new source needs an explicit parser/validation change.

A normal push rebuilds the bundled data offline. To collect new metadata after changing collection settings, run **RFC Trail · Capture, check and publish → Run workflow**, leaving **Refresh the official index** checked. The same workflow refreshes on Mondays at **11:47 UTC**. It makes one bounded source request, validates the full index, then stages the result atomically. Failed requests or validation preserve the previous good data. Unchanged XML updates `checkedAt` without creating a redundant capture; changed XML creates a new compressed capture. GitHub schedules can be delayed.

Local refresh and verification:

```sh
python3 scripts/refresh.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

For reproducible parser work, `python3 scripts/refresh.py --source-file /path/to/rfc-index.xml` processes a saved official download. The resulting timestamp records the import time; the XML source digest identifies the exact bytes. `web/data/status.json` exposes checked time, capture time, record count, latest publication month and retained capture count. There is no claimed publication timestamp for the index itself because the response does not supply one.

## Development

Source lives in `web/`; the build copies it to `dist/` and adds shared CoolCode reporting links. Only the generated site is deployed, with relative assets at `/rfctrail/`. No CNAME is needed. Tests cover RFC identity validation, source namespaces, unknown fields, historical date precision, relationship direction, inverse deduplication, cycles, missing records, bounded traversal, filtered exports, expanding coverage and failed-refresh preservation. Browser CI checks the actual bundled dataset, an RFC outside the presets, relation navigation, CSV/JSON downloads and mobile overflow.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
