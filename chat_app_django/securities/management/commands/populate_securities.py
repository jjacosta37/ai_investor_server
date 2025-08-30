from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from securities.models import Security
from securities.services.polygon_service import get_polygon_service
import logging
import time
from typing import List, Dict, Any


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Populate Securities model with stock data from Polygon.io for XNYS and XNAS markets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--exchanges",
            nargs="+",
            default=["XNYS", "XNAS", "ARCX"],
            help="Exchange codes to fetch (default: XNYS XNAS)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="Maximum number of tickers per exchange (default: 1000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating records",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process in each batch (default: 100)",
        )

    def handle(self, *args, **options):
        exchanges = options["exchanges"]
        limit = options["limit"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting securities population for exchanges: {', '.join(exchanges)}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No records will be created")
            )

        try:
            polygon_service = get_polygon_service()
        except ValueError as e:
            raise CommandError(f"Failed to initialize Polygon service: {str(e)}")

        total_processed = 0
        total_created = 0
        total_skipped = 0
        total_errors = 0

        for exchange in exchanges:
            self.stdout.write(f"\nProcessing exchange: {exchange}")

            try:
                # Fetch tickers for this exchange
                tickers = polygon_service.list_tickers_by_exchange(
                    exchange=exchange, limit=limit
                )

                if not tickers:
                    self.stdout.write(
                        self.style.WARNING(f"No tickers found for exchange {exchange}")
                    )
                    continue

                self.stdout.write(f"Found {len(tickers)} tickers for {exchange}")

                # Process tickers in batches
                for i in range(0, len(tickers), batch_size):
                    batch = tickers[i : i + batch_size]
                    batch_results = self._process_batch(
                        batch, polygon_service, dry_run, exchange
                    )

                    total_processed += batch_results["processed"]
                    total_created += batch_results["created"]
                    total_skipped += batch_results["skipped"]
                    total_errors += batch_results["errors"]

                    # Progress update
                    progress = min(i + batch_size, len(tickers))
                    self.stdout.write(
                        f"Progress for {exchange}: {progress}/{len(tickers)} "
                        f"(Created: {batch_results['created']}, "
                        f"Skipped: {batch_results['skipped']}, "
                        f"Errors: {batch_results['errors']})"
                    )

                    # Rate limiting - be nice to the API
                    time.sleep(0.1)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing exchange {exchange}: {str(e)}")
                )
                total_errors += 1
                continue

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(f"Total processed: {total_processed}")
        self.stdout.write(f"Total created: {total_created}")
        self.stdout.write(f"Total skipped: {total_skipped}")
        self.stdout.write(f"Total errors: {total_errors}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "This was a dry run - no records were actually created"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully populated {total_created} securities!"
                )
            )

    def _process_batch(
        self, batch: List[Dict[str, Any]], polygon_service, dry_run: bool, exchange: str
    ) -> Dict[str, int]:
        """Process a batch of tickers."""
        results = {"processed": 0, "created": 0, "skipped": 0, "errors": 0}

        for ticker_data in batch:
            results["processed"] += 1
            symbol = ticker_data.get("symbol", "").upper()

            if not symbol:
                self.stdout.write(
                    self.style.WARNING(f"Skipping ticker with no symbol: {ticker_data}")
                )
                results["skipped"] += 1
                continue

            try:
                # Check if security already exists
                if Security.objects.filter(symbol=symbol).exists():
                    results["skipped"] += 1
                    continue

                # Map Polygon asset types to our security types
                security_type = ticker_data.get("type", "")

                # Only process MVP asset types
                if security_type not in Security.MVP_ASSET_TYPES:
                    results["skipped"] += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"Would create: {symbol} ({ticker_data.get('name', 'N/A')}) "
                        f"- Type: {security_type}"
                    )
                    results["created"] += 1
                else:
                    # Get detailed ticker information
                    detailed_data = polygon_service.get_ticker_details(symbol)

                    if detailed_data:
                        # Use detailed data if available, fall back to basic data
                        name = detailed_data.get("name") or ticker_data.get("name", "")
                        logo_url = detailed_data.get("logo_url", "")
                        market_cap = detailed_data.get("market_cap")
                        sector = detailed_data.get("sic_description") or ""
                    else:
                        # Use basic ticker data
                        name = ticker_data.get("name", "")
                        logo_url = ""
                        market_cap = None
                        sector = ""

                    # Create the security
                    with transaction.atomic():
                        security = Security.objects.create(
                            symbol=symbol,
                            name=name or "",  # Ensure name is never None
                            security_type=security_type,
                            exchange=ticker_data.get("primary_exchange", exchange)
                            or "",
                            sic_description=sector or "",  # Ensure sector is never None
                            logo_url=logo_url or "",
                            is_active=True,
                        )

                    results["created"] += 1
                    logger.info(f"Created security: {symbol}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {symbol}: {str(e)}")
                )
                results["errors"] += 1
                logger.error(f"Error processing {symbol}: {str(e)}")

        return results

    def _map_polygon_type_to_security_type(self, polygon_type: str) -> str:
        """Map Polygon asset types to our Security model types."""
        type_mapping = {
            "CS": "CS",  # Common Stock
            "ETF": "ETF",  # Exchange Traded Fund
            "ADRC": "ADRC",  # American Depository Receipt
        }
        return type_mapping.get(polygon_type, "CS")  # Default to CS
