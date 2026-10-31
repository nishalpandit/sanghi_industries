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


def generate_openai_image(prompt, size, safety_identifier=None, reference_image=None, reference_images=None):
    """Generate one PNG image and return its decoded bytes."""
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
        raise OpenAIImageError(message)

    try:
        encoded_image = response_data["data"][0]["b64_json"]
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise OpenAIImageError("OpenAI did not return valid image data.") from exc

    if not image_bytes:
        raise OpenAIImageError("OpenAI returned an empty image.")

    return image_bytes
