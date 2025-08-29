"""
Django management command to update news summaries for watchlisted securities.
"""

import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ai_agents.agents.stock_analysis_agent import StockAnalysisAgent
from securities.services.news_data_transformer import NewsDataTransformer
from securities.models import Security

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update news summaries for all securities in user watchlists using Tavily AI analysis"

    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            "--symbol",
            type=str,
            help="Process only the specified stock symbol (e.g., AAPL)",
        )

        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update existing summaries",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making database changes",
        )

        parser.add_argument(
            "--delay",
            type=int,
            default=2,
            help="Delay in seconds between API calls (default: 2)",
        )

        parser.add_argument(
            "--max-securities", type=int, help="Maximum number of securities to process"
        )

        parser.add_argument(
            "--max-news-items",
            type=int,
            default=20,
            help="Maximum number of news items to keep per security (default: 20)",
        )

        parser.add_argument(
            "--max-events",
            type=int,
            default=20,
            help="Maximum number of upcoming events to keep per security (default: 20)",
        )

        parser.add_argument(
            "--no-cleanup",
            action="store_true",
            help="Skip cleanup operations (keep all items, ignore limits)",
        )

    def handle(self, *args, **options):
        """Main command handler"""

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        try:
            # Initialize services
            self.stdout.write(
                self.style.SUCCESS("Initializing Stock Analysis Service...")
            )
            analysis_service = StockAnalysisAgent()
            transformer = NewsDataTransformer()

            # Determine which securities to process
            securities = self._get_securities_to_process(options)

            if not securities:
                self.stdout.write(self.style.WARNING("No securities found to process"))
                return

            # Apply max limit if specified
            if options["max_securities"]:
                securities = securities[: options["max_securities"]]
                self.stdout.write(
                    self.style.WARNING(
                        f'Limited to {options["max_securities"]} securities'
                    )
                )

            self.stdout.write(
                self.style.SUCCESS(f"Processing {len(securities)} securities...")
            )

            # Show configuration
            if not options["no_cleanup"]:
                self.stdout.write(
                    f'Using limits: {options["max_news_items"]} news items, {options["max_events"]} events per security'
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Cleanup disabled - all items will be kept")
                )

            # Process each security
            processed_count = 0
            error_count = 0

            for i, security in enumerate(securities, 1):
                try:
                    self.stdout.write(
                        f"[{i}/{len(securities)}] Processing {security.symbol} - {security.name}"
                    )

                    if options["dry_run"]:
                        self.stdout.write(
                            self.style.WARNING(
                                f"DRY RUN: Would process {security.symbol}"
                            )
                        )
                        processed_count += 1
                        continue

                    # Get analysis from AI service
                    self.stdout.write(f"  → Getting AI analysis...")
                    analysis = analysis_service.get_stock_analysis(security.symbol)

                    if not analysis:
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ✗ Failed to get analysis for {security.symbol}"
                            )
                        )
                        error_count += 1
                        continue

                    # Validate analysis
                    if not analysis_service.validate_analysis(analysis):
                        self.stdout.write(
                            self.style.ERROR(
                                f"  ✗ Invalid analysis data for {security.symbol}"
                            )
                        )
                        error_count += 1
                        continue

                    # Save to database
                    self.stdout.write(f"  → Saving to database...")

                    with transaction.atomic():
                        news_summary = transformer.save_analysis_to_db(
                            security,
                            analysis,
                            max_news_items=options["max_news_items"],
                            max_events=options["max_events"],
                            skip_cleanup=options["no_cleanup"],
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Saved analysis for {security.symbol}"
                            )
                        )

                        # Show summary statistics
                        self.stdout.write(
                            f"    • Sentiment: {analysis.overall_sentiment.sentiment}"
                        )
                        self.stdout.write(
                            f"    • News items: {len(analysis.recent_news)}"
                        )
                        self.stdout.write(
                            f"    • Events: {len(analysis.upcoming_events)}"
                        )
                        self.stdout.write(
                            f"    • Highlights: {len(analysis.key_highlights)}"
                        )

                    processed_count += 1

                    # Add delay between API calls to avoid rate limiting
                    if i < len(securities) and options["delay"] > 0:
                        self.stdout.write(f'  → Waiting {options["delay"]} seconds...')
                        time.sleep(options["delay"])

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Error processing {security.symbol}: {e}")
                    )
                    logger.exception(f"Error processing {security.symbol}")

                    # Continue with next security
                    continue

            # Final summary
            self.stdout.write(self.style.SUCCESS(f"\n=== Summary ==="))
            self.stdout.write(f"Securities processed: {processed_count}")
            self.stdout.write(f"Errors encountered: {error_count}")

            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(f"Completed with {error_count} errors")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("All securities processed successfully!")
                )

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\nOperation cancelled by user"))
            raise CommandError("Operation cancelled")

        except Exception as e:
            logger.exception("Command failed")
            raise CommandError(f"Command failed: {e}")

    def _get_securities_to_process(self, options):
        """Get list of securities to process based on options"""

        if options["symbol"]:
            # Process single symbol
            security = NewsDataTransformer.get_security_by_symbol(options["symbol"])
            if not security:
                raise CommandError(f'Security not found: {options["symbol"]}')

            self.stdout.write(
                f"Processing single security: {security.symbol} - {security.name}"
            )
            return [security]

        else:
            # Process all watchlisted securities
            self.stdout.write("Finding securities in user watchlists...")
            securities = NewsDataTransformer.get_watchlisted_securities()

            if not securities:
                self.stdout.write(
                    self.style.WARNING("No securities found in watchlists")
                )
                return []

            self.stdout.write(
                f"Found {len(securities)} unique securities in watchlists:"
            )
            for security in securities:
                self.stdout.write(f"  • {security.symbol} - {security.name}")

            return securities
