from pathlib import Path

ROOT_DIR = Path(r"C:\Users\t02077\Code\aw-center")

converted_count = 0

for file_path in ROOT_DIR.rglob("*"):
    if not file_path.is_file():
        continue

    try:
        data = file_path.read_bytes()

        # Binary dosya kontrolü
        if b"\x00" in data:
            continue

        new_data = data.replace(b"\r\n", b"\n")

        if new_data != data:
            file_path.write_bytes(new_data)
            print(f"Converted: {file_path}")
            converted_count += 1

    except Exception as e:
        print(f"Skipped: {file_path} ({e})")

print(f"\nToplam dönüştürülen dosya: {converted_count}")