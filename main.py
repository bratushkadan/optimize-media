import argparse
import subprocess
import os
import tempfile
from pathlib import Path

p = Path("./")

OPUS_QUALITY_KB = 32

IMAGES_FORMATS = {
    "JPEG": ["jpeg", "jpg"],
    "PNG": ["png"],
    "HEIF": ["heic", "heif"],
    "DNG": ["dng"],
    # "GIF":  ["gif"],
}

AUDIO_FORMATS = {
    "MP3": ["mp3"],
    "WAV": ["wav"],
    "M4A": ["m4a"],
    "AIFF": ["aiff", "aif"],
    "WMA": ["wma"],
}

# FFmpeg demuxer names do not always match file extensions.
AUDIO_INPUT_FORMATS = {
    "MP3": "mp3",
    "WAV": "wav",
    "M4A": "mov",
    "AIFF": "aiff",
    "WMA": "asf",
}

FORMATS = {
    *IMAGES_FORMATS,
    *AUDIO_FORMATS,
}

WEBP_QUALITY_DEFAULT = None

ENABLED_FORMATS = set()
for format_aliases in IMAGES_FORMATS.values():
    for alias in format_aliases:
        ENABLED_FORMATS.add(alias)


def run_cmd(
    cmd,
    args,
    *,
    check_returncode=True,
    # наследовать stdout родителя (по умолчанию)
    stdout=None,
    # наследовать stderr родителя (по умолчанию)
    stderr=None,
):
    sp = subprocess.run([cmd, *args], stdout=stdout, stderr=stderr)
    if check_returncode:
        sp.check_returncode()


# quality (100 - lossless, 10% - extremely compressed)
def get_compression_threshold(size_bytes):
    size_kib = size_bytes / 1024

    if size_kib < 2:
        return 100
    if size_kib < 4:
        return 90
    if size_kib < 8:
        return 80
    if size_kib < 16:
        return 70
    if size_kib < 32:
        return 50
    if size_kib < 64:
        return 40
    if size_kib < 128:
        return 30
    if size_kib < 256:
        return 20
    return 10


def parse_args():
    parser = argparse.ArgumentParser(
        description="Recursively convert images to WEBP and compress audio."
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=WEBP_QUALITY_DEFAULT,
        help="Override automatic WEBP quality (0-100). Resizing remains automatic.",
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Reconvert and atomically replace existing WEBP files; audio is unchanged.",
    )
    args = parser.parse_args()
    if args.quality is not None and not 0 <= args.quality <= 100:
        parser.error("quality must be between 0 and 100")
    return args


def image_settings(size, size_bytes):
    longest = max(size)
    if longest <= 1600:
        limit, quality = 1600, 80
    elif longest <= 3000:
        limit, quality = 1920, 75
    else:
        limit, quality = 2560, 75
    if size_bytes <= 250 * 1024:
        quality = 85
    return limit, quality


def convert_image(file, quality=None, overwrite=False):
    from PIL import Image, ImageOps

    output_path = file.with_suffix(".webp")
    if output_path.exists() and not overwrite:
        return False

    if file.suffix.lower().lstrip(".") in IMAGES_FORMATS["HEIF"]:
        from pillow_heif import register_heif_opener
        # libheif applies container transforms; the plugin resets EXIF orientation
        # so ImageOps does not apply the same rotation twice.
        register_heif_opener()

    # Keep temporary files on the same filesystem for atomic replacement.
    # Source images are never renamed or deleted.
    with tempfile.TemporaryDirectory(prefix=".webp-", dir=file.parent) as temp:
        temp_dir = Path(temp)
        normalized_path = temp_dir / "normalized.png"
        encoded_path = temp_dir / "encoded.webp"
        lossless_path = temp_dir / "lossless.webp"
        with Image.open(file) as image:
            normalized = ImageOps.exif_transpose(image)
            original_size = normalized.size
            limit, auto_quality = image_settings(original_size, file.stat().st_size)
            selected_quality = auto_quality if quality is None else quality
            icc_profile = normalized.info.get("icc_profile")
            if normalized.mode not in ("RGB", "RGBA"):
                has_alpha = "A" in normalized.getbands() or "transparency" in normalized.info
                mode = "RGBA" if has_alpha else "RGB"
                normalized = normalized.convert(mode)
            normalized.thumbnail((limit, limit), Image.Resampling.LANCZOS)
            # Strip stale EXIF/XMP after baking orientation into pixels.
            normalized.info.clear()
            normalized.save(normalized_path, format="PNG", icc_profile=icc_profile)
            expected_size = normalized.size
        run_cmd("cwebp", ["-q", str(selected_quality), "-metadata", "icc",
                          str(normalized_path), "-o", str(encoded_path)])
        run_cmd("cwebp", ["-lossless", "-metadata", "icc",
                          str(normalized_path), "-o", str(lossless_path)])
        selected_path = min((encoded_path, lossless_path), key=lambda path: path.stat().st_size)
        encoding = "lossless" if selected_path == lossless_path else f"quality {selected_quality}"
        with Image.open(selected_path) as result:
            result.load()
            if result.format != "WEBP" or result.size != expected_size:
                raise ValueError(f"Invalid WEBP output: {file}")
        if output_path.exists() and not overwrite:
            return False
        selected_path.replace(output_path)
    print(f"Converted image {file} -> {output_path} "
          f"({original_size[0]}x{original_size[1]} -> "
          f"{expected_size[0]}x{expected_size[1]}, {encoding})")
    return True


def main():
    args = parse_args()
    webp_quality = args.quality

    # Все поддерживаемые аудио-расширения
    audio_exts = {
        alias: AUDIO_INPUT_FORMATS[format_name]
        for format_name, aliases in AUDIO_FORMATS.items()
        for alias in aliases
    }

    for file in list(p.rglob("*")):
        if not file.is_file():
            continue

        orig_ext = file.suffix.lstrip(".")
        ext_lower = orig_ext.lower()

        # --- АУДИО ---
        if ext_lower in audio_exts:
            output_path = file.with_suffix(".opus")
            if output_path.exists():
                continue

            run_cmd(
                "ffmpeg",
                [
                    "-f",
                    audio_exts[ext_lower],
                    "-i",
                    str(file),
                    # "-map",
                    # "0:a",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "128k",
                    "-vbr",
                    "on",
                    "-compression_level",
                    "10",
                    "-map_metadata",
                    "0",
                    str(output_path),
                ],
            )
            print(f"Converted audio {file} -> {output_path}")
            continue

        # --- ИЗОБРАЖЕНИЯ ---
        if not ext_lower in ENABLED_FORMATS:
            continue

        try:
            convert_image(file, webp_quality, overwrite=args.overwrite)
        except (OSError, ValueError, subprocess.CalledProcessError, ImportError) as error:
            print(f"ERROR {file}: {error}")
            if isinstance(error, ImportError):
                print("Install image dependencies: python3 -m pip install Pillow pillow-heif")


def old_main():

    # Только имена файлов и папок
    for file in p.rglob("*"):
        if not file.is_file():
            continue

        lfilename = file.name.lower()

        extension_type = None
        for t, fexts in ENABLED_FORMATS.items():
            for fext in fexts:
                if not lfilename.endswith(f".{fext}"):
                    continue
                extension_type = t

        if extension_type == None:
            continue

        size = os.path.getsize(file)
        kib = round(size / 1024, 2)

        if extension_type == "JPEG":
            subprocess.run(
                [
                    "jpegoptim",
                    "--size",
                    str(get_compression_threshold(size)),
                    "--strip-all",
                    "--dest",
                    str(file.parent),
                    str(file),
                ],
                stdout=None,  # наследовать stdout родителя (по умолчанию)
                stderr=None,  # наследовать stderr родителя (по умолчанию)
            )
        elif extension_type == "PNG":
            subprocess.run(
                [
                    "pngquant",
                    "--quality",
                    str(get_compression_threshold(size)),
                    "--speed",
                    "1",
                    "--strip",
                    "--output",
                    str(file.parent / file.name),
                    str(file),
                ],
                stdout=None,  # наследовать stdout родителя (по умолчанию)
                stderr=None,  # наследовать stderr родителя (по умолчанию)
            )
        elif extension_type == "GIF":
            subprocess.run(
                [
                    "gifsicle",
                    "-O3",
                    "--lossy=320",
                    "--colors=128",
                    "--resize=320x_",
                    str(file),
                    "-o",
                    str(file.parent / file.name),
                ],
                stdout=None,  # наследовать stdout родителя (по умолчанию)
                stderr=None,  # наследовать stderr родителя (по умолчанию)
            )
        elif extension_type in ["MP3", "WAV"]:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(file),
                    "-ac",
                    "1",
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "32k",
                    "-application",
                    "voip",
                    "-map_metadata",
                    "-1",
                    "-map_metadata:s:a",
                    "-1",
                    "-map_chapters",
                    "-1",
                    "-fflags",
                    "+bitexact",
                    str(file.parent / f"{file.name}.opus"),
                ],
                stdout=None,  # наследовать stdout родителя (по умолчанию)
                stderr=None,  # наследовать stderr родителя (по умолчанию)
            )
            # the command below is for reducing the bitrate and making target file .mp3 format
            #   ffmpeg -i "$f" -ac 1 -c:a libmp3lame -b:a 32k "${f%.wav}.mp3"

    # Рекурсивно все файлы
    # for file in p.rglob("*"):
    #     if file.is_file():
    #         print(file)


if __name__ == "__main__":
    main()
