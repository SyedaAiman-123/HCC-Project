# Requirement-to-Implementation Checklist

## A. Official assignment requirements

| # | Requirement | Where fulfilled | Evidence / how to check |
|---|---|---|---|
| 1 | Combine >= 2 different classical techniques | `vigenere.py` (substitution) + `rail_fence.py` (transposition) combined in `hybrid_cipher.py` | Report s7-8 |
| 2 | >= 2 encryption stages | `hybrid_cipher.encrypt_with_trace` returns plaintext, stage-1 output and ciphertext | Menu 1 shows both stages; `test_hcc_manual_pipeline` |
| 3 | Key length >= 10 characters | `utils.validate_keyword` (min 10, letters only, not periodic); demo key `SECURITYKEYS` (12) | `TestValidation` (short, non-letter, periodic keys rejected) |
| 4 | Encrypt/decrypt implemented in Python | all modules; CLI in `main.py` | Menu 1 and 2; `TestRoundTrips` |
| 5 | Messages of different lengths, A-Z | `utils.normalize_text`, round trips for lengths 1-79, 10,000 and shorter/longer than the key | `test_every_short_length_and_many_rails`, `test_long_message`, `test_message_shorter_than_key` |
| 6 | Attack using frequency analysis and/or known plaintext | `attack.known_plaintext_attack` (main), `attack.ciphertext_only_attack` (bonus), `frequency_analysis.py` | Menu 3 and 4; `TestKnownPlaintextAttack`, `TestFrequencyAnalysis` |
| 7 | Document attack success rates and computational effort for different ciphertext lengths | `performance.attack_success_experiment`, `ciphertext_only_experiment`; results in `results/*.csv`, `results/attack_success.png`; Report s18.2-18.3 | Menu 6 or `python performance.py` |
| 8 | Analyse encryption/decryption time complexity | Report s20 (tables) plus measured scaling check in `performance.format_timing_table`; docstrings of each module | Report s18.1 (200x length -> 174x time) |
| 9 | Compare efficiency with a single-stage cipher (Shift) | `shift_cipher.py`; `performance.benchmark_ciphers`; menu 5; Report s19 | Menu 5, 6 |
| 10 | Suggest improvements without much complexity | Report s23 and menu 7 | 5 concrete O(n) improvements |
| 11 | Algorithms, explanations, security analysis, performance metrics and source code in a GitHub repository | `report/HCC_Report.md` (pseudocode + Mermaid flowcharts, s10-11, 13), s21 (security), s18 (metrics), source in repo, `README.md` upload steps | README "Uploading to GitHub" |

## B. Extra requirements from the project brief

| Requirement | Where |
|---|---|
| Vigenere keyword >= 12 characters (demo) | `sample_data.DEFAULT_KEYWORD = "SECURITYKEYS"` |
| Configurable rails; user-entered valid keys | `main.ask_keys`, `utils.validate_rails` |
| Pipeline Plaintext -> Vigenere -> Rail Fence; decryption reversed | `hybrid_cipher.py` |
| Attack: try rail counts in range | `attack._rails_to_test`, loop in `known_plaintext_attack` |
| Attack: reverse Rail Fence per candidate | `attack.undo_rail_fence_raw` |
| Attack: derive key letters by modular arithmetic | `(stage1_numbers[t] - known_numbers[t]) % 26` in `known_plaintext_attack`; shown in menu 3 table |
| Attack: consistency check of repeating keyword | `conflicts` counter; `TraceRow` search log |
| Attack: identify candidate, recover keyword, decrypt, compare with original, report success | steps 5-7 in `known_plaintext_attack`; `print_attack_report` ("ATTACK SUCCEEDED") |
| Mathematics of the attack explained | module docstring of `attack.py`; Report s12-13 |
| Frequency module, comparison with English, explanation of its limits | `frequency_analysis.py`; menu 4; Report s14 |
| Secret keys NOT passed to attack; assumed vs recovered clearly separated | `test_attack_never_receives_secret_keys`; module docstring; Report s12 table; simulation prints "Attacker does NOT receive..." |
| Menu with options 1-8 | `main.py` (`MENU`, `ACTIONS`) |
| Graphical user interface | `app.py` + `ui/` (web workbench: encrypt/decrypt with stage visualisation, attack lab, frequency analysis, performance charts); `tests/test_app.py`; screenshots in `docs/screenshots/` |
| Input validation, error handling | `utils.ValidationError`, EOF/KeyboardInterrupt handling in `main.py`; `TestValidation` |
| Explain normalization of non A-Z | `NORMALIZATION_NOTE` shown in menu 1 and 7; Report s15; README |
| Real measured timing with `perf_counter`, repeated trials, averages, table, graph | `performance.py`; `results/timing.png` |
| Lengths 50, 100, 500, 1000, 5000, 10000 | `performance.TIMING_LENGTHS` |
| Attack success vs ciphertext length AND known-plaintext size; reproducible | `performance.attack_success_experiment` (seeded) |
| Time and space complexity of every major algorithm | Report s20 |
| Security analysis (all listed topics), no "unbreakable" claim | Report s21, s22 |
| Complete report, 25 sections | `report/HCC_Report.md` |
| Project structure | see README |
| Tests: short/long, shorter/longer than key, different rails, invalid keys, empty, repeated letters, round trip, successful attack, wrong/insufficient known plaintext, different lengths, recovered keys reproduce ciphertext | `tests/test_ciphers.py`, `tests/test_attack.py` (57 tests incl. web API, all passing) |
| Viva preparation (>= 20 Q&A) | `report/Viva_Questions.md` (27) |
| README, repository description, upload instructions | `README.md` |

## C. Design issues found and corrected before implementation

1. **Known-plaintext attack with k = m is undecidable** (no redundancy): documented, requirement k > m, ambiguity reported, optional English-likeness tie-break.
2. **Weak keywords** (`AAAAAAAAAAAA`): effective-length rule added.
3. **Rails >= message length** makes Stage 2 the identity: allowed, warning displayed; attack tests only one such value.
4. **Known segment is scattered after transposition**: attack takes the whole ciphertext plus the segment's offset.
5. **Formatting preservation** rejected (leaks word boundaries): consistent removal of non-letters.
