from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from securities.models import Security, SecurityFundamentals
from securities.services.fmp_service import get_fmp_service
import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update SecurityFundamentals with financial data from Financial Modeling Prep API"

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
            "--force-update",
            action="store_true",
            help="Update all records regardless of when they were last updated",
        )
        parser.add_argument(
            "--symbols",
            nargs="+",
            help="Update specific symbols only (e.g., --symbols AAPL MSFT GOOGL)",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Skip records updated within the last 24 hours (default behavior)",
        )

    def handle(self, *args, **options):
        rate_limit = options["rate_limit"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        force_update = options["force_update"]
        specific_symbols = options["symbols"]
        resume = options["resume"]

        # Calculate sleep time between requests (in seconds)
        sleep_time = 60.0 / rate_limit if rate_limit > 0 else 0.3

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting fundamentals update - Rate limit: {rate_limit}/min "
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
        
        # Filter out recently updated records unless force update is specified
        if not force_update:
            cutoff_time = timezone.now() - timedelta(hours=24)
            securities_queryset = securities_queryset.exclude(
                fundamentals__last_updated__gte=cutoff_time
            )

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

        # Process in batches
        total_processed = 0
        total_updated = 0
        total_created = 0
        total_errors = 0

        start_time = time.time()

        for i in range(0, total_securities, batch_size):
            batch = securities[i : i + batch_size]
            batch_results = self._process_batch(
                batch, fmp_service, sleep_time, dry_run
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
        self.stdout.write(self.style.SUCCESS("FINAL SUMMARY"))
        self.stdout.write(f"Total processed: {total_processed}")
        self.stdout.write(f"Total updated: {total_updated}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total errors: {total_errors}")
        self.stdout.write(f"Total time: {elapsed_time/60:.1f} minutes")
        self.stdout.write(f"Average rate: {total_processed/(elapsed_time/60):.1f} securities/minute")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("This was a dry run - no data was actually saved")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated fundamentals for {total_updated + total_created} securities!"
                )
            )

    def _process_batch(
        self, batch: List[Security], fmp_service, sleep_time: float, dry_run: bool
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
                    self.stdout.write(
                        self.style.WARNING(f"No quote data returned for {symbol}")
                    )
                    results["errors"] += 1
                    time.sleep(sleep_time)  # Still respect rate limit on errors
                    continue

                if dry_run:
                    self.stdout.write(
                        f"Would update {symbol}: Price={quote_data.get('price')}, "
                        f"Market Cap={quote_data.get('marketCap')}"
                    )
                    results["updated"] += 1
                else:
                    # Update or create SecurityFundamentals record
                    is_created = self._update_security_fundamentals(security, quote_data)
                    if is_created:
                        results["created"] += 1
                    else:
                        results["updated"] += 1

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

    def _update_security_fundamentals(
        self, security: Security, quote_data: Dict[str, Any]
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
        fundamentals_data = {
            'current_price': to_decimal(quote_data.get('price')),
            'previous_close': to_decimal(quote_data.get('previousClose')),
            'day_change': to_decimal(quote_data.get('change')),
            'day_change_percent': to_decimal(quote_data.get('changesPercentage')),
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

                logger.info(
                    f"{'Created' if created else 'Updated'} fundamentals for {security.symbol}"
                )
                
                return created

        except Exception as e:
            logger.error(f"Error saving fundamentals for {security.symbol}: {str(e)}")
            raise