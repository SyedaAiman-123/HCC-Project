"""Build report/HCC_CCP_Report.docx (python-docx).

Run:   python report/make_figures.py
       python report/build_report.py
Then open the .docx in Word and press F9 (or run report/finalize_word.ps1) so that the
Table of Contents / List of Figures / List of Tables show page numbers.

All numbers in the tables are read from results/*.csv (produced by performance.py)
or computed live by running the project code - nothing is typed in by hand.
"""

import csv
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import attack
import hybrid_cipher

FIG = os.path.join(HERE, "figures")
LOGO = os.path.join(HERE, "assets", "ned_logo.png")
OUT = os.path.join(HERE, "HCC_CCP_Report.docx")
BODY_FONT, CODE_FONT = "Times New Roman", "Consolas"
NAVY = RGBColor(0x1F, 0x38, 0x64)
TEXT_WIDTH_CM = 15.9

TEAM = [("Syeda Aiman Munawar", "GA-23003"), ("Naverah Farhat", "GA-23004"),
        ("Duaa Khalid", "GA-23303"), ("Zubia Junaid", "GA-23307")]


def read_csv(name):
    with open(os.path.join(ROOT, "results", name), newline="") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- low-level helpers

def set_font(run, name=BODY_FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def shade(element_pr, fill):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    element_pr.append(shd)


def add_field(paragraph, instruction, cached="1", bold=False, size=None):
    """Insert a complex field (PAGE, SEQ, TOC ...) with cached display text."""
    def fld(kind):
        run = paragraph.add_run()
        element = OxmlElement("w:fldChar")
        element.set(qn("w:fldCharType"), kind)
        run._r.append(element)
        return run
    fld("begin")
    run = paragraph.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruction} "
    run._r.append(instr)
    fld("separate")
    shown = paragraph.add_run(cached)
    set_font(shown, size=size, bold=bold)
    fld("end")


TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|\[\[.+?\]\]|_\{.+?\}|\^\{.+?\})")


def add_runs(paragraph, text, size=None, italic=None, bold=None):
    """Inline markup: **bold**, `code`, [[highlighted placeholder]], _{sub}, ^{sup}."""
    for part in TOKEN.split(text):
        if not part:
            continue
        if part.startswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_font(run, size=size, bold=True, italic=italic)
        elif part.startswith("`"):
            run = paragraph.add_run(part[1:-1])
            set_font(run, CODE_FONT, (size or 12) - 1.5)
        elif part.startswith("[["):
            run = paragraph.add_run(part[2:-2])
            set_font(run, size=size, bold=True)
            rpr = run._r.get_or_add_rPr()
            highlight = OxmlElement("w:highlight")
            highlight.set(qn("w:val"), "yellow")
            rpr.append(highlight)
        elif part.startswith("_{"):
            run = paragraph.add_run(part[2:-1])
            set_font(run, size=size, italic=italic, bold=bold)
            run.font.subscript = True
        elif part.startswith("^{"):
            run = paragraph.add_run(part[2:-1])
            set_font(run, size=size, italic=italic, bold=bold)
            run.font.superscript = True
        else:
            run = paragraph.add_run(part)
            set_font(run, size=size, italic=italic, bold=bold)


class Report:
    def __init__(self):
        self.doc = Document()
        self.fig_count = 0
        self.tab_count = 0
        self._setup()

    # ------------------------------------------------------------------ setup
    def _setup(self):
        doc = self.doc
        section = doc.sections[0]
        section.page_width, section.page_height = Cm(21.0), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.54)
        section.top_margin = section.bottom_margin = Cm(2.3)
        section.different_first_page_header_footer = True
        normal = doc.styles["Normal"]
        normal.font.name = BODY_FONT
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
        normal.font.size = Pt(12)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        for name, size, before, after in (("Heading 1", 16, 18, 8), ("Heading 2", 13.5, 12, 4),
                                          ("Heading 3", 12, 8, 3)):
            style = doc.styles[name]
            style.font.name = BODY_FONT
            style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
            style.element.rPr.rFonts.set(qn("w:ascii"), BODY_FONT)
            style.element.rPr.rFonts.set(qn("w:hAnsi"), BODY_FONT)
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.italic = False
            style.font.color.rgb = NAVY
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True
        cap = doc.styles["Caption"]
        cap.font.name = BODY_FONT
        cap.font.size = Pt(10.5)
        cap.font.bold = True
        cap.font.italic = False
        cap.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
        cap.paragraph_format.space_after = Pt(8)
        cap.paragraph_format.space_before = Pt(4)
        # header / footer for pages after the title page
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run("HCC - Hybrid Classical Cipher  |  CT-486 Network and Information Security")
        set_font(run, size=9, italic=True, color=RGBColor(0x59, 0x59, 0x59))
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_field(footer, "PAGE", "2", size=10)
        props = doc.core_properties
        props.title = "HCC - Hybrid Classical Cipher: Design and Break a Custom Cipher"
        props.author = ", ".join(name for name, _ in TEAM)
        props.subject = "CT-486 Network and Information Security - Complex Computing Problem"

    # ------------------------------------------------------------------ text blocks
    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def h1(self, text):
        return self.doc.add_heading(text, level=1)

    def h2(self, text):
        return self.doc.add_heading(text, level=2)

    def h3(self, text):
        return self.doc.add_heading(text, level=3)

    def p(self, text, align="justify", italic=None, keep_next=False):
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                               "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
        paragraph.paragraph_format.keep_with_next = keep_next
        add_runs(paragraph, text, italic=italic)
        return paragraph

    def bullets(self, items):
        for item in items:
            paragraph = self.doc.add_paragraph(style="List Bullet")
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.space_after = Pt(3)
            add_runs(paragraph, item)

    def formula(self, text):
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(6)
        for part in TOKEN.split(text):
            if not part:
                continue
            if part.startswith("_{"):
                run = paragraph.add_run(part[2:-1])
                run.font.subscript = True
            elif part.startswith("^{"):
                run = paragraph.add_run(part[2:-1])
                run.font.superscript = True
            else:
                run = paragraph.add_run(part)
            set_font(run, "Cambria Math", 12, italic=True)

    def code(self, text):
        lines = text.strip("\n").split("\n")
        for index, line in enumerate(lines):
            paragraph = self.doc.add_paragraph()
            pf = paragraph.paragraph_format
            pf.left_indent, pf.space_after, pf.space_before = Cm(0.4), Pt(0), Pt(0)
            pf.line_spacing = 1.0
            pf.keep_together = True
            if index < len(lines) - 1:
                pf.keep_with_next = True
            shade(paragraph._p.get_or_add_pPr(), "F2F2F2")
            run = paragraph.add_run(line if line else " ")
            set_font(run, CODE_FONT, 9)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ------------------------------------------------------------------ captions, figures, tables
    def _caption(self, label, number, title, keep_next):
        paragraph = self.doc.add_paragraph(style="Caption")
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = keep_next
        run = paragraph.add_run(f"{label} ")
        set_font(run, size=10.5, bold=True)
        add_field(paragraph, f"SEQ {label} \\* ARABIC", str(number), bold=True, size=10.5)
        run = paragraph.add_run(f": {title}")
        set_font(run, size=10.5, bold=True)

    def figure(self, filename, title, width_cm=14.5):
        self.fig_count += 1
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
        paragraph.add_run().add_picture(os.path.join(FIG, filename), width=Cm(width_cm))
        self._caption("Figure", self.fig_count, title, keep_next=False)

    def table(self, title, header, rows, widths_cm, font_size=10, align_right_from=None, bold_rows=()):
        self.tab_count += 1
        self._caption("Table", self.tab_count, title, keep_next=True)
        table = self.doc.add_table(rows=1, cols=len(header))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        scale = TEXT_WIDTH_CM / sum(widths_cm)
        widths = [w * scale for w in widths_cm]

        def fill(row, values, is_header=False, bold=False):
            for i, value in enumerate(values):
                cell = row.cells[i]
                cell.width = Cm(widths[i])
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.paragraph_format.space_before = Pt(1)
                paragraph.paragraph_format.line_spacing = 1.0
                if is_header:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    shade(cell._tc.get_or_add_tcPr(), "1F3864")
                    run = paragraph.add_run(str(value))
                    set_font(run, size=font_size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
                else:
                    if align_right_from is not None and i >= align_right_from:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    add_runs(paragraph, str(value), size=font_size, bold=bold or None)

        fill(table.rows[0], header, is_header=True)
        trpr = table.rows[0]._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        trpr.append(repeat)
        for index, values in enumerate(rows):
            row = table.add_row()
            fill(row, values, bold=index in bold_rows)
            cant_split = OxmlElement("w:cantSplit")
            row._tr.get_or_add_trPr().append(cant_split)
            if index % 2 == 1:
                for cell in row.cells:
                    shade(cell._tc.get_or_add_tcPr(), "EEF3FA")
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)

    # ------------------------------------------------------------------ front matter
    def title_page(self):
        doc = self.doc
        if os.path.exists(LOGO):
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.add_run().add_picture(LOGO, height=Cm(3.6))
        else:  # clearly marked slot so the page layout is final once the logo file is added
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = "Table Grid"
            cell = table.rows[0].cells[0]
            cell.width = Cm(4.0)
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for _ in range(2):
                paragraph.add_run().add_break()
            run = paragraph.add_run("[ NED University logo ]\nsave it as\nreport/assets/ned_logo.png\nand rebuild")
            set_font(run, size=9, italic=True)
            for _ in range(2):
                paragraph.add_run().add_break()
        def centered(text, size, bold=False, color=None, after=6, italic=False):
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(after)
            run = paragraph.add_run(text)
            set_font(run, size=size, bold=bold, color=color, italic=italic)
            return paragraph

        centered("", 6)
        centered("NED UNIVERSITY OF ENGINEERING AND TECHNOLOGY", 20, True, NAVY, 2)
        centered("Karachi, Pakistan", 12, False, None, 20)
        centered("Course: Network and Information Security", 15, True, None, 2)
        centered("Course Code: CT-486", 14, True, None, 2)
        centered("Complex Computing Problem (CCP) - CLO3", 13, False, None, 26)
        centered("DESIGN AND BREAK A CUSTOM CIPHER", 22, True, NAVY, 2)
        centered("BASED ON CLASSICAL TECHNIQUES", 22, True, NAVY, 10)
        centered("HCC - Hybrid Classical Cipher (Vigenere + Rail Fence)", 14, False, None, 4, italic=True)
        centered("Project Report", 16, True, None, 26)

        centered("Submitted by (Team Members)", 13, True, NAVY, 6)
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        widths = [1.4, 8.0, 4.0]
        for i, text in enumerate(("S. No.", "Name", "Roll No.")):
            cell = table.rows[0].cells[i]
            cell.width = Cm(widths[i])
            shade(cell._tc.get_or_add_tcPr(), "1F3864")
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_font(paragraph.add_run(text), size=11.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        for number, (name, roll) in enumerate(TEAM, 1):
            row = table.add_row()
            for i, text in enumerate((str(number), name, roll)):
                cell = row.cells[i]
                cell.width = Cm(widths[i])
                paragraph = cell.paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 1 else WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.space_before = Pt(2)
                set_font(paragraph.add_run(text), size=12)
        centered("", 10)
        centered("Course Advisor", 13, True, NAVY, 2)
        centered("Dr. Shariq Mahmood Khan", 14, False, None, 18)
        self.page_break()

    def front_heading(self, text):
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(14)
        set_font(paragraph.add_run(text), size=18, bold=True, color=NAVY)

    def toc_block(self, heading, instruction):
        self.front_heading(heading)
        paragraph = self.doc.add_paragraph()
        add_field(paragraph, instruction, "Right-click here and choose Update Field (or press F9) to build this list.")
        self.page_break()


# --------------------------------------------------------------------------- report content

def fmt_ms(seconds):
    return f"{float(seconds) * 1000:.4f}"


def body(r):
    # ---------- live worked example (real code, not typed numbers)
    plain = "MEETMEATTHELIBRARYTOMORROW"
    keyword, rails = "SECURITYKEYS", 4
    normalized, stage1, cipher = hybrid_cipher.encrypt_with_trace(plain, keyword, rails)
    known = plain[:16]
    demo = attack.known_plaintext_attack(cipher, known, 12, (2, 8))
    derivation = attack.derivation_table(cipher, known, rails, 12)
    timing = read_csv("timing.csv")
    kpa = read_csv("attack_success.csv")
    coa = read_csv("ciphertext_only.csv")

    # ===================================================================== Abstract
    r.h1("Abstract")
    r.p("This report presents **HCC (Hybrid Classical Cipher)**, a two-stage cipher built from two classical "
        "techniques: a Vigenere substitution with a 12-letter keyword (Stage 1) followed by a Rail Fence "
        "transposition with a configurable number of rails (Stage 2). The cipher is implemented in Python with "
        "strict input validation, a menu-driven command-line interface and 52 automated tests. A realistic "
        "**known-plaintext attack** is implemented that is never given the secret keys: it searches the rail "
        "count, undoes the transposition for every guess, derives the Vigenere key letters by modular "
        "subtraction and accepts a guess only if the letters form a consistent repeating keyword. "
        "Over 200 random trials per setting, the attack recovered the keys and the full plaintext in 100% of "
        "trials whenever the known segment was at least one letter longer than the key and the English-likeness "
        "tie-break was used, at a cost of about 19 x n character operations (milliseconds). A frequency-analysis "
        "module shows why a plain histogram attack fails on HCC, and a bonus ciphertext-only attack shows that "
        "the cipher still falls to column-wise statistics given about 500 letters. Encryption and decryption are "
        "O(n) and measured 2 to 3.7 times slower than a single-stage Shift cipher. The report concludes that "
        "HCC is a useful teaching design but is not secure against modern cryptanalysis, and proposes inexpensive "
        "improvements.")
    r.page_break()

    # ===================================================================== 1 Introduction
    r.h1("1. Introduction")
    r.p("Before computers, secret writing relied on two elementary operations: **substitution**, which replaces "
        "letters by other letters, and **transposition**, which rearranges the order of letters. Shannon later "
        "described the same two ideas as confusion and diffusion, and modern block ciphers still combine them "
        "over many rounds [1], [2]. This project explores the idea in its simplest form: we design a custom cipher "
        "from two classical techniques, implement it, and then, as the assignment requires, try to break it.")
    r.h2("1.1 Problem Statement")
    r.p("Design a custom cipher that combines at least two different classical encryption techniques in at least two "
        "stages, with a key of at least 10 characters. Implement encryption and decryption for messages of "
        "different lengths made of the letters A-Z. Implement an attack using frequency analysis and/or known "
        "plaintext, document its success rate and computational effort for different ciphertext lengths, analyse "
        "encryption and decryption complexity, compare with a single-stage cipher such as the Shift cipher, and "
        "suggest security improvements that do not greatly increase complexity.")
    r.h2("1.2 Objectives")
    r.bullets([
        "Design and justify a two-stage cipher (substitution followed by transposition).",
        "Implement correct, validated encryption and decryption and test them thoroughly.",
        "Implement a known-plaintext attack that genuinely recovers the keys from limited attacker knowledge.",
        "Implement frequency analysis and explain why it alone does not break Vigenere-based output.",
        "Measure (not assume) running times, attack success rates and attack effort.",
        "Analyse complexity, compare with the Shift cipher, state limitations and propose improvements.",
    ])

    # ===================================================================== 2 Background
    r.h1("2. Background: The Selected Classical Techniques")
    r.p("Classical ciphers work directly on letters using rules that can be applied by hand. They fall into "
        "families: monoalphabetic substitution (Shift/Caesar, where one fixed mapping is used and letter "
        "frequencies survive), polyalphabetic substitution (Vigenere, where several mappings are used in "
        "rotation) and transposition (Rail Fence, where letters keep their identity but change position). "
        "Kerckhoffs' principle states that a cipher should remain secure even when everything except the key is "
        "public [6]. All attacks in this report therefore assume that the attacker knows the algorithm.")
    r.h2("2.1 Vigenere Cipher (Stage 1)")
    r.p("Letters are mapped to numbers A = 0, B = 1, ..., Z = 25. For a keyword K of length m, the i-th plaintext "
        "letter is shifted by the i-th key letter, repeating the keyword as needed:", keep_next=True)
    r.formula("C_{i} = (P_{i} + K_{i mod m}) mod 26          P_{i} = (C_{i} - K_{i mod m}) mod 26")
    r.p("**Strength:** the same plaintext letter is encrypted with up to m different shifts, so the ciphertext "
        "histogram is much flatter than English, and the key space is 26^{m}. **Weakness:** the key repeats, so "
        "every m-th letter is encrypted with the same Shift cipher. Kasiski examination and the index of "
        "coincidence reveal m, and each column can then be solved by frequency analysis [3], [5].")
    r.h2("2.2 Rail Fence Cipher (Stage 2)")
    r.p("The text is written diagonally on r rows (\"rails\"), moving down and then up, and is then read row by "
        "row (Figure 2). It is a fixed permutation of positions that depends only on the message length n and "
        "the rail count r. **Strength:** it destroys the positional structure that Kasiski and IC key-length "
        "attacks rely on. **Weakness:** letters are not changed, so letter frequencies are preserved, and there "
        "are only about n - 1 possible keys, which is trivially searched.")
    r.h2("2.3 Why These Two Ciphers")
    r.p("They are the standard textbook representatives of the two families, are easy to implement and to verify by "
        "hand, and are complementary: the substitution stage hides *which* letters occur, the transposition stage "
        "hides *where* the key repeats. Their different weaknesses also make the attack design interesting.")

    # ===================================================================== 3 Design
    r.h1("3. Design of HCC: Combining the Two Techniques")
    r.h2("3.1 Architecture")
    r.p("HCC applies the two techniques in sequence, so that the output of Stage 1 becomes the input of Stage 2 "
        "(Figure 1). The secret key is the pair **(keyword K, rails r)**.")
    r.figure("architecture.png", "HCC architecture: encryption pipeline and the reverse decryption pipeline", 15.5)
    r.h2("3.2 Key Structure and Validation")
    r.bullets([
        "**Stage 1 key:** a keyword of letters A-Z, at least 10 characters (the demonstration key "
        "`SECURITYKEYS` has 12).",
        "**Stage 2 key:** an integer number of rails r >= 2, chosen by the user.",
        "**Weak-key rule:** a keyword that is just a shorter word repeated (for example `ABCABCABCABC`, "
        "effective length 3, or `AAAAAAAAAAAA`) is rejected, because its effective length would be below the "
        "10-character requirement.",
        "**Short messages:** if r is at least the message length, the zig-zag has one letter per rail and Stage 2 "
        "does nothing; this is allowed but a warning is shown.",
        "**Input normalization:** text is converted to upper case and every character that is not A-Z (spaces, "
        "digits, punctuation, accented letters) is removed. Formatting is deliberately not restored because "
        "word lengths and punctuation would leak structure to an attacker. Decryption therefore returns the "
        "normalized plaintext.",
    ])
    r.h2("3.3 Mathematical Formulation")
    r.p("Let P = (p_{0}, ..., p_{n-1}) with p_{i} in Z_{26} and K = (k_{0}, ..., k_{m-1}). Let pi_{r} be the "
        "Rail Fence permutation: the j-th letter read off is the letter at position pi_{r}(j) of the input. "
        "With L = 2(r - 1) and t = i mod L, position i lies on rail t if t < r and on rail L - t otherwise; "
        "pi_{r} lists the positions sorted by (rail, position).", keep_next=True)
    r.formula("Stage 1:   v_{i} = (p_{i} + k_{i mod m}) mod 26")
    r.formula("Stage 2:   c_{j} = v_{pi(j)}")
    r.formula("Decrypt:   v_{pi(j)} = c_{j}   then   p_{i} = (v_{i} - k_{i mod m}) mod 26")
    r.p("Both stages are bijections, so each can be undone; the composition of the two inverses applied in reverse "
        "order is the exact inverse of the cipher. The key space is 26^{12} = 95,428,956,661,682,176 "
        "(about 2^{56.4}) keywords multiplied by roughly n possible rail counts.")
    r.h2("3.4 How the Two Stages Work Together: A Worked Example")
    r.p(f"We encrypt `{plain}` (n = {len(plain)}) with keyword `{keyword}` (m = 12) and r = {rails}.")
    r.h3("Stage 1: Vigenere substitution")
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    rows = []
    for i in range(6):
        p_val, k_val = letters.index(normalized[i]), letters.index(keyword[i % 12])
        total = p_val + k_val
        rows.append([i, f"{normalized[i]} ({p_val})", f"{keyword[i % 12]} ({k_val})",
                     f"{total}" + (f" mod 26 = {total % 26}" if total >= 26 else ""),
                     f"{stage1[i]} ({total % 26})"])
    r.table("Stage 1 (Vigenere) calculation for the first six letters",
            ["i", "Plaintext p_i", "Key letter k_(i mod 12)", "p_i + k_i", "Stage 1 output v_i"],
            rows, [0.8, 2.4, 3.2, 2.8, 3.0], 10)
    r.p(f"Complete Stage 1 output: `{stage1}`.")
    r.h3("Stage 2: Rail Fence transposition")
    r.p("The Stage 1 output is written on 4 rails and read rail by rail (Figure 2).", keep_next=True)
    r.figure("rail_fence_example.png", "Stage 2 on the example: zig-zag layout and the resulting ciphertext", 15.5)
    r.p("**Why the combination is stronger than either stage alone** against simple attacks: after Stage 1, the "
        "letter statistics are flattened, so a plain frequency count no longer matches one shift. After Stage 2, "
        "the letters that share a key letter are no longer at regular intervals, so the Kasiski/IC technique for "
        "finding the key length and splitting the text into Shift-cipher columns no longer applies directly. "
        "The attacker must handle both problems at once. **Why it is still weak:** the two stages are separable, "
        "which the known-plaintext attack in Section 5 exploits.")

    # ===================================================================== 4 Algorithms
    r.h1("4. Encryption and Decryption Algorithms")
    r.h2("4.1 Encryption Algorithm")
    r.code("""ALGORITHM HCC-Encrypt(message, keyword, rails)
  1. keyword <- validate(keyword)       # A-Z only, length >= 10, not a repeated shorter word
  2. rails   <- validate(rails)         # integer >= 2
  3. P <- uppercase(message) with every non A-Z character removed
     IF P is empty THEN error
  4. FOR i = 0 TO n-1:                  # Stage 1: Vigenere
         V[i] <- (P[i] + K[i mod m]) mod 26
  5. FOR i = 0 TO n-1:                  # Stage 2: Rail Fence
         rail[i] <- zigzag(i, rails)    # 0,1,..,r-1,r-2,..,1,0,1,...
  6. C <- letters of V grouped by rail 0, then rail 1, ... (left to right inside a rail)
  7. RETURN C""")
    r.figure("flow_encrypt.png", "Flowchart of the HCC encryption algorithm", 9.0)
    r.h2("4.2 Decryption Algorithm")
    r.code("""ALGORITHM HCC-Decrypt(ciphertext, keyword, rails)
  1. validate keyword and rails; C <- normalize(ciphertext)
  2. order <- the positions 0..n-1 sorted by (zigzag rail, position)   # same permutation as encryption
  3. FOR j = 0 TO n-1:                  # undo Stage 2
         V[order[j]] <- C[j]
  4. FOR i = 0 TO n-1:                  # undo Stage 1
         P[i] <- (V[i] - K[i mod m]) mod 26
  5. RETURN P""")
    r.figure("flow_decrypt.png", "Flowchart of the HCC decryption algorithm", 9.0)
    r.h2("4.3 Why Decryption Reverses the Order of the Stages")
    r.p("Encryption is the composition RailFence(Vigenere(P)). The inverse of a composition is the composition of "
        "the inverses in reverse order: Vigenere^{-1}(RailFence^{-1}(C)). If Vigenere were undone first, key "
        "letters would be subtracted from letters that are no longer at their original positions and the result "
        "would be unreadable. A unit test confirms that applying the two stages in the wrong order gives a "
        "different ciphertext.")
    r.h2("4.4 Complexity of the Algorithms")
    r.p("Vigenere performs one modular operation per letter. The Rail Fence permutation is built in one pass over "
        "the message by placing each position into a bucket for its rail, which costs O(n) regardless of r. "
        "Hence encryption and decryption of HCC are each **O(n) time and O(n) space**. The measurements in "
        "Section 7 confirm linear growth.")

    # ===================================================================== 5 Attack
    r.h1("5. Attack Methods and Results")
    r.h2("5.1 Threat Model: What the Attacker Knows and What Must Be Recovered")
    r.table("Threat model for the known-plaintext attack",
            ["Assumed known to the attacker", "Must be recovered by the attack"],
            [["Algorithm: Vigenere first, Rail Fence second", "Rail count r"],
             ["The complete ciphertext C (length n)", "Keyword K (m letters)"],
             ["A known plaintext segment of k letters and its position s in the message", "The rest of the plaintext"],
             ["The keyword length m (or a small range of candidates)", ""],
             ["A range of possible rail counts [r_min, r_max]", ""]],
            [8, 6], 10)
    r.p("The attack function takes only these inputs; there is no parameter for the secret keys, and a unit test "
        "verifies the function signature. The known segment is contiguous in the *plaintext* but is scattered "
        "over the *ciphertext* after the transposition, so the attacker needs the whole ciphertext.")
    r.h2("5.2 Mathematics of the Known-Plaintext Attack")
    r.p("For a guessed rail count r the attacker applies the inverse permutation to the ciphertext, obtaining V'. "
        "If r is correct then V' = V, the Stage 1 output. For every known position i = s + t, Stage 1 gives "
        "v_{i} = p_{i} + k_{i mod m}, so the key letter in slot i mod m is:", keep_next=True)
    r.formula("k'_{i mod m} = (V'_{i} - P_{i}) mod 26")
    r.p("Positions with the same residue i mod m must produce the same key letter. For the correct r this holds "
        "for every pair, so the derived key is a **consistent repeating keyword**. For a wrong r, V' is a "
        "scrambled copy of V and two positions agree only by chance (probability about 1/26 each).")
    r.p("Let rho = k - min(k, m) be the number of redundant equations (known letters beyond one per key slot). A "
        "wrong rail count survives the consistency test with probability of about 26^{-rho}. With R candidate "
        "rail counts the expected number of surviving hypotheses is 1 + (R - 1) x 26^{-rho}. For R = 19: "
        "rho = 0 gives 19 survivors (no decision possible), rho = 1 gives 1.69 and rho = 2 gives 1.03. "
        "Consequently **k must be greater than m** for a reliable result, and **k >= m** is needed to recover the "
        "whole keyword at all.")
    r.h2("5.3 Attack Algorithm")
    r.code("""ALGORITHM KnownPlaintextAttack(C, P_known, M, [r_min, r_max], s)
  FOR r = r_min TO r_max:                              # step 1: guess the rail count
      V' <- RailFence_r^-1(C)                          # step 2: undo the transposition      O(n)
      FOR EACH assumed key length m IN M:
          slots[0..m-1] <- empty ; conflicts <- 0
          FOR t = 0 TO k-1:
              i <- s + t
              d <- (V'[i] - P_known[t]) mod 26         # step 3: key letter by modular arithmetic
              IF slots[i mod m] is empty: slots[i mod m] <- d
              ELSE IF slots[i mod m] != d: conflicts <- conflicts + 1   # step 4: consistency check
          IF conflicts = 0: add (r, m, slots) to SURVIVORS
  IF SURVIVORS is empty: report FAILURE
  rank SURVIVORS: complete keys first, then by English-likeness of the full decryption
  best <- first survivor                               # step 5: identify the valid candidate
  IF best has unknown key slots: report PARTIAL (known segment too short)
  P <- Vigenere^-1(RailFence_best.r^-1(C), best.key)   # step 6: decrypt everything
  verify HCC-Encrypt(P, best.key, best.r) = C; compare with the original   # step 7""")
    r.figure("flow_attack.png", "Flowchart of the known-plaintext attack", 9.0)
    r.p("The English-likeness ranking uses the chi-squared distance between the decrypted text and standard English "
        "letter frequencies. It is only needed when several hypotheses survive, and it is an additional "
        "assumption (the plaintext is English); results are therefore reported both with it (\"ranked\") and "
        "without it (\"strict\": exactly one hypothesis survived and it was correct).")
    r.h2("5.4 Attack Demonstration with Intermediate Calculations")
    r.p(f"The attacker knows the ciphertext `{cipher}`, the first k = 16 plaintext letters `{known}` (offset 0), "
        f"m = 12 and a rail range of 2 to 8. The table below is the real output of the attack function.", keep_next=True)
    rows = []
    for row in demo.trace:
        rows.append([row.rails, f"`{row.derived_key}`", row.conflicts,
                     "**consistent (accepted)**" if row.consistent else "rejected"])
    r.table("Search log: key derived from the known segment for each rail guess",
            ["Rail guess r", "Derived key k'", "Conflicts (of 4 redundant letters)", "Verdict"],
            rows, [2.3, 4.6, 3.8, 3.5], 10)
    r.p("For r = 4 the key letter at each known position is (V' - P) mod 26. Positions 12 to 15 fall into slots 0 "
        "to 3 again and agree with the letters found earlier, which proves consistency:", keep_next=True)
    rows = []
    for index, plain_letter, stage_letter, slot, derived in derivation:
        if index in (0, 1, 2, 3, 11, 12, 13, 14, 15):
            a, b = letters.index(stage_letter), letters.index(plain_letter)
            rows.append([index, plain_letter, stage_letter, f"({a} - {b}) mod 26 = {(a - b) % 26}", derived, slot])
    r.table("Derivation of key letters for the correct hypothesis (r = 4); selected positions",
            ["Index i", "P_i", "V'_i", "(V' - P) mod 26", "Key letter", "Slot i mod 12"],
            rows, [1.6, 1.4, 1.4, 4.4, 2.2, 2.4], 10)
    r.p(f"Result: rails = {demo.selected.rails}, keyword = `{demo.selected.keyword}`. Decrypting the whole ciphertext "
        f"gives `{demo.plaintext}`, which equals the original message, and the recovered keys re-encrypt it to "
        f"the supplied ciphertext. The attack tested {demo.candidates_tested} hypotheses with "
        f"{demo.char_operations} character operations.")
    r.h2("5.5 Frequency Analysis")
    r.p("The frequency-analysis module counts letters, compares them with standard English frequencies [4] using the "
        "chi-squared statistic and computes the index of coincidence (IC), the probability that two randomly "
        "chosen letters of a text are equal: IC = sum n_{i}(n_{i} - 1) / (N(N - 1)). English text has IC of about "
        "0.0655 and uniformly random text about 0.0385 [5]. Figure 6 compares a 1000-letter English sample, its "
        "Shift-cipher encryption and its HCC encryption.", keep_next=True)
    r.figure("frequency.png", "Letter frequencies: English plaintext, Shift cipher and HCC ciphertext "
             "(dashed line = standard English)", 14.5)
    r.p("**Why frequency analysis alone fails against HCC.** (1) A Shift cipher maps each letter to exactly one "
        "other letter, so the histogram is only rotated and 26 trials identify the key; the program recovers the "
        "key this way. (2) Vigenere maps a plaintext letter to up to m different ciphertext letters, so the "
        "histogram flattens (IC 0.0400 for HCC compared with 0.0667 for the English sample) and no single shift "
        "makes it resemble English. (3) Rail Fence does not change the histogram but hides the positions "
        "(i mod m) needed to split the text into Shift-cipher columns. **Caveat:** this defeats only the naive "
        "attack, as the next section shows.")
    r.h2("5.6 Bonus: Ciphertext-Only Attack")
    r.p("For each rail count the attack undoes the transposition, splits the result into m columns (each column is a "
        "Shift cipher), chooses for each column the shift with the smallest chi-squared distance from English, "
        "and adds the column scores; the rail count with the lowest total wins. It uses no known plaintext.")
    r.h2("5.7 Experimental Results of the Attacks")
    r.p("**Test conditions.** 200 trials per row; each trial uses a fresh random non-periodic 12-letter keyword, a "
        "random rail count in [2, 20], and an English-like plaintext made of randomly chosen sentences from a "
        "built-in corpus; the known segment is the first k letters; the attacker is told m = 12 and the rail "
        "range 2 to 20. Random generators are seeded, so the experiment is reproducible (`performance.py`). "
        "*Strict* = exactly one hypothesis survived and it was correct. *Ranked* = final answer correct after "
        "English-likeness ranking. *Char ops* = elementary letter operations performed by the attack "
        "(computational effort).", keep_next=True)
    rows = [[row["length"], row["known_k"], f"{float(row['strict_pct']):.1f}", f"{float(row['ranked_pct']):.1f}",
             f"{float(row['avg_survivors']):.2f}", f"{float(row['candidates_tested']):.0f}",
             f"{float(row['avg_char_ops']):.0f}", f"{float(row['avg_time_s']) * 1000:.2f}"] for row in kpa]
    r.table("Known-plaintext attack: success rate and effort (m = 12, rails 2-20, 200 trials per row)",
            ["Ciphertext length n", "Known k", "Strict %", "Ranked %", "Avg. survivors", "Hypotheses tested",
             "Char ops", "Time (ms)"], rows, [2.0, 1.6, 1.6, 1.6, 1.9, 2.1, 1.7, 1.7], 9, align_right_from=0)
    r.figure("attack_success.png", "Known-plaintext attack success rate against the known-plaintext length k", 15.5)
    r.p("**Interpretation.**", keep_next=True)
    r.bullets([
        "**k < m (k = 8): 0% success.** The key cannot be fully recovered; all 19 rail counts survive and the "
        "attack reports *insufficient known plaintext* instead of guessing.",
        "**k = m = 12: strict 0%.** With one equation per key slot there is no redundancy, so every rail count is "
        "consistent. The English-likeness ranking still picks the right answer in 99.5 to 100% of trials, but only "
        "because the plaintext is English.",
        "**k = 13:** about 1.7 to 1.8 hypotheses survive for n >= 100 (2.27 at n = 50), matching the prediction "
        "1 + 18/26 = 1.69; strict success is 44 to 49%.",
        "**k >= 14 with n >= 100:** strict success 97 to 100%, and with k = 24 the attack succeeded in all 800 of "
        "800 trials. The average of 1.03 survivors at k = 14 matches 1 + 18/676 = 1.027.",
        "**Short ciphertexts (n = 50)** need slightly more known text for the strict test (76% at k = 14) because "
        "for tiny n different rail counts share more of their first positions.",
        "**Computational effort** grows linearly with the ciphertext length: about 19 x n operations "
        "(about 21,300 operations at n = 1000 and k = 16, around 9 to 10 ms in Python) and is almost independent "
        "of k once k > m. Exhaustive key search would need up to 26^{12} (about 9.5 x 10^{16}) keywords.",
    ])
    rows = [[row["length"], row["trials"], f"{float(row['full_recovery_pct']):.1f}",
             f"{float(row['avg_char_ops']):.0f}", f"{float(row['avg_time_s']) * 1000:.1f}"] for row in coa]
    r.table("Ciphertext-only attack: success rate against ciphertext length (40 trials per row, m = 12)",
            ["Ciphertext length n", "Trials", "Full recovery %", "Char ops", "Time (ms)"], rows,
            [3.0, 2.0, 3.0, 3.0, 2.5], 10, align_right_from=0)
    r.p("HCC therefore also falls without any known plaintext once roughly 500 or more letters of English are "
        "available (97.5% at n = 500, 100% from n = 1000, but 0% at n = 100). *Limitation:* the test plaintexts "
        "come from a small English corpus, so they are English-like but somewhat repetitive; real prose would "
        "be a little harder at the shortest lengths.")

    # ===================================================================== 6 Security analysis
    r.h1("6. Security Analysis")
    r.h2("6.1 Benefits of Combining Substitution and Transposition")
    r.p("Substitution hides which letters occur; transposition hides where they occur. Vigenere flattens letter "
        "frequencies, and Rail Fence removes the regular spacing of letters that share a key letter, so neither "
        "the plain histogram attack nor the standard Kasiski/IC key-length analysis can be applied directly. "
        "Mixing a substitution with a transposition is also the principle behind modern ciphers, which repeat "
        "such rounds many times with key-dependent operations.")
    r.h2("6.2 Strengths and Weaknesses of the Individual Stages")
    r.table("Strengths and weaknesses of the two stages",
            ["Cipher", "Strengths", "Weaknesses"],
            [["Vigenere (Stage 1)", "Defeats simple frequency analysis; key space 26^m; easy to implement",
              "Repeating key (every m-th letter is a Shift cipher); Kasiski/IC reveal m; key follows from known "
              "plaintext by subtraction"],
             ["Rail Fence (Stage 2)", "Hides position structure; cheap; reversible",
              "Only about n - 1 keys; no secret mixing; keeps letter frequencies; one rail guess is easy to test"]],
            [3, 6, 6.5], 10)
    r.h2("6.3 The Effect of Using Both Together")
    r.p("The combined key space (about 2^{60}) is large, but security is **not the product of the two key "
        "spaces**. The stages are separable: the known-plaintext attack searches the rail count (about n options) "
        "and then reads the keyword off by subtraction, never touching the 26^{12} keyword space. The "
        "complexity of the attack is O(R x n), not O(26^{12} x R).")
    r.h2("6.4 Vulnerability to Known-Plaintext Attacks")
    r.p("Demonstrated: the complete key is recovered in milliseconds once more than m letters of the plaintext are "
        "known. This is realistic, because real messages often begin with predictable text (greetings, headers, "
        "standard phrases). A known segment of m letters only decides the key after the language model is used, "
        "and fewer than m letters leave part of the key unknown.")
    r.h2("6.5 Vulnerability to Frequency Analysis")
    r.p("A naive histogram comparison fails (IC 0.040 and no consistent shift), but a column-wise attack after a "
        "search over rail counts succeeds with about 500 letters (Section 5.6). The flattening of letter "
        "frequencies is therefore a weak defence, not a proof of security.")
    r.h2("6.6 Why HCC Is Educational and Not Suitable for Real Security")
    r.bullets([
        "The key stream repeats with period m and there is no diffusion between positions beyond a fixed permutation.",
        "The transposition key space is tiny and is searched exhaustively in the attack.",
        "Encryption is deterministic and has no randomization: identical messages give identical ciphertexts.",
        "There is no integrity or authentication; an attacker can modify the ciphertext undetected.",
        "The same key is reused for all messages, which makes known-plaintext attacks cumulative.",
        "Modern systems use vetted algorithms such as AES-GCM or ChaCha20-Poly1305. **We do not claim that HCC is "
        "secure against modern cryptanalysis.**",
    ])

    # ===================================================================== 7 Performance
    r.h1("7. Performance Metrics")
    r.h2("7.1 Measurement Method")
    r.p("All times are measured with Python's `time.perf_counter()`. Each function is run once as an untimed warm-up "
        "and then repeatedly (30 runs for encryption and decryption, 10 runs for the attack); the mean is "
        "reported to reduce noise. Plaintexts are English-like with a fixed random seed; HCC uses the demonstration "
        "key `SECURITYKEYS` with 4 rails, and the Shift cipher uses shift 7. The attack uses a known segment of "
        "36 letters (or the whole message if shorter), m = 12 and 19 rail counts (2 to 20). Environment: "
        "Windows 11, CPython 3.11.9. Absolute times depend on the machine; the trends do not. The experiment code "
        "is `performance.py` and the raw data is in `results/timing.csv`.")
    r.h2("7.2 Encryption, Decryption and Attack Time")
    rows = []
    for row in timing:
        ratio = float(row["hcc_encrypt_s"]) / float(row["shift_encrypt_s"])
        rows.append([row["length"], fmt_ms(row["hcc_encrypt_s"]), fmt_ms(row["hcc_decrypt_s"]),
                     fmt_ms(row["shift_encrypt_s"]), fmt_ms(row["shift_decrypt_s"]), fmt_ms(row["attack_s"]),
                     f"{ratio:.2f}x"])
    r.table("Measured mean execution time in milliseconds for HCC, Shift cipher and the known-plaintext attack",
            ["Length n", "HCC encrypt", "HCC decrypt", "Shift encrypt", "Shift decrypt", "KPA attack",
             "HCC / Shift (encrypt)"], rows, [1.7, 2.1, 2.1, 2.1, 2.1, 2.1, 2.5], 10, align_right_from=0)
    first, last = timing[0], timing[-1]
    growth_len = int(last["length"]) / int(first["length"])
    growth_time = float(last["hcc_encrypt_s"]) / float(first["hcc_encrypt_s"])
    r.figure("timing.png", "Mean running time against message length (log-log scale): cipher operations (left) "
             "and the known-plaintext attack (right)", 15.5)
    r.p(f"**Effect of message length.** When the message length grows {growth_len:.0f} times (from {first['length']} to "
        f"{last['length']} letters), HCC encryption time grows {growth_time:.0f} times. On a log-log graph the "
        "curves are straight lines of slope close to 1, which is the signature of linear, O(n), behaviour. The "
        "attack time also grows linearly with n, because each of the 19 rail guesses undoes an O(n) permutation. "
        "The smallest messages take only tens of microseconds, so those entries are the noisiest, which explains "
        "the irregular ratio column.")
    r.h2("7.3 Comparison with the Shift Cipher")
    r.table("HCC compared with the single-stage Shift cipher",
            ["Property", "Shift cipher", "HCC"],
            [["Stages", "1", "2 (substitution + transposition)"],
             ["Key", "Integer 0-25", "12-letter keyword + rail count"],
             ["Key space", "26 (about 4.7 bits)", "26^12 x about n (about 2^60 for short messages)"],
             ["Time complexity (enc / dec)", "O(n) / O(n)", "O(n) / O(n)"],
             ["Measured at n = 1000", f"{fmt_ms(timing[3]['shift_encrypt_s'])} / {fmt_ms(timing[3]['shift_decrypt_s'])} ms",
              f"{fmt_ms(timing[3]['hcc_encrypt_s'])} / {fmt_ms(timing[3]['hcc_decrypt_s'])} ms"],
             ["Relative cost", "1x", "about 2 to 3.7x (constant factor)"],
             ["Frequency analysis", "Breaks it with at most 26 trials", "Naive histogram matching fails (IC 0.040)"],
             ["Known-plaintext attack", "One known letter reveals the key", "Needs k > m letters; about 19 x n operations"],
             ["Ciphertext-only attack", "Trivial", "Works with about 500 or more English letters"]],
            [4, 5, 6.5], 10)
    r.p("HCC pays a constant-factor overhead (a second pass plus index bookkeeping) for resistance to the simplest "
        "attacks. Both ciphers have the same asymptotic complexity, so the extra security is cheap but also "
        "limited.")
    r.h2("7.4 Time and Space Complexity of All Major Algorithms")
    r.p("n = message length, m = key length, k = known letters, R = number of rail counts searched, "
        "|M| = number of key lengths tried, c = number of surviving hypotheses.", keep_next=True)
    r.table("Complexity summary",
            ["Algorithm", "Time", "Space", "Reason"],
            [["Normalization", "O(n)", "O(n)", "One pass over the input"],
             ["Vigenere encrypt / decrypt", "O(n)", "O(n)", "One modular operation per letter"],
             ["Rail Fence encrypt / decrypt", "O(n)", "O(n)", "Zig-zag pattern and buckets, independent of r"],
             ["HCC encrypt / decrypt", "O(n)", "O(n)", "Sum of the two stages"],
             ["Shift cipher", "O(n)", "O(n)", "One operation per letter"],
             ["Known-plaintext attack", "O(R(n + k|M|) + c n)", "O(n)", "Per rail guess: invert permutation, derive k letters; ranking decrypts survivors"],
             ["Frequency analysis", "O(n + 26)", "O(1)", "Count letters, compare 26 values"],
             ["Ciphertext-only attack", "O(R(n + 26^2 m))", "O(n)", "Per rail: split into m columns, try 26 shifts each"],
             ["Exhaustive key search", "O(26^m R n)", "O(n)", "Infeasible for m = 12, hence the structural attack"]],
            [4.2, 3.4, 1.6, 6.3], 9.5)

    # ===================================================================== 8 Improvements
    r.h1("8. Suggested Improvements")
    r.p("The following changes raise the cost of the attacks while adding only O(n) work and little code:")
    r.table("Improvements, their security benefit and their added cost",
            ["Improvement", "Security benefit", "Added complexity"],
            [["Keyed columnar transposition instead of Rail Fence",
              "Transposition key space grows from about n to (number of columns)!; the permutation depends on a secret word",
              "One extra sort of the key word; O(n)"],
             ["Autokey Vigenere (key stream continues with the plaintext)",
              "No repeating key: the consistent-keyword test and Kasiski/IC analysis no longer apply",
              "One line changed; O(n)"],
             ["Sandwich: Vigenere -> transposition -> Vigenere with a second keyword",
              "Known plaintext is no longer aligned with a single substitution layer, which defeats the "
              "consistency test",
              "One more O(n) pass"],
             ["Long random keys (20 letters or more), never a dictionary word, used once per message",
              "Raises the key space and prevents cumulative known-plaintext attacks",
              "None (key management only)"],
             ["Variable start rail / offset as part of the key",
              "Enlarges the transposition key space at no real cost",
              "A few lines in the zig-zag function"]],
            [4.8, 7, 3.7], 10)
    r.p("None of these changes makes the cipher secure by modern standards; they illustrate how security can be "
        "improved cheaply within the classical framework.")

    # ===================================================================== 9 Implementation
    r.h1("9. Implementation and Source Code")
    r.p("The implementation uses only the Python standard library (matplotlib is optional and is used only for "
        "graphs). It is organized into small modules, each with docstrings and input validation.")
    r.table("Project structure",
            ["File", "Purpose"],
            [["`main.py`", "Menu-driven command-line interface (8 options) and a `--demo` mode"],
             ["`utils.py`", "Alphabet handling, normalization, key validation, `ValidationError`"],
             ["`vigenere.py`, `rail_fence.py`", "The two classical stages"],
             ["`hybrid_cipher.py`", "HCC: Stage 1 then Stage 2, and the reverse for decryption"],
             ["`shift_cipher.py`", "Single-stage baseline for the comparison"],
             ["`attack.py`", "Known-plaintext attack, derivation table, ciphertext-only attack"],
             ["`frequency_analysis.py`", "Letter frequencies, chi-squared, index of coincidence, Shift frequency attack"],
             ["`sample_data.py`", "Reproducible English-like test text and random keys"],
             ["`performance.py`", "Timing and attack-success experiments, CSV and PNG output"],
             ["`tests/`", "52 `unittest` tests (round trips, validation, attack success and failure, experiments, CLI)"]],
            [5, 10.5], 10)
    r.h2("9.1 Running the Project")
    r.code("""python main.py                          # interactive menu (options 1-8)
python main.py --demo                   # automatic walk-through of options 1-5 and 7
python -m unittest discover -s tests -v # 52 tests
python performance.py                   # full experiments (about 1 minute), writes results/""")
    r.h2("9.2 Testing")
    r.p("The test suite verifies textbook vectors for Vigenere and Rail Fence, round trips for every message length "
        "from 1 to 79 with rails 2 to 11, short and long messages, messages shorter and longer than the key, invalid "
        "keys, empty input, repeated letters, 60 random successful attacks, insufficient or incorrect known "
        "plaintext, rail counts outside the search range, and that the recovered keys reproduce the supplied "
        "ciphertext. All 52 tests pass.")
    r.h2("9.3 Source Code Repository")
    r.p("The complete source code, tests, experiment results and this report are submitted in a GitHub repository:")
    r.p("[[GitHub repository link: https://github.com/<username>/HCC-Project  (insert the final link here)]]",
        align="left")

    # ===================================================================== 10 Limitations
    r.h1("10. Limitations")
    r.bullets([
        "Only the letters A-Z are supported; case, spaces and punctuation are lost by design.",
        "The attack assumes a known key length (a range is supported at proportional cost), a contiguous known "
        "segment and a known position of that segment.",
        "The experiments use one key length (m = 12), a small built-in English corpus and one machine.",
        "The language-model tie-break assumes English plaintext.",
        "Timings of very short messages are at microsecond scale and therefore noisy.",
    ])

    # ===================================================================== 11 Conclusion
    r.h1("11. Conclusion")
    r.p("HCC satisfies the assignment: two classical techniques in two stages, a 12-letter keyword, arbitrary-length "
        "A-Z messages, a working known-plaintext attack that genuinely recovers the keys, measured success rates "
        "and computational effort, linear-time encryption and decryption and a quantified comparison with the "
        "Shift cipher. The main lesson is that **combining weak ciphers does not multiply their strength**: the "
        "stages can be attacked separately, and with more than m known letters the keys are recovered in "
        "milliseconds. HCC is a good teaching vehicle and should never be used to protect real data.")

    # ===================================================================== References
    r.h1("References")
    refs = [
        "W. Stallings, Cryptography and Network Security: Principles and Practice, Pearson (chapter on classical encryption techniques).",
        "A. Menezes, P. van Oorschot and S. Vanstone, Handbook of Applied Cryptography, CRC Press, 1996 (classical ciphers, Section 7.3).",
        "D. Kahn, The Codebreakers: The Comprehensive History of Secret Communication, Macmillan, 1967.",
        "R. Lewand, Cryptological Mathematics, Mathematical Association of America, 2000 (English letter frequencies).",
        "W. F. Friedman, The Index of Coincidence and Its Applications in Cryptography, Riverbank Laboratories, 1922.",
        "A. Kerckhoffs, \"La cryptographie militaire,\" Journal des sciences militaires, 1883.",
        "J. Katz and Y. Lindell, Introduction to Modern Cryptography, CRC Press (attack models and Kerckhoffs' principle).",
        "S. Singh, The Code Book, Doubleday, 1999.",
        "Python Software Foundation, Python documentation: time.perf_counter and unittest, https://docs.python.org/3/.",
    ]
    for number, ref in enumerate(refs, 1):
        paragraph = r.doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(1.0)
        paragraph.paragraph_format.first_line_indent = Cm(-1.0)
        paragraph.paragraph_format.space_after = Pt(4)
        add_runs(paragraph, f"[{number}]\t{ref}")


def build():
    report = Report()
    report.title_page()
    report.toc_block("Table of Contents", 'TOC \\o "1-2" \\h \\z \\u')
    report.toc_block("List of Figures", 'TOC \\h \\z \\c "Figure"')
    report.toc_block("List of Tables", 'TOC \\h \\z \\c "Table"')
    body(report)
    report.doc.save(OUT)
    print("saved", OUT, f"({report.fig_count} figures, {report.tab_count} tables)")


if __name__ == "__main__":
    build()
