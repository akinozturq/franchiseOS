import io
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)

# Colors matching Design System
PRIMARY_COLOR = colors.HexColor("#0f172a")    # Slate 900
SECONDARY_COLOR = colors.HexColor("#334155")  # Slate 700
BORDER_COLOR = colors.HexColor("#cbd5e1")     # Slate 300
BG_LIGHT = colors.HexColor("#f8fafc")         # Slate 50
ACCENT_BLUE = colors.HexColor("#2563eb")      # Blue 600
SUCCESS_GREEN = colors.HexColor("#16a34a")    # Green 600
MUTED_TEXT = colors.HexColor("#64748b")       # Slate 500

def format_currency(val: Any) -> str:
    if val is None:
        return "0,00 ₺"
    try:
        d = Decimal(str(val))
        return f"{d:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{val} ₺"

def format_percent(val: Any) -> str:
    if val is None:
        return "%0"
    try:
        d = Decimal(str(val))
        if d < 1 and d > 0:
            pct = d * 100
        else:
            pct = d
        return f"%{pct:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")
    except Exception:
        return f"%{val}"

def generate_reconciliation_pdf(data: Dict[str, Any]) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=PRIMARY_COLOR
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT
    )
    badge_style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=PRIMARY_COLOR
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=PRIMARY_COLOR
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=SECONDARY_COLOR
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR,
        alignment=2
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR,
        alignment=2
    )

    story = []

    # 1. Header
    period = data.get("period", "2026-01")
    branch_name = data.get("branch_name", "Bayi")
    is_closed = data.get("is_closed", False)
    closed_at = data.get("closed_at")
    closed_by = data.get("closed_by_name", "Franchisor Admin")

    status_text = "RESMI KAPALI & DONDURULMUS DONEM" if is_closed else "TASLAK DONEM (ACIK / HESAPLAMA)"
    badge_bg = SUCCESS_GREEN if is_closed else ACCENT_BLUE

    header_table = Table(
        [
            [
                Paragraph("FRANCHISE RESMİ DÖNEM MUTABAKAT BELGESİ", title_style),
                Paragraph(f"<font color='white'><b>{status_text}</b></font>", badge_style)
            ],
            [
                Paragraph(f"Dönem: <b>{period}</b> | Bayi: <b>{branch_name}</b>", subtitle_style),
                Paragraph(f"Oluşturulma: {datetime.now().strftime('%d.%m.%Y %H:%M')}", subtitle_style)
            ]
        ],
        colWidths=[380, 142]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), badge_bg),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=2, spaceAfter=8))

    # 2. Entity & Audit Meta Table
    inv_summary = data.get("invoice_summary") or {}
    collector = inv_summary.get("collector_party") or data.get("collector_party", "BAYI")
    issuer = inv_summary.get("issuer", "Franchisor")
    recipient = inv_summary.get("recipient", "Bayi")
    dir_text = f"{issuer} -> {recipient}"

    audit_rows = [
        [
            Paragraph("Bayi Ünvanı / Şube:", meta_label), Paragraph(str(branch_name), meta_val),
            Paragraph("Franchisor:", meta_label), Paragraph("Franchise Genel Merkez A.Ş.", meta_val),
        ],
        [
            Paragraph("Tahsilatı Yapan:", meta_label), Paragraph(f"<b>{collector}</b>", meta_val),
            Paragraph("Fatura Yönü:", meta_label), Paragraph(f"<b>{dir_text}</b>", meta_val),
        ]
    ]
    if is_closed:
        audit_rows.append([
            Paragraph("Kapatma Tarihi:", meta_label), Paragraph(str(closed_at)[:19].replace("T", " ") if closed_at else "-", meta_val),
            Paragraph("Onaylayan:", meta_label), Paragraph(str(closed_by), meta_val),
        ])

    audit_table = Table(audit_rows, colWidths=[100, 160, 100, 162])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 14))

    # 3. Financial Summary KPIs
    story.append(Paragraph("1. FİNANSAL MUTABAKAT ÖZETİ", heading_style))
    story.append(Spacer(1, 4))

    net_turnover = format_currency(data.get("total_turnover_excl_vat"))
    total_comm = format_currency(data.get("franchisor_share_total_excl_vat") or data.get("total_commission_amount"))
    bayi_net = format_currency(data.get("bayi_share_total_excl_vat"))
    eff_rate = format_percent(data.get("applied_rate_percentage") or data.get("effective_commission_rate"))

    inv_net = format_currency(inv_summary.get("amount_excl_vat") or data.get("reconciliation_amount_excl_vat"))
    inv_vat = format_currency(inv_summary.get("vat_amount") or data.get("reconciliation_vat_amount"))
    inv_tot = format_currency(inv_summary.get("total_amount_incl_vat") or data.get("reconciliation_amount_incl_vat"))
    vat_pct = format_percent(inv_summary.get("vat_rate") or data.get("vat_rate", 0.20))

    kpi_data = [
        [
            Paragraph("Toplam Ciro (KDV Hariç)", meta_label),
            Paragraph("Bayi Payı (KDV Hariç)", meta_label),
            Paragraph("Franchisor Komisyon Payı", meta_label),
            Paragraph("Uygulanan Oran %", meta_label),
        ],
        [
            Paragraph(net_turnover, cell_bold),
            Paragraph(bayi_net, cell_bold),
            Paragraph(total_comm, cell_bold),
            Paragraph(eff_rate, cell_bold),
        ],
        [
            Paragraph("Fatura Matrahı (KDV Hariç)", meta_label),
            Paragraph(f"KDV ({vat_pct})", meta_label),
            Paragraph("Toplam Fatura Tutarı", meta_label),
            Paragraph("Toplam İşlem Adedi", meta_label),
        ],
        [
            Paragraph(inv_net, cell_bold),
            Paragraph(inv_vat, cell_bold),
            Paragraph(f"<font color='#2563eb'><b>{inv_tot}</b></font>", cell_bold),
            Paragraph(str(data.get("total_transactions") or data.get("transaction_count", 0)), cell_bold),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 132, 130])
    kpi_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (-1, 0), BG_LIGHT),
        ('BACKGROUND', (0, 2), (-1, 2), BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 4. Departman Bazlı Dağılım
    dept_details = data.get("department_breakdown", [])
    if dept_details:
        story.append(Paragraph("2. DEPARTMAN BAZINDA DAĞILIM", heading_style))
        story.append(Spacer(1, 4))

        dept_headers = [
            Paragraph("Departman", meta_label),
            Paragraph("İşlem Sayısı", meta_label),
            Paragraph("Ciro (KDV Hariç)", meta_label),
            Paragraph("Ciro Payı %", meta_label),
        ]
        dept_rows = [dept_headers]
        for d in dept_details:
            dept_rows.append([
                Paragraph(d.get("department_name", "-"), body_style),
                Paragraph(str(d.get("transaction_count", 0)), cell_right),
                Paragraph(format_currency(d.get("total_turnover_excl_vat")), cell_right),
                Paragraph(format_percent(d.get("percentage_of_total")), cell_right),
            ])
        dept_table = Table(dept_rows, colWidths=[160, 90, 130, 142])
        dept_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(dept_table)
        story.append(Spacer(1, 14))

    # 5. Kural ve İstisna Özeti
    applied_tier = data.get("applied_tier")
    if applied_tier or data.get("rate_explanation"):
        story.append(Paragraph("3. UYGULANAN KURAL VE İSTİSNA DETAYLARI", heading_style))
        story.append(Spacer(1, 4))
        tier_text = f"<b>Uygulanan Dilim:</b> {applied_tier.get('name', 'Dilim') if applied_tier else '-'} (Oran: {eff_rate})<br/>"
        tier_text += f"<b>Açıklama:</b> {data.get('rate_explanation', '-')}<br/>"
        if data.get("override_transactions_count", 0) > 0:
            tier_text += f"<b>Kategori İstisnası:</b> {data.get('override_transactions_count')} işlem özel istisnalı oran üzerinden hesaplanmıştır (İstisna Cirosu: {format_currency(data.get('override_turnover_excl_vat'))})."
        
        info_table = Table([[Paragraph(tier_text, body_style)]], colWidths=[522])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 14))

    # 6. Audit & Signature Block
    sign_block = [
        [
            Paragraph("<b>BAYİ YETKİLİSİ</b>", meta_label),
            Paragraph("<b>FRANCHİSOR MERKEZ YETKİLİSİ</b>", meta_label)
        ],
        [
            Paragraph(f"{branch_name}<br/>Tarih: .........................<br/>İmza / Kaşe:", subtitle_style),
            Paragraph("Franchise Genel Merkez A.Ş.<br/>Tarih: .........................<br/>İmza / Kaşe:", subtitle_style)
        ]
    ]
    sign_table = Table(sign_block, colWidths=[260, 262])
    sign_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=4, spaceAfter=8),
        Paragraph("İşbu mutabakat raporu FranchiseOS tarafından elektronik ve değişmez olarak üretilmiştir.", subtitle_style),
        Spacer(1, 8),
        sign_table
    ]))

    doc.build(story)
    buf.seek(0)
    return buf

def generate_bonus_pdf(data: Dict[str, Any]) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=PRIMARY_COLOR
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT
    )
    badge_style = ParagraphStyle(
        "Badge",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=PRIMARY_COLOR
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=SECONDARY_COLOR
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR,
        alignment=2
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=PRIMARY_COLOR,
        alignment=2
    )

    story = []

    period = data.get("period", "2026-01")
    branch_name = data.get("branch_name", "Bayi")
    is_closed = data.get("is_closed", False)
    closed_at = data.get("closed_at")
    closed_by = data.get("closed_by_name", "Franchisor Admin")

    status_text = "RESMI KAPALI & DONDURULMUS" if is_closed else "TASLAK HESAPLAMA (ACIK)"
    badge_bg = SUCCESS_GREEN if is_closed else ACCENT_BLUE

    header_table = Table(
        [
            [
                Paragraph("FRANCHISE PERSONEL PRİM RAPORU", title_style),
                Paragraph(f"<font color='white'><b>{status_text}</b></font>", badge_style)
            ],
            [
                Paragraph(f"Dönem: <b>{period}</b> | Şube: <b>{branch_name}</b>", subtitle_style),
                Paragraph(f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}", subtitle_style)
            ]
        ],
        colWidths=[380, 142]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), badge_bg),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceBefore=2, spaceAfter=8))

    # Summary KPI
    tot_bonus = format_currency(data.get("grand_total_bonus") or data.get("total_bonus_amount"))
    items = data.get("items") or data.get("employees") or []
    emp_count = data.get("total_employees", len(items))
    unassigned_turnover = format_currency(data.get("unassigned_turnover") or "0.00")

    summary_table = Table(
        [
            [
                Paragraph("Hak Edilen Toplam Prim", meta_label),
                Paragraph("Prim Alan Personel Sayısı", meta_label),
                Paragraph("Toplam İşlem Adedi", meta_label)
            ],
            [
                Paragraph(f"<font color='#2563eb' size='11'><b>{tot_bonus}</b></font>", cell_bold),
                Paragraph(f"<font size='11'><b>{emp_count} Kişi</b></font>", cell_bold),
                Paragraph(str(data.get("total_transactions", 0)), cell_bold)
            ]
        ],
        colWidths=[174, 174, 174]
    )
    summary_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (-1, 0), BG_LIGHT),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Personnel details table
    story.append(Paragraph("PERSONEL BAZLI PRİM DETAYLARI", heading_style))
    story.append(Spacer(1, 4))

    headers = [
        Paragraph("Personel Adı", meta_label),
        Paragraph("Departman", meta_label),
        Paragraph("Rol / Kapsam", meta_label),
        Paragraph("Kapsam Cirosu", meta_label),
        Paragraph("İşlem Sayısı", meta_label),
        Paragraph("Hak Edilen Prim", meta_label),
    ]
    rows = [headers]

    for emp in items:
        name = emp.get("employee_name", "-")
        dept = emp.get("department_name") or "-"
        role = emp.get("role_name", "-")
        source = emp.get("turnover_source", "")
        source_label = "Kendi İşlemleri" if source == "kendi_islemleri" else ("Departman" if source == "kendi_departmani" else "Tüm Bayi")
        turnover = format_currency(emp.get("applicable_turnover_excl_vat") or emp.get("turnover"))
        tx_count = str(emp.get("transaction_count", 0))
        bonus = format_currency(emp.get("bonus_amount") or emp.get("total_bonus"))

        rows.append([
            Paragraph(name, cell_bold),
            Paragraph(dept, body_style),
            Paragraph(f"{role}<br/><font color='#64748b' size='7'>{source_label}</font>", body_style),
            Paragraph(turnover, cell_right),
            Paragraph(tx_count, cell_right),
            Paragraph(f"<font color='#16a34a'><b>{bonus}</b></font>", cell_right_bold),
        ])

    emp_table = Table(rows, colWidths=[120, 82, 110, 80, 50, 80])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 16))

    # Audit & Signature
    sign_block = [
        [
            Paragraph("<b>BAYİ ŞUBE YÖNETİCİSİ</b>", meta_label),
            Paragraph("<b>GENEL MERKEZ İK / FİNANS ONAYI</b>", meta_label)
        ],
        [
            Paragraph(f"{branch_name}<br/>Tarih: .........................<br/>İmza:", subtitle_style),
            Paragraph("Franchise Genel Merkez A.Ş.<br/>Tarih: .........................<br/>İmza:", subtitle_style)
        ]
    ]
    sign_table = Table(sign_block, colWidths=[260, 262])
    sign_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))

    story.append(KeepTogether([
        HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=4, spaceAfter=8),
        Paragraph("İşbu prim raporu FranchiseOS tarafından elektronik ortamda oluşturulmuş ve denetime hazırdır.", subtitle_style),
        Spacer(1, 8),
        sign_table
    ]))

    doc.build(story)
    buf.seek(0)
    return buf
