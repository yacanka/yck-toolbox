#!/usr/bin/env python3
"""
Bir klasördeki dosyaları, ffmpeg'in desteklediği herhangi bir formattan
herhangi bir formata dönüştürür. Giriş/çıkış formatını sen seçersin.

Gereksinimler:
    pip install rich
    (ve sistemde ffmpeg kurulu olmalı)

Kullanım örnekleri:
    python format_donustur.py ./videolar --from webm --to mp3
    python format_donustur.py ./muzikler --from wav --to flac --bitrate 320k
    python format_donustur.py ./klasor --from mov --to mp4 --recursive
    python format_donustur.py --list-formats
"""

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)

console = Console()

# ffmpeg'in en yaygın desteklediği formatlar (kategorize edilmiş, kürate liste).
# Tam liste için: ffmpeg -formats
AUDIO_FORMATS = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma", "opus", "aiff", "alac"]
VIDEO_FORMATS = ["mp4", "webm", "mkv", "mov", "avi", "flv", "wmv", "m4v", "mpg", "3gp", "ts", "gif"]
ALL_FORMATS = AUDIO_FORMATS + VIDEO_FORMATS


def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(Panel.fit(
            "[bold red]ffmpeg bulunamadı![/bold red]\n\n"
            "[cyan]Windows:[/cyan] winget install ffmpeg\n"
            "[cyan]Mac:[/cyan] brew install ffmpeg\n"
            "[cyan]Linux:[/cyan] sudo apt install ffmpeg",
            title="Kurulum Gerekli", border_style="red",
        ))
        sys.exit(1)


def show_formats_table():
    table = Table(title="Desteklenen Formatlar", show_header=True, header_style="bold cyan")
    table.add_column("Kategori", style="bold")
    table.add_column("Formatlar")
    table.add_row("🎵 Ses", ", ".join(AUDIO_FORMATS))
    table.add_row("🎬 Video", ", ".join(VIDEO_FORMATS))
    console.print(table)
    console.print(
        "[dim]Not: Bu liste en yaygın kullanılanlardır. ffmpeg çok daha fazlasını "
        "destekler; tam liste için terminalde 'ffmpeg -formats' yazabilirsin.[/dim]"
    )


def validate_format(fmt: str, label: str) -> str:
    fmt = fmt.lower().lstrip(".")
    if fmt not in ALL_FORMATS:
        console.print(Panel.fit(
            f"[bold red]Geçersiz {label} formatı:[/bold red] '{fmt}'",
            border_style="red",
        ))
        show_formats_table()
        sys.exit(1)
    return fmt


def is_audio_only(fmt: str) -> bool:
    return fmt in AUDIO_FORMATS


def convert_file(src: Path, dst: Path, audio_only: bool, bitrate: str, overwrite: bool) -> tuple[bool, str]:
    if dst.exists() and not overwrite:
        return True, "atlandı (zaten var)"

    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if audio_only:
        cmd += ["-vn", "-b:a", bitrate]
    cmd += [str(dst)]

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        err = result.stderr.decode(errors="ignore").strip().splitlines()
        return False, err[-1] if err else "bilinmeyen hata"
    return True, "tamam"


def main():
    parser = argparse.ArgumentParser(
        description="Klasördeki dosyaları ffmpeg ile bir formattan diğerine çevirir."
    )
    parser.add_argument("klasor", nargs="?", help="Dosyaların bulunduğu klasör")
    parser.add_argument("--from", dest="src_fmt", help="Giriş formatı (ör: webm)")
    parser.add_argument("--to", dest="dst_fmt", help="Çıkış formatı (ör: mp3)")
    parser.add_argument("--bitrate", default="192k", help="Ses bitrate'i (varsayılan: 192k, sadece ses çıktısında)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Alt klasörleri de tara")
    parser.add_argument("--delete", action="store_true", help="Başarılı dönüşümden sonra orijinali sil")
    parser.add_argument("--overwrite", action="store_true", help="Var olan hedef dosyaların üzerine yaz")
    parser.add_argument("--list-formats", action="store_true", help="Desteklenen formatları göster ve çık")
    args = parser.parse_args()

    if args.list_formats:
        show_formats_table()
        return

    if not args.klasor or not args.src_fmt or not args.dst_fmt:
        console.print("[bold red]Hata:[/bold red] klasör, --from ve --to belirtmelisin.\n")
        parser.print_help()
        return

    check_ffmpeg()

    src_fmt = validate_format(args.src_fmt, "giriş")
    dst_fmt = validate_format(args.dst_fmt, "çıkış")

    klasor = Path(args.klasor)
    if not klasor.is_dir():
        console.print(f"[bold red]Hata:[/bold red] '{klasor}' geçerli bir klasör değil.")
        sys.exit(1)

    pattern = f"**/*.{src_fmt}" if args.recursive else f"*.{src_fmt}"
    files = sorted(klasor.glob(pattern))

    if not files:
        console.print(f"[yellow]'.{src_fmt}' uzantılı dosya bulunamadı.[/yellow]")
        return

    console.print(Panel.fit(
        f"[bold]{len(files)}[/bold] dosya bulundu  →  "
        f"[cyan].{src_fmt}[/cyan] ➜ [green].{dst_fmt}[/green]",
        border_style="blue",
    ))

    audio_only = is_audio_only(dst_fmt)
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Dönüştürülüyor...", total=len(files))
        for src in files:
            dst = src.with_suffix(f".{dst_fmt}")
            progress.update(task, description=f"[cyan]{src.name}[/cyan]")
            ok, msg = convert_file(src, dst, audio_only, args.bitrate, args.overwrite)
            results.append((src.name, ok, msg))
            if ok and args.delete and dst.exists() and msg != "atlandı (zaten var)":
                src.unlink()
            progress.advance(task)

    table = Table(title="Sonuç", show_header=True, header_style="bold cyan")
    table.add_column("Dosya")
    table.add_column("Durum")
    basarili = 0
    for name, ok, msg in results:
        if ok:
            basarili += 1
            table.add_row(name, f"[green]✔ {msg}[/green]")
        else:
            table.add_row(name, f"[red]✘ {msg}[/red]")
    console.print(table)

    console.print(Panel.fit(
        f"[bold green]{basarili}[/bold green]/{len(files)} dosya başarıyla dönüştürüldü.",
        border_style="green" if basarili == len(files) else "yellow",
    ))


if __name__ == "__main__":
    main()