import json

with open('crawl4ai_schema.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

with open('schema_output.txt', 'w', encoding='utf-8') as f:
    f.write("=== /crawl endpoint ===\n")
    f.write(json.dumps(d.get('paths', {}).get('/crawl', {}), indent=2))
    
    f.write("\n\n=== CrawlRequest ===\n")
    schemas = d.get('components', {}).get('schemas', {})
    for key in ['CrawlRequest', 'CrawlerRunConfig', 'BrowserConfig', 'Body_crawl_crawl_post']:
        if key in schemas:
            f.write(f"\n--- {key} ---\n")
            f.write(json.dumps(schemas[key], indent=2))
