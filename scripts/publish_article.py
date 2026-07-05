#!/usr/bin/env python3
"""
Heezo Article Publisher
=======================
Takes article data and generates a complete HTML file from the article template.
Can be run standalone or as part of the GitHub Actions daily-content workflow.

Usage:
    # From research output (workflow mode)
    python scripts/publish_article.py --from-research artifacts/research_output.json

    # Direct mode with arguments
    python scripts/publish_article.py \
        --title "Your Article Title" \
        --content article_body.html \
        --category "Movies" \
        --image-url "https://heezo.co/assets/articles/hero.jpg" \
        --meta-description "A short description for SEO"

    # Interactive mode (prompts for input)
    python scripts/publish_article.py --interactive
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


def slugify(title: str) -> str:
    """Generate a URL-friendly slug from the article title."""
    # Convert to lowercase
    slug = title.lower()
    # Remove special characters except hyphens and spaces
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'[\s]+', '-', slug)
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to reasonable length
    if len(slug) > 80:
        slug = slug[:80].rsplit('-', 1)[0]
    return slug


def calculate_reading_time(content: str) -> int:
    """Calculate reading time in minutes (avg 200 words/min for detailed content)."""
    # Strip HTML tags for word count
    text = re.sub(r'<[^>]+>', '', content)
    word_count = len(text.split())
    reading_time = max(1, math.ceil(word_count / 200))
    return reading_time


def count_words(content: str) -> int:
    """Count words in content (strip HTML tags first)."""
    text = re.sub(r'<[^>]+>', '', content)
    return len(text.split())


def format_date_display(dt: datetime) -> str:
    """Format date for display (e.g., 'Jul 5, 2025')."""
    return dt.strftime('%b %-d, %Y') if os.name != 'nt' else dt.strftime('%b %d, %Y')


def format_date_iso(dt: datetime) -> str:
    """Format date as ISO 8601."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def generate_related_articles_html(category: str, current_slug: str) -> str:
    """Generate related articles HTML based on category.
    
    In production, this would query the articles index.
    For now, generates placeholder related cards.
    """
    # Default related articles by category
    related_map = {
        "Movies": [
            {"title": "Every Nolan Film Ranked — From Good to Masterpiece", "slug": "nolan-films-ranked", "emoji": "🎬", "time": "7 min"},
            {"title": "The A24 Starter Pack: 10 Films That'll Rewire Your Brain", "slug": "a24-starter-pack", "emoji": "🎭", "time": "6 min"},
            {"title": "Why Practical Effects Still Hit Different in 2025", "slug": "practical-effects-2025", "emoji": "💥", "time": "5 min"},
        ],
        "Anime": [
            {"title": "Top 10 Anime of 2025 (So Far) That You're Sleeping On", "slug": "best-anime-2025", "emoji": "🎌", "time": "6 min"},
            {"title": "How to Catch Up on One Piece Without Watching 1100+ Episodes", "slug": "one-piece-catch-up", "emoji": "🏴‍☠️", "time": "9 min"},
            {"title": "The Golden Age of Anime Is Right Now — Here's Proof", "slug": "golden-age-anime", "emoji": "✨", "time": "7 min"},
        ],
        "Gaming": [
            {"title": "Your Gaming Backlog Strategy is Wrong — Here's a Better One", "slug": "gaming-backlog-strategy", "emoji": "🎮", "time": "5 min"},
            {"title": "Elden Ring DLC: Every Secret You Missed", "slug": "elden-ring-dlc-guide", "emoji": "⚔️", "time": "10 min"},
            {"title": "The Indie Games That Outclass AAA in 2025", "slug": "indie-games-2025", "emoji": "🕹️", "time": "6 min"},
        ],
        "TV Shows": [
            {"title": "House of the Dragon S3: What the Book Readers Won't Tell You", "slug": "house-of-the-dragon-s3", "emoji": "🐉", "time": "7 min"},
            {"title": "Peak TV is Dead — Here's What Replaced It", "slug": "peak-tv-dead", "emoji": "📺", "time": "6 min"},
            {"title": "The 5 Shows Everyone Will Be Talking About This Fall", "slug": "fall-2025-shows", "emoji": "🍂", "time": "5 min"},
        ],
    }

    articles = related_map.get(category, related_map["Movies"])
    # Filter out current article
    articles = [a for a in articles if a["slug"] != current_slug][:3]

    cards_html = ""
    for article in articles:
        cards_html += f'''
            <a href="/lore/articles/{article['slug']}" class="related-card">
                <div class="related-card-img">{article['emoji']}</div>
                <div class="related-card-body">
                    <h3 class="related-card-title">{article['title']}</h3>
                    <span class="related-card-meta">{category} • {article['time']} read</span>
                </div>
            </a>'''

    return cards_html


def load_template() -> str:
    """Load the article HTML template."""
    # Try multiple paths (workspace vs repo root)
    possible_paths = [
        Path(__file__).parent.parent / "lore" / "articles" / "template.html",
        Path("lore/articles/template.html"),
        Path("artifacts/heezo_blog/lore/articles/template.html"),
    ]

    for path in possible_paths:
        if path.exists():
            return path.read_text(encoding='utf-8')

    raise FileNotFoundError(
        "Could not find template.html. Looked in:\n" +
        "\n".join(f"  - {p}" for p in possible_paths)
    )


def build_article_html(
    title: str,
    content: str,
    category: str,
    meta_description: str,
    image_url: str = "",
    published_date: datetime = None,
    modified_date: datetime = None,
) -> tuple[str, dict]:
    """
    Build complete article HTML from template and return (html, metadata).
    
    Args:
        title: Article title
        content: HTML content for the article body
        category: One of Movies, Anime, Gaming, TV Shows
        meta_description: SEO meta description (155 chars max recommended)
        image_url: Hero image URL (1200x630 min for Discover)
        published_date: Publication datetime (defaults to now)
        modified_date: Last modified datetime (defaults to published_date)
    
    Returns:
        Tuple of (complete_html_string, metadata_dict)
    """
    if published_date is None:
        published_date = datetime.now(timezone.utc)
    if modified_date is None:
        modified_date = published_date

    slug = slugify(title)
    word_count = count_words(content)
    reading_time = calculate_reading_time(content)
    title_encoded = quote(title)

    # Default hero image if none provided
    if not image_url:
        image_url = f"https://heezo.co/assets/articles/{slug}-hero.jpg"

    # Generate related articles
    related_html = generate_related_articles_html(category, slug)

    # Load and fill template
    template = load_template()

    # Replace all template variables
    replacements = {
        "{{ARTICLE_TITLE}}": title,
        "{{META_DESCRIPTION}}": meta_description,
        "{{SLUG}}": slug,
        "{{HERO_IMAGE_URL}}": image_url,
        "{{DATE_ISO}}": format_date_iso(published_date),
        "{{DATE_MODIFIED_ISO}}": format_date_iso(modified_date),
        "{{DATE_DISPLAY}}": format_date_display(published_date),
        "{{CATEGORY}}": category,
        "{{WORD_COUNT}}": str(word_count),
        "{{READING_TIME}}": str(reading_time),
        "{{ARTICLE_CONTENT}}": content,
        "{{ARTICLE_TITLE_ENCODED}}": title_encoded,
        "{{RELATED_ARTICLES}}": related_html,
    }

    html = template
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Build metadata
    metadata = {
        "title": title,
        "slug": slug,
        "category": category,
        "meta_description": meta_description,
        "image_url": image_url,
        "published_date": format_date_iso(published_date),
        "modified_date": format_date_iso(modified_date),
        "word_count": word_count,
        "reading_time": reading_time,
        "file_path": f"lore/articles/{slug}.html",
        "url": f"https://heezo.co/lore/articles/{slug}",
    }

    return html, metadata


def publish_article(
    title: str,
    content: str,
    category: str,
    meta_description: str,
    image_url: str = "",
    output_dir: str = None,
) -> dict:
    """
    Generate and save the article HTML file.
    
    Returns metadata dict with file path and article info.
    """
    html, metadata = build_article_html(
        title=title,
        content=content,
        category=category,
        meta_description=meta_description,
        image_url=image_url,
    )

    # Determine output directory
    if output_dir is None:
        possible_dirs = [
            Path(__file__).parent.parent / "lore" / "articles",
            Path("lore/articles"),
        ]
        output_dir = next((d for d in possible_dirs if d.exists()), possible_dirs[0])
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Write the HTML file
    output_path = output_dir / f"{metadata['slug']}.html"
    output_path.write_text(html, encoding='utf-8')

    metadata["file_path"] = str(output_path)
    print(f"✅ Published: {metadata['title']}")
    print(f"   File: {output_path}")
    print(f"   URL:  {metadata['url']}")
    print(f"   Words: {metadata['word_count']} | Reading time: {metadata['reading_time']} min")

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Heezo Article Publisher")
    parser.add_argument("--title", type=str, help="Article title")
    parser.add_argument("--content", type=str, help="Path to HTML content file, or raw HTML string")
    parser.add_argument("--category", type=str, choices=["Movies", "Anime", "Gaming", "TV Shows"], help="Article category")
    parser.add_argument("--image-url", type=str, default="", help="Hero image URL (1200x630 min)")
    parser.add_argument("--meta-description", type=str, default="", help="SEO meta description")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for the article")
    parser.add_argument("--from-research", type=str, help="Path to research_output.json (workflow mode)")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--save-meta", type=str, default="artifacts/latest_article_meta.json",
                       help="Path to save article metadata JSON")

    args = parser.parse_args()

    # Mode 1: From research output (GitHub Actions workflow)
    if args.from_research:
        research_path = Path(args.from_research)
        if not research_path.exists():
            print(f"❌ Research file not found: {research_path}")
            sys.exit(1)

        with open(research_path) as f:
            research = json.load(f)

        metadata = publish_article(
            title=research["title"],
            content=research["content"],
            category=research["category"],
            meta_description=research["meta_description"],
            image_url=research.get("image_url", ""),
            output_dir=args.output_dir,
        )

        # Save metadata for the git commit message
        meta_path = Path(args.save_meta)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"   Meta: {meta_path}")
        return

    # Mode 2: Interactive
    if args.interactive:
        print("\n🎬 Heezo Article Publisher — Interactive Mode\n")
        title = input("Title: ").strip()
        category = input("Category (Movies/Anime/Gaming/TV Shows): ").strip()
        meta_desc = input("Meta description (155 chars): ").strip()
        image_url = input("Hero image URL (or blank for default): ").strip()
        print("\nPaste article HTML content (end with 'EOF' on its own line):")
        
        content_lines = []
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            content_lines.append(line)
        content = "\n".join(content_lines)

        metadata = publish_article(
            title=title,
            content=content,
            category=category,
            meta_description=meta_desc,
            image_url=image_url,
            output_dir=args.output_dir,
        )
        return

    # Mode 3: Command-line arguments
    if not args.title:
        parser.print_help()
        print("\n❌ Either --title, --from-research, or --interactive is required.")
        sys.exit(1)

    # Load content from file or use as raw HTML
    content = ""
    if args.content:
        content_path = Path(args.content)
        if content_path.exists():
            content = content_path.read_text(encoding='utf-8')
        else:
            # Assume it's raw HTML
            content = args.content

    if not content:
        print("❌ No content provided. Use --content with a file path or HTML string.")
        sys.exit(1)

    if not args.category:
        print("❌ --category is required.")
        sys.exit(1)

    # Generate meta description if not provided
    meta_description = args.meta_description
    if not meta_description:
        # Auto-generate from first paragraph
        text = re.sub(r'<[^>]+>', '', content)
        meta_description = text[:155].rsplit(' ', 1)[0] + "..."

    metadata = publish_article(
        title=args.title,
        content=content,
        category=args.category,
        meta_description=meta_description,
        image_url=args.image_url,
        output_dir=args.output_dir,
    )

    # Save metadata
    meta_path = Path(args.save_meta)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   Meta: {meta_path}")


if __name__ == "__main__":
    main()
