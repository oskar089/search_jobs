"""Final focused analysis: dump card HTML and find stable selectors."""
import asyncio
import re

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="es-AR",
        )

        await context.route(
            re.compile(r"\.(png|jpg|jpeg|gif|svg|woff2?|ttf|eot)$"),
            lambda route: route.abort(),
        )
        await context.route(
            re.compile(r"(google-analytics|googletagmanager|facebook|doubleclick)"),
            lambda route: route.abort(),
        )

        page = await context.new_page()

        # =============================================
        # BUMERAN - dump FIRST card outer HTML
        # =============================================
        print("=" * 60)
        print("  BUMERAN - card wrapper link HTML")
        print("=" * 60)

        await page.goto("https://www.bumeran.com.ar/empleos.html",
                        timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        card_links = await page.query_selector_all("a[href*='/empleos/']")
        print(f"  Found {len(card_links)} a[href*='/empleos/'] elements")

        # Filter to job cards only (exclude nav links)
        for link in card_links:
            href = await link.get_attribute("href") or ""
            # Job card links have the full URL + path containing /empleos/ + job-name-id.html
            if "empleos/" in href and href.count("/") > 4:
                outer = await link.evaluate("el => el.outerHTML")
                print(f"\n  === First job card wrapper (a tag) ===")
                print(f"  {outer[:3000]}")
                break

        print(f"\n  === a[href*='/empleos/'] - HREFs ===")
        for link in card_links[:5]:
            href = await link.get_attribute("href") or ""
            cls = await link.get_attribute("class") or ""
            print(f"    href='{href}' class='{cls}'")

        # =============================================
        # COMPUTRABAJO - try actual search
        # =============================================
        print(f"\n{'='*60}")
        print(f"  COMPUTRABAJO - search results page")
        print(f"{'='*60}")

        # Computrabajo search URL
        search_url = "https://www.computrabajo.com.ar/empleos?q=developer&provincia=&p=1"
        await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        body_len = await page.evaluate("document.body.innerText.length")
        print(f"  Body length: {body_len} chars")
        page_title = await page.title()
        print(f"  Title: {page_title}")

        text_preview = await page.evaluate("document.body.innerText.slice(0, 1000)")
        print(f"  Body text preview:\n{text_preview}")

        # Try to find repeating patterns for job cards
        pattern_info = await page.evaluate("""() => {
            const candidates = [];
            const tags = ['div', 'article', 'li', 'section'];
            for (const tag of tags) {
                const elements = document.querySelectorAll(tag);
                const classCounts = {};
                elements.forEach(el => {
                    const cls = el.className && typeof el.className === 'string'
                        ? el.className.trim() : '';
                    if (!cls || cls.length < 3) return;
                    const childCount = el.children.length;
                    if (childCount < 2 || childCount > 20) return;
                    const key = tag + '.' + cls;
                    if (!classCounts[key]) classCounts[key] = { count: 0 };
                    classCounts[key].count++;
                });
                for (const [key, info] of Object.entries(classCounts)) {
                    if (info.count >= 3 && info.count <= 100) {
                        candidates.push({ key, count: info.count });
                    }
                }
            }
            candidates.sort((a, b) => b.count - a.count);
            return candidates.slice(0, 15);
        }""")
        print(f"\n  Repeated structural patterns:")
        for p in pattern_info:
            print(f"    {p['key']:<50} count={p['count']}")

        # Check for job links
        job_links = await page.evaluate("""() => {
            const anchors = document.querySelectorAll('a[href]');
            const jobs = [];
            for (const a of anchors) {
                const href = a.href;
                if (href.includes('/oferta') || href.includes('/job')
                    || href.includes('/empleo') || href.includes('trabajo')) {
                    jobs.push({
                        href: href.slice(0, 120),
                        text: (a.innerText || '').trim().slice(0, 60),
                        cls: (a.className || '').slice(0, 40)
                    });
                }
            }
            return jobs.slice(0, 10);
        }""")
        print(f"\n  Job-related links found:")
        for j in job_links:
            print(f"    href='{j['href']}' cls='{j['cls']}' text='{j['text']}'")

        # Show all data-testid and ID elements
        testids = await page.evaluate("""() => {
            const els = document.querySelectorAll('[data-testid]');
            return [...new Set(Array.from(els).map(e => e.getAttribute('data-testid')))].sort().slice(0, 30);
        }""")
        print(f"\n  data-testid attributes: {testids}")

        ids = await page.evaluate("""() => {
            const els = document.querySelectorAll('[id]');
            return [...new Set(Array.from(els).map(e => e.id))].filter(id => id.length > 5).sort().slice(0, 30);
        }""")
        print(f"\n  ID attributes (length > 5): {ids[:15]}")

        # =============================================
        # INFOJOBS - stable selectors
        # =============================================
        print(f"\n{'='*60}")
        print(f"  INFOJOBS - stable classes check")
        print(f"{'='*60}")

        await page.goto("https://www.infojobs.net/ofertas-trabajo",
                        timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # Accept cookies if possible
        try:
            accept_btn = await page.query_selector("button.didomi-dismiss")
            if accept_btn:
                await accept_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass

        card = await page.query_selector("div.ij-OfferCardContent")
        if card:
            outer = await card.evaluate("el => el.outerHTML")
            print(f"\n  === Full card HTML ===")
            print(f"  {outer[:4000]}")

            # Extract the card's structure via evaluate
            print(f"\n  === Card structure (tag > class) ===")
            structure = await card.evaluate("""el => {
                const items = [];
                const walk = (node, depth) => {
                    if (depth > 4) return;
                    for (const child of node.children) {
                        const tag = child.tagName.toLowerCase();
                        const cls = child.className && typeof child.className === 'string'
                            ? child.className.trim() : '-';
                        const txt = (child.innerText || '').trim().slice(0, 80).replace(/\\n/g, ' | ');
                        const testid = child.getAttribute('data-testid') || '';
                        const id = child.id || '';
                        const ref = testid ? `[testid=${testid}]` : (id ? `#${id}` : '');
                        items.push({
                            tag, cls: cls.slice(0, 60), ref: ref.slice(0, 30),
                            text: txt, depth
                        });
                        walk(child, depth + 1);
                    }
                };
                walk(el, 1);
                return items;
            }""")
            for item in structure:
                indent = "  " * (item["depth"] + 1)
                print(f"{indent}<{item['tag']} .{item['cls'][:40]} {item['ref']}> \"{item['text'][:60]}\"")

        await context.close()
        await browser.close()


asyncio.run(main())
