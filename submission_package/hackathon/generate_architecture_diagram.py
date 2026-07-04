"""Генерирует PNG-диаграмму архитектуры SnabAgent для submission (matplotlib, без graphviz).

Запуск:  python submission_package/hackathon/generate_architecture_diagram.py
Результат: submission_package/hackathon/architecture_diagram.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

QWEN = "#6d28d9"
QWEN_LIGHT = "#ede9fe"
ALI = "#ff6a00"
GREY = "#334155"
BLUE = "#0ea5e9"
GREEN = "#16a34a"
BG = "#0f172a"

fig, ax = plt.subplots(figsize=(15, 9))
fig.patch.set_facecolor("white")
ax.set_xlim(0, 15)
ax.set_ylim(0, 9)
ax.axis("off")

ax.text(
    7.5,
    8.6,
    "SnabAgent — Qwen-Powered Autopilot for Enterprise Procurement",
    ha="center",
    va="center",
    fontsize=17,
    fontweight="bold",
    color=GREY,
)
ax.text(
    7.5,
    8.15,
    "Autopilot Agent · MemoryAgent · Agent Society   |   LangGraph + Qwen Cloud on Alibaba Cloud",
    ha="center",
    va="center",
    fontsize=10.5,
    color="#64748b",
)


def box(x, y, w, h, text, face, edge, fc_text="white", fs=10, bold=True):
    p = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.6,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=fc_text,
        fontweight="bold" if bold else "normal",
        zorder=3,
    )
    return (x + w / 2, y + h / 2, x, y, w, h)


def arrow(p1, p2, color=GREY, style="-|>", lw=1.8, ls="-"):
    a = FancyArrowPatch(
        p1,
        p2,
        arrowstyle=style,
        mutation_scale=14,
        lw=lw,
        color=color,
        zorder=1,
        linestyle=ls,
        connectionstyle="arc3,rad=0.0",
    )
    ax.add_patch(a)


# Input
inp = box(0.4, 6.6, 2.1, 0.9, "Dirty request\n(email · PDF · Excel)", "#f1f5f9", GREY, GREY, 9)

# Agent pipeline (row)
agents = [
    ("Memory\nRecall", GREEN),
    ("Planner", GREY),
    ("Sourcer", GREY),
    ("Communi-\ncator", GREY),
    ("Negotiator", GREY),
    ("Verifier", QWEN),
    ("Reporter", GREY),
    ("Memory\nWriteback", GREEN),
]
ax.text(7.5, 7.75, "LangGraph StateGraph (8 agents)", ha="center", fontsize=11, fontweight="bold", color=GREY)
xs = 0.4
w = 1.72
gap = 0.06
centers = []
y = 5.2
for name, col in agents:
    face = QWEN_LIGHT if col == QWEN else ("#dcfce7" if col == GREEN else "#e2e8f0")
    tcol = QWEN if col == QWEN else (GREEN if col == GREEN else GREY)
    c = box(xs, y, w, 1.0, name, face, col, tcol, 9)
    centers.append(c)
    xs += w + gap

# chain arrows
for i in range(len(centers) - 1):
    _, cy, x, yy, ww, hh = centers[i]
    nx = centers[i + 1][2]
    arrow((x + ww, y + 0.5), (nx, y + 0.5))

# input -> memory recall
arrow((inp[2] + inp[4] / 2, inp[1] - 0.45), (centers[0][0], y + 1.0))

# Escalation from planner
esc = box(2.0, 3.7, 2.0, 0.7, "Escalate to human\n(low confidence)", "#fef2f2", "#dc2626", "#dc2626", 8.5)
arrow((centers[1][0], y), (esc[0], esc[1] + 0.35), color="#dc2626", ls="--")

# Output
out = box(12.5, 6.6, 2.1, 0.9, "Verified decision\n+ full audit tree", "#f1f5f9", GREEN, GREEN, 9)
arrow((centers[-1][0], y + 1.0), (out[2] + out[4] / 2, out[1] - 0.45))

# Qwen Cloud block
qb = box(
    3.0,
    1.9,
    5.2,
    1.15,
    "Qwen Cloud / DashScope  (OpenAI-compatible)\nqwen-max  →  reasoning        qwen-plus  →  INDEPENDENT verifier",
    QWEN_LIGHT,
    QWEN,
    QWEN,
    9.5,
)
# reasoning agents -> qwen
for idx in (1, 2, 4, 6):
    arrow((centers[idx][0], y), (qb[0] - 1.4, qb[1] + qb[5]), color=QWEN, ls=":", lw=1.4)
# verifier -> qwen (independent)
arrow((centers[5][0], y), (qb[0] + 1.6, qb[1] + qb[5]), color=QWEN, lw=2.2)

# State / storage
sb = box(
    8.7,
    1.9,
    5.9,
    1.15,
    "Persistent state · Alibaba Cloud ECS\nPostgreSQL (lots · audit · MEMORY)   ·   Qdrant (NSI+suppliers)   ·   Redis",
    "#e0f2fe",
    BLUE,
    GREY,
    9,
)
arrow((centers[0][0], y), (sb[2] + 0.6, sb[1] + sb[5]), color=BLUE, ls=":", lw=1.4)
arrow((centers[7][0], y), (sb[2] + 1.6, sb[1] + sb[5]), color=BLUE, ls=":", lw=1.4)
arrow((centers[2][0], y), (sb[2] + 2.6, sb[1] + sb[5]), color=BLUE, ls=":", lw=1.4)

# Legend
ax.text(
    0.4,
    0.9,
    "Anti-hallucination: verifier uses a DIFFERENT Qwen model than the primary reasoner.",
    fontsize=9,
    color=QWEN,
    fontweight="bold",
)
ax.text(
    0.4,
    0.5,
    "MemoryAgent: Recall before planning, Writeback after report → the agent self-improves per lot.",
    fontsize=9,
    color=GREEN,
    fontweight="bold",
)

legend_handles = [
    mpatches.Patch(color=QWEN_LIGHT, label="Qwen-served agent"),
    mpatches.Patch(color="#dcfce7", label="Memory (MemoryAgent)"),
    mpatches.Patch(color="#e0f2fe", label="Storage (Alibaba Cloud)"),
]
ax.legend(handles=legend_handles, loc="lower right", fontsize=8.5, framealpha=0.9)

out_path = Path(__file__).with_name("architecture_diagram.png")
plt.tight_layout()
plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
print(f"wrote {out_path}")
