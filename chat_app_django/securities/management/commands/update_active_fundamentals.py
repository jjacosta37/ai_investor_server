from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from securities.models import Security, SecurityFundamentals, WatchlistItem, Holding
from securities.services.fmp_service import get_fmp_service
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update SecurityFundamentals for stocks that users actively hold or watch"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rate-limit",
            type=int,
            default=250,
            help="API calls per minute (default: 250 for continuous updates)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25,
            help="Number of securities to process per batch (default: 25)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without actually saving data",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging for debugging",
        )

    def handle(self, *args, **options):
        rate_limit = options["rate_limit"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        # Set up logging level
        if verbose:
            logging.getLogger(__name__).setLevel(logging.DEBUG)

        # Calculate sleep time between requests (in seconds)
        sleep_time = 60.0 / rate_limit if rate_limit > 0 else 0.24

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting active securities fundamentals update - Rate limit: {rate_limit}/min "
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

        # Get securities that users actively hold or watch
        active_securities = self._get_active_securities()
        total_securities = len(active_securities)

        if total_securities == 0:
            self.stdout.write(
                self.style.WARNING("No active securities found to update")
            )
            return

        self.stdout.write(f"Found {total_securities} active securities to update")

        # Show breakdown by source
        watchlist_count = WatchlistItem.objects.values('security').distinct().count()
        holdings_count = Holding.objects.values('security').distinct().count()
        self.stdout.write(f"  - From watchlists: {watchlist_count} unique securities")
        self.stdout.write(f"  - From holdings: {holdings_count} unique securities")

        # Calculate estimated time
        estimated_minutes = (total_securities * sleep_time) / 60
        self.stdout.write(f"Estimated completion time: {estimated_minutes:.1f} minutes")

        # Process in batches
        total_processed = 0
        total_updated = 0
        total_created = 0
        total_errors = 0

        start_time = time.time()

        for i in range(0, total_securities, batch_size):
            batch = active_securities[i : i + batch_size]
            batch_results = self._process_batch(
                batch, fmp_service, sleep_time, dry_run, verbose
            )

            total_processed += batch_results["processed"]
            total_updated += batch_results["updated"]
            total_created += batch_results["created"]
            total_errors += batch_results["errors"]

            # Progress update
            progress = min(i + batch_size, total_securities)
            elapsed_time = time.time() - start_time
            
            self.stdout.write(
                f"Progress: {progress}/{total_securities} "
                f"(Updated: {batch_results['updated']}, "
                f"Created: {batch_results['created']}, "
                f"Errors: {batch_results['errors']}, "
                f"Elapsed: {elapsed_time/60:.1f}min)"
            )

        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("ACTIVE SECURITIES UPDATE SUMMARY"))
        self.stdout.write(f"Total processed: {total_processed}")
        self.stdout.write(f"Total updated: {total_updated}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total errors: {total_errors}")
        self.stdout.write(f"Total time: {elapsed_time/60:.1f} minutes")
        self.stdout.write(f"Average rate: {total_processed/(elapsed_time/60):.1f} securities/minute")

        # Log summary for systemd journal
        success_rate = ((total_updated + total_created) / total_processed * 100) if total_processed > 0 else 0
        logger.info(
            f"Active fundamentals update completed: {total_updated + total_created}/{total_processed} "
            f"securities updated ({success_rate:.1f}% success rate) in {elapsed_time/60:.1f} minutes"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("This was a dry run - no data was actually saved")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated fundamentals for {total_updated + total_created} active securities!"
                )
            )

    def _get_active_securities(self) -> List[Security]:
        """
        Get all securities that are actively held or watched by users.
        Returns unique securities sorted by symbol.
        """
        # Get securities from watchlists (using correct relationship name)
        watchlist_securities = Security.objects.filter(
            watchlistitem__isnull=False,
            is_active=True
        ).distinct()

        # Get securities from holdings
        holdings_securities = Security.objects.filter(
            holding__isnull=False,
            is_active=True
        ).distinct()

        # Combine and get unique securities
        active_securities = Security.objects.filter(
            Q(watchlistitem__isnull=False) | Q(holding__isnull=False),
            is_active=True
        ).distinct().order_by('symbol')

        return list(active_securities)

    def _process_batch(
        self, batch: List[Security], fmp_service, sleep_time: float, 
        dry_run: bool, verbose: bool
    ) -> Dict[str, int]:
        """Process a batch of securities."""
        results = {"processed": 0, "updated": 0, "created": 0, "errors": 0}

        for security in batch:
            results["processed"] += 1
            symbol = security.symbol

            try:
                # Fetch quote data from FMP
                quote_data = fmp_service.get_quote(symbol)
                
                if not quote_data:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"No quote data returned for {symbol}")
                        )
                    results["errors"] += 1
                    time.sleep(sleep_time)  # Still respect rate limit on errors
                    continue

                if dry_run:
                    self.stdout.write(
                        f"Would update {symbol}: Price=${quote_data.get('price')}, "
                        f"Volume={quote_data.get('volume')}"
                    )
                    results["updated"] += 1
                else:
                    # Update or create SecurityFundamentals record
                    is_created = self._update_security_fundamentals(security, quote_data, verbose)
                    if is_created:
                        results["created"] += 1
                    else:
                        results["updated"] += 1

                # Respect rate limit
                time.sleep(sleep_time)

            except Exception as e:
                if verbose:
                    self.stdout.write(
                        self.style.ERROR(f"Error processing {symbol}: {str(e)}")
                    )
                results["errors"] += 1
                logger.error(f"Error processing {symbol}: {str(e)}")
                time.sleep(sleep_time)  # Still respect rate limit on errors

        return results

    def _update_security_fundamentals(
        self, security: Security, quote_data: Dict[str, Any], verbose: bool
    ) -> bool:
        """Update or create SecurityFundamentals record. Returns True if created, False if updated."""
        
        # Convert values to Decimal where needed, handling None values
        def to_decimal(value):
            if value is None or value == '':
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError, InvalidOperation):
                return None

        def to_int(value):
            if value is None or value == '':
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        # Prepare the data for SecurityFundamentals
        # Note: day_change_percent is now calculated automatically by the model property
        fundamentals_data = {
            'current_price': to_decimal(quote_data.get('price')),
            'previous_close': to_decimal(quote_data.get('previousClose')),
            'day_change': to_decimal(quote_data.get('change')),
            'market_cap': to_int(quote_data.get('marketCap')),
            'volume': to_int(quote_data.get('volume')),
            'avg_volume': to_int(quote_data.get('avgVolume')),
            'day_high': to_decimal(quote_data.get('dayHigh')),
            'day_low': to_decimal(quote_data.get('dayLow')),
            'open_price': to_decimal(quote_data.get('open')),
            'year_high': to_decimal(quote_data.get('yearHigh')),
            'year_low': to_decimal(quote_data.get('yearLow')),
            'price_avg_50': to_decimal(quote_data.get('priceAvg50')),
            'price_avg_200': to_decimal(quote_data.get('priceAvg200')),
            'exchange_name': quote_data.get('exchange', '')[:50],  # Ensure field length limit
            'data_timestamp': to_int(quote_data.get('timestamp')),
        }

        # Remove None values to avoid overwriting existing data with None
        fundamentals_data = {k: v for k, v in fundamentals_data.items() if v is not None}

        try:
            with transaction.atomic():
                fundamentals, created = SecurityFundamentals.objects.get_or_create(
                    security=security,
                    defaults=fundamentals_data
                )
                
                if not created:
                    # Update existing record
                    for field, value in fundamentals_data.items():
                        setattr(fundamentals, field, value)
                    fundamentals.save()

                if verbose:
                    logger.info(
                        f"{'Created' if created else 'Updated'} fundamentals for {security.symbol}"
                    )
                
                return created

        except Exception as e:
            logger.error(f"Error saving fundamentals for {security.symbol}: {str(e)}")
            raise