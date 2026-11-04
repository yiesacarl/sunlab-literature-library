# Daily Digest maintenance

Site: https://yiesacarl.github.io/sunlab-literature-library/#digest
Repository: yiesacarl/sunlab-literature-library, main/root GitHub Pages.
Daily trigger: 07:00 Asia/Shanghai in the user's Codex desktop chat. Local scheduled execution requires the computer on, online and app running. 07:00 starts research; publishing follows successful validation. No paid model API is configured. No email or group messages are sent.

## Editorial policy
Five topics: spin, control, sense, matter, chem. Never include other.
Prefer eligible, relevant papers first discovered on the issue date or previous six calendar days; choose 3–5 per topic. Only when fewer than three qualify, supplement from ages 7–29 days to reach three. If insufficient, publish the actual number. Never fill a quota with unrelated or previously recommended work.
First discovery is immutable. Rediscovery and metadata changes must not reset it. Publication date is distinct; retain partial precision. The first issue begins tracking on 2026-11-04 and does not infer historical discovery dates. The 60-day publication lookback in discovery only bounds candidate searches, not the 7/30-day discovery policy.
Exclude existing library records by DOI/arXiv identity or exact normalized title. Deduplicate journal/preprint versions when the relationship can be established. Investigate near-identical titles manually; do not merge unrelated work because of similar keywords.

## Each run
1. Read current Shanghai date and remote main head/tree. Fetch the current DIGEST_AUTOMATION.md, scripts, bibliography.json, digest/state.json, digest/manifest.json and all referenced issue files into a clean working directory. The remote is authoritative. Preserve unrelated changes and all historical issues. Local source may be stale.
2. If today's issue exists, verify the live issue and deployment; do not rewrite it or select the same papers again. If a prior commit is waiting for deployment, resume verification. Missed days are not backdated.
3. Run `python3 scripts/digest.py discover --date YYYY-MM-DD --cache <private-run-directory>`. In a source checkout, scripts detect the dist subdirectory; in the published root checkout they use root files. Use a fresh date-scoped cache. Crossref and arXiv are public metadata APIs, not model APIs. Inspect source failures. If all sources fail, preserve the previous issue and report the failure. Public pages can supplement unavailable APIs; keep a dated search/evidence record.
4. Read the retrieved candidates and original publisher/arXiv abstracts (or lawfully accessible article content). Review relevance against the lab bibliography. Collect additional candidate sources if a topic has inadequate matches. Never claim to read full text from a title, search snippet or abstract. No PDF downloads are required. Raw abstracts and logs stay in private local work directories and are not published.
5. Write `reviews.json` in the cache. Each review must reference a discovered id and include approved (boolean), one topic, score (editorial ranking, not a research-quality metric), an original concise English summary (usually 25–55 words), whyRelevant (explicitly editorial), readingBasis, and relatedPapers [{id,reason}] using actual existing library IDs. Set evidenceUrl if a publisher page was read instead of the Crossref-deposited abstract. Approve only records actually checked. For existing unreviewed candidates aged 7–29 days retrieve their evidence before approving. Do not fabricate results or quantitative claims. Remove/reject corrections, retractions, duplicates, generic unrelated quantum/medical/catalysis matches.
6. Run `python3 scripts/test_digest.py`, then `python3 scripts/digest.py build --date YYYY-MM-DD --cache <private-run-directory>` and `python3 scripts/refresh_assets.py`. Build validates windows, identifiers, required provenance, counts and prior recommendations. It refuses to replace an existing issue. If a candidate/metadata relationship needs correction, review before building. Leave historic content unchanged.
7. Verify generated issue counts, dates, related IDs, links and browser rendering. All five sections remain visible even if one has zero papers. If some sources failed, retain the partial-coverage disclosure. Do not present old issues as fresh or a scheduler entry as proof of a successful run.
8. Publish only digest/issues/YYYY-MM-DD.json, merged digest/manifest.json, digest/state.json, digest-data.js and asset-versioned index.html through the connected GitHub tool. Use the latest remote tree and expected-head check. Never force push, replace an entire repository from a stale local folder, alter the AI news repository, or upload private raw evidence/caches/credentials/local paths.
9. Check Pages deployment for the new commit, then fetch/open the actual public issue and verify the date/count. Report success only after deployment and live data match. On failure preserve the old site, keep resumable local progress, and report the actual failing stage. A completed run may have fewer than 15 papers by policy.

## Public files
- digest/state.json: metadata, immutable first discovery dates and reviewed candidate summaries (no full abstracts).
- digest/issues/YYYY-MM-DD.json: immutable daily issue and public source provenance.
- digest/manifest.json: issue directory and latest issue.
- digest-data.js: browser bundle rebuilt from the issue archive.
- digest.js: compact UI, date/topic navigation, provenance and related-paper drawers.

The Daily Digest does not automatically add items to Sunlab Papers, Earlier Work or Sharing Papers. Those collections retain their meaning and counts. All displayed summaries are AI-assisted; related links describe thematic connections, not necessarily citations.

## Authorized historical reconstruction
The user requested a one-off backfill for 2026-10-28 through 2026-11-03. These issues are explicitly marked `mode: historical-backfill` and `selectionDateBasis: publicationDate`. No discovery ledger existed then: their 7/30-day windows therefore use precise source publication dates, while first discovery remains 2026-11-04 and preparation timestamps remain actual. This is an explicit exception for those seven issue dates only; ordinary daily issues retain the discovery-date policy above.

`scripts/backfill_digest.py` validates and builds an authorized historical range from privately cached evidence and human/AI editorial reviews. It refuses to overwrite issues, excludes all original library records and all existing recommendations (including later issues), preserves the latest live issue, and keeps raw abstracts private. Future daily runs must preserve these issues and exclude their papers from repeat recommendations. The existing 2026-11-04 issue is unchanged.
