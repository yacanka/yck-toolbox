from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any

import xlsxwriter
from jira import JIRA


# ============================================================
# CONFIGURATION
# ============================================================

JIRA_SERVER = "https://jira.example.com"

# "basic" -> kullanıcı/e-posta + password/API token
# "token" -> Personal Access Token (özellikle Jira Server/Data Center)
AUTH_MODE = "basic"

JIRA_USERNAME = "user@example.com"
JIRA_SECRET = "YOUR_API_TOKEN_OR_PASSWORD"

# True önerilir.
# Kurumsal CA kullanıyorsan örneğin:
# VERIFY_SSL = r"C:\certificates\company-ca.pem"
VERIFY_SSL: bool | str = True


# ------------------------------------------------------------
# Jira sorgusu
# ------------------------------------------------------------

JQL = """
project = MYPROJECT
ORDER BY created DESC
""".strip()


# ------------------------------------------------------------
# ÇEKİLECEK ALANLAR
#
# SIRA = EXCEL SÜTUN SIRASI
#
# Jira'daki görünen alan adlarını doğrudan yazabilirsin.
# Custom field isimleri de kullanılabilir.
#
# Ayrıca doğrudan:
#   customfield_12345
# gibi field ID de kullanılabilir.
#
# "Key" ve "URL" özel alanlardır.
# ------------------------------------------------------------

FIELDS = [
    "Key",
    "Summary",
    "Issue Type",
    "Status",
    "Priority",
    "Assignee",
    "Reporter",
    "Created",
    "Updated",
    "Due Date",
    "Labels",
    "Components",
    "Fix Version/s",
    "Description",
    "URL",
]


OUTPUT_FILE = "jira_export.xlsx"

SHEET_NAME = "Issues"
INFO_SHEET_NAME = "Export Info"


# ============================================================
# JIRA CONNECTION
# ============================================================


def create_jira_client() -> JIRA:
    options = {
        "verify": VERIFY_SSL,
    }

    if AUTH_MODE == "basic":
        return JIRA(
            server=JIRA_SERVER,
            options=options,
            basic_auth=(JIRA_USERNAME, JIRA_SECRET),
            timeout=60,
        )

    if AUTH_MODE == "token":
        return JIRA(
            server=JIRA_SERVER,
            options=options,
            token_auth=JIRA_SECRET,
            timeout=60,
        )

    raise ValueError(
        f"Geçersiz AUTH_MODE: {AUTH_MODE!r}. "
        "'basic' veya 'token' kullanılmalı."
    )


# ============================================================
# FIELD RESOLUTION
# ============================================================


SPECIAL_FIELDS = {
    "key": "key",
    "issue key": "key",
    "jira key": "key",

    "url": "url",
    "issue url": "url",
    "jira url": "url",
}


def validate_field_list() -> None:
    if not FIELDS:
        raise ValueError("FIELDS listesi boş olamaz.")

    normalized = [field.strip().casefold() for field in FIELDS]

    if len(normalized) != len(set(normalized)):
        raise ValueError(
            "FIELDS listesinde aynı sütun birden fazla kez bulunuyor."
        )


def resolve_fields(
    jira: JIRA,
) -> list[dict[str, Any]]:
    """
    Kullanıcının FIELDS listesinde verdiği alan adlarını
    Jira field ID'lerine dönüştürür.

    Örnek:
        "Summary"      -> "summary"
        "Status"       -> "status"
        "Story Points" -> "customfield_10016"
    """

    all_fields = jira.fields()

    fields_by_id: dict[str, dict[str, Any]] = {}

    fields_by_name: defaultdict[
        str,
        list[dict[str, Any]]
    ] = defaultdict(list)

    for field in all_fields:
        field_id = str(field["id"])
        field_name = str(field.get("name", field_id))

        fields_by_id[field_id.casefold()] = field
        fields_by_name[field_name.strip().casefold()].append(field)

    resolved: list[dict[str, Any]] = []

    available_names = [
        str(field.get("name", field["id"]))
        for field in all_fields
    ]

    for requested in FIELDS:
        lookup = requested.strip().casefold()

        # --------------------------------------------
        # Özel alanlar
        # --------------------------------------------

        special_kind = SPECIAL_FIELDS.get(lookup)

        if special_kind:
            resolved.append(
                {
                    "header": requested,
                    "kind": special_kind,
                    "field_id": None,
                    "schema_type": None,
                }
            )
            continue

        # --------------------------------------------
        # Field ID doğrudan verilmiş olabilir
        # --------------------------------------------

        if lookup in fields_by_id:
            field = fields_by_id[lookup]

            resolved.append(
                create_field_definition(
                    requested,
                    field,
                )
            )
            continue

        # --------------------------------------------
        # Jira görünen field adı
        # --------------------------------------------

        matches = fields_by_name.get(lookup, [])

        if len(matches) == 1:
            resolved.append(
                create_field_definition(
                    requested,
                    matches[0],
                )
            )
            continue

        # Aynı isimli custom field varsa
        if len(matches) > 1:
            field_ids = [
                field["id"]
                for field in matches
            ]

            raise ValueError(
                f"Jira'da {requested!r} adında birden fazla field var.\n"
                f"Field ID kullan:\n"
                f"{field_ids}"
            )

        # --------------------------------------------
        # Bulunamadı
        # --------------------------------------------

        suggestions = get_close_matches(
            requested,
            available_names,
            n=5,
            cutoff=0.4,
        )

        suggestion_text = ""

        if suggestions:
            suggestion_text = (
                "\nBenzer alanlar:\n- "
                + "\n- ".join(suggestions)
            )

        raise ValueError(
            f"Jira field bulunamadı: {requested!r}"
            f"{suggestion_text}"
        )

    return resolved


def create_field_definition(
    requested_name: str,
    jira_field: dict[str, Any],
) -> dict[str, Any]:

    schema = jira_field.get("schema") or {}

    return {
        "header": requested_name,
        "kind": "jira",
        "field_id": jira_field["id"],
        "schema_type": schema.get("type"),
    }


# ============================================================
# VALUE CONVERSION
# ============================================================


def parse_jira_datetime(value: str) -> datetime | None:
    """
    Jira ISO tarihini Excel'e uygun datetime nesnesine çevirir.
    """

    try:
        value = value.strip()

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        parsed = datetime.fromisoformat(value)

        # Excel timezone-aware datetime kabul etmez.
        if parsed.tzinfo:
            parsed = parsed.replace(tzinfo=None)

        return parsed

    except (ValueError, TypeError):
        return None


def adf_to_text(node: Any) -> str:
    """
    Jira Cloud Description gibi Atlassian Document Format
    değerlerini düz metne çevirir.
    """

    if node is None:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, list):
        return "".join(
            adf_to_text(item)
            for item in node
        )

    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("type")

    if node_type == "text":
        return str(node.get("text", ""))

    content = node.get("content", [])

    text = "".join(
        adf_to_text(item)
        for item in content
    )

    block_types = {
        "paragraph",
        "heading",
        "listItem",
        "bulletList",
        "orderedList",
        "blockquote",
        "codeBlock",
    }

    if node_type in block_types:
        return text.rstrip() + "\n"

    return text


def format_comments(value: dict[str, Any]) -> str:
    comments = value.get("comments", [])

    result = []

    for comment in comments:
        author_data = comment.get("author") or {}

        author = (
            author_data.get("displayName")
            or author_data.get("name")
            or ""
        )

        body = normalize_value(
            comment.get("body"),
            schema_type=None,
        )

        created = comment.get("created", "")

        header = author

        if created:
            header += f" [{created}]"

        if header:
            result.append(
                f"{header}\n{body}"
            )
        else:
            result.append(str(body))

    return "\n\n".join(result)


def normalize_value(
    value: Any,
    schema_type: str | None,
) -> Any:

    if value is None:
        return ""

    # --------------------------------------------------------
    # Excel'e doğal olarak yazılabilecek türler
    # --------------------------------------------------------

    if isinstance(value, (int, float, bool)):
        return value

    # --------------------------------------------------------
    # Tarihler
    # --------------------------------------------------------

    if schema_type == "datetime" and isinstance(value, str):
        parsed = parse_jira_datetime(value)

        if parsed:
            return parsed

    if schema_type == "date" and isinstance(value, str):
        try:
            return datetime.strptime(
                value,
                "%Y-%m-%d",
            )
        except ValueError:
            pass

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(value, str):
        return value

    # --------------------------------------------------------
    # Listeler
    #
    # labels
    # components
    # versions
    # multi-select custom fields
    # --------------------------------------------------------

    if isinstance(value, list):
        values = [
            normalize_value(item, None)
            for item in value
        ]

        return "\n".join(
            str(item)
            for item in values
            if item not in ("", None)
        )

    # --------------------------------------------------------
    # Jira object / dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        # Atlassian Document Format
        if value.get("type") == "doc":
            return adf_to_text(value).strip()

        # Comment alanı
        if isinstance(value.get("comments"), list):
            return format_comments(value)

        # Kullanıcı
        if "displayName" in value:
            return value["displayName"]

        # Select / custom option
        if "value" in value:
            return value["value"]

        # Status, priority, issue type, version, sprint vb.
        if "name" in value:
            return value["name"]

        # Issue / project vb.
        if "key" in value:
            return value["key"]

        # Son fallback
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    return str(value)


def excel_safe_value(value: Any) -> Any:
    """
    Excel hücresinin maksimum string uzunluğunu aşmasını engeller.
    """

    if not isinstance(value, str):
        return value

    max_length = 32767

    if len(value) <= max_length:
        return value

    return value[:32750] + "\n[TRUNCATED]"


# ============================================================
# JIRA DATA
# ============================================================


def get_issue_value(
    issue: Any,
    field: dict[str, Any],
) -> Any:

    kind = field["kind"]

    if kind == "key":
        return issue.key

    if kind == "url":
        return (
            f"{JIRA_SERVER.rstrip('/')}"
            f"/browse/{issue.key}"
        )

    field_id = field["field_id"]

    raw_fields = issue.raw.get(
        "fields",
        {},
    )

    raw_value = raw_fields.get(field_id)

    return normalize_value(
        raw_value,
        field["schema_type"],
    )


def fetch_issues(
    jira: JIRA,
    resolved_fields: list[dict[str, Any]],
):
    jira_fields = []

    for field in resolved_fields:
        if field["kind"] != "jira":
            continue

        field_id = field["field_id"]

        if field_id not in jira_fields:
            jira_fields.append(field_id)

    # Sadece Key/URL seçildiyse Jira'nın yine de
    # minimal bir fields parametresi almasını sağlıyoruz.
    if not jira_fields:
        jira_fields = ["summary"]

    print("Jira sorgusu çalıştırılıyor...")

    issues = jira.search_issues(
        JQL,
        fields=jira_fields,
        maxResults=False,
    )

    print(
        f"{len(issues)} issue bulundu."
    )

    return issues


# ============================================================
# EXCEL
# ============================================================


def create_excel(
    issues,
    resolved_fields: list[dict[str, Any]],
) -> Path:

    output_path = Path(
        OUTPUT_FILE
    ).resolve()

    workbook = xlsxwriter.Workbook(
        output_path,
        {
            "strings_to_urls": False,
            "strings_to_formulas": False,
        },
    )

    workbook.set_properties(
        {
            "title": "Jira Issue Export",
            "subject": "Jira issue report",
            "author": "Jira Export Script",
            "company": "",
            "comments": f"Generated from {JIRA_SERVER}",
        }
    )

    worksheet = workbook.add_worksheet(
        SHEET_NAME
    )

    info_sheet = workbook.add_worksheet(
        INFO_SHEET_NAME
    )

    # ========================================================
    # FORMATS
    # ========================================================

    header_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#172B4D",
            "border": 0,
            "align": "center",
            "valign": "vcenter",
        }
    )

    text_format = workbook.add_format(
        {
            "valign": "top",
            "text_wrap": True,
        }
    )

    center_format = workbook.add_format(
        {
            "valign": "vcenter",
            "align": "center",
        }
    )

    date_format = workbook.add_format(
        {
            "num_format": "yyyy-mm-dd hh:mm",
            "valign": "vcenter",
        }
    )

    date_only_format = workbook.add_format(
        {
            "num_format": "yyyy-mm-dd",
            "valign": "vcenter",
        }
    )

    link_format = workbook.add_format(
        {
            "font_color": "#0052CC",
            "underline": True,
            "valign": "vcenter",
        }
    )

    done_format = workbook.add_format(
        {
            "bg_color": "#E3FCEF",
            "font_color": "#006644",
        }
    )

    progress_format = workbook.add_format(
        {
            "bg_color": "#DEEBFF",
            "font_color": "#0747A6",
        }
    )

    blocked_format = workbook.add_format(
        {
            "bg_color": "#FFEBE6",
            "font_color": "#BF2600",
        }
    )

    high_priority_format = workbook.add_format(
        {
            "bg_color": "#FFEBE6",
            "font_color": "#BF2600",
            "bold": True,
        }
    )

    # ========================================================
    # ISSUES SHEET
    # ========================================================

    worksheet.hide_gridlines(2)

    worksheet.freeze_panes(
        1,
        0,
    )

    worksheet.set_zoom(90)

    worksheet.set_default_row(24)

    headers = [
        field["header"]
        for field in resolved_fields
    ]

    data_rows: list[list[Any]] = []

    for issue in issues:
        row = []

        for field in resolved_fields:
            value = get_issue_value(
                issue,
                field,
            )

            row.append(
                excel_safe_value(value)
            )

        data_rows.append(row)

    # --------------------------------------------------------
    # Data
    # --------------------------------------------------------

    first_data_row = 1

    for row_index, row_data in enumerate(
        data_rows,
        start=first_data_row,
    ):

        issue = issues[
            row_index - first_data_row
        ]

        for column_index, (
            value,
            field,
        ) in enumerate(
            zip(
                row_data,
                resolved_fields,
            )
        ):

            if field["kind"] == "key":
                issue_url = (
                    f"{JIRA_SERVER.rstrip('/')}"
                    f"/browse/{issue.key}"
                )

                worksheet.write_url(
                    row_index,
                    column_index,
                    issue_url,
                    link_format,
                    string=str(value),
                )

                continue

            if field["kind"] == "url":
                worksheet.write_url(
                    row_index,
                    column_index,
                    str(value),
                    link_format,
                    string=str(value),
                )

                continue

            schema_type = field.get(
                "schema_type"
            )

            if (
                isinstance(value, datetime)
                and schema_type == "date"
            ):
                worksheet.write_datetime(
                    row_index,
                    column_index,
                    value,
                    date_only_format,
                )
                continue

            if isinstance(value, datetime):
                worksheet.write_datetime(
                    row_index,
                    column_index,
                    value,
                    date_format,
                )
                continue

            if isinstance(value, (int, float)):
                worksheet.write_number(
                    row_index,
                    column_index,
                    value,
                )
                continue

            if isinstance(value, bool):
                worksheet.write_boolean(
                    row_index,
                    column_index,
                    value,
                )
                continue

            worksheet.write(
                row_index,
                column_index,
                value,
                text_format,
            )

    # --------------------------------------------------------
    # Excel Table
    # --------------------------------------------------------

    last_column = len(headers) - 1

    if data_rows:
        last_row = len(data_rows)

        worksheet.add_table(
            0,
            0,
            last_row,
            last_column,
            {
                "name": "JiraIssuesTable",
                "style": "Table Style Medium 2",
                "columns": [
                    {
                        "header": header,
                        "header_format": header_format,
                    }
                    for header in headers
                ],
            },
        )

    else:
        for col, header in enumerate(headers):
            worksheet.write(
                0,
                col,
                header,
                header_format,
            )

        worksheet.autofilter(
            0,
            0,
            0,
            last_column,
        )

    worksheet.set_row(
        0,
        30,
    )

    # ========================================================
    # COLUMN WIDTH
    # ========================================================

    for column_index, field in enumerate(
        resolved_fields
    ):

        header = field["header"]

        sample_values = [
            row[column_index]
            for row in data_rows[:1000]
        ]

        lengths = [
            len(str(header))
        ]

        for value in sample_values:

            if isinstance(value, datetime):
                lengths.append(19)
                continue

            text = str(
                value if value is not None else ""
            )

            lines = text.splitlines() or [""]

            lengths.append(
                max(
                    len(line)
                    for line in lines
                )
            )

        width = max(lengths) + 2

        field_name = header.casefold()

        if "summary" in field_name:
            width = max(width, 35)

        if (
            "description" in field_name
            or "comment" in field_name
        ):
            width = max(width, 45)

        if field["kind"] == "key":
            width = max(width, 14)

        if field["kind"] == "url":
            width = max(width, 35)

        if field.get("schema_type") in {
            "datetime",
            "date",
        }:
            width = max(width, 18)

        width = min(
            max(width, 12),
            55,
        )

        worksheet.set_column(
            column_index,
            column_index,
            width,
        )

    # ========================================================
    # CONDITIONAL FORMATTING
    # ========================================================

    if data_rows:
        last_data_row = len(data_rows)

        for column_index, field in enumerate(
            resolved_fields
        ):

            field_id = field.get(
                "field_id"
            )

            header = field["header"].casefold()

            # Status
            if (
                field_id == "status"
                or header == "status"
            ):

                for text in (
                    "Done",
                    "Closed",
                    "Resolved",
                    "Complete",
                ):
                    worksheet.conditional_format(
                        1,
                        column_index,
                        last_data_row,
                        column_index,
                        {
                            "type": "text",
                            "criteria": "containing",
                            "value": text,
                            "format": done_format,
                        },
                    )

                worksheet.conditional_format(
                    1,
                    column_index,
                    last_data_row,
                    column_index,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": "In Progress",
                        "format": progress_format,
                    },
                )

                worksheet.conditional_format(
                    1,
                    column_index,
                    last_data_row,
                    column_index,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": "Blocked",
                        "format": blocked_format,
                    },
                )

            # Priority
            if (
                field_id == "priority"
                or header == "priority"
            ):

                for text in (
                    "Highest",
                    "Critical",
                    "Blocker",
                ):
                    worksheet.conditional_format(
                        1,
                        column_index,
                        last_data_row,
                        column_index,
                        {
                            "type": "text",
                            "criteria": "containing",
                            "value": text,
                            "format": high_priority_format,
                        },
                    )

    # ========================================================
    # PRINT SETTINGS
    # ========================================================

    worksheet.set_landscape()

    worksheet.fit_to_pages(
        1,
        0,
    )

    worksheet.repeat_rows(
        0,
        0,
    )

    worksheet.set_margins(
        0.3,
        0.3,
        0.5,
        0.5,
    )

    worksheet.set_header(
        "&CJira Issue Report"
    )

    worksheet.set_footer(
        "&LGenerated from Jira"
        "&RPage &P of &N"
    )

    # ========================================================
    # EXPORT INFO SHEET
    # ========================================================

    create_info_sheet(
        workbook=workbook,
        worksheet=info_sheet,
        issue_count=len(issues),
        resolved_fields=resolved_fields,
    )

    workbook.close()

    return output_path


# ============================================================
# INFO SHEET
# ============================================================


def create_info_sheet(
    workbook,
    worksheet,
    issue_count: int,
    resolved_fields: list[dict[str, Any]],
) -> None:

    worksheet.hide_gridlines(2)

    title_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 20,
            "font_color": "#FFFFFF",
            "bg_color": "#172B4D",
            "align": "left",
            "valign": "vcenter",
        }
    )

    section_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 11,
            "font_color": "#172B4D",
            "bg_color": "#DEEBFF",
            "border": 0,
        }
    )

    label_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#42526E",
            "valign": "top",
        }
    )

    value_format = workbook.add_format(
        {
            "font_color": "#172B4D",
            "text_wrap": True,
            "valign": "top",
        }
    )

    url_format = workbook.add_format(
        {
            "font_color": "#0052CC",
            "underline": True,
        }
    )

    number_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 14,
            "font_color": "#0052CC",
        }
    )

    worksheet.merge_range(
        "A1:D2",
        "Jira Export Report",
        title_format,
    )

    worksheet.set_row(
        0,
        28,
    )

    worksheet.write(
        "A4",
        "Export Information",
        section_format,
    )

    worksheet.merge_range(
        "A4:D4",
        "Export Information",
        section_format,
    )

    info = [
        (
            "Generated",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ),
        (
            "Issue count",
            issue_count,
        ),
        (
            "Authentication",
            AUTH_MODE,
        ),
    ]

    row = 4

    for label, value in info:
        worksheet.write(
            row,
            0,
            label,
            label_format,
        )

        if label == "Issue count":
            worksheet.write(
                row,
                1,
                value,
                number_format,
            )
        else:
            worksheet.write(
                row,
                1,
                value,
                value_format,
            )

        row += 1

    worksheet.write(
        row,
        0,
        "Jira Server",
        label_format,
    )

    worksheet.write_url(
        row,
        1,
        JIRA_SERVER,
        url_format,
        string=JIRA_SERVER,
    )

    row += 2

    worksheet.merge_range(
        row,
        0,
        row,
        3,
        "JQL",
        section_format,
    )

    row += 1

    worksheet.merge_range(
        row,
        0,
        row + 2,
        3,
        JQL,
        value_format,
    )

    row += 4

    worksheet.merge_range(
        row,
        0,
        row,
        3,
        "Exported Fields",
        section_format,
    )

    row += 1

    worksheet.write(
        row,
        0,
        "#",
        label_format,
    )

    worksheet.write(
        row,
        1,
        "Excel Column",
        label_format,
    )

    worksheet.write(
        row,
        2,
        "Jira Field ID",
        label_format,
    )

    worksheet.write(
        row,
        3,
        "Type",
        label_format,
    )

    row += 1

    for index, field in enumerate(
        resolved_fields,
        start=1,
    ):

        worksheet.write(
            row,
            0,
            index,
        )

        worksheet.write(
            row,
            1,
            field["header"],
            value_format,
        )

        worksheet.write(
            row,
            2,
            field.get("field_id") or field["kind"],
            value_format,
        )

        worksheet.write(
            row,
            3,
            field.get("schema_type") or "-",
            value_format,
        )

        row += 1

    worksheet.set_column(
        "A:A",
        18,
    )

    worksheet.set_column(
        "B:B",
        35,
    )

    worksheet.set_column(
        "C:C",
        28,
    )

    worksheet.set_column(
        "D:D",
        20,
    )


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    validate_field_list()

    print(
        f"Jira'ya bağlanılıyor: {JIRA_SERVER}"
    )

    jira = create_jira_client()

    print("Jira bağlantısı başarılı.")

    resolved_fields = resolve_fields(
        jira
    )

    print("\nAlanlar:")

    for index, field in enumerate(
        resolved_fields,
        start=1,
    ):
        print(
            f"{index:>2}. "
            f"{field['header']:<30} -> "
            f"{field.get('field_id') or field['kind']}"
        )

    issues = fetch_issues(
        jira,
        resolved_fields,
    )

    output_path = create_excel(
        issues,
        resolved_fields,
    )

    print()
    print("Excel oluşturuldu:")
    print(output_path)


if __name__ == "__main__":
    main()