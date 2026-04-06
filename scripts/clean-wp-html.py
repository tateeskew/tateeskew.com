#!/usr/bin/env python3
"""
clean-wp-html.py — Convert WordPress gallery HTML and image tags to clean Markdown.

This script processes migrated WordPress content files and:
1. Converts WordPress gallery <dl>/<dt> blocks into simple Markdown image grids
2. Replaces verbose <img> tags with clean Markdown ![alt](/images/file.jpg)
3. Strips resize suffixes from image filenames (-300x300, -1024x1024, etc.)
4. Removes WordPress wrapper divs (<div class="el-p">, <div class="ut-alert">, etc.)
5. Strips srcset attributes and other WordPress HTML cruft
6. Fixes indentation that causes Hugo to treat HTML as code blocks

Usage:
    python3 scripts/clean-wp-html.py [--dry-run] [--file path/to/file.md]
"""

import re
import sys
import os
import glob

DRY_RUN = "--dry-run" in sys.argv
SINGLE_FILE = None
for i, arg in enumerate(sys.argv):
    if arg == "--file" and i + 1 < len(sys.argv):
        SINGLE_FILE = sys.argv[i + 1]

CONTENT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")


def strip_resize_suffix(path):
    """Remove WordPress resize suffixes like -300x300, -1024x997 from image paths."""
    return re.sub(r'-\d+x\d+\.(jpg|jpeg|png|gif|webp)', r'.\1', path)


def extract_gallery_images(html):
    """Extract original image URLs from WordPress gallery HTML."""
    # Look for href attributes in gallery links (these point to originals)
    hrefs = re.findall(r"href=['\"]([^'\"]+\.(jpg|jpeg|png|gif|webp))['\"]", html, re.IGNORECASE)
    images = []
    seen = set()
    for href, ext in hrefs:
        clean = strip_resize_suffix(href)
        if clean not in seen:
            seen.add(clean)
            images.append(clean)
    return images


def convert_img_tag(match):
    """Convert an <img> tag to Markdown image syntax."""
    tag = match.group(0)
    
    # Extract src
    src_match = re.search(r'src=["\']([^"\']+)["\']', tag)
    if not src_match:
        return tag
    src = strip_resize_suffix(src_match.group(1))
    
    # Extract alt text
    alt_match = re.search(r'alt=["\']([^"\']*)["\']', tag)
    alt = alt_match.group(1) if alt_match else ""
    
    # Extract title
    title_match = re.search(r'title=["\']([^"\']*)["\']', tag)
    if title_match and not alt:
        alt = title_match.group(1)
    
    return f"![{alt}]({src})"


def clean_content(content, filename=""):
    """Clean WordPress HTML from a content file, preserving front matter."""
    # Split front matter from body
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content
    
    front_matter = parts[0] + "---" + parts[1] + "---"
    body = parts[2]
    original_body = body
    
    # Step 1: Convert WordPress galleries to image grids
    # Match the entire gallery div block
    gallery_pattern = re.compile(
        r"<div[^>]*class=['\"][^'\"]*gallery[^'\"]*['\"][^>]*>(.+?)</div>\s*",
        re.DOTALL
    )
    
    def replace_gallery(match):
        gallery_html = match.group(0)
        images = extract_gallery_images(gallery_html)
        if not images:
            return ""
        
        # Build a clean HTML image grid
        lines = []
        lines.append('<div class="image-grid">')
        for img in images:
            basename = os.path.splitext(os.path.basename(img))[0]
            alt = basename.replace("-", " ").replace("_", " ").title()
            lines.append(f'<a href="{img}" class="gallery-item"><img src="{img}" alt="{alt}" loading="lazy"></a>')
        lines.append('</div>')
        return "\n".join(lines) + "\n"
    
    body = gallery_pattern.sub(replace_gallery, body)
    
    # Step 2: Convert standalone <a><img></a> patterns to Markdown
    # Pattern: <a href="..."><img ... /></a>
    linked_img_pattern = re.compile(
        r'<a[^>]*href=["\']([^"\']+\.(jpg|jpeg|png|gif|webp|svg))["\'][^>]*>\s*'
        r'<img[^>]*(?:alt=["\']([^"\']*)["\'])?[^>]*/?\s*>\s*</a>',
        re.IGNORECASE | re.DOTALL
    )
    
    def replace_linked_img(match):
        href = strip_resize_suffix(match.group(1))
        alt = match.group(3) or ""
        return f"![{alt}]({href})"
    
    body = linked_img_pattern.sub(replace_linked_img, body)
    
    # Step 3: Convert remaining standalone <img> tags to Markdown
    img_pattern = re.compile(r'<img[^>]+/?\s*>', re.IGNORECASE)
    body = img_pattern.sub(convert_img_tag, body)
    
    # Step 4: Remove WordPress wrapper divs
    # <div class="el-p"> ... content ... </div>
    body = re.sub(r'<div[^>]*class=["\'][^"\']*(?:el-p|ut-alert|ut-highlight|ut-social)[^"\']*["\'][^>]*>\s*', '', body)
    
    # Step 5: Remove closing </div> tags (leftover from gallery/wrapper removal)
    # Be careful to only remove divs that appear to be wrappers (preceded by whitespace or newline)
    body = re.sub(r'\n\s*</div>\s*', '\n', body)
    # Also handle </div> at end of lines
    body = re.sub(r'</div>\s*$', '', body, flags=re.MULTILINE)
    
    # Step 6: Clean up remaining HTML cruft
    # Remove <p> and </p> tags (Markdown handles paragraphs)
    body = re.sub(r'</?p[^>]*>', '', body)
    
    # Remove <br /> and <br> tags, replace with newlines where they're paragraph breaks
    body = re.sub(r'<br\s*/?\s*>\s*<br\s*/?\s*>', '\n\n', body)
    body = re.sub(r'\s*<br\s*/?>\s*', '  \n', body)
    
    # Step 7: Clean up aggressive indentation (WordPress visual editor creates deep nesting)
    lines = body.split('\n')
    cleaned_lines = []
    for line in lines:
        # Strip leading whitespace that would make Markdown treat content as code blocks
        stripped = line.lstrip()
        # But preserve intended indentation for list items
        if stripped.startswith('-') or stripped.startswith('*') or stripped.startswith('>'):
            cleaned_lines.append(stripped)
        elif stripped.startswith('{{'):
            # Preserve shortcode indentation
            cleaned_lines.append(stripped)
        else:
            cleaned_lines.append(stripped)
    body = '\n'.join(cleaned_lines)
    
    # Step 8: Fix HTML entities that the migration script may have missed
    body = body.replace('&#8217;', "'")
    body = body.replace('&#8216;', "'")
    body = body.replace('&#8220;', '"')
    body = body.replace('&#8221;', '"')
    body = body.replace('&#8211;', '–')
    body = body.replace('&#8212;', '—')
    body = body.replace('&#8230;', '…')
    body = body.replace('&amp;', '&')
    body = body.replace('&#038;', '&')
    body = body.replace('&nbsp;', ' ')
    
    # Step 9: Clean up excessive blank lines
    body = re.sub(r'\n{4,}', '\n\n\n', body)
    
    # Step 10: Fix featured_image in front matter if it has resize suffix
    front_matter = re.sub(
        r'(featured_image:\s*)/images/([^-\n]+)-\d+x\d+\.(jpg|jpeg|png|gif|webp)',
        r'\1/images/\2.\3',
        front_matter
    )
    
    return front_matter + body


def process_file(filepath):
    """Process a single Markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    cleaned = clean_content(content, filepath)
    
    if cleaned == content:
        return False  # No changes needed
    
    if DRY_RUN:
        print(f"  📋 Would clean: {os.path.basename(filepath)}")
        return True
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f"  ✅ Cleaned: {os.path.basename(filepath)}")
    return True


def main():
    print("═══════════════════════════════════════════════════════════")
    print("  WordPress HTML → Clean Markdown Converter")
    print(f"  Mode: {'DRY RUN' if DRY_RUN else 'CLEAN'}")
    print("═══════════════════════════════════════════════════════════")
    print()
    
    if SINGLE_FILE:
        files = [SINGLE_FILE]
    else:
        files = sorted(glob.glob(os.path.join(CONTENT_DIR, "**", "*.md"), recursive=True))
    
    changed = 0
    for filepath in files:
        if process_file(filepath):
            changed += 1
    
    print()
    print(f"  {'Would clean' if DRY_RUN else 'Cleaned'}: {changed} files")
    print(f"  Scanned: {len(files)} total files")


if __name__ == "__main__":
    main()
