# Viva Preparation - HCC (Vigenere + Rail Fence)

Numbers quoted come from `python performance.py` on the author's machine (see the report); say "on my machine" when quoting them.

**1. What is HCC in one sentence?**
A two-stage classical cipher: Vigenere substitution with a keyword of at least 10 letters, followed by a Rail Fence transposition; decryption undoes the stages in reverse order.

**2. Why did you choose Vigenere and Rail Fence?**
They represent the two classical families (polyalphabetic substitution and transposition), are simple to implement and verify by hand, and are complementary: substitution hides which letters occur, transposition hides where the key repeats. That also makes the attack design non-trivial.

**3. How does the Vigenere stage work?**
Letters are numbers 0-25. `C[i] = (P[i] + K[i mod m]) mod 26`. The key repeats, so messages shorter or longer than the key are both handled by the index `i mod m`.

**4. How does the Rail Fence stage work and what is its key?**
Write the text in a zig-zag over r rows (period 2(r-1)), read row by row. The key is the number of rails r >= 2. It is a pure permutation of positions: letters do not change.

**5. What exactly is the secret key?**
The pair (keyword, rails). Keyword >= 10 letters, A-Z, not a repetition of a shorter word; rails an integer >= 2.

**6. Why is the effective-length rule needed?** (`ABCABCABCABC` has 12 characters.)
That keyword behaves like a 3-letter key, so it would break the "at least 10 characters" requirement in spirit and be much weaker. `validate_keyword` rejects keys whose smallest repeating unit is shorter than 10.

**7. Why does decryption reverse the order of the stages?**
Encryption is `RailFence(Vigenere(P))`. The inverse of a composition is the composition of inverses in reverse order: `Vigenere^-1(RailFence^-1(C))`. Subtracting key letters before undoing the transposition would subtract them from the wrong positions.

**8. How do you handle spaces, punctuation and lower case?**
Upper-case everything and delete every non A-Z character, consistently in all modules. Decryption returns the normalized plaintext. I did not preserve formatting because spaces would reveal word lengths and help an attacker; I documented this.

**9. What does the attacker know and what must be recovered?**
Known: algorithm, full ciphertext, a known plaintext segment and its offset, the keyword length and a rail range. Recovered: the rail count, the keyword, and then the whole plaintext. The attack function has no parameter for the secret keys (a unit test checks the signature).

**10. Explain your known-plaintext attack.**
For each rail count r in the range: invert the Rail Fence on the whole ciphertext to get V'; for each known position i compute `(V'[i] - P[i]) mod 26`, which is the key letter at slot `i mod m`; check that all positions with the same slot give the same letter. The right r gives a consistent repeating keyword; wrong r's almost always conflict. Then decrypt everything with the recovered keys.

**11. Why must the attacker use the whole ciphertext, not just the "matching piece"?**
After Rail Fence the known plaintext letters are scattered over the ciphertext. Only by undoing the transposition for a guessed r can we locate the Vigenere output at the known positions.

**12. Why is a known segment of exactly m letters not enough?**
With k = m every key slot gets exactly one equation, so *every* rail count is consistent (no redundancy; 19 of 19 survive in my tests). With k > m, the extra rho = k - m equations let a wrong r pass only with probability about 26^-rho. Measured: k = 13 gives 1.7 survivors on average, k = 14 gives 1.03.

**13. What if the known segment is shorter than the key?**
Only k key letters are recoverable; the attack reports PARTIAL and says it needs more known letters. It never pretends to succeed.

**14. What are your measured success rates?**
200 trials per setting: k < 12 -> 0%; k = 12 -> strict 0% but 99.5-100% with English-likeness ranking; k = 13 -> strict 44-49%; k >= 14 and n >= 100 -> strict 97-100%; k = 24 -> 100% (800/800). The table is produced by running the code, not hard-coded.

**15. What is the computational effort of the attack?**
O(R x (n + k x |M|)) character operations: about 19 x n for R = 19 rail counts. For n = 1000 that is roughly 21,000 operations, about 9-10 ms in Python. Compare with exhaustive key search of 26^12 ~ 9.5 x 10^16 keywords.

**16. Why does frequency analysis alone fail against HCC?**
Vigenere uses m different shifts so a plaintext letter maps to many ciphertext letters and the histogram flattens (IC 0.040 vs 0.067 in my demo). Rail Fence keeps the histogram but destroys the position structure needed to split text into Shift-cipher columns. One histogram cannot be matched to one shift.

**17. Is frequency analysis therefore useless against HCC?**
No. If you search the rail count, undo the transposition and analyse each of the m columns separately (a Shift cipher each), the key falls given enough ciphertext. My bonus ciphertext-only attack recovered the keys in 97.5% of trials at n = 500 and 100% at n >= 1000 (0% at n = 100).

**18. What is the time and space complexity of HCC?**
Encryption and decryption are O(n) time and O(n) space: Vigenere is one modular operation per letter; Rail Fence builds the zig-zag pattern and buckets in O(n) independent of r. Measured time grew 174x when length grew 200x.

**19. How does HCC compare with the Shift cipher?**
Both are O(n); HCC is about 2-3.7x slower in my measurements (constant factor from the second pass). Shift has 26 keys, breaks with <= 26 trials by frequency analysis or one known letter; HCC has about 2^60 keys and resists the naive frequency attack but still falls to a known-plaintext attack in milliseconds.

**20. Does a larger key space mean more security?**
No. The key space is 26^12 x n, but the stages are separable: the attack searches rails (about n options) and reads the keyword off by subtraction, never touching 26^12. Security is not the product of the key spaces.

**21. Is HCC secure? Could it be used in practice?**
No. Fixed key-stream period, tiny rail key space, deterministic encryption, no integrity, and it fails known-plaintext and ciphertext-only attacks. It is for teaching; real systems use AES-GCM or ChaCha20-Poly1305.

**22. What improvements do you suggest and why do they help?**
(a) Keyed columnar transposition: bigger transposition key space. (b) Autokey Vigenere: key stream depends on the plaintext, no repeating key, so the consistency test and Kasiski/IC fail. (c) Vigenere -> transposition -> Vigenere: breaks the simple alignment of known plaintext with a single layer. (d) Longer random keys used once. All are O(n) additions, none makes it modern-grade.

**23. How did you verify the implementation is correct?**
52 unit tests: textbook vectors (Vigenere `ATTACKATDAWN`/`LEMON`, Rail Fence `WEAREDISCOVEREDFLEEATONCE` with 3 rails), round-trip for every length 1-79 and rails 2-11, short/long messages, invalid keys, empty input, repeated letters, 60 random successful attacks, insufficient/incorrect known text, re-encryption of recovered keys, and an end-to-end CLI run.

**24. How do you make the experiments reproducible and honest?**
Seeded `random.Random` for keys, rails and plaintexts; `time.perf_counter()` with a warm-up run and averaged repeats; results saved as CSV; nothing hard-coded. Limitation: small built-in corpus, one key length, one machine.

**25. What would happen if the attacker's assumptions are wrong?**
If the true rails are outside the range, or the assumed key length is wrong, or the known text is wrong, no hypothesis is consistent and the attack reports FAILED (tested). The attack does not "force" a result.

**26. (Bonus) Why did you add the English-likeness tie-break and is it cheating?**
When several hypotheses survive the consistency test, something must choose between them. I use chi-squared against English letter frequencies on the full decrypted message. It is an additional assumption (English plaintext), so I report results both with it (ranked) and without it (strict).

**27. (Bonus) What is the index of coincidence?**
The probability that two randomly chosen letters of a text are equal: IC = sum n_i(n_i - 1) / (N(N - 1)). About 0.0655 for English, 0.0385 for random letters; a flat Vigenere-type ciphertext sits in between.
