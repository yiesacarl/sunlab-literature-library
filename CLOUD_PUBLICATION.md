# Cloud daily publication: bounded data transport

This supersedes older instructions that upload `digest/state.json` and a complete `digest-data.js` bundle. Read this file before each run. No extra model API or personal computer is required. Only yiesacarl/sunlab-literature-library main is authorized.

## Working data
Download a clean current main checkout into the private cloud execution environment. Fetch large files directly to disk with network-capable Python or shell; do not return their bodies to the chat. Read scripts and instructions; inspect JSON with targeted summaries. All `digest/state-deltas` files must be present. `scripts.state_store.load(root)` reconstructs the current ledger and validates byte counts, SHA256 hashes, per-record prior hashes and source history. `discover` already uses this loader. The base ledger alone is intentionally an old snapshot.

Run normal discovery and evidence-based reviews with all five editorial categories and existing discovery-window rules. Preserve earliest discovery dates, all identity aliases, all history and private-evidence restrictions. Build with current scripts; `build` now writes only changed metadata as compressed, hashed, public delta parts (each at most 24,000 bytes), preserving the 8 MB base ledger. These compressed parts contain PUBLIC METADATA only, not source abstracts. Compression does not grant permission to publish private content. Raw evidence stays in the private cache.

`build` also writes the new issue and merged manifest, preserving historical mode flags. The stable browser loader fetches issue JSON directly. Do not replace it with a full archive bundle. Run all unit tests and `scripts/refresh_assets.py`. Independently verify links, related IDs and actual reading evidence. Selection and factual review are not replaced by transport tests.

## Inventory and upload
Run `python3 scripts/cloud_publication.py --date YYYY-MM-DD`. It prints only the allowed daily file list, byte sizes, SHA256, Git blob SHA1, and number of 12,000-byte chunks. Retain this small inventory in the cloud workspace. Compare generated files with the clean checkout; no library, old issues, base state, UI or unrelated repository files may change in a daily run.

For each allowed file, obtain a chunk with:
`python3 scripts/cloud_publication.py --date YYYY-MM-DD --path PATH --chunk N`
Each result is small JSON containing base64 and the exact byte count. Use tool orchestration to capture command results into program variables, parse and concatenate the base64 strings (all non-final chunks are a multiple of three bytes). Do NOT print chunk contents, full files, full tool results or base64 into the model conversation. Do not hand-copy or regenerate file bodies. Tool output truncation, mismatched lengths or missing chunks are hard failures; retry the bounded chunk, never upload partial content. Preserve a private path-to-blob-SHA progress file to resume without reuploading completed files.

Call the connected GitHub create_blob tool with encoding=base64 and the assembled contents from program memory. Check the returned SHA equals inventory gitBlobSha before continuing. A mismatch means the data did not arrive intact; do not create a commit. Keep outputs to path, byte count and verified SHA. If programmatic transfer is unavailable, stop with that exact limitation rather than copying megabytes through the conversation or requesting credentials.

After all blobs are verified, read current remote main. It must equal the checkout head. If different, refresh and rebuild against the new head; do not merely replace the expected head. Create a tree based on that head's tree with only the inventory paths, create a child commit, and update main with expected_sha and force=false. Publish all parts and their descriptor atomically in that one commit, never a partially assembled ledger.

## Verification and recovery
Wait for the Pages run for the actual new commit. Fetch the live manifest and new issue and compare their bytes or SHA256 with the cloud files. Check live issue date, per-topic counts and total. Open/fetch the page and confirm the loader and archive paths are available. Only then report success. If committed but not deployed, report that distinction and resume verification next time. Repeated runs finding the date already published verify it and stop. Missed days are not backdated. Record actual execution date.

Run each scheduled invocation in a new cloud chat, using these repository files as durable context. Keep a failed run's small checkpoint with the run, not in the public repository. Never use the same growing chat as an unbounded daily job log. Do not turn on or replace a paused schedule until the current recovery has passed an independent cloud end-to-end production test.
