"""
main.py — Scholarship Pipeline CLI Orchestrator

Usage:
    python main.py
    python main.py --skip-discover              # Load URLs from DB
    python main.py --skip-crawl                 # Load markdown from cache
    python main.py --skip-extract               # Load items from DB
    python main.py --run-id <id>                # Resume a previous run
    python main.py --source-id <uuid>           # Process a single source only

All steps are fault-isolated: a failure in one site never aborts the pipeline.
Progress is saved to SQLite after every page, so the pipeline resumes correctly.
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone

from utils.logger import get_logger
from utils.progress import (
    init_db, update_meta, get_meta, finish_run, get_all_extracted_items,
    get_type_maps_from_db, get_crawl_results_from_cache,
)

log = get_logger("main")


def _make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _print_summary(summary: dict, output_paths: dict, duration_s: float) -> None:
    h, rem = divmod(int(duration_s), 3600)
    m, s = divmod(rem, 60)
    duration_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    counts = summary.get("by_type", {})
    print("\n" + "═" * 52)
    print("║" + "      PIPELINE COMPLETE".center(50) + "║")
    print("╠" + "═" * 50 + "╣")
    rows = [
        ("Sources processed",     summary.get("sources_processed", "?")),
        ("URLs discovered",        summary.get("total_discovered",  "?")),
        ("URLs after filter",      summary.get("total_filtered",    "?")),
        ("  └─ Heuristic-typed",   summary.get("heuristic_typed",   "?")),
        ("  └─ AMBIGUOUS resolved",summary.get("ambiguous_resolved","?")),
        ("Pages crawled",          summary.get("total_crawled",     "?")),
        ("Items extracted",        summary.get("total_extracted",   "?")),
        ("  ├─ SCHOLARSHIP",       counts.get("SCHOLARSHIP", 0)),
        ("  ├─ PROGRAM",           counts.get("PROGRAM",     0)),
        ("  ├─ CONFERENCE",        counts.get("CONFERENCE",  0)),
        ("  └─ EXCHANGE",          counts.get("EXCHANGE",    0)),
        ("Duplicates removed",     summary.get("total_dupes",       "?")),
        ("Final items",            summary.get("total_final",       "?")),
        ("Total duration",         duration_str),
    ]
    for label, value in rows:
        print(f"║  {label:<28}: {str(value):<18}║")
    print("╚" + "═" * 50 + "╝")

    if output_paths:
        print(f"\n📁 JSON : {output_paths.get('json_path', '')}")
        print(f"📁 CSV  : {output_paths.get('csv_path', '')}")
    print()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scholarship Pipeline — discovers, crawls, and extracts opportunities"
    )
    parser.add_argument("--skip-discover", action="store_true",
                        help="Skip Steps 1+2, load URLs from DB")
    parser.add_argument("--skip-crawl",    action="store_true",
                        help="Skip Step 3, load markdown from crawl cache")
    parser.add_argument("--skip-extract",  action="store_true",
                        help="Skip Steps 4+5, load items from DB")
    parser.add_argument("--run-id",        type=str, default=None,
                        help="Resume a specific previous run ID")
    parser.add_argument("--source-id",     type=str, default=None,
                        help="Process a single source only (for testing)")
    args = parser.parse_args()

    run_id = args.run_id or _make_run_id()
    log.info(f"Pipeline started. Run ID: {run_id}")
    start_time = time.time()

    # ── Init DB ────────────────────────────────────────────────────────────────
    init_db(run_id)

    # ── Late imports (avoids circular imports at module level) ─────────────────
    from pipeline.step0_sources import load_sources, load_item_schemas
    from pipeline.step1_discover import run as discover
    from pipeline.step2_classify import run as classify
    from pipeline.step3_crawl    import run as crawl
    from pipeline.step4_resolve  import run as resolve
    from pipeline.step5_extract  import run as extract
    from pipeline.step6_dedup    import run as dedup
    from pipeline.step7_save     import run as save

    summary: dict = {}

    try:
        # ── Step 0: Load sources ───────────────────────────────────────────────
        log.info("Loading sources from portal API...")
        sources = await load_sources(skip_api=False)
        schemas = await load_item_schemas()

        if args.source_id:
            sources = [s for s in sources if s.id == args.source_id]
            if not sources:
                log.error(f"Source ID {args.source_id} not found")
                sys.exit(1)
            log.info(f"Processing single source: {sources[0].name}")

        summary["sources_processed"] = len(sources)

        # ── Step 1+2: Discover + Classify ─────────────────────────────────────
        discovered: dict = {}
        type_maps:  dict = {}

        if not args.skip_discover:
            discovered = await discover(sources, run_id, skip=False)
            type_maps  = classify(discovered, sources, run_id, skip=False)

            total_discovered = sum(len(v) for v in discovered.values())
            total_filtered   = sum(len(v) for v in type_maps.values())
            heuristic_typed  = sum(
                sum(1 for t in tm.values() if t not in ("AMBIGUOUS",))
                for tm in type_maps.values()
            )
            summary.update({
                "total_discovered": total_discovered,
                "total_filtered":   total_filtered,
                "heuristic_typed":  heuristic_typed,
            })
            update_meta(run_id,
                        total_discovered=total_discovered,
                        total_filtered=total_filtered)
        else:
            log.info("--skip-discover: loading classified URLs from DB")
            # BUG FIX: load type_maps from DB so crawl has URLs to work with
            type_maps = get_type_maps_from_db(run_id, sources)
            summary["total_discovered"] = "skipped (resumed)"
            summary["total_filtered"] = sum(len(v) for v in type_maps.values())

        # ── Step 3: Crawl ──────────────────────────────────────────────────────
        crawl_results: dict = {}
        if not args.skip_crawl:
            crawl_results = await crawl(type_maps, sources, run_id, skip=False)
            total_crawled = sum(len(v) for v in crawl_results.values())
            summary["total_crawled"] = total_crawled
            update_meta(run_id, total_crawled=total_crawled)
        else:
            log.info("--skip-crawl: loading markdown from crawl cache")
            # BUG FIX: load crawl_results from cache so extract has pages to work with
            crawl_results = get_crawl_results_from_cache(run_id)
            summary["total_crawled"] = sum(len(v) for v in crawl_results.values())

        # ── Step 4: Resolve AMBIGUOUS ──────────────────────────────────────────
        resolved_types: dict = {}
        if not args.skip_extract:
            resolved_types = await resolve(crawl_results, run_id, skip=False)
            summary["ambiguous_resolved"] = len(resolved_types)

        # ── Step 5: Extract ────────────────────────────────────────────────────
        all_items: list = []
        if not args.skip_extract:
            all_items = await extract(
                crawl_results, resolved_types, schemas, sources, run_id, skip=False
            )
        else:
            log.info("--skip-extract: loading from DB")
            all_items = get_all_extracted_items(run_id)

        summary["total_extracted"] = len(all_items)

        # ── Step 6: Deduplicate ────────────────────────────────────────────────
        final_items, total_dupes = dedup(all_items)
        summary["total_dupes"] = total_dupes
        summary["total_final"] = len(final_items)

        # Per-type counts
        by_type: dict = {}
        for item in final_items:
            t = item.get("item_type", "OTHER")
            by_type[t] = by_type.get(t, 0) + 1
        summary["by_type"] = by_type

        update_meta(run_id,
                    total_extracted=len(all_items),
                    total_dupes=total_dupes,
                    total_final=len(final_items))

        # ── Step 7: Save ───────────────────────────────────────────────────────
        output_paths = save(final_items, summary, run_id)
        finish_run(run_id)

    except KeyboardInterrupt:
        log.warning("Pipeline interrupted by user. Progress saved — resume with --run-id " + run_id)
        output_paths = {}
    except Exception as e:
        log.exception(f"Pipeline failed: {e}")
        output_paths = {}

    duration = time.time() - start_time
    _print_summary(summary, output_paths, duration)


if __name__ == "__main__":
    asyncio.run(main())
