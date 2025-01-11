# kbdx_brute_search
This is a script for doing brute force search for kbdx master passwords.

Requires installing kpcli: `pip install kpcli`.

Example:
```
python search_kdbx.py \
  --words_filepath=test/test_wordlist \
  --output_filepath=/tmp/test_pwds \
  --min_optional=1 \
  --kdbx_filepath=test/testkdbx.kdbx
```

Options:
- `--words_filepath`: Text file giving the word vocabulary for generating passwords.
See the description below on how to write this file.
- `--output_filepath`: (Optional) The path where the generated passwords would be written to.
Each line in this file would be one generated password.
- `--min_optional`: (Default = 0) Minimum number of optional words to use in each generated
password. See the description of `words_filepath` below.
- `--kdbx_filepath`: (Optional) If given, will test generated passwords on this kdbx file.
- `--n_threads`: (Default = 10) Number of parallel threads to run for searching passwords.
- `--n_parallel_splits`: (Default = 1000) Number of splits for searching passwords.

The `words_filepath` can be used to specify the words to compose  passwords for
the brute force search. It can control the words that are always included in
generated passwords, or words that are optionally included, or words that are
used mutually exclusively. Each word can be a single character or multiple
characters long. Any character can be used except the comma (since it holds a
special meaning as you will see below). Every line in the file defines a unique
word to be used for generating passwords. The file has the following format:
  ```
  word1
  word2
  ```
This will generate passwords `["word1", "word2", "word1word2", "word2word1"]`.
To ensure a certain word is used in all generated passwords add the suffix
`'[c]'` ('c' for compulsory):
  ```
  word1
  word2[c]
  ```
This will generate passwords "word2", "word1word2", "word2word1".
If you have a list of words which you want to use mutually exclusively in
generated passords (i.e. use only one of the words at a time), you can give the
words as a comma separated list on the same line::
  ```
  pA,pB,pC
  word2[c]
  ```
This will generate passwords `["word2", "pAword2", "pBword2", "pCword2", `
`"word2pA", "word2pB", "word2pC"]`. You can mix and match the above options as
you please:
  ```
  pA,pB
  word1,word2[c]
  ```
This will generate passwords `["word1", "word2", "pAword1", "pBword1",`
`"word1pA", "word1pB", "pAword2", "pBword2", "word2pA", "word2pB"]`.
