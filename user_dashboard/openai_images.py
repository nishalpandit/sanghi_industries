"""OpenAI Images API integration for poster generation."""

import base64
import os

import requests
from django.conf import settings


OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"


class OpenAIImageError(Exception):
    """Raised when OpenAI cannot generate or return an image."""


class OpenAIImageConfigurationError(OpenAIImageError):
    """Raised when the OpenAI image integration is not configured."""


class OpenAIBillingQuotaError(OpenAIImageError):
    """Raised when the OpenAI account has run out of credits or reached its billing quota."""


class OpenAISafetyError(OpenAIImageError):
    """Raised when OpenAI's content safety/moderation filter flags or rejects a prompt or image."""


def generate_openai_image(prompt, size, safety_identifier=None, reference_image=None, reference_images=None):
    """Generate one PNG image and return its decoded bytes."""
    mock_mode = (
        getattr(settings, "MOCK_AI_GENERATION", False)
        or os.getenv("MOCK_AI_GENERATION", "false").strip().lower() in ("true", "1", "yes")
    )
    if mock_mode:
        return generate_mock_poster(prompt, size)

    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    api_key = api_key.strip() if api_key else ""
    if not api_key:
        raise OpenAIImageConfigurationError(
            "OpenAI API key is missing. Add OPENAI_API_KEY to the project .env file."
        )

    model = getattr(settings, "OPENAI_IMAGE_MODEL", "") or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-sunburst")
    quality = getattr(settings, "OPENAI_IMAGE_QUALITY", "") or os.getenv("OPENAI_IMAGE_QUALITY", "high")

    payload = {
        "model": model.strip(),
        "prompt": prompt,
        "size": size,
        "quality": quality.strip(),
        "output_format": "png",
        "background": "opaque",
        "n": 1,
    }
    if safety_identifier:
        payload["safety_identifier"] = safety_identifier

    endpoint = OPENAI_IMAGES_URL
    references = reference_images or ([reference_image] if reference_image else [])
    if references:
        endpoint = "https://api.openai.com/v1/images/edits"
        payload["images"] = [{"image_url": image} for image in references]
        if model.strip() == "gpt-image-1.5":
            payload["input_fidelity"] = "high"

    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )
    except requests.RequestException as exc:
        raise OpenAIImageError(f"Could not connect to OpenAI: {exc}") from exc

    try:
        response_data = response.json()
    except ValueError as exc:
        raise OpenAIImageError(
            f"OpenAI returned an invalid response (HTTP {response.status_code})."
        ) from exc

    if response.status_code != 200:
        error = response_data.get("error", {})
        message = error.get("message") or f"OpenAI returned HTTP {response.status_code}."
        code = error.get("code")
        err_type = error.get("type")
        msg_lower = (message or "").lower()

        if code in ("credit_balance_exhausted", "insufficient_quota") or err_type == "insufficient_quota":
            raise OpenAIBillingQuotaError(
                "You have no credits remaining on your OpenAI account. "
                "Add credits at https://platform.openai.com/settings/organization/billing/ "
                "or update OPENAI_API_KEY in .env."
            )

        if (
            code in ("safety_system_rejection", "content_policy_violation")
            or err_type in ("safety_system_rejection", "content_policy_violation")
            or "rejected by the safety system" in msg_lower
            or "safety system" in msg_lower
            or "content policy" in msg_lower
        ):
            raise OpenAISafetyError(
                "Your request was rejected by OpenAI's safety system. "
                "This usually happens when the description or uploaded photo contains real public figures, "
                "politicians, sensitive words, or policy-restricted content. "
                "Please simplify your description, remove sensitive names, or try with a different reference photo."
            )

        raise OpenAIImageError(message)

    try:
        encoded_image = response_data["data"][0]["b64_json"]
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise OpenAIImageError("OpenAI did not return valid image data.") from exc

    if not image_bytes:
        raise OpenAIImageError("OpenAI returned an empty image.")

    return image_bytes

def generate_mock_poster(prompt, size):
    """Generate a placeholder poster PNG for local testing when OpenAI is unavailable."""
    import io
    from PIL import Image, ImageDraw, ImageFont

    try:
        w, h = [int(v) for v in size.split("x")]
    except Exception:
        w, h = 1024, 1024

    img = Image.new("RGB", (w, h), (18, 16, 38))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        r = int(18 + (y / h) * 45)
        g = int(16 + (y / h) * 20)
        b = int(38 + (y / h) * 60)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    margin = int(min(w, h) * 0.05)
    draw.rectangle([(margin, margin), (w - margin, h - margin)], outline=(255, 255, 255), width=3)

    try:
        font_large = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", int(min(w, h) * 0.06))
        font_small = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", int(min(w, h) * 0.035))
    except Exception:
        font_large = font_small = ImageFont.load_default()

    draw.text((w // 2, margin + 50), "SMART FLEX AI", fill=(255, 215, 0), font=font_large, anchor="mm")
    
    snippet = (prompt[:120] + "...") if len(prompt) > 120 else prompt
    draw.text((w // 2, h // 2), snippet, fill=(240, 240, 240), font=font_small, anchor="mm")
    
    draw.text((w // 2, h - margin - 50), f"Demo Mode • {size}", fill=(180, 180, 200), font=font_small, anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
