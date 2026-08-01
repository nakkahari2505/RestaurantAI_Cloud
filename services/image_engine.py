from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = [
    # Common Linux / Railway paths
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),

    # Windows
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
]


def find_font_path(
    bold: bool = False,
) -> Path | None:
    """
    Find a usable TrueType font on Windows or Linux.

    Returns None when no supported system font exists.
    """
    preferred_names = (
        [
            "DejaVuSans-Bold.ttf",
            "arialbd.ttf",
        ]
        if bold
        else [
            "DejaVuSans.ttf",
            "arial.ttf",
        ]
    )

    for preferred_name in preferred_names:
        for font_path in FONT_CANDIDATES:
            if (
                font_path.name.lower()
                == preferred_name.lower()
                and font_path.exists()
            ):
                return font_path

    return None


def load_font(
    size: int,
    bold: bool = False,
):
    """
    Load a TrueType font when available.

    If the Railway container has no supported system font,
    fall back to Pillow's built-in font instead of crashing.
    """
    font_path = find_font_path(
        bold=bold,
    )

    if font_path is not None:
        return ImageFont.truetype(
            str(font_path),
            size=size,
        )

    print(
        "Warning: No supported system font found. "
        "Using Pillow default font."
    )

    return ImageFont.load_default()


def create_canvas(
    width: int,
    height: int,
    background: str = "white",
) -> tuple[
    Image.Image,
    ImageDraw.ImageDraw,
]:
    """
    Create a blank image and drawing context.
    """
    image = Image.new(
        "RGB",
        (width, height),
        background,
    )

    draw = ImageDraw.Draw(image)

    return image, draw


def get_text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
) -> int:
    """
    Return rendered text width.
    """
    text_box = draw.textbbox(
        (0, 0),
        text,
        font=font,
    )

    return text_box[2] - text_box[0]


def draw_right_aligned_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    right_x: int,
    y: int,
    font,
    fill: str,
) -> None:
    """
    Draw text ending at the supplied right-side position.
    """
    text_width = get_text_width(
        draw=draw,
        text=text,
        font=font,
    )

    draw.text(
        (
            right_x - text_width,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    left_x: int,
    right_x: int,
    y: int,
    font,
    fill: str,
) -> None:
    """
    Draw text horizontally centred between two positions.
    """
    text_width = get_text_width(
        draw=draw,
        text=text,
        font=font,
    )

    available_width = right_x - left_x

    text_x = (
        left_x
        + (
            available_width
            - text_width
        )
        // 2
    )

    draw.text(
        (
            text_x,
            y,
        ),
        text,
        font=font,
        fill=fill,
    )


def draw_table_row(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    right: int,
    bottom: int,
    background: str,
    border_colour: str,
    border_width: int = 1,
) -> None:
    """
    Draw one rectangular table row.
    """
    draw.rectangle(
        (
            left,
            top,
            right,
            bottom,
        ),
        fill=background,
        outline=border_colour,
        width=border_width,
    )


def draw_status_box(
    draw: ImageDraw.ImageDraw,
    left: int,
    top: int,
    right: int,
    bottom: int,
    heading: str,
    message: str,
    heading_font,
    message_font,
    background: str,
    text_colour: str,
) -> None:
    """
    Draw a rounded success or warning box.
    """
    draw.rounded_rectangle(
        (
            left,
            top,
            right,
            bottom,
        ),
        radius=20,
        fill=background,
    )

    draw.text(
        (
            left + 28,
            top + 22,
        ),
        heading,
        font=heading_font,
        fill=text_colour,
    )

    draw.text(
        (
            left + 28,
            top + 72,
        ),
        message,
        font=message_font,
        fill=text_colour,
    )


def save_png(
    image: Image.Image,
    file_path: Path,
) -> None:
    """
    Save the final image as an optimized PNG.
    """
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.save(
        file_path,
        format="PNG",
        optimize=True,
    )