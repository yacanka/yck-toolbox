from pathlib import Path
import re
import win32com.client as win32


def safe_filename(text: str, max_len: int = 80) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] or "untitled"


def split_docx_by_headings(
    input_docx: str,
    output_dir: str,
    heading_level: int = 1,
):
    input_path = Path(input_docx).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    word = win32.Dispatch("Word.Application")
    word.Visible = False

    doc = None

    try:
        doc = word.Documents.Open(str(input_path))

        headings = []

        for i in range(1, doc.Paragraphs.Count + 1):
            paragraph = doc.Paragraphs(i)
            outline_level = paragraph.OutlineLevel

            # Word outline level:
            # 1 = Heading 1
            # 2 = Heading 2
            # ...
            # 10 = Normal body text
            if outline_level == heading_level:
                title = paragraph.Range.Text.strip()
                headings.append({
                    "title": title,
                    "start": paragraph.Range.Start,
                })

        if not headings:
            print(f"Belgede Heading {heading_level} seviyesinde başlık bulunamadı.")
            return

        for index, heading in enumerate(headings):
            start = heading["start"]

            if index + 1 < len(headings):
                end = headings[index + 1]["start"] - 1
            else:
                end = doc.Content.End

            section_range = doc.Range(Start=start, End=end)

            new_doc = word.Documents.Add()
            new_doc.Range().FormattedText = section_range.FormattedText

            filename = f"{index + 1:02d}_{safe_filename(heading['title'])}.docx"
            save_path = output_path / filename

            new_doc.SaveAs2(str(save_path), FileFormat=16)  # 16 = docx
            new_doc.Close(False)

            print(f"Kaydedildi: {save_path}")

    finally:
        if doc is not None:
            doc.Close(False)

        word.Quit()


if __name__ == "__main__":
    split_docx_by_headings(
        input_docx=r"C:\Users\t02077\Desktop\splitter\input.docx",
        output_dir=r"C:\Users\t02077\Desktop\splitter\output",
        heading_level=2,
    )