from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class APISecurityContractTests(TestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=True)
        self.user_model = get_user_model()
        self.admin_user = self.user_model.objects.create_superuser(
            username="security_admin",
            email="security_admin@example.com",
            password="S3curePass!234",
        )

    def test_unauthenticated_api_request_returns_json_401(self):
        response = self.client.get("/api/unified-dashboard/data/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("application/json", response["Content-Type"])
        payload = response.json()
        self.assertIn("error", payload)

    def test_mutating_api_without_csrf_returns_json_403(self):
        self.client.force_login(self.admin_user)
        response = self.client.post("/api/keys/generate/", {"name": "No CSRF Key"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("application/json", response["Content-Type"])
        payload = response.json()
        self.assertTrue(payload.get("csrf_error", False))

    def test_mutating_api_with_valid_csrf_succeeds(self):
        self.client.force_login(self.admin_user)

        csrf_response = self.client.get("/api/csrf-token/")
        self.assertEqual(csrf_response.status_code, 200)
        csrf_token = csrf_response.json().get("csrfToken")
        self.assertTrue(csrf_token)

        response = self.client.post(
            "/api/keys/generate/",
            {"name": "CSRF Valid Key"},
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["Content-Type"])
        payload = response.json()
        self.assertTrue(payload.get("success", False))
        self.assertIn("key", payload)

