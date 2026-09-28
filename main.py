import argparse
import subprocess
import os
from pathlib import Path

p = Path("./")

OPUS_QUALITY_KB = 32

IMAGES_FORMATS = {
    "JPEG": ["jpeg", "jpg"],
    "PNG":  ["png"],
    "HEIF": ["heic", "heif"],
    "DNG": ["dng"],
    # "GIF":  ["gif"],
}

AUDIO_FORMATS = {
    "MP3":  ["mp3"],
    "WAV":  ["wav"],
    "M4A":  ["m4a"],
}

FORMATS = {
  *IMAGES_FORMATS,
  *AUDIO_FORMATS,
}

WEBP_QUALITY_DEFAULT = 30

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
  stderr=None
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
        "-q", "--quality",
        type=int,
        default=WEBP_QUALITY_DEFAULT,
        help=f"WEBP quality (0-100, default: {WEBP_QUALITY_DEFAULT}). "
             "100 = lossless-ish, lower = smaller/more compressed.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    webp_quality = args.quality

    # Все поддерживаемые аудио-расширения
    audio_exts = set()
    for aliases in AUDIO_FORMATS.values():
        for alias in aliases:
            audio_exts.add(alias)

    for file in p.rglob("*"):
        if not file.is_file():
            continue

        orig_ext = file.suffix.lstrip(".")
        ext = file.suffix.lstrip("")
        ext_lower = orig_ext.lower()

        # --- АУДИО ---
        if ext_lower in audio_exts:
            output_path = file.parent / f"{file.name.rstrip(f'.{ext}')}.opus"
            if output_path.exists():
                continue

            run_cmd(
                "ffmpeg",
                [
                    "-i", str(file),
                    "-map", "0:a",
                    "-c:a", "libopus",
                    "-b:a", "128k",
                    "-vbr", "on",
                    "-compression_level", "10",
                    "-map_metadata", "0",
                    str(output_path),
                ],
            )
            print(f"Converted audio {file} -> {output_path}")
            continue

        # --- ИЗОБРАЖЕНИЯ ---
        if not ext_lower in ENABLED_FORMATS:
            continue

        filename = file.name
        parent_dir = file.parent

        output_filename = f"{filename.rstrip(f'.{ext}')}.webp"
        output_path = parent_dir / output_filename
        if output_path.exists():
            continue

        if ext_lower in IMAGES_FORMATS["HEIF"]:
            png_filename = f"{file.name.rstrip(f'.{ext}')}.png"
            png_path = parent_dir / png_filename

            try:
                run_cmd("heif-convert", [str(file), str(png_path)])
                
                filename = png_filename
                ext = "png"
            except:
                filename = f"{file.name.rstrip(f'.{ext}')}.jpg"
                file_path = parent_dir / filename
                file.rename(file_path)

        output_path = parent_dir / output_filename

        run_cmd("cwebp", ["-q", str(webp_quality), str(parent_dir / filename), "-o", str(output_path)])
        print(f"Converted {filename} to WEBP format (quality {webp_quality}): {file} -> {output_path}")

        if orig_ext.lower() in IMAGES_FORMATS["HEIF"]:
            (parent_dir / filename).unlink()

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