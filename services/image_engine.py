from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = [
    # Railway / Linux
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),

    # Windows
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
]


def find_font_path(bold: bool = False) -> Path:
    """
    Find a font that works both locally on Windows
    and in the Railway Linux environment.
    """
    preferred_names = (
        ["DejaVuSans-Bold.ttf", "arialbd.ttf"]
        if bold
        else ["DejaVuSans.ttf", "arial.ttf"]
    )

    for preferred_name in preferred_names:
        for font_path in FONT_CANDIDATES:
            if (
                font_path.name.lower()
                == preferred_name.lower()
                and font_path.exists()
            ):
                return font_path

    raise FileNotFoundError(
        "No supported font was found. "
        "Expected DejaVu Sans on Railway or Arial on Windows."
    )


def load_font(
    size: int,
    bold: bool = False,
) -> ImageFont.FreeTypeFont:
    """
    Load a TrueType font using a local system font.
    """
    font_path = find_font_path(bold=bold)

    return ImageFont.truetype(
        str(font_path),
        size=size,
    )


def create_canvas(
    width: int,
    height: int,
    background: str = "white",
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """
    Create a blank image and its drawing object.
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
    font: ImageFont.FreeTypeFont,
) -> int:
    """
    Return the rendered width of a text value.
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
    font: ImageFont.FreeTypeFont,
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
        (right_x - text_width, y),
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
    font: ImageFont.FreeTypeFont,
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
    text_x = left_x + (
        available_width - text_width
    ) // 2

    draw.text(
        (text_x, y),
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
    heading_font: ImageFont.FreeTypeFont,
    message_font: ImageFont.FreeTypeFont,
    background: str,
    text_colour: str,
) -> None:
    """
    Draw a rounded status box for success or warning messages.
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