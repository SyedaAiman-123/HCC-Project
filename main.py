"""HCC - Hybrid Classical Cipher: command-line application.

Run:   python main.py          (interactive menu)
       python main.py --demo   (non-interactive walk-through using default values)
"""

import math
import sys
import time

import attack
import frequency_analysis as fa
import hybrid_cipher
import performance
import rail_fence
import sample_data
import shift_cipher
from utils import ValidationError, group_text, normalize_text

BANNER = """
==============================================================
  HCC - Hybrid Classical Cipher   (Vigenere + Rail Fence)
  CT-486 Network and Information Security - CCP (CLO3)
  Educational project: NOT suitable for protecting real data
=============================================================="""

MENU = """
 1. Encrypt a message
 2. Decrypt a message
 3. Launch known-plaintext attack
 4. Perform frequency analysis
 5. Compare HCC with Shift Cipher
 6. Run performance experiments
 7. View cipher information and security analysis
 8. Exit
"""

NORMALIZATION_NOTE = ("Input handling: letters are converted to UPPERCASE; spaces, digits, punctuation "
                      "and any other non A-Z characters are removed (word boundaries would leak "
                      "information to an attacker).")

# Session memory so that "decrypt previously generated ciphertext" works.
session = {"ciphertext": None, "keyword": sample_data.DEFAULT_KEYWORD, "rails": sample_data.DEFAULT_RAILS}
AUTO_ACCEPT_DEFAULTS = False      # set by --demo: every prompt takes its default


# ------------------------------------------------------------------ input helpers

def ask(prompt, default=None):
    """Prompt the user; an empty answer returns `default`."""
    shown = str(default) if default is not None else ""
    if len(shown) > 40:
        shown = shown[:37] + "..."
    suffix = f" [{shown}]" if shown else ""
    if AUTO_ACCEPT_DEFAULTS:
        print(f"{prompt}{suffix}: (default)")
        return "" if default is None else str(default)
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        print("\nInput closed - exiting.")
        sys.exit(0)
    return answer if answer else ("" if default is None else str(default))


def ask_int(prompt, default, minimum=None):
    """Prompt until a valid integer is entered."""
    while True:
        raw = ask(prompt, default)
        try:
            value = int(raw)
        except ValueError:
            print("  ! Please enter a whole number.")
            if AUTO_ACCEPT_DEFAULTS:
                return default
            continue
        if minimum is not None and value < minimum:
            print(f"  ! Value must be at least {minimum}.")
            if AUTO_ACCEPT_DEFAULTS:
                return default
            continue
        return value


def ask_keys():
    """Ask for keyword and rails; validate; keep asking until valid."""
    while True:
        keyword = ask("Vigenere keyword (>= 10 letters)", session["keyword"])
        rails = ask("Number of rails (>= 2)", session["rails"])
        try:
            keyword = hybrid_cipher.validate_keyword(keyword)
            rails = hybrid_cipher.validate_rails(rails)
            return keyword, rails
        except ValidationError as error:
            print(f"  ! {error}")
            if AUTO_ACCEPT_DEFAULTS:
                sys.exit(1)


def show(label, text, width=14):
    print(f"  {label:<{width}}: {group_text(text) if len(text) > 5 else text}")


# ------------------------------------------------------------------ menu actions

def action_encrypt():
    print("\n--- Encrypt a message ---")
    print(NORMALIZATION_NOTE)
    message = ask("Plaintext", sample_data.DEFAULT_MESSAGE)
    keyword, rails = ask_keys()
    try:
        normalized, stage1, ciphertext = hybrid_cipher.encrypt_with_trace(message, keyword, rails)
    except ValidationError as error:
        print(f"  ! {error}")
        return
    removed = len(message) - len(normalized)
    print(f"\n  Characters removed during normalization: {removed}")
    if rails >= len(normalized):
        print("  ! Warning: rails >= message length, so Rail Fence leaves the text unchanged.")
    show("Normalized", normalized)
    print(f"  Stage 1 key   : {keyword} (repeated)")
    show("After Vigenere", stage1)
    print(f"  Stage 2 key   : {rails} rails")
    if len(normalized) <= 40:
        print("  Rail Fence layout of the Stage 1 output:")
        print("    " + rail_fence.draw_fence(stage1, rails).replace("\n", "\n    "))
    show("CIPHERTEXT", ciphertext)
    session.update(ciphertext=ciphertext, keyword=keyword, rails=rails)


def action_decrypt():
    print("\n--- Decrypt a message ---")
    ciphertext = ask("Ciphertext", session["ciphertext"] or "")
    if not ciphertext:
        print("  ! No ciphertext available. Encrypt something first or paste one.")
        return
    keyword, rails = ask_keys()
    try:
        normalized, stage1, plaintext = hybrid_cipher.decrypt_with_trace(ciphertext, keyword, rails)
    except ValidationError as error:
        print(f"  ! {error}")
        return
    show("Ciphertext", normalized)
    print(f"  Step 1: undo Rail Fence ({rails} rails)")
    show("After RF^-1", stage1)
    print(f"  Step 2: undo Vigenere (keyword {keyword})")
    show("PLAINTEXT", plaintext)
    print("  (Spaces/punctuation of the original message were removed at encryption time.)")


def print_attack_report(result, ciphertext, known, offset, original=None):
    print("\n  --- Search log (hypothesis -> key derived from the known segment) ---")
    for row in result.trace:
        flag = "CONSISTENT" if row.consistent else f"{row.conflicts} conflict(s)"
        print(f"    rails={row.rails:<3} m={row.key_length:<3} key'={row.derived_key:<24} {flag}")
    print(f"\n  Hypotheses tested     : {result.candidates_tested}")
    print(f"  Consistent hypotheses : {len(result.consistent)}")
    print(f"  Character operations  : {result.char_operations}")
    print(f"  Attack time           : {result.elapsed_seconds * 1000:.3f} ms")
    print(f"  STATUS                : {result.status.upper()}")
    print(f"  {result.message}")
    if result.selected is not None:
        best = result.selected
        print("\n  --- Intermediate calculations for the selected hypothesis ---")
        print(f"  Rail Fence reversed with {best.rails} rails; key letter = (V' - P) mod 26")
        print("    index  P   V'   key-pos  key = V'-P")
        for index, plain, stage1, key_pos, derived in attack.derivation_table(
                ciphertext, known, best.rails, best.key_length, offset, rows=min(len(known), 14)):
            print(f"    {index:>5}  {plain}   {stage1}    {key_pos:>5}      "
                  f"({ord(stage1) - 65} - {ord(plain) - 65}) mod 26 = {ord(derived) - 65} -> {derived}")
    if result.status == "recovered":
        shown = result.plaintext if len(result.plaintext) <= 120 else result.plaintext[:120] + "..."
        print(f"\n  Recovered plaintext   : {shown}")
        print(f"  Keys reproduce the ciphertext (re-encryption check): {'YES' if result.verified else 'NO'}")
        if original is not None:
            ok = result.plaintext == original
            print(f"  Matches the original message                       : {'YES - ATTACK SUCCEEDED' if ok else 'NO - attack failed'}")


def action_attack():
    print("\n--- Known-plaintext attack ---")
    print("  a) Simulation: we encrypt a message with secret keys, then attack it using only")
    print("     the attacker's information")
    print("  b) Manual: supply your own ciphertext and known plaintext")
    print("  c) Bonus: ciphertext-only attack (frequency statistics)")
    choice = ask("Choose a/b/c", "a").lower()
    try:
        if choice == "a":
            attack_simulation()
        elif choice == "b":
            attack_manual()
        elif choice == "c":
            attack_ciphertext_only()
        else:
            print("  ! Unknown choice.")
    except ValidationError as error:
        print(f"  ! {error}")


def attack_simulation():
    default_text = sample_data.generate_english_text(300, sample_data.make_rng(42))
    message = hybrid_cipher.require_message(ask("Victim's plaintext", default_text))
    print("  Secret keys (used ONLY by the victim to create the ciphertext):")
    keyword, rails = ask_keys()
    ciphertext = hybrid_cipher.encrypt(message, keyword, rails)
    print(f"  Ciphertext length n = {len(ciphertext)}")
    show("Ciphertext", ciphertext if len(ciphertext) <= 150 else ciphertext[:150])
    print("\n  Attacker's assumptions / knowledge:")
    k = ask_int("  Known plaintext length k (needs k > m to be reliable)", min(24, len(message)), 1)
    offset = ask_int("  Position of the known segment in the message", 0, 0)
    m = ask_int("  Assumed keyword length m", len(keyword), 1)
    low = ask_int("  Rail search range: minimum", 2, 2)
    high = ask_int("  Rail search range: maximum", 20, low)
    known = message[offset:offset + k]
    if len(known) < k:
        print("  ! Known segment runs past the end of the message.")
        return
    print(f"  Known plaintext       : {known}")
    print("  Attacker does NOT receive: keyword, rails, rest of the plaintext.")
    result = attack.known_plaintext_attack(ciphertext, known, m, (low, high), offset)
    print_attack_report(result, ciphertext, known, offset, original=message)
    print(f"\n  (Secret was keyword={keyword}, rails={rails}; "
          f"recovered {'identical keys' if result.selected and result.selected.keyword == keyword and result.selected.rails == rails else 'different/partial keys'}.)")


def attack_manual():
    ciphertext = ask("Full ciphertext", session["ciphertext"] or "")
    known = ask("Known plaintext segment")
    offset = ask_int("Position of the segment in the message (0 = start)", 0, 0)
    m = ask_int("Assumed keyword length m", len(session["keyword"]), 1)
    low = ask_int("Rail search range: minimum", 2, 2)
    high = ask_int("Rail search range: maximum", 20, low)
    result = attack.known_plaintext_attack(ciphertext, known, m, (low, high), offset)
    print_attack_report(result, hybrid_cipher.require_message(ciphertext, "ciphertext"),
                        hybrid_cipher.require_message(known, "known plaintext"), offset)


def attack_ciphertext_only():
    print("  Needs a long ciphertext (hundreds of letters) of English text.")
    ciphertext = ask("Ciphertext", session["ciphertext"] or "")
    m = ask_int("Assumed keyword length m", len(session["keyword"]), 1)
    low = ask_int("Rail search range: minimum", 2, 2)
    high = ask_int("Rail search range: maximum", 20, low)
    result = attack.ciphertext_only_attack(ciphertext, m, (low, high))
    print(f"  Best rails   : {result.rails}")
    print(f"  Best keyword : {result.keyword}")
    print("  Top 3 hypotheses (rails, score): " + ", ".join(f"({r}, {s:.0f})" for r, s in result.ranking[:3]))
    print(f"  Plaintext    : {result.plaintext[:120]}")
    print(f"  Effort       : {result.candidates_tested} hypotheses, {result.char_operations} operations, "
          f"{result.elapsed_seconds * 1000:.1f} ms")
    print("  (No ground truth here: judge by whether the plaintext reads as English.)")


def action_frequency():
    print("\n--- Frequency analysis ---")
    print("  1) Analyse a text   2) Demo: English vs Shift cipher vs HCC")
    if ask("Choose", "2") == "1":
        text = ask("Text (blank = last ciphertext)", session["ciphertext"] or "")
        if not normalize_text(text):
            print("  ! No letters to analyse.")
            return
        print(fa.frequency_report(text))
        return
    rng = sample_data.make_rng(5)
    plain = sample_data.generate_english_text(1000, rng)
    shift_ct = shift_cipher.encrypt(plain, 11)
    hcc_ct = hybrid_cipher.encrypt(plain, sample_data.DEFAULT_KEYWORD, sample_data.DEFAULT_RAILS)
    for title, text in (("PLAINTEXT (English)", plain), ("SHIFT CIPHER ciphertext (key 11)", shift_ct),
                        ("HCC ciphertext", hcc_ct)):
        print(f"\n[{title}]  IC={fa.index_of_coincidence(text):.4f}  chi2={fa.chi_squared(text):.0f}")
    print("\nFull table for the HCC ciphertext:")
    print(fa.frequency_report(hcc_ct))
    best, _ = fa.break_shift_by_frequency(shift_ct)
    print(f"\nFrequency attack on Shift: guessed key {best} (true 11) -> "
          f"{'BROKEN' if shift_cipher.decrypt(shift_ct, best) == plain else 'failed'}")
    best, _ = fa.break_shift_by_frequency(hcc_ct)
    print(f"Same attack on HCC: guessed shift {best} -> "
          f"{'broken' if shift_cipher.decrypt(hcc_ct, best) == plain else 'FAILS (output is not English)'}")
    print("""
Why plain frequency analysis fails against HCC:
  * Vigenere uses m different shifts, so each letter maps to up to m different
    letters; the overall histogram is flattened (IC drops from ~0.066 towards 0.038).
  * Rail Fence only reorders letters, so it does not change the histogram - but it
    hides the position structure (i mod m) that Kasiski/IC-based key-length attacks use.
  * A single histogram therefore cannot be matched to a single shift.
  * Caveat: the flattening is not security. Splitting the text into m columns and
    analysing each column (option 3c) still breaks HCC given enough ciphertext.""")


def action_compare():
    print("\n--- HCC vs Shift cipher ---")
    n = ask_int("Message length", 1000, 10)
    rng = sample_data.make_rng(99)
    plain = sample_data.generate_english_text(n, rng)
    keyword, rails = sample_data.DEFAULT_KEYWORD, sample_data.DEFAULT_RAILS
    hcc_ct = hybrid_cipher.encrypt(plain, keyword, rails)
    shift_ct = shift_cipher.encrypt(plain, 3)
    trials = 30
    rows = [
        ("HCC encrypt", performance.time_calls(lambda: hybrid_cipher.encrypt(plain, keyword, rails), trials)[0]),
        ("HCC decrypt", performance.time_calls(lambda: hybrid_cipher.decrypt(hcc_ct, keyword, rails), trials)[0]),
        ("Shift encrypt", performance.time_calls(lambda: shift_cipher.encrypt(plain, 3), trials)[0]),
        ("Shift decrypt", performance.time_calls(lambda: shift_cipher.decrypt(shift_ct, 3), trials)[0]),
    ]
    print(f"\n  Measured time for n={n} (mean of {trials} runs):")
    for name, seconds in rows:
        print(f"    {name:<14}{seconds * 1000:>10.4f} ms")
    print(f"    HCC is about {rows[0][1] / rows[2][1]:.1f}x slower - both are O(n).")
    best, _ = fa.break_shift_by_frequency(shift_ct)
    print(f"\n  Frequency attack on Shift: recovered key {best}, "
          f"{'plaintext recovered' if shift_cipher.decrypt(shift_ct, best) == plain else 'failed'} "
          f"(<= 26 trials, no known plaintext needed)")
    best, _ = fa.break_shift_by_frequency(hcc_ct)
    print(f"  Frequency attack on HCC  : "
          f"{'plaintext recovered' if shift_cipher.decrypt(hcc_ct, best) == plain else 'fails (same method)'}")
    keyspace = 26 ** len(keyword)
    print(f"\n  Key space: Shift = 26 (4.7 bits); HCC = 26^{len(keyword)} x (rails choices) "
          f"~ 2^{math.log2(keyspace):.1f} x ~19 = ~2^{math.log2(keyspace * 19):.1f}")
    print("  But a large key space is not security: HCC still falls to the known-plaintext attack"
          "\n  in about 19 x n steps (menu 3).")


def action_performance():
    print("\n--- Performance experiments ---")
    print("  1) Quick (a few seconds)   2) Full (about 1-2 minutes, saves CSV + PNG in results/)")
    performance.run_all(quick=ask("Choose", "1") != "2")


def action_info():
    keyspace = 26 ** 12
    print(f"""
--- HCC cipher information ---
Architecture : plaintext -> Vigenere (keyword >= 10 letters) -> Rail Fence (rails >= 2) -> ciphertext
Decryption   : ciphertext -> Rail Fence^-1 -> Vigenere^-1 -> plaintext   (reverse order)
Alphabet     : A-Z only. {NORMALIZATION_NOTE}
Demo keys    : keyword={sample_data.DEFAULT_KEYWORD}, rails={sample_data.DEFAULT_RAILS}

Complexity   : encryption O(n), decryption O(n), memory O(n); known-plaintext attack
               O(R*(n+k)) for R candidate rail counts; Shift cipher O(n).
Key space    : 26^12 = {keyspace:,} (~2^{math.log2(keyspace):.1f}) keywords x about n rail counts.

Security analysis (summary)
 + Substitution + transposition: Vigenere flattens letter frequencies, Rail Fence hides the
   positional pattern (i mod m) that Kasiski/IC key-length attacks need, so simple attacks
   that break each stage on its own no longer apply directly.
 - Vigenere is a repeating-key cipher: its security is limited by the key length and
   falls to Kasiski/IC analysis and per-column frequency analysis.
 - Rail Fence has only about n-1 keys and no secret mixing, so it is easy to search.
 - Known-plaintext: with k > m known letters, all rail counts are tested and the keyword
   is read off by modular subtraction (menu 3). The cost is tiny.
 - Ciphertext-only: with a few hundred letters of English, per-column chi-squared analysis
   over all rail counts recovers the keys (menu 3, option c).
 ! HCC is an educational design. It is NOT secure against modern cryptanalysis and must
   never protect real data - use AES-GCM / ChaCha20-Poly1305.

Cheap improvements: keyed columnar transposition instead of Rail Fence; autokey Vigenere;
longer keys with a random (non-word) keyword; apply the substitution again after the
transposition (Vig -> Rail -> Vig) so known-plaintext positions are no longer aligned.
""")


ACTIONS = {"1": action_encrypt, "2": action_decrypt, "3": action_attack, "4": action_frequency,
           "5": action_compare, "6": action_performance, "7": action_info}


def run_demo():
    """Non-interactive walkthrough: every prompt accepts its default value."""
    global AUTO_ACCEPT_DEFAULTS
    AUTO_ACCEPT_DEFAULTS = True
    for number in ("1", "2", "3", "4", "5", "7"):
        print("\n" + "=" * 62 + f"\nDEMO: menu option {number}\n" + "=" * 62)
        ACTIONS[number]()


def main():
    if "--demo" in sys.argv:
        run_demo()
        return
    print(BANNER)
    while True:
        print(MENU)
        choice = ask("Select an option (1-8)").strip()
        if choice == "8":
            print("Goodbye.")
            return
        action = ACTIONS.get(choice)
        if action is None:
            print("  ! Invalid option - enter a number from 1 to 8.")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\n  (cancelled)")
        except ValidationError as error:
            print(f"  ! {error}")


if __name__ == "__main__":
    main()
