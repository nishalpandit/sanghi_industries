import base64
import json
import tempfile
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from users.models import GeneratedPoster, Profile
from .openai_images import OpenAIImageError, generate_openai_image
from .views import OPENAI_IMAGE_SIZES, resolve_openai_image_size


@override_settings(
    OPENAI_API_KEY="test-key",
    OPENAI_IMAGE_MODEL="gpt-image-2.5-sunburst",
    OPENAI_IMAGE_QUALITY="high",
)
class OpenAIImageClientTests(TestCase):
    @patch("user_dashboard.openai_images.requests.post")
    def test_generates_png_with_expected_openai_payload(self, mock_post):
        expected_image = b"generated-png-bytes"
        response = Mock(status_code=200)
        response.json.return_value = {
            "data": [{"b64_json": base64.b64encode(expected_image).decode("ascii")}]
        }
        mock_post.return_value = response

        result = generate_openai_image(
            prompt="A polished festival poster",
            size="864x1536",
            safety_identifier="hashed-user-id",
        )

        self.assertEqual(result, expected_image)
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["model"], "gpt-image-2.5-sunburst")
        self.assertEqual(kwargs["json"]["size"], "864x1536")
        self.assertEqual(kwargs["json"]["quality"], "high")
        self.assertEqual(kwargs["json"]["output_format"], "png")
        self.assertEqual(kwargs["json"]["safety_identifier"], "hashed-user-id")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")


@override_settings(
    OPENAI_API_KEY="test-key",
    OPENAI_IMAGE_MODEL="gpt-image-2.5-sunburst",
    OPENAI_IMAGE_QUALITY="high",
)
class AIGenerationViewTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()

        self.user = User.objects.create_user(username="poster-user", password="password")
        self.profile = Profile.objects.create(user=self.user, mobile_number="9876543210")
        self.subscription = self.profile.subscription
        self.subscription.plan_name = "Pro"
        self.subscription.credits_available = 2
        self.subscription.save()
        self.client.force_login(self.user)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

    def test_ai_generation_route_renders_openai_ui(self):
        response = self.client.get("/user-dashboard/ai-generation/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your poster")
        self.assertContains(response, "Generating with OpenAI...")
        self.assertContains(response, "Choose a canvas")
        self.assertContains(response, "864 × 1536 px")
        self.assertNotContains(response, 'id="styleInput"')

    def test_all_ratio_presets_meet_openai_size_constraints(self):
        for aspect_ratio, size in OPENAI_IMAGE_SIZES.items():
            with self.subTest(aspect_ratio=aspect_ratio):
                width, height = (int(value) for value in size.split("x"))
                self.assertEqual(width % 16, 0)
                self.assertEqual(height % 16, 0)
                self.assertGreaterEqual(width * height, 655_360)
                self.assertGreaterEqual(width / height, 1 / 3)
                self.assertLessEqual(width / height, 3)

        self.assertEqual(resolve_openai_image_size("unknown"), "1024x1024")

    @patch("user_dashboard.views.generate_openai_image", return_value=b"png-bytes")
    def test_success_saves_image_and_deducts_one_credit(self, mock_generate):
        response = self.client.post(
            "/user-dashboard/ai-generation/generate/",
            data=json.dumps({
                "prompt": "A modern Diwali sale poster",
                "aspect_ratio": "9:16",
                "color_theme": "#663399",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["credits_available"], 1)
        self.assertEqual(GeneratedPoster.objects.filter(profile=self.profile).count(), 1)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.credits_available, 1)
        self.assertEqual(mock_generate.call_args.kwargs["size"], "864x1536")
        self.assertIn("polished poster design", mock_generate.call_args.kwargs["prompt"])

        download = self.client.get(payload["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "image/png")

    @patch(
        "user_dashboard.views.generate_openai_image",
        side_effect=OpenAIImageError("provider unavailable"),
    )
    def test_openai_failure_does_not_deduct_credit(self, _mock_generate):
        response = self.client.post(
            "/user-dashboard/ai-generation/generate/",
            data=json.dumps({"prompt": "A professional launch poster"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json()["success"])
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.credits_available, 2)
        self.assertFalse(GeneratedPoster.objects.filter(profile=self.profile).exists())
