"""OutreachPilot CLI entry point.

Usage:
    python -m outreachpilot scan --reddit          # Run Reddit scan (same as old script)
    python -m outreachpilot scan --reddit --csv     # Scan and export to CSV too
    python -m outreachpilot serve                   # Start web UI (Phase 1)
"""

import argparse
import datetime
import logging
import sys
import time

logger = logging.getLogger("outreachpilot")


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_scan(args):
    """Run a scan — equivalent to the original reddit_outreach.py."""
    from outreachpilot.config import (
        load_subreddits, load_personality, load_filters,
        get_max_post_age_hours, SPREADSHEET_ID, ensure_data_dirs,
    )
    from outreachpilot.scanners.reddit import RedditScanner
    from outreachpilot.filters.rule_filter import apply_pre_filters
    from outreachpilot.analyzers.pipeline import analyze_signal
    from outreachpilot.exporters.google_sheets import GoogleSheetsExporter
    from outreachpilot.exporters.csv_exporter import CSVExporter
    from outreachpilot.storage.progress import load_progress, save_progress
    from outreachpilot.storage.signals import save_signals

    ensure_data_dirs()

    today = datetime.date.today().isoformat()
    personality = load_personality()
    filters = load_filters()
    max_age = get_max_post_age_hours(filters)

    # Load subreddits
    sub_file = args.subreddits if args.subreddits else "subreddits.yml"
    subreddits = load_subreddits(sub_file)

    logger.info("OutreachPilot Sweep – %s", today)
    logger.info("Scanning %d subreddits for posts from the last %dh", len(subreddits), max_age)

    # Initialize exporter
    sheets_exporter = None
    tab_name = None
    if not args.no_sheets and SPREADSHEET_ID:
        sheets_exporter = GoogleSheetsExporter()
        logger.info("Authenticating with Google Sheets...")
        tab_name = sheets_exporter.get_or_create_daily_tab(today)

    csv_exporter = CSVExporter() if args.csv else None

    # Load checkpoint
    progress = load_progress()
    logger.info(
        "Progress: %d/%d subreddits done, %d rows written",
        len(progress["completed_subs"]), len(subreddits), progress["total_written"],
    )

    # Scan
    scanner = RedditScanner()
    pending_rows = []        # buffer for the next Sheets flush (cleared per subreddit)
    all_rows = []            # every row produced this run (kept for CSV + fallback)
    all_signal_dicts = []

    try:
        for i, subreddit in enumerate(subreddits, 1):
            if subreddit in progress["completed_subs"]:
                continue

            logger.info("[%d/%d] r/%s", i, len(subreddits), subreddit)

            # Fetch signals for this subreddit
            signals = scanner.scan([subreddit], max_age_hours=max_age)
            raw_count = len(signals)
            signals = apply_pre_filters(signals, filters)

            if not signals:
                if raw_count:
                    logger.info("  No posts in last %dh (fetched %d, all filtered out)", max_age, raw_count)
                else:
                    logger.info("  No posts in last %dh", max_age)
                empty_row = {
                    "Subreddit": f"r/{subreddit}",
                    "Post title": "[No last-24h post detected in accessible /new snapshot]",
                    "Post link": "",
                    "Status": "inactive",
                    "Summary": f"Newest accessible post in the /new feed appeared far older "
                               f"than {max_age} hours, so this subreddit looked "
                               f"quiet for today's sweep.",
                    "Coolest comment": "no cool comments",
                    "Suggested reply to cool comment": "\u2014",
                    "Suggested post comment": "\u2014",
                    "Engage?": "No",
                    "Why": "",
                    "Source URL(s)": f"https://www.reddit.com/r/{subreddit}/new/.json?limit=5",
                    "Created UTC": "",
                    "Age (hrs)": "",
                }
                pending_rows.append(empty_row)
                all_rows.append(empty_row)
            else:
                logger.info("  Found %d posts (from %d raw)", len(signals), raw_count)
                for signal in signals:
                    if signal.platform_id in progress["processed_ids"]:
                        continue

                    # Analyze with AI
                    analysis = analyze_signal(signal, personality=personality, filters=filters)

                    # Calculate age
                    age_hrs = round((time.time() - signal.created_utc) / 3600, 1)
                    created_str = (
                        datetime.datetime.utcfromtimestamp(signal.created_utc)
                        .strftime("%Y-%m-%d %H:%M")
                        if signal.created_utc else ""
                    )

                    source_urls = (
                        f"https://www.reddit.com/r/{subreddit}/new/.json?limit=5 ; "
                        f"https://www.reddit.com/r/{subreddit}/comments/{signal.platform_id}/.json?limit=10"
                    )

                    engage = analysis.engage
                    show = engage == "Yes"

                    row = {
                        "Subreddit": f"r/{subreddit}",
                        "Post title": signal.title,
                        "Post link": signal.url,
                        "Status": signal.status,
                        "Summary": analysis.summary,
                        "Coolest comment": analysis.coolest_comment if show else "\u2014",
                        "Suggested reply to cool comment": analysis.suggested_reply if show else "\u2014",
                        "Suggested post comment": analysis.suggested_post_comment if show else "\u2014",
                        "Engage?": engage,
                        "Why": analysis.why if show else "",
                        "Source URL(s)": source_urls,
                        "Created UTC": created_str,
                        "Age (hrs)": str(age_hrs),
                    }
                    pending_rows.append(row)
                    all_rows.append(row)

                    # Also build a signal dict for local storage
                    all_signal_dicts.append({
                        "id": f"reddit_{signal.platform_id}",
                        "platform": "reddit",
                        "platform_id": signal.platform_id,
                        "url": signal.url,
                        "title": signal.title,
                        "body": signal.body[:500],
                        "author": signal.author,
                        "subreddit": subreddit,
                        "score": signal.score,
                        "reply_count": signal.reply_count,
                        "created_utc": signal.created_utc,
                        "status": signal.status,
                        "analysis": {
                            "summary": analysis.summary,
                            "engage": analysis.engage,
                            "why": analysis.why,
                            "coolest_comment": analysis.coolest_comment,
                            "suggested_reply": analysis.suggested_reply,
                            "suggested_comment": analysis.suggested_post_comment,
                        },
                    })

                    progress["processed_ids"].add(signal.platform_id)

            # Write batch for this subreddit
            if pending_rows and sheets_exporter and tab_name:
                sheets_exporter.append_rows(tab_name, pending_rows)
                progress["total_written"] += len(pending_rows)
                pending_rows = []

            progress["completed_subs"].add(subreddit)
            save_progress(progress)

    except KeyboardInterrupt:
        logger.info("Interrupted! Saving progress...")
    finally:
        # Flush remaining rows
        if pending_rows:
            if sheets_exporter and tab_name:
                try:
                    sheets_exporter.append_rows(tab_name, pending_rows)
                    progress["total_written"] += len(pending_rows)
                except Exception as e:
                    sheets_exporter.save_fallback(pending_rows)
                    logger.error("Sheet write failed (%s), saved to fallback", e)

        # Save signals to local storage
        if all_signal_dicts:
            save_signals(all_signal_dicts)

        # CSV export — uses all_rows (every row produced this run), not the
        # Sheets-flush buffer which gets cleared per subreddit.
        if csv_exporter and all_rows:
            csv_exporter.export(
                all_rows,
                config={"filename": f"outreach_{today}.csv"},
            )

        save_progress(progress)
        logger.info("Done! %d total rows written", progress["total_written"])
        if SPREADSHEET_ID:
            logger.info("Sheet: https://docs.google.com/spreadsheets/d/%s", SPREADSHEET_ID)


def cmd_serve(args):
    """Start the web UI server."""
    import uvicorn
    from outreachpilot.config import ensure_data_dirs
    ensure_data_dirs()
    logger.info("Starting OutreachPilot web UI on http://localhost:%d", args.port)
    uvicorn.run("outreachpilot.app:create_app", factory=True, host="0.0.0.0",
                port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(
        prog="outreachpilot",
        description="OutreachPilot — Open source AI outreach intelligence tool",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Run an outreach scan")
    scan_parser.add_argument("--reddit", action="store_true", default=True,
                             help="Scan Reddit (default)")
    scan_parser.add_argument("--subreddits", type=str, default=None,
                             help="YAML file with subreddit list (default: subreddits.yml)")
    scan_parser.add_argument("--csv", action="store_true",
                             help="Also export to CSV")
    scan_parser.add_argument("--no-sheets", action="store_true",
                             help="Skip Google Sheets export")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the web UI")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
