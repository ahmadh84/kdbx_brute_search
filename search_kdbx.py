"""Kdbx master password brute force search.
"""

from typing import Any
import sys
import os
import itertools
import math
import subprocess
import tqdm
import concurrent.futures
import argparse


def get_all_combos(
    words: list[list[str]],
    min_select: int
) -> list[tuple[tuple[int, int], ...]]:
  """Creates all permutation of words, going from `min_select` to `len(words)` # of words."""
  all_choices = []
  for num_words_select in range(min_select, len(words)+1):
    words_choice_i = itertools.permutations(range(len(words)), num_words_select)
    for word_choice_i in words_choice_i:
      all_word_options = [[(i, ii) for ii in range(len(words[i]))] for i in word_choice_i]
      curr_choices = list(itertools.product(*all_word_options))
      all_choices.extend(curr_choices)
  return all_choices


def combine_choices(
    word_list1: list[tuple[tuple[int, int], ...]],
    word_list2: list[tuple[tuple[int, int], ...]],
) -> list[tuple[tuple[int, int, int], ...]]:
  word_choices = []
  for wc1 in word_list1:
    for wc2 in word_list2:
      n_words = len(wc1) + len(wc2)
      pos_for_1 = tuple(itertools.combinations(range(n_words), len(wc1)))
      for curr_pos1 in pos_for_1:
        curr_words_choice = []
        i1, i2 = 0, 0
        for i in range(n_words):
          if i1 < len(curr_pos1) and curr_pos1[i1] == i:
            curr_words_choice.append((0,) + wc1[i1])
            i1 += 1
          else:
            curr_words_choice.append((1,) + wc2[i2])
            i2 += 1
        word_choices.append(tuple(curr_words_choice))
  return word_choices


def n_total_choices(
    optional_list: list[list[str]],
    compulsory_list: list[list[str]],
    min_optional: int
) -> int:
  optional_count = [len(words) for words in optional_list]
  comp_count = [len(words) for words in compulsory_list]
  comp_n_choices = math.prod(comp_count) * math.factorial(len(compulsory_list))
  total_n_choices = 0
  for n_optional in range(min_optional, len(optional_list)+1):
    total_n_words = len(compulsory_list) + n_optional
    common_perm_count = math.factorial(total_n_words) // math.factorial(total_n_words - n_optional)
    common_perm_count *= comp_n_choices
    word_choice_count = [
        math.prod(c) * common_perm_count for c in itertools.combinations(optional_count, n_optional)
    ]
    total_n_choices += sum(word_choice_count)
  return total_n_choices


def return_words(
    list_of_words: list,
    all_choices: list[tuple[tuple[int,...],...]]
) -> list[str]:
  all_words = []
  for choice_i in all_choices:
    curr_words = []
    for select_ii in choice_i:
      w = list_of_words
      for iii in select_ii:
        w = w[iii]
      assert isinstance(w, str)
      curr_words.append(w)
    all_words.append("".join(curr_words))
  return all_words


def generate_passwords(
    words_filepath: str,
    output_filepath: str | None,
    min_optional: int
) -> list[str]:
  if not os.path.isfile(words_filepath):
    raise ValueError(f"Invalid filepath: '{words_filepath}'")
  if output_filepath is not None and os.path.isfile(output_filepath):
    raise ValueError(f"Output filepath exists: '{output_filepath}'")

  with open(words_filepath, "r") as fd:
    word_list = fd.read().splitlines()
    # ignore empty linees
    word_list = [line.rstrip() for line in word_list if len(line.rstrip()) > 0]
    optional_list = [line.split(",") for line in word_list if not line.endswith("[c]")]
    compulsory_list = [line[:-3].split(",") for line in word_list if line.endswith("[c]")]
  print(f"Optional word list ({len(optional_list)}):   {optional_list}")
  print(f"Compulsory word list ({len(compulsory_list)}):   {compulsory_list}")
  min_optional = min(len(optional_list), min_optional)
  expected_n = n_total_choices(optional_list, compulsory_list, min_optional)
  print(f"Expected number of generated passwords: {expected_n:,}")
  optional_word_choices = get_all_combos(optional_list, min_optional)
  compulsory_word_choices = get_all_combos(compulsory_list, len(compulsory_list))
  word_choices = combine_choices(optional_word_choices, compulsory_word_choices)
  all_passwords = return_words([optional_list, compulsory_list], word_choices)
  print(f"Created {len(all_passwords):,d} possible passwords")
  assert len(all_passwords) == len(set(all_passwords)), "Somehow generated not unique pwds"
  assert len(all_passwords) == expected_n, "Generated number of pwds doesn't match the expected count"

  if output_filepath is not None:
    with open(output_filepath, "w+") as fd:
      for word in all_passwords:
        fd.write(f"{word}\n")

  return all_passwords


def test_passwords(
    kdbx_filepath: str,
    passwords: str,
    values: dict[str, Any]
) -> tuple[int, str | None]:
  tested_passwords = 0
  password_found = None
  for pwd in passwords:
    cmd = f'/bin/echo "{pwd}" | keepassxc-cli open "{kdbx_filepath}" &> /dev/null'
    return_code = subprocess.call(cmd, shell=True)
    tested_passwords += 1
    if return_code == 0:
      password_found = pwd
      values["password_found"] = pwd
      break
  return tested_passwords, password_found


def test_all_passwords(
    all_passwords: list[str],
    kdbx_filepath: str,
    n_threads: int,
    n_parallel_splits: int
):
  if not os.path.isfile(kdbx_filepath):
    raise ValueError(f"Invalid password filepath: '{kdbx_filepath}'")

  n_parallel_splits = min(n_parallel_splits, len(all_passwords))

  pbar = tqdm.tqdm(total=len(all_passwords), desc="Testing passwords")
  executor = concurrent.futures.ThreadPoolExecutor(max_workers=n_threads)
  futures = []
  parallel_values = {}

  def callback(future):
    try:
      tested_pwds, pwd_found = future.result()
      pbar.update(tested_pwds)
      if pwd_found is not None:
        executor.shutdown(wait=False)
        for f in futures:
          f.cancel()
    except concurrent.futures._base.CancelledError as excp:
      pass

  # split set of passwords across thread workers
  all_passwords_chunks = []
  for split_i in range(n_parallel_splits):
    chunk = all_passwords[split_i::n_parallel_splits]
    all_passwords_chunks.append(chunk)
  assert sorted(p for c in all_passwords_chunks for p in c) == sorted(all_passwords)

  for split_i in range(n_parallel_splits):
    future = executor.submit(
        test_passwords,
        kdbx_filepath=kdbx_filepath,
        passwords=all_passwords_chunks[split_i],
        values=parallel_values,
    )
    future.add_done_callback(callback)
    futures.append(future)

  executor.shutdown(wait=True)
  pbar.close()

  password_found = parallel_values.get("password_found")
  if password_found is not None:
    print(f"FOUND PASSWORD: '{password_found}'")
  else:
    print("PASSWORD NOT FOUND!")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Kdbx brute force password search")
  parser.add_argument(
      "--words_filepath",
      type=str,
      help="File giving word options for generating passwords",
      required=True,
  )
  parser.add_argument(
      "--output_filepath",
      type=str,
      help="Output filepath where each line gives a password to be tested",
  )
  parser.add_argument(
      "--min_optional",
      default=0,
      type=int,
      help="Minimum number of optional words to use each generated password",
  )
  parser.add_argument(
      "--kdbx_filepath",
      type=str,
      help="If given, will test generated passwords on the kdbx file",
  )
  parser.add_argument(
      "--n_threads",
      default=10,
      type=int,
      help="Number of parallel threads to run for searching password",
  )
  parser.add_argument(
      "--n_parallel_splits",
      default=1000,
      type=int,
      help="Number of splits for searching passwords",
  )
  args = parser.parse_args()
  print(args)
  all_passwords = generate_passwords(
      words_filepath=args.words_filepath,
      output_filepath=args.output_filepath,
      min_optional=args.min_optional,
  )
  if args.kdbx_filepath:
    test_all_passwords(
        all_passwords=all_passwords,
        kdbx_filepath=args.kdbx_filepath,
        n_threads=args.n_threads,
        n_parallel_splits=args.n_parallel_splits,
    )
