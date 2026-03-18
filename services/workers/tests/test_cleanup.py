import cv2
import numpy as np

from mangai_workers.cleanup import CleanupMaskSpec, render_cleaned_png


def build_test_png_bytes() -> bytes:
    image = np.full((120, 120, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (100, 100), (245, 245, 245), thickness=-1)
    cv2.putText(
        image,
        "A",
        (48, 72),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (10, 10, 10),
        2,
        cv2.LINE_AA,
    )
    success, encoded = cv2.imencode(".png", image)
    assert success
    return encoded.tobytes()


def test_render_cleaned_png_replaces_solid_fill_text() -> None:
    source_bytes = build_test_png_bytes()
    cleaned_bytes = render_cleaned_png(
        source_bytes=source_bytes,
        masks=[
            CleanupMaskSpec(
                cleanup_strategy="solid_fill",
                points=((36, 30), (84, 30), (84, 86), (36, 86)),
            )
        ],
    )

    assert cleaned_bytes is not None
    cleaned_image = cv2.imdecode(np.frombuffer(cleaned_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert cleaned_image is not None
    center_pixel = cleaned_image[58, 58]
    assert int(center_pixel[0]) >= 235
    assert int(center_pixel[1]) >= 235
    assert int(center_pixel[2]) >= 235


def test_render_cleaned_png_uses_inpaint_for_background_reconstruction() -> None:
    image = np.full((120, 120, 3), 255, dtype=np.uint8)
    for index in range(120):
        image[:, index] = (180 + (index // 3), 180 + (index // 3), 180 + (index // 3))
    cv2.line(image, (20, 20), (100, 100), (0, 0, 0), thickness=2)
    success, encoded = cv2.imencode(".png", image)
    assert success

    cleaned_bytes = render_cleaned_png(
        source_bytes=encoded.tobytes(),
        masks=[
            CleanupMaskSpec(
                cleanup_strategy="background_reconstruction",
                points=((44, 44), (76, 44), (76, 76), (44, 76)),
            )
        ],
    )

    assert cleaned_bytes is not None
    cleaned_image = cv2.imdecode(np.frombuffer(cleaned_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert cleaned_image is not None
    assert int(cleaned_image[60, 60][0]) > 120
