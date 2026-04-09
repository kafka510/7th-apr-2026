"""
Test that Celery workers are active and functional with the current config.

Run: python manage.py test_celery_workers [--no-email]

1. Checks broker connection and that at least one worker responds to ping.
2. Dispatches a task that sends a test email via a worker (unless --no-email).
3. Reports success or failure.

Ensure workers are running (e.g. celery -A web_app worker -Q data_acquisition,default -l info)
and CELERY_BROKER_URL is set (e.g. redis://localhost:6379/0 or redis://redis:6379/0 in Docker).
"""

import sys

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test that Celery workers are active and functional; optionally send a test email via a worker"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-email",
            action="store_true",
            help="Only check broker and worker ping; do not send the test email.",
        )
        parser.add_argument(
            "--email",
            type=str,
            default=None,
            help="Send test email to this address (default: SECURITY_ALERT_EMAIL or DEFAULT_FROM_EMAIL).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Seconds to wait for the test task (default: 30).",
        )

    def handle(self, *args, **options):
        send_email = not options["no_email"]
        recipient = options["email"]
        timeout = options["timeout"]

        self.stdout.write("Testing Celery workers and config...")
        errors = []

        # 1. Broker URL
        broker = getattr(settings, "CELERY_BROKER_URL", None) or ""
        if not broker or broker.startswith("memory://"):
            self.stdout.write(
                self.style.WARNING(
                    "  CELERY_BROKER_URL is not set or is memory://. Workers in other processes won't receive tasks."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"  Broker: {broker}"))

        # 2. Ping workers
        try:
            from web_app.celery_app import app
            reply = app.control.ping(timeout=timeout)
            if not reply:
                errors.append("No workers responded to ping. Start workers: celery -A web_app worker -Q data_acquisition,default -l info")
            else:
                self.stdout.write(self.style.SUCCESS(f"  Workers responded: {list(reply)}"))
        except Exception as e:
            errors.append(f"Could not ping workers: {e}")

        if errors:
            for msg in errors:
                self.stderr.write(self.style.ERROR(f"  {msg}"))
            self.stdout.write("")
            self.stderr.write(self.style.ERROR("Celery worker check failed. Fix the issues above and run again."))
            sys.exit(1)

        if not send_email:
            self.stdout.write(self.style.SUCCESS("\nWorker ping OK (--no-email: no test email sent)."))
            return

        # 3. Send test email via worker
        from data_collection.tasks import send_celery_test_email

        result_backend = getattr(settings, "CELERY_RESULT_BACKEND", None) or ""
        if not result_backend or str(result_backend).strip().lower().startswith("disabled"):
            self.stdout.write(
                self.style.WARNING(
                    "\nCELERY_RESULT_BACKEND is not set or is disabled. Task was sent to the worker, "
                    "but we cannot wait for the result. Check the inbox for the test email."
                )
            )
            self.stdout.write(
                "To get confirmation in this command, set in .env: CELERY_RESULT_BACKEND=redis://redis:6379/0"
            )
            send_celery_test_email.delay(recipient_email=recipient)
            self.stdout.write(self.style.SUCCESS("Task dispatched. Check your inbox."))
            return

        self.stdout.write("Sending test email via Celery worker...")
        try:
            result = send_celery_test_email.delay(recipient_email=recipient).get(timeout=timeout)
            if result.get("success"):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nTest email sent successfully to: {result.get('recipient', '?')}"
                    )
                )
                self.stdout.write("Check the inbox to confirm delivery (and that EMAIL_* settings are correct).")
            else:
                self.stderr.write(
                    self.style.ERROR(f"\nTask ran but email failed: {result.get('error', 'unknown')}")
                )
                sys.exit(1)
        except Exception as e:
            err_msg = str(e).strip().lower()
            if "no result backend" in err_msg or "result backend" in err_msg:
                self.stdout.write(
                    self.style.WARNING(
                        "\nNo result backend configured; cannot wait for task result. "
                        "The task was sent to the worker—check your inbox for the test email."
                    )
                )
                self.stdout.write(
                    "To get confirmation here, set in .env: CELERY_RESULT_BACKEND=redis://redis:6379/0"
                )
                return
            self.stderr.write(
                self.style.ERROR(f"\nTask did not complete within {timeout}s or failed: {e}")
            )
            self.stderr.write("Ensure a worker is consuming the default queue: celery -A web_app worker -Q data_acquisition,default -l info")
            sys.exit(1)
