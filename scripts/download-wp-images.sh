#!/usr/bin/env bash
# =============================================================================
# download-wp-images.sh — Download ONLY original images from WordPress
# =============================================================================
# This script uses the WordPress REST API to enumerate every media item,
# extracts only the full-size (original) source URL, and downloads it into
# static/images/ with a flat structure (no YYYY/MM subdirectories).
#
# WordPress generates 15-25+ resized/cropped versions per upload. We skip
# all of those and grab only the originals — the `source_url` field on the
# top-level media object, which always points to the full-size file.
#
# Usage:
#   chmod +x scripts/download-wp-images.sh
#   ./scripts/download-wp-images.sh
#
# Options:
#   --dry-run     List URLs without downloading
#   --keep-dirs   Preserve YYYY/MM directory structure (default: flat)
#   --limit N     Download only the first N images (for testing)
#
# Requirements: curl, jq
# =============================================================================

set -euo pipefail

# --- Configuration ---
WP_SITE="https://tateeskew.com"
API_BASE="${WP_SITE}/wp-json/wp/v2/media"
PER_PAGE=100
OUTPUT_DIR="static/images"
DRY_RUN=false
KEEP_DIRS=false
LIMIT=0
TOTAL_DOWNLOADED=0
TOTAL_SKIPPED=0
TOTAL_FAILED=0

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)    DRY_RUN=true;   shift ;;
    --keep-dirs)  KEEP_DIRS=true; shift ;;
    --limit)      LIMIT="$2";     shift 2 ;;
    *)            echo "Unknown option: $1"; exit 1 ;;
  esac
done

# --- Preflight checks ---
for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "❌ Required tool '$cmd' not found. Install it first."
    exit 1
  fi
done

# --- Find project root (directory containing hugo.toml) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PROJECT_ROOT/hugo.toml" ]]; then
  echo "❌ Cannot find hugo.toml. Run this from the project root or scripts/ dir."
  exit 1
fi

DEST="$PROJECT_ROOT/$OUTPUT_DIR"
mkdir -p "$DEST"

echo "═══════════════════════════════════════════════════════════"
echo "  WordPress → Hugo Image Migration"
echo "  Source:  $WP_SITE"
echo "  Output:  $DEST"
echo "  Mode:    $(if $DRY_RUN; then echo 'DRY RUN (no downloads)'; else echo 'DOWNLOAD'; fi)"
echo "  Layout:  $(if $KEEP_DIRS; then echo 'YYYY/MM subdirectories'; else echo 'Flat (all in images/)'; fi)"
if [[ $LIMIT -gt 0 ]]; then
echo "  Limit:   $LIMIT images"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""

# --- Step 1: Discover total media count ---
echo "🔍 Querying WordPress media library..."
HEADERS=$(curl -sI "${API_BASE}?per_page=${PER_PAGE}" 2>/dev/null)
TOTAL=$(echo "$HEADERS" | grep -i "x-wp-total:" | tr -d '\r' | awk '{print $2}')
TOTAL_PAGES=$(echo "$HEADERS" | grep -i "x-wp-totalpages:" | tr -d '\r' | awk '{print $2}')

if [[ -z "$TOTAL" || "$TOTAL" == "0" ]]; then
  echo "❌ Could not determine media count. Check if REST API is accessible."
  exit 1
fi

echo "📦 Found $TOTAL media items across $TOTAL_PAGES pages"
echo ""

# --- Step 2: Paginate through API and download originals ---
PAGE=1
COUNT=0

while [[ $PAGE -le $TOTAL_PAGES ]]; do
  echo "── Page $PAGE of $TOTAL_PAGES ──"

  # Fetch page of media items (only the fields we need)
  RESPONSE=$(curl -s "${API_BASE}?per_page=${PER_PAGE}&page=${PAGE}&_fields=id,source_url,title,mime_type")

  # Extract each media item
  ITEMS=$(echo "$RESPONSE" | jq -c '.[]')

  while IFS= read -r item; do
    # Stop if we hit the limit
    if [[ $LIMIT -gt 0 && $COUNT -ge $LIMIT ]]; then
      echo ""
      echo "🛑 Reached limit of $LIMIT images"
      break 2
    fi

    # Get the original source URL (this is always the full-size image)
    SOURCE_URL=$(echo "$item" | jq -r '.source_url')
    MIME_TYPE=$(echo "$item" | jq -r '.mime_type // "unknown"')
    TITLE=$(echo "$item" | jq -r '.title.rendered // "untitled"')

    # Skip non-image media (PDFs, videos, etc.)
    if [[ ! "$MIME_TYPE" =~ ^image/ ]]; then
      echo "  ⏭  Skipping non-image: $TITLE ($MIME_TYPE)"
      TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
      continue
    fi

    # Determine destination filename
    FILENAME=$(basename "$SOURCE_URL")

    if $KEEP_DIRS; then
      # Preserve the YYYY/MM structure from the URL path
      URL_PATH=$(echo "$SOURCE_URL" | grep -oP 'uploads/\K[0-9]+/[0-9]+' || true)
      if [[ -n "$URL_PATH" ]]; then
        DEST_FILE="$DEST/$URL_PATH/$FILENAME"
        mkdir -p "$DEST/$URL_PATH"
      else
        DEST_FILE="$DEST/$FILENAME"
      fi
    else
      # Flat structure
      DEST_FILE="$DEST/$FILENAME"
    fi

    # Check if already downloaded
    if [[ -f "$DEST_FILE" ]]; then
      echo "  ✓  Already exists: $FILENAME"
      TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
      COUNT=$((COUNT + 1))
      continue
    fi

    if $DRY_RUN; then
      echo "  📋 Would download: $SOURCE_URL"
      echo "     → $DEST_FILE"
    else
      # Download with progress indicator
      echo -n "  ⬇  $FILENAME ... "
      HTTP_CODE=$(curl -s -o "$DEST_FILE" -w "%{http_code}" "$SOURCE_URL")

      if [[ "$HTTP_CODE" == "200" ]]; then
        SIZE=$(du -h "$DEST_FILE" | cut -f1)
        echo "✅ ($SIZE)"
        TOTAL_DOWNLOADED=$((TOTAL_DOWNLOADED + 1))
      else
        echo "❌ HTTP $HTTP_CODE"
        rm -f "$DEST_FILE"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
      fi
    fi

    COUNT=$((COUNT + 1))

  done <<< "$ITEMS"

  PAGE=$((PAGE + 1))
done

# --- Summary ---
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Migration Complete"
echo "  Downloaded: $TOTAL_DOWNLOADED"
echo "  Skipped:    $TOTAL_SKIPPED (already existed or non-image)"
echo "  Failed:     $TOTAL_FAILED"
if ! $DRY_RUN; then
  TOTAL_SIZE=$(du -sh "$DEST" 2>/dev/null | cut -f1)
  echo "  Total size: $TOTAL_SIZE"
fi
echo "═══════════════════════════════════════════════════════════"

# --- Step 3: Generate URL rewrite map ---
if ! $DRY_RUN; then
  MAPFILE="$PROJECT_ROOT/scripts/image-url-map.txt"
  echo ""
  echo "📝 Generating URL rewrite map → $MAPFILE"
  echo "# WordPress URL → Hugo path" > "$MAPFILE"
  echo "# Use this to find-and-replace image URLs in your migrated Markdown" >> "$MAPFILE"
  echo "#" >> "$MAPFILE"
  echo "# OLD (WordPress):  /wp-content/uploads/2025/03/photo.jpg" >> "$MAPFILE"
  echo "# NEW (Hugo):       /images/photo.jpg" >> "$MAPFILE"
  echo "#" >> "$MAPFILE"

  find "$DEST" -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' -o -name '*.gif' -o -name '*.webp' -o -name '*.svg' \) | sort | while read -r f; do
    BASENAME=$(basename "$f")
    if $KEEP_DIRS; then
      REL_PATH="${f#$DEST/}"
      echo "/images/$REL_PATH" >> "$MAPFILE"
    else
      echo "/images/$BASENAME" >> "$MAPFILE"
    fi
  done

  echo "   Done. $(wc -l < "$MAPFILE") entries."

  echo ""
  echo "💡 Next step: After migrating your Markdown content, run this to fix image paths:"
  echo ""
  echo "   # In your content directory, replace WP upload paths with Hugo paths:"
  echo "   find content/ -name '*.md' -exec sed -i 's|/wp-content/uploads/[0-9]*/[0-9]*/||g' {} +"
  echo "   find content/ -name '*.md' -exec sed -i 's|https://www.tateeskew.com/wp-content/uploads/[0-9]*/[0-9]*/|/images/|g' {} +"
  echo "   find content/ -name '*.md' -exec sed -i 's|https://tateeskew.com/wp-content/uploads/[0-9]*/[0-9]*/|/images/|g' {} +"
  echo ""
  echo "   This strips the YYYY/MM directories and rewrites absolute URLs to /images/filename"
fi
