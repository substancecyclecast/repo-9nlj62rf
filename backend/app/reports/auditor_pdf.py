"""Auditor-ready PDF report generation (ReportLab).

Produces a treasury & accounting report a firm like Deloitte could review:
cover, treasury position, trial balance, income statement, and the recent
transaction register — all generated from the same double-entry source of truth.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, Transaction
from app.services import ledger_service, treasury_service

_BRAND = colors.HexColor("#4f46e5")
_DARK = colors.HexColor("#0f172a")
_MUTED = colors.HexColor("#64748b")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("MTitle", parent=ss["Title"], textColor=_DARK, fontSize=24))
    ss.add(ParagraphStyle("MH2", parent=ss["Heading2"], textColor=_BRAND, fontSize=14))
    ss.add(ParagraphStyle("MMuted", parent=ss["Normal"], textColor=_MUTED, fontSize=9))
    return ss


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), _DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def build_auditor_report(db: Session, organization_id: int) -> bytes:
    org = db.get(Organization, organization_id)
    if org is None:
        raise ValueError("Organization not found")

    ov = treasury_service.overview(db, organization_id)
    tb = ledger_service.trial_balance(db, organization_id)
    pnl = ledger_service.income_statement(db, organization_id)

    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER, topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch, title="Mandate Treasury Report",
    )
    story: list = []

    # Cover
    story.append(Paragraph("Mandate", ss["MTitle"]))
    story.append(Paragraph("Autonomous Treasury &amp; Accounting Report", ss["MH2"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>{org.name}</b> — {org.legal_entity or 'Crypto-native organization'}", ss["Normal"]))
    story.append(
        Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
            f"Base currency {org.base_currency} · Reporting stablecoin {org.base_stablecoin}",
            ss["MMuted"],
        )
    )
    story.append(Spacer(1, 16))

    # Treasury position
    story.append(Paragraph("1. Treasury Position", ss["MH2"]))
    pos_rows = [
        ["Metric", "Value"],
        ["Net Asset Value (NAV)", _money(ov["nav_usd"])],
        ["Liquid (wallets)", _money(ov["liquid_usd"])],
        ["Deployed in yield", _money(ov["yield_usd"])],
        ["Stablecoins", f"{_money(ov['stablecoin_usd'])} ({ov['stablecoin_pct'] * 100:.1f}%)"],
        ["Volatile assets", _money(ov["volatile_usd"])],
        ["Projected annual yield", _money(ov["projected_annual_yield_usd"])],
    ]
    story.append(_table(pos_rows, col_widths=[3.0 * inch, 3.0 * inch]))
    story.append(Spacer(1, 10))

    if ov["by_chain"]:
        story.append(Paragraph("Allocation by chain", ss["Normal"]))
        chain_rows = [["Chain", "USD Value"]] + [
            [c, _money(v)] for c, v in sorted(ov["by_chain"].items(), key=lambda x: -x[1])
        ]
        story.append(_table(chain_rows, col_widths=[3.0 * inch, 3.0 * inch]))
    story.append(Spacer(1, 16))

    # Trial balance
    story.append(Paragraph("2. Trial Balance (double-entry)", ss["MH2"]))
    tb_rows = [["Code", "Account", "Type", "Debit", "Credit", "Balance"]]
    total_d = total_c = 0.0
    for r in tb:
        tb_rows.append(
            [r["code"], r["name"], r["type"], _money(r["debit"]), _money(r["credit"]), _money(r["balance"])]
        )
        total_d += r["debit"]
        total_c += r["credit"]
    tb_rows.append(["", "TOTALS", "", _money(round(total_d, 2)), _money(round(total_c, 2)), ""])
    t = _table(tb_rows, col_widths=[0.6 * inch, 2.3 * inch, 0.9 * inch, 1.1 * inch, 1.1 * inch, 1.1 * inch])
    t.setStyle(TableStyle([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                           ("LINEABOVE", (0, -1), (-1, -1), 0.75, _DARK)]))
    story.append(t)
    balanced = abs(round(total_d, 2) - round(total_c, 2)) < 0.005
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"Books are {'<b>balanced</b>' if balanced else '<b>OUT OF BALANCE</b>'}: "
            f"total debits {_money(round(total_d, 2))} vs credits {_money(round(total_c, 2))}.",
            ss["MMuted"],
        )
    )
    story.append(Spacer(1, 16))

    # Income statement
    story.append(Paragraph("3. Income Statement", ss["MH2"]))
    is_rows = [
        ["Line", "Amount"],
        ["Total revenue", _money(pnl["revenue"])],
        ["Total expense", _money(pnl["expense"])],
        ["Net income", _money(pnl["net_income"])],
    ]
    story.append(_table(is_rows, col_widths=[3.0 * inch, 3.0 * inch]))
    story.append(Spacer(1, 16))

    # Transaction register (recent)
    story.append(Paragraph("4. Transaction Register (most recent 25)", ss["MH2"]))
    txs = db.scalars(
        select(Transaction)
        .where(Transaction.organization_id == organization_id)
        .order_by(Transaction.created_at.desc())
        .limit(25)
    ).all()
    if txs:
        tx_rows = [["Date", "Type", "Counterparty", "Chain", "Asset", "USD", "Status"]]
        for t_ in txs:
            tx_rows.append(
                [
                    t_.created_at.strftime("%m-%d %H:%M"),
                    t_.tx_type,
                    (t_.counterparty or "—")[:22],
                    t_.chain,
                    t_.asset,
                    _money(t_.usd_value),
                    t_.status,
                ]
            )
        story.append(
            _table(
                tx_rows,
                col_widths=[0.9 * inch, 0.8 * inch, 1.6 * inch, 0.8 * inch, 0.6 * inch, 1.0 * inch, 1.2 * inch],
            )
        )
    else:
        story.append(Paragraph("No transactions recorded.", ss["MMuted"]))

    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "Prepared by Mandate — autonomous CFO agent. Every figure derives from the "
            "organization's on-chain activity and double-entry ledger. This report is "
            "suitable as a working paper for external audit.",
            ss["MMuted"],
        )
    )

    doc.build(story)
    return buf.getvalue()
