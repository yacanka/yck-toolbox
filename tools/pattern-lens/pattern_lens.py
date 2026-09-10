from __future__ import annotations

import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path


COMPOUND_EXTENSIONS = (
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".nii.gz",
    ".backup.sql",
)


UUID_RE = re.compile(
    r"(?i)(?<![0-9a-f])"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    r"(?![0-9a-f])"
)

DATE_YMD_RE = re.compile(
    r"(?<!\d)"
    r"(?P<y>(?:19|20)\d{2})"
    r"(?P<sep>[-_.]?)"
    r"(?P<m>0[1-9]|1[0-2])"
    r"(?P=sep)"
    r"(?P<d>0[1-9]|[12]\d|3[01])"
    r"(?:(?:[T _-]?)"
    r"(?P<h>[01]\d|2[0-3])"
    r"(?P<tsep>[-_.:]?)"
    r"(?P<mi>[0-5]\d)"
    r"(?:(?P=tsep)(?P<s>[0-5]\d))?"
    r")?"
    r"(?!\d)"
)

DATE_DMY_RE = re.compile(
    r"(?<!\d)"
    r"(?P<d>0[1-9]|[12]\d|3[01])"
    r"(?P<sep>[-_.])"
    r"(?P<m>0[1-9]|1[0-2])"
    r"(?P=sep)"
    r"(?P<y>(?:19|20)\d{2})"
    r"(?!\d)"
)

TIME_RE = re.compile(
    r"(?<!\d)"
    r"(?P<h>[01]\d|2[0-3])"
    r"(?P<sep>[:._-])?"
    r"(?P<m>[0-5]\d)"
    r"(?:(?P=sep)(?P<s>[0-5]\d))"
    r"(?!\d)"
)

VERSION_RE = re.compile(
    r"(?i)(?<![a-z0-9])v?\d+(?:\.\d+){1,4}(?![a-z0-9])"
)

NUMBER_RE = re.compile(r"\d+")

WORD_RE = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]+")


@dataclass
class PatternGroup:
    count: int = 0
    examples: list[str] = field(default_factory=list)
    extensions: Counter[str] = field(default_factory=Counter)

    def add(self, relative_path: str, extension: str) -> None:
        self.count += 1
        self.extensions[extension] += 1

        if len(self.examples) < 5:
            self.examples.append(relative_path)


def split_filename(filename: str) -> tuple[str, str]:
    """
    Dosya adını stem + extension olarak ayırır.

    Normalde pathlib sadece son uzantıyı verir:
        archive.tar.gz -> stem=archive.tar, ext=.gz

    Biz bazı bileşik uzantıları birlikte ele alıyoruz:
        archive.tar.gz -> stem=archive, ext=.tar.gz
    """
    lower_name = filename.lower()

    for ext in COMPOUND_EXTENSIONS:
        if lower_name.endswith(ext):
            return filename[:-len(ext)], filename[-len(ext):]

    path = Path(filename)
    return path.stem, path.suffix


def marker(index: int) -> str:
    """
    Geçici placeholder üretir.
    Private-use Unicode alanı kullanıyoruz ki regex'ler yanlışlıkla değiştirmesin.
    """
    return chr(0xE000 + index)


def patternize_name(name: str, *, generalize_words: bool = False) -> str:
    replacements: list[str] = []

    def protect(regex: re.Pattern, token_factory, text: str) -> str:
        def repl(match: re.Match) -> str:
            token = token_factory(match)
            replacements.append(token)
            return marker(len(replacements) - 1)

        return regex.sub(repl, text)

    def date_ymd_token(match: re.Match) -> str:
        sep = match.group("sep")
        date_fmt = f"YYYY{sep}MM{sep}DD" if sep else "YYYYMMDD"

        if match.group("h"):
            time_sep = match.group("tsep") or ""

            if match.group("s"):
                time_fmt = (
                    f"HH{time_sep}MM{time_sep}SS"
                    if time_sep
                    else "HHMMSS"
                )
            else:
                time_fmt = (
                    f"HH{time_sep}MM"
                    if time_sep
                    else "HHMM"
                )

            return f"<DATETIME:{date_fmt}_{time_fmt}>"

        return f"<DATE:{date_fmt}>"

    def date_dmy_token(match: re.Match) -> str:
        sep = match.group("sep")
        return f"<DATE:DD{sep}MM{sep}YYYY>"

    def time_token(match: re.Match) -> str:
        sep = match.group("sep") or ""

        if sep:
            return f"<TIME:HH{sep}MM{sep}SS>"

        return "<TIME:HHMMSS>"

    text = name

    text = protect(UUID_RE, lambda _: "<UUID>", text)
    text = protect(DATE_YMD_RE, date_ymd_token, text)
    text = protect(DATE_DMY_RE, date_dmy_token, text)
    text = protect(VERSION_RE, lambda _: "<VERSION>", text)
    text = protect(TIME_RE, time_token, text)

    # Sayı uzunluğunu koruyoruz.
    # 001 ile 2024 aynı format sayılmasın.
    text = protect(
        NUMBER_RE,
        lambda match: f"<NUM:{len(match.group(0))}>",
        text,
    )

    if generalize_words:
        text = WORD_RE.sub("<WORD>", text)

    for i, token in enumerate(replacements):
        text = text.replace(marker(i), token)

    return text


def iter_files(root: Path, *, include_hidden: bool = False):
    for dirpath, dirnames, filenames in os.walk(root):
        if not include_hidden:
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if not dirname.startswith(".")
            ]

        for filename in filenames:
            if not include_hidden and filename.startswith("."):
                continue

            yield Path(dirpath) / filename


def build_patterns(
    file_path: Path,
    *,
    root: Path,
    case_sensitive: bool,
    ignore_extension: bool,
) -> tuple[str, str, str, str]:
    stem, ext = split_filename(file_path.name)

    if not case_sensitive:
        stem = stem.casefold()
        ext = ext.casefold()

    extension_label = ext if ext else "<NO_EXT>"

    literal_name_pattern = patternize_name(
        stem,
        generalize_words=False,
    )

    structural_name_pattern = patternize_name(
        stem,
        generalize_words=True,
    )

    if ignore_extension:
        literal_pattern = literal_name_pattern
        structural_pattern = structural_name_pattern
    else:
        literal_pattern = f"{literal_name_pattern}{extension_label}"
        structural_pattern = f"{structural_name_pattern}{extension_label}"

    relative_path = str(file_path.relative_to(root))

    return literal_pattern, structural_pattern, extension_label, relative_path


def scan_folder(
    root: Path,
    *,
    include_hidden: bool,
    case_sensitive: bool,
    ignore_extension: bool,
):
    literal_groups: dict[str, PatternGroup] = defaultdict(PatternGroup)
    structural_groups: dict[str, PatternGroup] = defaultdict(PatternGroup)
    extension_counts: Counter[str] = Counter()

    total_files = 0

    for file_path in iter_files(root, include_hidden=include_hidden):
        if not file_path.is_file():
            continue

        total_files += 1

        (
            literal_pattern,
            structural_pattern,
            extension_label,
            relative_path,
        ) = build_patterns(
            file_path,
            root=root,
            case_sensitive=case_sensitive,
            ignore_extension=ignore_extension,
        )

        extension_counts[extension_label] += 1

        literal_groups[literal_pattern].add(relative_path, extension_label)
        structural_groups[structural_pattern].add(relative_path, extension_label)

    return total_files, extension_counts, literal_groups, structural_groups


def print_groups(
    title: str,
    groups: dict[str, PatternGroup],
    *,
    min_count: int,
    top: int,
) -> None:
    print()
    print(title)
    print("=" * len(title))

    rows = [
        (pattern, group)
        for pattern, group in groups.items()
        if group.count >= min_count
    ]

    rows.sort(key=lambda item: (-item[1].count, item[0]))

    if not rows:
        print(f"{min_count} veya daha fazla dosyada tekrar eden örüntü bulunamadı.")
        return

    for pattern, group in rows[:top]:
        print(f"\n{group.count:>5} dosya  |  {pattern}")

        example_text = " | ".join(group.examples[:3])
        print(f"      örnek: {example_text}")

        ext_text = ", ".join(
            f"{ext}:{count}"
            for ext, count in group.extensions.most_common()
        )
        print(f"      uzantı: {ext_text}")


def write_csv_report(
    csv_path: Path,
    *,
    literal_groups: dict[str, PatternGroup],
    structural_groups: dict[str, PatternGroup],
    min_count: int,
) -> None:
    rows = []

    for mode, groups in [
        ("literal", literal_groups),
        ("structural", structural_groups),
    ]:
        for pattern, group in groups.items():
            if group.count < min_count:
                continue

            rows.append(
                {
                    "mode": mode,
                    "count": group.count,
                    "pattern": pattern,
                    "extensions": "; ".join(
                        f"{ext}:{count}"
                        for ext, count in group.extensions.most_common()
                    ),
                    "examples": " | ".join(group.examples),
                }
            )

    rows.sort(key=lambda row: (-row["count"], row["mode"], row["pattern"]))

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "mode",
                "count",
                "pattern",
                "extensions",
                "examples",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Klasördeki dosya adlarından örüntü/format yakalayıcı."
    )

    parser.add_argument(
        "folder",
        help="Taranacak klasör yolu.",
    )

    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Raporlanması için örüntünün en az kaç dosyada geçmesi gerektiği.",
    )

    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="Ekranda gösterilecek maksimum örüntü sayısı.",
    )

    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="CSV rapor dosyası yolu. Örn: report.csv",
    )

    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Gizli dosya ve klasörleri de tara.",
    )

    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Büyük/küçük harf farkını ayrı örüntü kabul et.",
    )

    parser.add_argument(
        "--ignore-extension",
        action="store_true",
        help="Örüntü çıkarırken uzantıyı hesaba katma.",
    )

    args = parser.parse_args()

    root = Path(args.folder).expanduser().resolve()

    if not root.exists():
        raise SystemExit(f"Klasör bulunamadı: {root}")

    if not root.is_dir():
        raise SystemExit(f"Verilen yol klasör değil: {root}")

    (
        total_files,
        extension_counts,
        literal_groups,
        structural_groups,
    ) = scan_folder(
        root,
        include_hidden=args.include_hidden,
        case_sensitive=args.case_sensitive,
        ignore_extension=args.ignore_extension,
    )

    print(f"Taranan klasör : {root}")
    print(f"Taranan dosya  : {total_files}")

    print()
    print("UZANTI DAĞILIMI")
    print("===============")

    for ext, count in extension_counts.most_common():
        print(f"{count:>5} dosya  |  {ext}")

    print_groups(
        "LITERAL ÖRÜNTÜLER",
        literal_groups,
        min_count=args.min_count,
        top=args.top,
    )

    print_groups(
        "YAPISAL ÖRÜNTÜLER",
        structural_groups,
        min_count=args.min_count,
        top=args.top,
    )

    if args.csv:
        csv_path = Path(args.csv).expanduser().resolve()
        write_csv_report(
            csv_path,
            literal_groups=literal_groups,
            structural_groups=structural_groups,
            min_count=args.min_count,
        )
        print()
        print(f"CSV rapor yazıldı: {csv_path}")


if __name__ == "__main__":
    main()