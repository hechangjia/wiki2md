# wiki2md Asset Download Resilience Design

Date: 2026-04-10
Status: Approved design

## Context

`wiki2md convert` currently fetches article metadata and HTML successfully, then downloads referenced image assets from `upload.wikimedia.org`.

The current implementation fails the entire conversion when any single asset download returns an HTTP error such as `429 Too Many Requests`.

## Problem

Wikimedia image delivery can rate-limit bots even when the article REST endpoints succeed.

Today that makes the whole export fail even though:

- the article body is already available
- the rate limit may be transient
- only one asset may be affected

There is also a consistency problem: infobox image paths are resolved before the download step, so a future tolerant implementation must avoid writing paths that point to files that were never downloaded.

## Goals

- Retry transient asset download failures automatically
- Respect `Retry-After` when present
- Continue article export when a specific asset still fails after retries
- Record asset download failures as warnings
- Only reference successfully downloaded assets in Markdown, infobox data, and metadata

## Non-Goals

- Do not change article fetch behavior for non-asset endpoints
- Do not add user-facing CLI flags in this change
- Do not redesign asset selection heuristics in this change

## Recommended Approach

1. Change asset downloading from fail-fast to result-based.
2. Retry only transient cases:
   - HTTP `429`
   - HTTP `5xx`
   - transport and timeout errors
3. Use bounded retries with backoff.
4. After retries are exhausted, treat the asset as skipped, not fatal.
5. Build `asset_map` and `image_manifest` from successful downloads only.
6. Append warning strings for skipped assets to conversion metadata.

## Error Handling

- Non-transient errors such as `404` should not be retried.
- Asset-level failures should not prevent writing the bundle.
- Article fetch failures should remain hard failures.

## Testing Strategy

- Asset downloader retries a `429` response and succeeds on a later attempt
- Asset downloader does not retry a non-transient `404`
- Service conversion continues when one asset fails permanently
- Failed infobox assets are omitted from rendered output and manifest
