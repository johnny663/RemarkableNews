import io

# reMarkable Paper Pro Move screen is ~954 x 1696 px (a small ~7.3" panel).
# Match that aspect ratio (in PDF points) so pages fill the screen with no
# wasted margins. 4.7in x 8.35in.
PAGE_SIZE = (4.7 * 72, 8.35 * 72)


def resize_pdf_to_move(pdf_bytes: bytes) -> bytes:
    """Rescale every page of a PDF to fill the Move screen, preserving layout.

    Newspaper pages arrive at broadsheet dimensions. Each page is scaled to
    fit inside PAGE_SIZE (no cropping) and centered, so the whole page is
    visible at the device's aspect ratio.
    """
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation

    target_w, target_h = PAGE_SIZE
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    for src in reader.pages:
        w = float(src.mediabox.width)
        h = float(src.mediabox.height)
        scale = min(target_w / w, target_h / h)
        tx = (target_w - w * scale) / 2
        ty = (target_h - h * scale) / 2

        page = PageObject.create_blank_page(width=target_w, height=target_h)
        page.merge_transformed_page(src, Transformation().scale(scale).translate(tx, ty))
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
