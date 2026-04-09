"""
Django management command to generate encrypted URLs for testing
"""
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from main.security.url_encryption.encryption import url_encryption
from main.security.url_encryption.management import generate_encrypted_urls_for_app, test_url_encryption, get_encryption_stats

class Command(BaseCommand):
    help = 'Generate encrypted URLs for all available views'

    def add_arguments(self, parser):
        parser.add_argument(
            '--view',
            type=str,
            help='Generate encrypted URL for specific view name'
        )
        parser.add_argument(
            '--path',
            type=str,
            help='Generate encrypted URL for specific path'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test encryption/decryption cycle'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show encryption system statistics'
        )
        parser.add_argument(
            '--app',
            type=str,
            default='main',
            help='App name to generate URLs for (default: main)'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔐 URL Encryption Generator\n')
        )
        
        if options['stats']:
            self.show_encryption_stats()
        elif options['test']:
            self.test_encryption_system()
        elif options['view']:
            self.generate_for_view(options['view'])
        elif options['path']:
            self.generate_for_path(options['path'])
        else:
            self.generate_all_urls(options['app'])

    def show_encryption_stats(self):
        """Show encryption system statistics"""
        stats = get_encryption_stats()
        
        self.stdout.write("📊 Encryption System Statistics:\n")
        
        if stats['encryption_working']:
            self.stdout.write(self.style.SUCCESS("✅ Encryption system is working"))
            self.stdout.write(f"Test URL: {stats['test_url']}")
            self.stdout.write(f"Encrypted length: {stats['encrypted_length']} characters")
            self.stdout.write(f"Decryption success: {stats['decryption_success']}")
            self.stdout.write(f"Key available: {stats['key_available']}")
        else:
            self.stdout.write(self.style.ERROR("❌ Encryption system has issues"))
            self.stdout.write(f"Error: {stats['error']}")

    def test_encryption_system(self):
        """Test encryption/decryption cycle"""
        test_urls = ['/dashboard/', '/user-management/', '/api/yield-data/']
        
        self.stdout.write("🧪 Testing Encryption/Decryption Cycle:\n")
        
        for url in test_urls:
            result = test_url_encryption(url)
            
            if result['success']:
                status = "✅" if result['cycle_success'] else "❌"
                self.stdout.write(f"{status} {url}")
                self.stdout.write(f"   Original: {result['original']}")
                self.stdout.write(f"   Encrypted: {result['encrypted'][:50]}...")
                self.stdout.write(f"   Decrypted: {result['decrypted']}")
                self.stdout.write(f"   Cycle Success: {result['cycle_success']}")
            else:
                self.stdout.write(f"❌ {url}")
                self.stdout.write(f"   Error: {result['error']}")
            self.stdout.write("-" * 50)

    def generate_for_view(self, view_name):
        """Generate encrypted URL for specific view"""
        try:
            from django.urls import reverse
            original_url = reverse(view_name)
            encrypted_url = url_encryption.encrypt_url(original_url)
            
            self.stdout.write(f"View: {view_name}")
            self.stdout.write(f"Original: {original_url}")
            self.stdout.write(f"Encrypted: /{encrypted_url}")
            self.stdout.write("-" * 50)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error generating URL for {view_name}: {e}")
            )

    def generate_for_path(self, path):
        """Generate encrypted URL for specific path"""
        try:
            encrypted_url = url_encryption.encrypt_url(path)
            
            self.stdout.write(f"Path: {path}")
            self.stdout.write(f"Encrypted: /{encrypted_url}")
            self.stdout.write("-" * 50)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error generating URL for {path}: {e}")
            )

    def generate_all_urls(self, app_name):
        """Generate encrypted URLs for all URLs in an app"""
        encrypted_urls = generate_encrypted_urls_for_app(app_name)
        
        self.stdout.write(f"🔗 Encrypted URLs for {app_name.title()} App:\n")
        
        success_count = 0
        error_count = 0
        
        for view_name, url_info in encrypted_urls.items():
            if 'error' in url_info:
                self.stdout.write(self.style.WARNING(f"❌ {view_name}: {url_info['error']}"))
                error_count += 1
            else:
                self.stdout.write(f"✅ {view_name}")
                self.stdout.write(f"   Original: {url_info['original']}")
                self.stdout.write(f"   Encrypted: /{url_info['encrypted'][:50]}...")
                success_count += 1
            self.stdout.write("-" * 50)
        
        self.stdout.write(f"\n📈 Summary:")
        self.stdout.write(f"   Successful: {success_count}")
        self.stdout.write(f"   Errors: {error_count}")
        self.stdout.write(f"   Total: {success_count + error_count}")
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Encryption complete! Use encrypted URLs to hide your app structure.')
        )