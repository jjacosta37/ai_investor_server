from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from securities.models import Security
from securities.services.fmp_service import get_fmp_service
import logging
import time
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update Security logo URLs using Financial Modeling Prep company profile data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rate-limit",
            type=int,
            default=200,
            help="API calls per minute (default: 200, max recommended: 250 for 300/min limit)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of securities to process per batch (default: 50)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually saving data",
        )
        parser.add_argument(
            "--symbols",
            nargs="+",
            help="Update specific symbols only (e.g., --symbols AAPL MSFT GOOGL)",
        )
        parser.add_argument(
            "--missing-only",
            action="store_true",
            help="Update only securities that don't currently have logo URLs",
        )

    def handle(self, *args, **options):
        rate_limit = options["rate_limit"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        specific_symbols = options["symbols"]
        missing_only = options["missing_only"]

        # Calculate sleep time between requests (in seconds)
        sleep_time = 60.0 / rate_limit if rate_limit > 0 else 0.3

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting logo URL update - Rate limit: {rate_limit}/min "
                f"(~{sleep_time:.2f}s between calls)"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be saved")
            )

        # Initialize FMP service
        try:
            fmp_service = get_fmp_service()
        except ValueError as e:
            raise CommandError(f"Failed to initialize FMP service: {str(e)}")

        # Get securities to update
        securities_queryset = Security.objects.filter(is_active=True)
        
        if specific_symbols:
            securities_queryset = securities_queryset.filter(
                symbol__in=[s.upper() for s in specific_symbols]
            )
            self.stdout.write(f"Processing specific symbols: {', '.join(specific_symbols)}")
        elif missing_only:
            securities_queryset = securities_queryset.filter(logo_url__in=['', None])
            self.stdout.write("Processing only securities without logo URLs")
        else:
            self.stdout.write("Processing ALL securities (will replace existing logos)")

        securities = list(securities_queryset.order_by('symbol'))
        total_securities = len(securities)

        if total_securities == 0:
            self.stdout.write(
                self.style.WARNING("No securities found to update")
            )
            return

        self.stdout.write(f"Found {total_securities} securities to update")

        # Calculate estimated time
        estimated_minutes = (total_securities * sleep_time) / 60
        self.stdout.write(f"Estimated completion time: {estimated_minutes:.1f} minutes")

        # Current logo status
        current_with_logos = Security.objects.exclude(logo_url__in=['', None]).count()
        self.stdout.write(f"Current securities with logos: {current_with_logos}")

        # Process in batches
        total_processed = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0

        start_time = time.time()

        for i in range(0, total_securities, batch_size):
            batch = securities[i : i + batch_size]
            batch_results = self._process_batch(
                batch, fmp_service, sleep_time, dry_run
            )

            total_processed += batch_results["processed"]
            total_updated += batch_results["updated"]
            total_skipped += batch_results["skipped"]
            total_errors += batch_results["errors"]

            # Progress update
            progress = min(i + batch_size, total_securities)
            elapsed_time = time.time() - start_time
            
            self.stdout.write(
                f"Progress: {progress}/{total_securities} "
                f"(Updated: {batch_results['updated']}, "
                f"Skipped: {batch_results['skipped']}, "
                f"Errors: {batch_results['errors']}, "
                f"Elapsed: {elapsed_time/60:.1f}min)"
            )

        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("FINAL SUMMARY"))
        self.stdout.write(f"Total processed: {total_processed}")
        self.stdout.write(f"Total updated: {total_updated}")
        self.stdout.write(f"Total skipped: {total_skipped}")
        self.stdout.write(f"Total errors: {total_errors}")
        self.stdout.write(f"Total time: {elapsed_time/60:.1f} minutes")
        self.stdout.write(f"Average rate: {total_processed/(elapsed_time/60):.1f} securities/minute")

        if not dry_run:
            # Final logo count
            final_with_logos = Security.objects.exclude(logo_url__in=['', None]).count()
            self.stdout.write(f"\nFinal securities with logos: {final_with_logos}")
            self.stdout.write(f"Logo coverage: {(final_with_logos/Security.objects.count())*100:.1f}%")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("This was a dry run - no data was actually saved")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated logos for {total_updated} securities!"
                )
            )

    def _process_batch(
        self, batch: List[Security], fmp_service, sleep_time: float, dry_run: bool
    ) -> Dict[str, int]:
        """Process a batch of securities."""
        results = {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

        for security in batch:
            results["processed"] += 1
            symbol = security.symbol

            try:
                # Fetch company profile data from FMP
                profile_data = fmp_service.get_ticker_details(symbol)
                
                if not profile_data:
                    self.stdout.write(
                        self.style.WARNING(f"No profile data returned for {symbol}")
                    )
                    results["errors"] += 1
                    time.sleep(sleep_time)  # Still respect rate limit on errors
                    continue

                # Extract logo URL from profile data
                new_logo_url = profile_data.get('image', '').strip()
                
                if not new_logo_url:
                    self.stdout.write(
                        self.style.WARNING(f"No logo URL found in profile for {symbol}")
                    )
                    results["skipped"] += 1
                    time.sleep(sleep_time)
                    continue

                # Validate URL format
                if not self._is_valid_url(new_logo_url):
                    self.stdout.write(
                        self.style.WARNING(f"Invalid logo URL format for {symbol}: {new_logo_url}")
                    )
                    results["skipped"] += 1
                    time.sleep(sleep_time)
                    continue

                # Check if logo URL is different (to avoid unnecessary updates)
                if security.logo_url == new_logo_url:
                    results["skipped"] += 1
                    time.sleep(sleep_time)
                    continue

                if dry_run:
                    old_logo = security.logo_url or "(empty)"
                    self.stdout.write(
                        f"Would update {symbol}: {old_logo} -> {new_logo_url}"
                    )
                    results["updated"] += 1
                else:
                    # Update the security logo URL
                    old_logo_url = security.logo_url
                    security.logo_url = new_logo_url
                    security.save(update_fields=['logo_url'])
                    
                    results["updated"] += 1
                    logger.info(
                        f"Updated logo for {symbol}: {old_logo_url or '(empty)'} -> {new_logo_url}"
                    )

                # Respect rate limit
                time.sleep(sleep_time)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {symbol}: {str(e)}")
                )
                results["errors"] += 1
                logger.error(f"Error processing {symbol}: {str(e)}")
                time.sleep(sleep_time)  # Still respect rate limit on errors

        return results

    def _is_valid_url(self, url: str) -> bool:
        """Validate if the provided string is a valid URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False