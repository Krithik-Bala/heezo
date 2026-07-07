"""
Heezo Cloud Publisher — Runs on GitHub Actions (Gemini Free Tier)
Generates a trending entertainment article and saves it to lore/articles/
Sends Discord notification when published.
"""

import os
import json
import re
import requests
from datetime import datetime

# Use the new google.genai package (google.generativeai is deprecated)
from google import genai

# Config — Multi-key rotation (each key from a different Google Cloud project)
API_KEYS = []
for var in ["GEMINI_API_KEY", "KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]:
    val = os.environ.get(var, "")
    if val:
        API_KEYS.append(val)

if not API_KEYS:
    print("ERROR: No Gemini API keys found")
    exit(1)

print(f"Loaded {len(API_KEYS)} API keys for rotation")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

MODEL = "gemini-2.0-flash"

def call_gemini(prompt):
    """Try each API key until one works."""
    for i, key in enumerate(API_KEYS):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"  Key {i+1} exhausted, trying next...")
                continue
            else:
                raise e
    raise Exception("All API keys exhausted (429 on all)")

TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_DISPLAY = datetime.now().strftime("%B %d, %Y")

# Step 1: Research trending topics
print("🔍 Researching trending entertainment topics...")

research_prompt = """You are a trending topic researcher for an entertainment website called Heezo.
Find ONE trending entertainment topic from the last 1-3 days that would make a great article.
Focus on: Movies, Anime, Gaming, TV Shows, Pop Culture.

IMPORTANT: Return ONLY a valid JSON object, no extra text:
{
  "topic": "The main topic",
  "headline": "A catchy headline (conversational tone, like a genius friend texting you the coolest thing)",
  "slug": "url-friendly-slug-here",
  "category": "movies|anime|gaming|tv-shows|pop-culture",
  "key_facts": ["fact 1", "fact 2", "fact 3", "fact 4", "fact 5"],
  "angle": "What unique angle to take"
}"""

MAX_RETRIES = 3
topic_data = None

for attempt in range(MAX_RETRIES):
    try:
        research_text = call_gemini(research_prompt).strip()
        # Remove markdown code fences if present
        research_text = re.sub(r'^```(?:json)?\s*', '', research_text)
        research_text = re.sub(r'\s*```$', '', research_text)
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', research_text)
        if json_match:
            topic_data = json.loads(json_match.group())
            break
        else:
            print(f"  Attempt {attempt+1}: Could not find JSON in response")
    except json.JSONDecodeError as e:
        print(f"  Attempt {attempt+1}: JSON parse error - {e}")
    except Exception as e:
        print(f"  Attempt {attempt+1}: Research failed - {e}")

if not topic_data:
    print("ERROR: Could not get topic after 3 attempts")
    exit(1)

# Validate required fields
required_fields = ["topic", "headline", "slug", "category", "key_facts", "angle"]
for field in required_fields:
    if field not in topic_data:
        print(f"ERROR: Missing field '{field}' in topic data")
        exit(1)

# Clean slug
topic_data['slug'] = re.sub(r'[^a-z0-9-]', '', topic_data['slug'].lower().replace(' ', '-'))

print(f"📝 Topic: {topic_data['headline']}")

# Step 2: Write the article
article_prompt = f"""Write a full entertainment article for Heezo.

TOPIC: {topic_data['topic']}
HEADLINE: {topic_data['headline']}
KEY FACTS: {json.dumps(topic_data['key_facts'])}
ANGLE: {topic_data['angle']}

VOICE: "A genius friend who texts you the coolest shit they just found — but makes it look cinematic."
- Conversational, punchy, uses "you" directly
- Specific details, numbers, dates
- Not generic blog writing — personality throughout
- Include a hot take / opinion at the end

STRUCTURE:
- Opening hook (1-2 sentences that grab attention)
- 3-4 sections with h2 subheadings
- Each section: 150-250 words
- Closing take / "Why this matters" section
- Total: 800-1200 words

Write ONLY the article body in HTML (h2 tags for headings, p tags for paragraphs). No wrapper, no head, no metadata. Just the article content HTML."""

article_body = None
for attempt in range(MAX_RETRIES):
    try:
        article_body = call_gemini(article_prompt).strip()
        # Clean any markdown code fences
        article_body = re.sub(r'^```(?:html)?\s*', '', article_body)
        article_body = re.sub(r'\s*```$', '', article_body)
        if '<p>' in article_body or '<h2>' in article_body:
            break
        else:
            print(f"  Attempt {attempt+1}: Response doesn't look like HTML")
    except Exception as e:
        print(f"  Attempt {attempt+1}: Article gen failed - {e}")

if not article_body:
    print("ERROR: Could not generate article after 3 attempts")
    exit(1)

# Step 3: Calculate reading time
word_count = len(article_body.split())
read_time = max(3, word_count // 200)
print(f"📊 Word count: {word_count}, Read time: {read_time} min")

# Step 4: Generate full HTML page
slug = topic_data['slug']
headline = topic_data['headline']
category = topic_data['category']
description = f"{headline} — Deep dive by Heezo Lore."

# Escape for HTML attributes
headline_escaped = headline.replace('"', '&quot;')
description_escaped = description.replace('"', '&quot;')

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline_escaped} — Heezo Lore</title>
    <meta name="description" content="{description_escaped}">
    <meta name="robots" content="index, follow, max-image-preview:large">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{headline_escaped}">
    <meta property="og:description" content="{description_escaped}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://heezo.vercel.app/lore/articles/{slug}">
    <meta property="og:site_name" content="Heezo">
    <meta property="article:published_time" content="{TODAY}T12:00:00+05:30">
    
    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{headline_escaped}">
    <meta name="twitter:description" content="{description_escaped}">
    
    <!-- Schema.org -->
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{headline_escaped}",
        "datePublished": "{TODAY}T12:00:00+05:30",
        "author": {{"@type": "Organization", "name": "Heezo"}},
        "publisher": {{"@type": "Organization", "name": "Heezo"}}
    }}
    </script>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --obsidian: #0a0a0f;
            --gold: #d4af37;
            --gold-glow: rgba(212, 175, 55, 0.15);
            --text-primary: #e8e6e3;
            --text-secondary: #9a9a9a;
            --border: rgba(212, 175, 55, 0.1);
        }}
        
        body {{
            font-family: 'Space Grotesk', sans-serif;
            background: var(--obsidian);
            color: var(--text-primary);
            line-height: 1.8;
            -webkit-font-smoothing: antialiased;
        }}
        
        .nav {{
            position: fixed;
            top: 0; left: 0; right: 0;
            z-index: 100;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(10, 10, 15, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
        }}
        
        .nav-logo {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--gold);
            text-decoration: none;
        }}
        
        .nav-links {{
            display: flex;
            gap: 2rem;
            list-style: none;
        }}
        
        .nav-links a {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.3s;
        }}
        
        .nav-links a:hover {{ color: var(--gold); }}
        
        .breadcrumb {{
            max-width: 720px;
            margin: 7rem auto 0;
            padding: 0 2rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .breadcrumb a {{
            color: var(--gold);
            text-decoration: none;
        }}
        
        .article {{
            max-width: 720px;
            margin: 2rem auto;
            padding: 0 2rem 4rem;
        }}
        
        .article-meta {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .article-category {{
            background: var(--gold-glow);
            color: var(--gold);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .article h1 {{
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 2rem;
            background: linear-gradient(135deg, var(--gold), #f5e6a3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .article h2 {{
            font-size: 1.4rem;
            font-weight: 600;
            margin: 2.5rem 0 1rem;
            color: var(--text-primary);
        }}
        
        .article p {{
            margin-bottom: 1.2rem;
            color: var(--text-secondary);
            font-size: 1.05rem;
        }}
        
        .article strong {{ color: var(--text-primary); }}
        
        .article ul, .article ol {{
            margin-bottom: 1.2rem;
            padding-left: 1.5rem;
            color: var(--text-secondary);
        }}
        
        .article li {{
            margin-bottom: 0.5rem;
        }}
        
        .footer {{
            text-align: center;
            padding: 3rem 2rem;
            border-top: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        .footer a {{ color: var(--gold); text-decoration: none; }}
        
        .more-articles {{
            max-width: 720px;
            margin: 0 auto;
            padding: 2rem;
            text-align: center;
        }}
        
        .more-articles a {{
            display: inline-block;
            padding: 0.75rem 2rem;
            border: 1px solid var(--gold);
            border-radius: 100px;
            color: var(--gold);
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
        }}
        
        .more-articles a:hover {{
            background: var(--gold);
            color: var(--obsidian);
        }}
        
        @media (max-width: 600px) {{
            .nav {{ padding: 1rem; }}
            .nav-links {{ gap: 1rem; }}
            .article {{ padding: 0 1rem 3rem; }}
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/" class="nav-logo">HEEZO</a>
        <ul class="nav-links">
            <li><a href="/">Home</a></li>
            <li><a href="/lore">Lore</a></li>
            <li><a href="/life">Life</a></li>
            <li><a href="/lore/articles">Articles</a></li>
        </ul>
    </nav>

    <div class="breadcrumb">
        <a href="/">Home</a> &rsaquo; <a href="/lore">Lore</a> &rsaquo; <a href="/lore/articles">Articles</a> &rsaquo; {headline}
    </div>

    <article class="article">
        <div class="article-meta">
            <span class="article-category">{category}</span>
            <span>{TODAY_DISPLAY}</span>
            <span>&bull;</span>
            <span>{read_time} min read</span>
        </div>
        
        <h1>{headline}</h1>
        
        {article_body}
    </article>

    <div class="more-articles">
        <a href="/lore/articles">&larr; More from Heezo</a>
    </div>

    <footer class="footer">
        <p>&copy; 2026 Heezo. Built with AI, powered by obsession.</p>
        <p style="margin-top: 0.5rem;">
            <a href="/lore">Lore</a> &bull; <a href="/life">Life</a> &bull; <a href="/about">About</a> &bull; <a href="/contact">Contact</a>
        </p>
    </footer>
</body>
</html>"""

# Step 5: Save the article
article_path = f"lore/articles/{slug}.html"
os.makedirs("lore/articles", exist_ok=True)

with open(article_path, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"✅ Article saved: {article_path}")

# Step 6: Update articles index (add new card at top)
index_path = "lore/articles/index.html"
if os.path.exists(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        index_content = f.read()
    
    # Create new article card HTML
    new_card = f'''        <a href="/lore/articles/{slug}" class="article-card" data-category="{category}">
            <div class="article-card-body">
                <span class="article-card-category">{category.replace("-", " ").title()}</span>
                <h3 class="article-card-title">{headline}</h3>
                <p class="article-card-excerpt">{description}</p>
                <div class="article-card-meta">
                    <span>{TODAY_DISPLAY}</span>
                    <span>&bull;</span>
                    <span>{read_time} min read</span>
                </div>
            </div>
        </a>'''
    
    # Insert after the articles-grid opening tag
    insert_marker = '<main class="articles-grid" id="articles-grid">'
    if insert_marker in index_content:
        index_content = index_content.replace(
            insert_marker,
            insert_marker + "\n" + new_card
        )
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"✅ Index updated with new card")

# Step 7: Update sitemap
sitemap_path = "sitemap.xml"
if os.path.exists(sitemap_path):
    with open(sitemap_path, "r", encoding="utf-8") as f:
        sitemap = f.read()
    
    new_url = f"""  <url>
    <loc>https://heezo.vercel.app/lore/articles/{slug}</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>"""
    
    sitemap = sitemap.replace("</urlset>", new_url)
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap)
    print("✅ Sitemap updated")

# Step 8: Update vercel.json with new route
vercel_path = "vercel.json"
if os.path.exists(vercel_path):
    try:
        with open(vercel_path, "r", encoding="utf-8") as f:
            vercel_config = json.load(f)
        
        new_route = {"src": f"/lore/articles/{slug}", "dest": f"/lore/articles/{slug}.html"}
        if "rewrites" in vercel_config:
            # Check if route already exists
            existing = [r["src"] for r in vercel_config["rewrites"]]
            if new_route["src"] not in existing:
                vercel_config["rewrites"].append(new_route)
                with open(vercel_path, "w", encoding="utf-8") as f:
                    json.dump(vercel_config, f, indent=2)
                print(f"✅ vercel.json updated with route: {new_route['src']}")
    except Exception as e:
        print(f"⚠️ Could not update vercel.json: {e}")

# Done!
print("ARTICLE_URL=https://heezo.vercel.app/lore/articles/" + slug)
print("ARTICLE_TITLE=" + headline)
print("Published: '" + headline + "' -> /lore/articles/" + slug)
