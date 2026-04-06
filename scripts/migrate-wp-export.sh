#!/usr/bin/env bash
# =============================================================================
# migrate-wp-export.sh — Import wordpress-to-hugo-exporter data into Hugo site
# =============================================================================
# This script takes the unzipped export from wordpress-to-hugo-exporter and:
#   1. Copies blog posts → content/weblog/
#   2. Copies static pages → appropriate content sections
#   3. Cleans up WordPress theme cruft from front matter
#   4. Rewrites image URLs to point to /images/ (flat structure)
#   5. Strips resized image suffixes (-300x300, -1024x1024, etc.)
#
# Usage:
#   ./scripts/migrate-wp-export.sh [--dry-run]
# =============================================================================

set -euo pipefail

EXPORT_DIR="/home/teskew/sourcecode/infra-system-tools/tateeskew.com/_wp-export/wp-hugo-7e4e0e666cb8fe2ae98f2660947444a8"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTENT_DIR="$PROJECT_ROOT/content"
DRY_RUN=false

[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

echo "═══════════════════════════════════════════════════════════"
echo "  WordPress → Hugo Content Migration"
echo "  Export:  $EXPORT_DIR"
echo "  Target:  $CONTENT_DIR"
echo "  Mode:    $(if $DRY_RUN; then echo 'DRY RUN'; else echo 'MIGRATE'; fi)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────────────────────
# Step 1: Copy blog posts → content/weblog/
# ─────────────────────────────────────────────────────────────
echo "📝 Step 1: Migrating blog posts..."
POST_COUNT=0
mkdir -p "$CONTENT_DIR/weblog"

for f in "$EXPORT_DIR"/posts/*.md; do
  BASENAME=$(basename "$f")

  # Skip if we already have a manually written version
  if [[ -f "$CONTENT_DIR/weblog/$BASENAME" ]]; then
    echo "  ⏭  Skipping (manual version exists): $BASENAME"
    continue
  fi

  if $DRY_RUN; then
    echo "  📋 Would copy: posts/$BASENAME → content/weblog/$BASENAME"
  else
    cp "$f" "$CONTENT_DIR/weblog/$BASENAME"
    echo "  ✅ $BASENAME"
  fi
  POST_COUNT=$((POST_COUNT + 1))
done
echo "   → $POST_COUNT posts"
echo ""

# ─────────────────────────────────────────────────────────────
# Step 2: Copy static pages → content sections
# ─────────────────────────────────────────────────────────────
echo "📄 Step 2: Migrating pages..."

# Map of WP export directories → Hugo content directories
# Format: "export_dir:hugo_dir:should_be_index"
# Pages that map to existing sections use _index.md
# Pages that become standalone sections get their own directory
declare -a PAGE_MAP=(
  "about:about:_index.md"
  "audio:audio:_index.md"
  "zero-art-studio:studio:_index.md"
  "press-kit:press-kit:_index.md"
  "using-tates-music-faq:music-faq:_index.md"
  "video:video:_index.md"
  "daniels-artwork:daniels-artwork:_index.md"
  "zero-art-project:zero-art-project:_index.md"
  "weekly-song-experiment:weekly-song-experiment:_index.md"
)

# Pages to SKIP (not needed in Hugo, handled by theme or obsolete)
# - events: we use data/events.yaml instead
# - mailing-list: obsolete
# - read-tates-weblog: just a redirect to /weblog
# - social: links handled in footer/about
# - tate: duplicate of about
# - weblog: handled by Hugo list template

PAGE_COUNT=0
for mapping in "${PAGE_MAP[@]}"; do
  IFS=':' read -r SRC_DIR DEST_DIR DEST_FILE <<< "$mapping"

  SRC_FILE="$EXPORT_DIR/$SRC_DIR/index.md"
  if [[ ! -f "$SRC_FILE" ]]; then
    echo "  ⏭  Source not found: $SRC_DIR/index.md"
    continue
  fi

  DEST_PATH="$CONTENT_DIR/$DEST_DIR"

  # Skip if we already have a manually written version
  if [[ -f "$DEST_PATH/$DEST_FILE" ]]; then
    # But only skip about, audio, studio — we wrote those by hand
    if [[ "$DEST_DIR" == "about" || "$DEST_DIR" == "audio" || "$DEST_DIR" == "studio" ]]; then
      echo "  ⏭  Skipping (manual version exists): $DEST_DIR/$DEST_FILE"
      continue
    fi
  fi

  if $DRY_RUN; then
    echo "  📋 Would copy: $SRC_DIR/index.md → content/$DEST_DIR/$DEST_FILE"
  else
    mkdir -p "$DEST_PATH"
    cp "$SRC_FILE" "$DEST_PATH/$DEST_FILE"
    echo "  ✅ $SRC_DIR → content/$DEST_DIR/$DEST_FILE"
  fi
  PAGE_COUNT=$((PAGE_COUNT + 1))
done
echo "   → $PAGE_COUNT pages"
echo ""

# ─────────────────────────────────────────────────────────────
# Step 3: Clean up WordPress front matter cruft
# ─────────────────────────────────────────────────────────────
if ! $DRY_RUN; then
  echo "🧹 Step 3: Cleaning front matter..."

  # List of WordPress/Brooklyn theme-specific front matter keys to remove
  WP_CRUFT_KEYS=(
    "ut_section_header_style"
    "ut_section_header_font_style"
    "ut_display_section_header"
    "ut_section_width"
    "ut_split_content_align"
    "ut_section_shadow"
    "ut_section_skin"
    "ut_parallax_section"
    "ut_parallax_image"
    "ut_overlay_section"
    "ut_overlay_pattern"
    "ut_overlay_pattern_style"
    "ut_custom_section_class"
    "ut_custom_content_class"
    "ut_section_effect"
    "ut_section_effect_color"
    "ut_navigation_skin"
    "ut_header_custom_slogan"
    "ut_section_video"
    "ut_section_video_mp4"
    "ut_section_video_ogg"
    "ut_section_video_webm"
    "ut_section_video_poster"
    "dsq_thread_id"
    "slide_template"
    "pyre_"
    "sbg_selected_sidebar"
    "et_enqueued_post_fonts"
  )

  # Build a sed script to remove all cruft lines from front matter
  # These are YAML key-value pairs and their continuation lines
  CLEAN_COUNT=0
  find "$CONTENT_DIR" -name '*.md' -newer "$EXPORT_DIR/config.yaml" | while read -r mdfile; do
    CHANGED=false

    for key in "${WP_CRUFT_KEYS[@]}"; do
      if grep -q "^${key}:" "$mdfile" 2>/dev/null; then
        # Remove the key line and any continuation lines (indented with spaces)
        sed -i "/^${key}:/,/^[^ ]/{ /^${key}:/d; /^  /d; }" "$mdfile"
        CHANGED=true
      fi
    done

    # Remove 'type: post' and 'type: page' — Hugo infers from directory
    sed -i '/^type: post$/d' "$mdfile"
    sed -i '/^type: page$/d' "$mdfile"

    # Remove 'author: Tate Eskew' — single-author site
    sed -i '/^author: Tate Eskew$/d' "$mdfile"

    # Remove 'format: gallery' — not used in Hugo theme
    sed -i '/^format: gallery$/d' "$mdfile"

    # Fix old-style WordPress URL field to Hugo-compatible aliases
    # url: /2025/12/03/im-gettin-too-old-to-do-that/ → aliases: [...]
    if grep -q "^url: " "$mdfile" 2>/dev/null; then
      OLD_URL=$(grep "^url: " "$mdfile" | head -1 | sed 's/^url: //')
      sed -i "s|^url: .*|aliases:\n  - $OLD_URL|" "$mdfile"
    fi

    if $CHANGED; then
      CLEAN_COUNT=$((CLEAN_COUNT + 1))
    fi
  done

  echo "   → Cleaned front matter in migrated files"
  echo ""

  # ─────────────────────────────────────────────────────────────
  # Step 4: Rewrite image URLs
  # ─────────────────────────────────────────────────────────────
  echo "🖼️  Step 4: Rewriting image URLs..."

  find "$CONTENT_DIR" -name '*.md' | while read -r mdfile; do
    # Rewrite absolute WordPress URLs to local paths
    # https://www.tateeskew.com/wp-content/uploads/2026/01/photo.jpg → /images/photo.jpg
    sed -i 's|https\?://\(www\.\)\?tateeskew\.com/wp-content/uploads/[0-9]*/[0-9]*/|/images/|g' "$mdfile"

    # Also handle relative wp-content paths
    sed -i 's|/wp-content/uploads/[0-9]*/[0-9]*/|/images/|g' "$mdfile"

    # Strip WordPress resized image suffixes from filenames
    # /images/photo-300x300.jpg → /images/photo.jpg
    # /images/photo-1024x1024.jpg → /images/photo.jpg
    # /images/photo-150x150.png → /images/photo.png
    # Handles: -NNNxNNN before the extension
    sed -i 's|\(/images/[^"]*\)-[0-9]\+x[0-9]\+\.\(jpg\|jpeg\|png\|gif\|webp\|svg\)|\1.\2|g' "$mdfile"
  done

  echo "   → Rewrote all image URLs to /images/ and stripped resize suffixes"
  echo ""

  # ─────────────────────────────────────────────────────────────
  # Step 5: Fix HTML entities
  # ─────────────────────────────────────────────────────────────
  echo "✏️  Step 5: Fixing HTML entities..."

  find "$CONTENT_DIR" -name '*.md' -newer "$EXPORT_DIR/config.yaml" | while read -r mdfile; do
    # Common WordPress HTML entities
    sed -i "s/\&#8217;/'/g" "$mdfile"
    sed -i "s/\&#8216;/'/g" "$mdfile"
    sed -i 's/\&#8220;/"/g' "$mdfile"
    sed -i 's/\&#8221;/"/g' "$mdfile"
    sed -i 's/\&#8211;/–/g' "$mdfile"
    sed -i 's/\&#8212;/—/g' "$mdfile"
    sed -i 's/\&#8230;/…/g' "$mdfile"
    sed -i 's/\&amp;/\&/g' "$mdfile"
    sed -i 's/\&#038;/\&/g' "$mdfile"
    sed -i 's/\&nbsp;/ /g' "$mdfile"
  done

  echo "   → Fixed HTML entities (smart quotes, dashes, ellipses)"
  echo ""
fi

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════"
echo "  Migration Complete"
echo "  Posts:  $POST_COUNT"
echo "  Pages:  $PAGE_COUNT"
if ! $DRY_RUN; then
echo ""
echo "  ⚠️  MANUAL REVIEW NEEDED:"
echo "  The exported content still contains WordPress theme HTML"
echo "  (Brooklyn theme divs, Visual Composer shortcodes, etc.)"
echo "  These will need to be cleaned up post-by-post."
echo ""
echo "  Skipped pages (handled differently in Hugo):"
echo "    - events/     → uses data/events.yaml"
echo "    - weblog/     → Hugo list template"
echo "    - social/     → footer/about links"
echo "    - tate/       → duplicate of about"
echo "    - mailing-list/ → obsolete"
echo "    - read-tates-weblog/ → redirect to /weblog"
fi
echo "═══════════════════════════════════════════════════════════"
