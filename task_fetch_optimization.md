# Optimize Metadata Fetching for Large Batches

## Problem
Fetching metadata for 50–100 videos is extremely slow and blocks the UI
during cover downloads. Wikipedia makes 4–12 HTTP requests per video,
all sequential, with no rate limiting.

## Changes

### 1. Move cover downloads to background thread
- `_apply_fetched_metadata` calls `download_cover()` on the main thread
- Instead: store the cover URL in results and download covers in the
  `BatchWorker` thread, or batch-download after all fetches complete

### 2. Defer UI updates to end of batch
- Currently `_apply_fetched_metadata` is called per-item via signal,
  triggering `_rebuild_video_map()` and `rename_item()` each time
- Collect all results in a list, apply metadata once, rebuild map once

### 3. Add small delay between API requests
- Insert `time.sleep(0.5–1)` between requests to avoid rate limiting
- Prevents 429 errors from Wikipedia/Wikidata/TMDB APIs

### 4. Improve cancellation responsiveness
- Python `urllib.request.urlopen` blocks even when `_cancelled` is set
- Consider using `QNetworkAccessManager` (async) or socket-level timeout
  for true mid-request cancellation
- At minimum, check `_cancelled` between each sub-request in Wikipedia

### Files to modify
- `src/fetch_dialog.py` — BatchWorker: add delay, collect raw results
- `src/window.py` — `_fetch_metadata` / `_apply_fetched_metadata`:
  defer UI updates, batch cover downloads
- `src/metadata_fetcher.py` — `download_cover`: make it safe for
  background-thread use (it already is, just needs to be called there)
