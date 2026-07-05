#!/usr/bin/env python3
"""
Heezo Trending Topics Research Script
======================================
Researches trending entertainment topics and generates article data
for the publish_article.py script to consume.

Used by the daily-content GitHub Actions workflow.

Outputs: artifacts/research_output.json with:
  - title: Article title
  - content: Full HTML article body
  - category: Movies | Anime | Gaming | TV Shows
  - meta_description: SEO description
  - image_url: Hero image URL (optional)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Requires: pip install openai requests
try:
    from openai import OpenAI
    import requests
except ImportError:
    print("❌ Missing dependencies. Run: pip install openai requests")
    sys.exit(1)


# Configuration
CATEGORIES = ["Movies", "Anime", "Gaming", "TV Shows"]
OUTPUT_PATH = Path("artifacts/research_output.json")

SYSTEM_PROMPT = """You are Heezo — a witty entertainment expert who writes like a genius friend 
giving advice. Your tone is confident, conversational, occasionally funny, and always informative.
You never sound corporate or generic. You use bold opinions but back them up.

Your writing style:
- Conversational but smart (not trying too hard)
- Strong opinions presented confidently
- Pop culture references woven in naturally
- Practical advice over fluff
- Occasionally break the fourth wall
- Use em-dashes, short punchy paragraphs, and rhetorical questions
- Never use phrases like "in today's landscape" or "at the end of the day"
"""

RESEARCH_PROMPT = """Research what's trending RIGHT NOW in entertainment (movies, anime, gaming, TV shows).
Pick ONE topic that would make a compelling article — something people are actively searching for
or talking about.

Rules for picking a topic:
- It should be TIMELY (trending this week or very recently)
- It should be USEFUL (a guide, ranking, explainer, or hot take)
- It should be SEARCHABLE (people would Google this)
- It should have DEPTH (enough for 800-1200 words)
- Pick from: {categories}
{override_instruction}

Return a JSON object with:
{{
    "topic": "The specific topic/angle",
    "category": "Movies|Anime|Gaming|TV Shows",
    "suggested_title": "A compelling, SEO-friendly title",
    "hook": "Why this is relevant right now (1-2 sentences)",
    "key_points": ["point1", "point2", "point3", "point4", "point5"]
}}"""

ARTICLE_PROMPT = """Write a full article on:
Topic: {topic}
Title: {title}
Category: {category}
Key Points to cover: {key_points}

Requirements:
- Write 800-1200 words
- Output as HTML (use <h2>, <h3>, <p>, <strong>, <em>, <ul>/<ol>, <blockquote> tags)
- Start with a compelling hook paragraph (no "In this article" intros)
- Include 3-5 subheadings (h2 or h3)
- End with a strong conclusion or call-to-action
- Write in the Heezo voice (genius friend, opinionated, fun)
- Be genuinely useful — real information, not fluff
- Include specific names, titles, dates where relevant

Also provide:
- meta_description: 150 chars max, compelling for search results
- image_prompt: A description for what the hero image should look like

Return as JSON:
{{
    "content": "<p>Full HTML article...</p>",
    "meta_description": "SEO description here",
    "image_prompt": "Description of ideal hero image"
}}"""


def get_openai_client() -> OpenAI:
    """Initialize OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def research_trending_topic(client: OpenAI, topic_override: str = "", category_override: str = "auto") -> dict:
    """Research trending topics and pick the best one."""
    override_instruction = ""
    if topic_override:
        override_instruction = f"\nIMPORTANT: The topic must be related to: {topic_override}"
    if category_override and category_override != "auto":
        override_instruction += f"\nIMPORTANT: The category MUST be: {category_override}"

    prompt = RESEARCH_PROMPT.format(
        categories=", ".join(CATEGORIES),
        override_instruction=override_instruction
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    result = json.loads(response.choices[0].message.content)
    print(f"📡 Research complete:")
    print(f"   Topic: {result['topic']}")
    print(f"   Category: {result['category']}")
    print(f"   Title: {result['suggested_title']}")
    return result


def generate_article(client: OpenAI, research: dict) -> dict:
    """Generate the full article content."""
    prompt = ARTICLE_PROMPT.format(
        topic=research["topic"],
        title=research["suggested_title"],
        category=research["category"],
        key_points=json.dumps(research["key_points"]),
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
        max_tokens=4000,
    )

    result = json.loads(response.choices[0].message.content)
    print(f"✍️  Article generated:")
    print(f"   Meta: {result['meta_description'][:80]}...")
    return result


def main():
    # Get overrides from environment (set by GitHub Actions)
    topic_override = os.environ.get("TOPIC_OVERRIDE", "")
    category_override = os.environ.get("CATEGORY_OVERRIDE", "auto")

    print("\n🔍 Heezo Content Research\n")
    print(f"   Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if topic_override:
        print(f"   Topic Override: {topic_override}")
    if category_override != "auto":
        print(f"   Category Override: {category_override}")
    print()

    # Initialize client
    client = get_openai_client()

    # Step 1: Research trending topic
    research = research_trending_topic(client, topic_override, category_override)

    # Step 2: Generate full article
    article = generate_article(client, research)

    # Step 3: Compile output
    output = {
        "title": research["suggested_title"],
        "content": article["content"],
        "category": research["category"],
        "meta_description": article["meta_description"],
        "image_url": "",  # To be filled by image generation step if added
        "research": {
            "topic": research["topic"],
            "hook": research["hook"],
            "key_points": research["key_points"],
            "image_prompt": article.get("image_prompt", ""),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Research output saved to: {OUTPUT_PATH}")
    print(f"   Ready for publish_article.py")


if __name__ == "__main__":
    main()
