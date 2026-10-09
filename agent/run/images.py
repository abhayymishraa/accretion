"""Screenshots resized for the model and cut to the project card's cover."""

import io

from PIL import Image, ImageOps

# What a vision model gets; the stored original the user sees is untouched. Anthropic's standard tier
# reads up to 1568px on the long edge and bills by size, not bytes; chrome-devtools-mcp and browser-use
# downscale to JPEG for the same reason (agent-browser's own JPEG default is quality 80).
MODEL_IMAGE_EDGE = 1568
MAX_MODEL_ASPECT = 2.5
# The project list's card image: 16:10, twice the widest card (3 columns of ~320px CSS px).
COVER_SIZE = (640, 400)
MAX_COVER_BYTES = 200_000


def shrink_for_model(data: bytes) -> tuple[bytes, bool]:
    """A JPEG a model can read, and whether a very tall page was cut to its top."""
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGB")
    # Fitting an 8000px-tall page into 1568px leaves text a few pixels high; keep the top instead. A phone
    # viewport (390x844) is about 2.2 tall, so only full-page captures pass 2.5.
    cropped = image.height > MAX_MODEL_ASPECT * image.width
    if cropped:
        image = image.crop((0, 0, image.width, int(MAX_MODEL_ASPECT * image.width)))
    image.thumbnail((MODEL_IMAGE_EDGE, MODEL_IMAGE_EDGE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=80, optimize=True)
    return buffer.getvalue(), cropped


def cover_image(data: bytes) -> bytes:
    """A screenshot cut to the card's shape from its top, where an app's header and hero are."""
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.fit(source.convert("RGB"), COVER_SIZE, Image.Resampling.LANCZOS, centering=(0.5, 0))
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=75)
    return buffer.getvalue()
