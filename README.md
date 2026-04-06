# tateeskew.com

A static personal website built with [Hugo](https://gohugo.io/), hosted on [GitHub Pages](https://pages.github.com/).

**Theme**: "The Tape Room" — a custom-built dark-first theme with warm analog aesthetics.

## Quick Start

```bash
# Install Hugo (https://gohugo.io/installation/)
# macOS
brew install hugo

# or download from https://github.com/gohugoio/hugo/releases

# Run locally
hugo server --buildDrafts

# Build for production
hugo --gc --minify
```

## Creating a New Blog Post

Create a new Markdown file in `content/weblog/`:

```bash
hugo new content weblog/my-new-post.md
```

Or create the file manually:

```markdown
---
title: "My New Post Title"
date: 2026-01-15
categories: ["Other Music"]
tags: ["ambient", "experimental"]
description: "A short description for SEO and social sharing."
featured_image: "/images/my-image.jpg"
---

Your content goes here in Markdown.
```

## Embedding Music

### Bandcamp

```markdown
{{</* bandcamp album="793200340" */>}}
{{</* bandcamp track="123456789" size="small" */>}}
```

### YouTube

```markdown
{{</* youtube id="dQw4w9WgXcQ" title="Video Title" */>}}
```

### SoundCloud

```markdown
{{</* soundcloud id="TRACK_ID" */>}}
```

### Subvert.fm (coming soon)

```markdown
{{</* subvertfm id="RELEASE_ID" type="album" */>}}
```

## Image Galleries

1. Place images in a folder under `static/images/`:
   ```
   static/images/2026/gallery-name/
   ├── photo1.jpg
   ├── photo2.jpg
   └── photo3.jpg
   ```

2. Use the gallery shortcode in any post:
   ```markdown
   {{</* gallery dir="/images/2026/gallery-name/" caption="My Gallery" */>}}
   ```

## Adding Events

Edit `data/events.yaml`:

```yaml
upcoming:
  - date: "2026-05-01"
    title: "Show Title"
    venue: "Venue Name"
    city: "Nashville, TN"
    details: "With Artist B"
    link: "https://tickets.example.com"
    past: false
```

## Project Structure

```
tateeskew.com/
├── content/           # Markdown content
│   ├── _index.md      # Homepage
│   ├── weblog/        # Blog posts
│   ├── audio/         # Music page
│   ├── studio/        # Zero Art Studio
│   ├── about/         # Bio & links
│   └── events/        # Events page
├── data/
│   └── events.yaml    # Event data
├── static/
│   └── images/        # All images
├── themes/taperoom/   # Custom theme
│   ├── assets/css/    # Stylesheet
│   ├── layouts/       # HTML templates
│   └── shortcodes/    # Embed shortcodes
├── hugo.toml          # Site configuration
└── .github/workflows/ # Auto-deploy
```

## Deployment

The site automatically deploys to GitHub Pages on every push to `main` via GitHub Actions.

### DNS Setup (Namecheap)

Point these records to GitHub Pages:
- `A` record: `185.199.108.153`
- `A` record: `185.199.109.153`
- `A` record: `185.199.110.153`
- `A` record: `185.199.111.153`
- `CNAME` record: `www` → `tateeskew.github.io`

## Search

Search is powered by [Pagefind](https://pagefind.app/) — a static search library that indexes the site at build time. No server required.

## License

Content © Tate Eskew. All rights reserved.
