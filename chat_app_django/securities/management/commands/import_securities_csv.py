from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from securities.models import Security
import csv
import logging
import os

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import securities data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the CSV file to import",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing securities before importing (DANGEROUS)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing data",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing securities if symbol already exists",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        clear_existing = options["clear_existing"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        # Check if CSV file exists
        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file '{csv_file}' not found")

        # Check current securities count
        current_count = Security.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(f"Current securities in database: {current_count}")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be imported")
            )

        # Warning if securities already exist and not clearing
        if current_count > 0 and not clear_existing and not update_existing:
            self.stdout.write(
                self.style.WARNING(
                    f"Database already contains {current_count} securities. "
                    "This may create duplicates. Use --clear-existing or --update-existing."
                )
            )
            confirm = input("Continue anyway? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled")
                return

        if clear_existing and not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"WARNING: This will DELETE all {current_count} existing securities!"
                )
            )
            confirm = input("Are you sure you want to continue? Type 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                self.stdout.write("Operation cancelled")
                return

        # Read and validate CSV file
        try:
            with open(csv_file, 'r', encoding='utf-8') as csvfile:
                # Peek at first line to validate headers
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                has_header = sniffer.has_header(sample)
                
                reader = csv.DictReader(csvfile)
                rows = list(reader)

        except Exception as e:
            raise CommandError(f"Error reading CSV file: {str(e)}")

        if not rows:
            raise CommandError("CSV file is empty or has no valid data")

        self.stdout.write(f"Found {len(rows)} securities in CSV file")

        # Validate required columns
        required_fields = ['symbol', 'name', 'security_type']
        first_row = rows[0]
        missing_fields = [field for field in required_fields if field not in first_row]
        
        if missing_fields:
            raise CommandError(f"Missing required CSV columns: {', '.join(missing_fields)}")

        # Import statistics
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        try:
            with transaction.atomic():
                if clear_existing and not dry_run:
                    self.stdout.write("Clearing existing securities...")
                    Security.objects.all().delete()
                    self.stdout.write("Existing securities cleared")

                for i, row in enumerate(rows, 1):
                    try:
                        symbol = row['symbol'].upper().strip()
                        
                        if not symbol:
                            self.stdout.write(
                                self.style.WARNING(f"Row {i}: Empty symbol, skipping")
                            )
                            stats['skipped'] += 1
                            continue

                        # Parse boolean field
                        is_active = row.get('is_active', 'true').lower() in ('true', '1', 'yes')
                        
                        # Parse datetime fields (optional)
                        created_at = None
                        updated_at = None
                        if row.get('created_at'):
                            created_at = parse_datetime(row['created_at'])
                        if row.get('updated_at'):
                            updated_at = parse_datetime(row['updated_at'])

                        security_data = {
                            'symbol': symbol,
                            'name': row['name'].strip(),
                            'security_type': row['security_type'].strip(),
                            'exchange': row.get('exchange', '').strip(),
                            'sic_description': row.get('sic_description', '').strip(),
                            'logo_url': row.get('logo_url', '').strip(),
                            'is_active': is_active,
                        }

                        if dry_run:
                            self.stdout.write(f"Would import: {symbol} - {security_data['name']}")
                            stats['created'] += 1
                        else:
                            if update_existing:
                                security, created = Security.objects.update_or_create(
                                    symbol=symbol,
                                    defaults=security_data
                                )
                                if created:
                                    stats['created'] += 1
                                else:
                                    stats['updated'] += 1
                            else:
                                # Check if already exists
                                if Security.objects.filter(symbol=symbol).exists():
                                    stats['skipped'] += 1
                                    continue
                                
                                security = Security.objects.create(**security_data)
                                stats['created'] += 1

                        # Progress update
                        if i % 1000 == 0:
                            self.stdout.write(f"Processed {i}/{len(rows)} rows...")

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Row {i} error: {str(e)}")
                        )
                        stats['errors'] += 1
                        logger.error(f"CSV import row {i} error: {str(e)}")

        except Exception as e:
            raise CommandError(f"Error during import: {str(e)}")

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("IMPORT SUMMARY"))
        self.stdout.write(f"Total processed: {len(rows)}")
        self.stdout.write(f"Created: {stats['created']}")
        self.stdout.write(f"Updated: {stats['updated']}")
        self.stdout.write(f"Skipped: {stats['skipped']}")
        self.stdout.write(f"Errors: {stats['errors']}")

        if not dry_run:
            final_count = Security.objects.count()
            active_count = Security.objects.filter(is_active=True).count()
            self.stdout.write(f"\nFinal database counts:")
            self.stdout.write(f"Total securities: {final_count}")
            self.stdout.write(f"Active securities: {active_count}")

        self.stdout.write(
            self.style.SUCCESS("CSV import completed!")
        )