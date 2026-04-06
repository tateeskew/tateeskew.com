#!/usr/bin/env python3
"""
Fix image-grid blocks: add missing </div>, convert Markdown images to HTML <img> tags.
Also fix all other standalone Markdown images that were incorrectly placed inside HTML blocks.
"""

import re
import glob
import os

content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content")
fixed = 0

for filepath in sorted(glob.glob(os.path.join(content_dir, "**", "*.md"), recursive=True)):
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    original = list(lines)
    new_lines = []
    in_image_grid = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped == '<div class="image-grid">':
            in_image_grid = True
            new_lines.append(line)
            continue
        
        if in_image_grid:
            # Check if this line is a Markdown image
            md_img = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', stripped)
            if md_img:
                alt = md_img.group(1)
                src = md_img.group(2)
                new_lines.append('<a href="{}" class="gallery-item"><img src="{}" alt="{}" loading="lazy"></a>\n'.format(src, src, alt))
                continue
            else:
                # End of image block - add closing </div>
                new_lines.append('</div>\n\n')
                in_image_grid = False
                new_lines.append(line)
                continue
        
        new_lines.append(line)
    
    # If we ended while still in a grid
    if in_image_grid:
        new_lines.append('</div>\n')
    
    if new_lines != original:
        with open(filepath, "w") as f:
            f.writelines(new_lines)
        print("  Fixed: {}".format(os.path.basename(filepath)))
        fixed += 1

print("\nFixed {} files".format(fixed))
