from django.core.management.base import BaseCommand, CommandError
from securities.models import Security
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export securities data to CSV file for backup or migration"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            type=str,
            default=f"securities_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            help="Output CSV file name (default: securities_export_YYYYMMDD_HHMMSS.csv)",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Export only active securities",
        )
        parser.add_argument(
            "--security-types",
            nargs="+",
            help="Export only specific security types (e.g., --security-types CS ETF)",
        )

    def handle(self, *args, **options):
        output_file = options["output_file"]
        active_only = options["active_only"]
        security_types = options["security_types"]

        # Build queryset based on filters
        queryset = Security.objects.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True)
            
        if security_types:
            queryset = queryset.filter(security_type__in=security_types)
            
        securities = queryset.order_by('symbol')
        total_count = securities.count()

        if total_count == 0:
            self.stdout.write(
                self.style.WARNING("No securities found matching the criteria")
            )
            return

        self.stdout.write(f"Exporting {total_count} securities to {output_file}")

        # Define CSV headers
        fieldnames = [
            'symbol',
            'name',
            'security_type',
            'exchange',
            'sic_description',
            'logo_url',
            'is_active',
            'created_at',
            'updated_at'
        ]

        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                exported_count = 0
                for security in securities:
                    writer.writerow({
                        'symbol': security.symbol,
                        'name': security.name,
                        'security_type': security.security_type,
                        'exchange': security.exchange,
                        'sic_description': security.sic_description,
                        'logo_url': security.logo_url,
                        'is_active': security.is_active,
                        'created_at': security.created_at.isoformat(),
                        'updated_at': security.updated_at.isoformat(),
                    })
                    exported_count += 1

                    # Progress update for large exports
                    if exported_count % 1000 == 0:
                        self.stdout.write(f"Exported {exported_count}/{total_count} securities...")

        except Exception as e:
            raise CommandError(f"Error writing CSV file: {str(e)}")

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("EXPORT SUMMARY"))
        self.stdout.write(f"Total exported: {exported_count}")
        self.stdout.write(f"Output file: {output_file}")
        
        # Show breakdown by security type
        if not security_types:  # Only show breakdown if not filtered by type
            types_breakdown = securities.values('security_type').distinct()
            self.stdout.write("\nSecurity types exported:")
            for type_info in types_breakdown:
                type_name = type_info['security_type']
                type_count = securities.filter(security_type=type_name).count()
                self.stdout.write(f"  {type_name}: {type_count}")

        self.stdout.write(
            self.style.SUCCESS(f"Securities exported successfully to {output_file}!")
        )