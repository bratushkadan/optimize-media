from pathlib import Path

root = Path(".")  # Root directory
extensions = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".wma", ".aiff"}

for opus in root.rglob("*.opus"):
    for ext in extensions:
        file = opus.with_suffix(ext)
        if file.is_file():
            print(f"Deleting: {file}")
            file.unlink()
