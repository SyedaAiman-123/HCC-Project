"""Create the figures used in the Word report (saved to report/figures/).

Run:  python report/make_figures.py
Flowcharts are drawn with matplotlib; the timing and attack graphs are copied
from results/ (produced by performance.py); the frequency chart is computed live.
"""

import os
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import frequency_analysis as fa
import hybrid_cipher
import rail_fence
import sample_data
import shift_cipher

FIG_DIR = os.path.join(HERE, "figures")
NAVY, LIGHT, ORANGE, GREEN = "#1F3864", "#DCE6F2", "#FCE4D6", "#E2EFDA"


def _box(ax, x, y, w, h, text, kind="proc", size=8.5):
    colors = {"term": (GREEN, "round,pad=0.02,rounding_size=0.25"),
              "proc": (LIGHT, "round,pad=0.02,rounding_size=0.08"),
              "io": (ORANGE, "round,pad=0.02,rounding_size=0.08")}
    if kind == "dec":
        pts = [(x, y + h / 2), (x + w / 2, y + h), (x + w, y + h / 2), (x + w / 2, y)]
        ax.add_patch(Polygon(pts, closed=True, facecolor="#FFF2CC", edgecolor=NAVY, linewidth=1.2))
    else:
        fill, style = colors[kind]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, facecolor=fill,
                                    edgecolor=NAVY, linewidth=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, wrap=True)


def _arrow(ax, x1, y1, x2, y2, label=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, linewidth=1.2))
    if label:
        ax.text((x1 + x2) / 2 + 0.08, (y1 + y2) / 2 + 0.05, label, fontsize=8, color="firebrick")


def flowchart(steps, filename, side_notes=None, width=6.4):
    """Vertical flowchart. steps = [(kind, text)], side_notes = {step_index: text}
    drawn as a 'No' branch box on the right of a decision."""
    side_notes = side_notes or {}
    gap, w = 0.45, 4.2
    heights = [1.1 if k == "dec" else 0.75 for k, _ in steps]
    total = sum(heights) + gap * (len(steps) - 1)
    fig, ax = plt.subplots(figsize=(width, total * 0.62))
    ax.set_xlim(0, 7.6)
    ax.set_ylim(-0.1, total + 0.1)
    ax.axis("off")
    x = 0.3
    y = total
    prev_bottom = None
    for index, ((kind, text), h) in enumerate(zip(steps, heights)):
        y -= h
        _box(ax, x, y, w, h, text, kind)
        if prev_bottom is not None:
            _arrow(ax, x + w / 2, prev_bottom, x + w / 2, y + h)
        if index in side_notes:
            _arrow(ax, x + w, y + h / 2, x + w + 0.45, y + h / 2, "No")
            _box(ax, x + w + 0.45, y + h / 2 - 0.35, 2.4, 0.7, side_notes[index], "io", size=8)
        prev_bottom = y
        y -= gap
    fig.savefig(os.path.join(FIG_DIR, filename), dpi=200, bbox_inches="tight")
    plt.close(fig)


def architecture():
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.set_xlim(0, 10.6)
    ax.set_ylim(0, 5)
    ax.axis("off")
    labels_top = [("Plaintext", "io"), ("Normalize\nA-Z only", "proc"),
                  ("Stage 1\nVigenere\nkey K (>= 10)", "proc"), ("Stage 2\nRail Fence\nkey r (>= 2)", "proc"),
                  ("Ciphertext", "io")]
    labels_bottom = [("Plaintext", "io"), ("Stage 1^-1\nVigenere\nsubtract K", "proc"),
                     ("Stage 2^-1\nRail Fence\nundo zig-zag", "proc"), ("Normalize\nciphertext", "proc"),
                     ("Ciphertext", "io")]
    w, h, gap = 1.7, 1.1, 0.5
    for row, (labels, y) in enumerate(((labels_top, 3.3), (labels_bottom, 0.5))):
        for i, (text, kind) in enumerate(labels):
            _box(ax, 0.2 + i * (w + gap), y, w, h, text, kind, size=8)
        for i in range(4):
            x1, x2 = 0.2 + i * (w + gap) + w, 0.2 + (i + 1) * (w + gap)
            if row == 0:
                _arrow(ax, x1, y + h / 2, x2, y + h / 2)
            else:
                _arrow(ax, x2, y + h / 2, x1, y + h / 2)
    ax.text(5.3, 4.65, "ENCRYPTION  (left to right)", ha="center", fontsize=10, color=NAVY, weight="bold")
    ax.text(5.3, 2.35, "DECRYPTION  (right to left: stages undone in reverse order)", ha="center",
            fontsize=10, color=NAVY, weight="bold")
    fig.savefig(os.path.join(FIG_DIR, "architecture.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def rail_fence_example():
    plain = "MEETMEATTHELIBRARYTOMORROW"
    _, stage1, cipher = hybrid_cipher.encrypt_with_trace(plain, "SECURITYKEYS", 4)
    pattern = rail_fence.rail_pattern(len(stage1), 4)
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.set_xlim(-1, len(stage1))
    ax.set_ylim(-2.6, 3.6)
    ax.axis("off")
    ax.plot(range(len(stage1)), [3 - r for r in pattern], color="#9DB4D6", linewidth=1.5, zorder=1)
    for i, (ch, rail) in enumerate(zip(stage1, pattern)):
        ax.scatter(i, 3 - rail, s=260, color=LIGHT, edgecolor=NAVY, zorder=2)
        ax.text(i, 3 - rail, ch, ha="center", va="center", fontsize=8, weight="bold", zorder=3)
    for rail in range(4):
        ax.text(-1, 3 - rail, f"rail {rail}", ha="right", va="center", fontsize=8, color=NAVY)
    rails = ["".join(c for c, r in zip(stage1, pattern) if r == k) for k in range(4)]
    ax.text(len(stage1) / 2, -0.8, "Read rail by rail:  " + "  +  ".join(rails), ha="center", fontsize=9)
    ax.text(len(stage1) / 2, -1.6, "Ciphertext = " + cipher, ha="center", fontsize=10, weight="bold",
            color="firebrick")
    ax.text(len(stage1) / 2, -2.3, "(Input to Stage 2 = Stage 1 output: " + stage1 + ")", ha="center", fontsize=8,
            color="gray")
    fig.savefig(os.path.join(FIG_DIR, "rail_fence_example.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


def frequency_chart():
    rng = sample_data.make_rng(5)
    plain = sample_data.generate_english_text(1000, rng)
    series = [("English plaintext (1000 letters)", plain),
              ("Shift cipher ciphertext (key 11)", shift_cipher.encrypt(plain, 11)),
              ("HCC ciphertext (SECURITYKEYS, 4 rails)",
               hybrid_cipher.encrypt(plain, sample_data.DEFAULT_KEYWORD, 4))]
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 6.2), sharex=True)
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for ax, (title, text) in zip(axes, series):
        observed = [100 * f for f in fa.letter_frequencies(text)]
        ax.bar(letters, observed, color="#6C8EBF")
        ax.plot(letters, fa.ENGLISH_PERCENT, "o--", color="firebrick", markersize=3, label="Standard English")
        ax.set_title(f"{title}   IC = {fa.index_of_coincidence(text):.4f}", fontsize=9)
        ax.set_ylabel("%", fontsize=8)
        ax.set_ylim(0, 14)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "frequency.png"), dpi=200)
    plt.close(fig)


def make_all():
    os.makedirs(FIG_DIR, exist_ok=True)
    architecture()
    flowchart([("term", "Start"),
               ("io", "Input plaintext, keyword K, rails r"),
               ("dec", "Keys valid?\nK: A-Z, >= 10, not periodic\nr: integer >= 2"),
               ("proc", "Normalize message: upper-case,\nremove every non A-Z character"),
               ("dec", "Message non-empty?"),
               ("proc", "Stage 1 (Vigenere)\nv[i] = (p[i] + k[i mod m]) mod 26"),
               ("proc", "Stage 2 (Rail Fence)\nwrite V in zig-zag on r rails,\nread rail 0, rail 1, ..."),
               ("io", "Output ciphertext C"),
               ("term", "End")],
              "flow_encrypt.png", side_notes={2: "Show error,\nask again", 4: "Show error,\nask again"})
    flowchart([("term", "Start"),
               ("io", "Input ciphertext, keyword K, rails r"),
               ("dec", "Keys valid and\nciphertext non-empty?"),
               ("proc", "Normalize ciphertext to A-Z"),
               ("proc", "Undo Stage 2 (Rail Fence)\nput c[j] back at position pi(j)"),
               ("proc", "Undo Stage 1 (Vigenere)\np[i] = (v[i] - k[i mod m]) mod 26"),
               ("io", "Output normalized plaintext P"),
               ("term", "End")],
              "flow_decrypt.png", side_notes={2: "Show error,\nask again"})
    flowchart([("term", "Start"),
               ("io", "Input C, known plaintext P_known (offset s),\nkey length m, rail range"),
               ("proc", "Take next rail count r in range"),
               ("proc", "Undo Rail Fence: V' = RailFence_r^-1(C)"),
               ("proc", "For each known position i = s + t:\nkey'[i mod m] = (V'[i] - P_known[t]) mod 26"),
               ("dec", "Letters of the same slot\nall agree (no conflicts)?"),
               ("proc", "Keep (r, key') as a surviving hypothesis;\nmore rail counts? -> repeat from step 3"),
               ("dec", "Any survivor?"),
               ("proc", "Rank survivors: complete keys first,\nthen English-likeness of decryption"),
               ("proc", "Decrypt whole ciphertext with best (r, key')\nand re-encrypt to verify"),
               ("io", "Report rails, keyword, plaintext, effort"),
               ("term", "End")],
              "flow_attack.png", side_notes={5: "Reject r,\nnext rail count", 7: "FAILURE: check\nassumptions"})
    rail_fence_example()
    frequency_chart()
    for name in ("timing.png", "attack_success.png"):
        shutil.copy(os.path.join(ROOT, "results", name), os.path.join(FIG_DIR, name))


if __name__ == "__main__":
    make_all()
    print("figures written to", FIG_DIR)
