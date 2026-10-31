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

    @patch("user_dashboard.openai_images.requests.post")
    def test_reference_uses_edit_endpoint_with_real_image(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = {"data": [{"b64_json": base64.b64encode(b"png").decode()}]}
        generate_openai_image("same face", "1024x1024", reference_image="data:image/jpeg;base64,YQ==")
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.openai.com/v1/images/edits")
        self.assertEqual(kwargs["json"]["images"], [{"image_url": "data:image/jpeg;base64,YQ=="}])
        self.assertNotIn("input_fidelity", kwargs["json"])


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
        self.assertContains(response, 'name="reference_images" multiple')
        self.assertNotContains(response, "For best face consistency")
        self.assertNotContains(response, "Add a clear face photo")
        self.assertContains(response, "864 × 1536 px")
        self.assertNotContains(response, 'id="styleInput"')

    @patch("user_dashboard.views.generate_openai_image", return_value=b"png-bytes")
    def test_multipart_reference_is_forwarded_and_poster_saved(self, mock_generate):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        output = io.BytesIO()
        Image.new("RGB", (48, 64), "red").save(output, format="PNG")
        response = self.client.post("/user-dashboard/ai-generation/generate/", {
            "prompt": "my pic diwali poster gold happy diwali",
            "reference_image": SimpleUploadedFile("face.png", output.getvalue(), content_type="image/png"),
        })
        self.assertEqual(response.status_code, 200)
        kwargs = mock_generate.call_args.kwargs
        self.assertTrue(kwargs["reference_images"][0].startswith("data:image/jpeg;base64,"))
        self.assertIn("preserve that specific person's identity", kwargs["prompt"])
        self.assertIn("rough wording", kwargs["prompt"])
        self.assertIn("my pic diwali poster gold happy diwali", kwargs["prompt"])
        self.assertEqual(GeneratedPoster.objects.filter(profile=self.profile).count(), 1)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.credits_available, 1)

    @patch("user_dashboard.views.generate_openai_image", return_value=b"png-bytes")
    def test_multiple_references_keep_upload_order(self, mock_generate):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        files = []
        for color in ["red", "blue"]:
            output = io.BytesIO()
            Image.new("RGB", (48, 64), color).save(output, format="PNG")
            files.append(SimpleUploadedFile(color + ".png", output.getvalue(), content_type="image/png"))
        response = self.client.post("/user-dashboard/ai-generation/generate/", {
            "prompt": "use image 1 person and image 2 background", "reference_images": files,
        })
        self.assertEqual(response.status_code, 200)
        refs = mock_generate.call_args.kwargs["reference_images"]
        self.assertEqual(len(refs), 2)
        self.assertNotEqual(refs[0], refs[1])
        self.assertIn("never blend their faces", mock_generate.call_args.kwargs["prompt"])

    @patch("user_dashboard.views.generate_openai_image")
    def test_too_many_references_rejected_without_provider_call(self, mock_generate):
        from django.core.files.uploadedfile import SimpleUploadedFile
        files = [SimpleUploadedFile(str(i) + ".png", b"image") for i in range(9)]
        response = self.client.post("/user-dashboard/ai-generation/generate/", {
            "prompt": "poster", "reference_images": files,
        })
        self.assertEqual(response.status_code, 400)
        mock_generate.assert_not_called()
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.credits_available, 2)

    @patch("user_dashboard.views.generate_openai_image")
    def test_invalid_reference_rejected_without_charge(self, mock_generate):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post("/user-dashboard/ai-generation/generate/", {
            "prompt": "my poster",
            "reference_image": SimpleUploadedFile("fake.png", b"not an image", content_type="image/png"),
        })
        self.assertEqual(response.status_code, 400)
        mock_generate.assert_not_called()
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.credits_available, 2)

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
