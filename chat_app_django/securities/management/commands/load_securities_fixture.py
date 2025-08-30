from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
from securities.models import Security
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load securities data from fixture file for production deployment"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture-file",
            type=str,
            default="securities_fixture.json",
            help="Path to the securities fixture file (default: securities_fixture.json)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing securities before loading fixture (DANGEROUS)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be loaded without actually loading data",
        )

    def handle(self, *args, **options):
        fixture_file = options["fixture_file"]
        clear_existing = options["clear_existing"]
        dry_run = options["dry_run"]

        # Check if fixture file exists
        if not os.path.exists(fixture_file):
            raise CommandError(f"Fixture file '{fixture_file}' not found")

        # Check current securities count
        current_count = Security.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(f"Current securities in database: {current_count}")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be loaded")
            )

        # Warning if securities already exist and not clearing
        if current_count > 0 and not clear_existing:
            self.stdout.write(
                self.style.WARNING(
                    f"Database already contains {current_count} securities. "
                    "This may create duplicates. Use --clear-existing to clear first."
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

        try:
            with transaction.atomic():
                if clear_existing and not dry_run:
                    self.stdout.write("Clearing existing securities...")
                    Security.objects.all().delete()
                    self.stdout.write("Existing securities cleared")

                if dry_run:
                    self.stdout.write(f"Would load fixture from: {fixture_file}")
                else:
                    self.stdout.write(f"Loading securities fixture from: {fixture_file}")
                    
                    # Load the fixture
                    call_command('loaddata', fixture_file, verbosity=0)
                    
                    new_count = Security.objects.count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully loaded {new_count} securities from fixture"
                        )
                    )

        except Exception as e:
            raise CommandError(f"Error loading fixture: {str(e)}")

        if not dry_run:
            # Final summary
            final_count = Security.objects.count()
            active_count = Security.objects.filter(is_active=True).count()
            
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("LOAD SUMMARY"))
            self.stdout.write(f"Total securities: {final_count}")
            self.stdout.write(f"Active securities: {active_count}")
            self.stdout.write(f"Inactive securities: {final_count - active_count}")
            
            # Show breakdown by security type
            types_breakdown = Security.objects.values('security_type').distinct()
            self.stdout.write("\nSecurity types:")
            for type_info in types_breakdown:
                type_name = type_info['security_type']
                type_count = Security.objects.filter(security_type=type_name).count()
                self.stdout.write(f"  {type_name}: {type_count}")

        self.stdout.write(
            self.style.SUCCESS("Securities fixture load completed!")
        )