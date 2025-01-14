from collections import defaultdict
from itertools import chain
from typing import List

import re

import logging

logger = logging.getLogger(__name__)

def _correct_tags(tok_sentence):
    """
    This function takes a tokenized sentence and ensures that all tags are closed.
    When a tag is not closed or opened properly, the entity is converted into a
    single-token tag.

    Tags that cannot be parsed are thrown out.
    """
    num_wrong_para = 0

    if not tok_sentence:
        return []

    entity_stacks = defaultdict(lambda: [])
    clean_toks = []

    for word_idx, word in enumerate(tok_sentence):
        splits = word.split("|")

        if len(splits) == 1:
            clean_toks.append(word)

        elif len(splits) == 2:
            tags = splits[1].split(",")

            ptags = map(lambda x: re.match(r"(\(?)e(\d+)(\)?)", x), tags)
            ptags = map(lambda x: x.groups() if x else ("", "", ""), ptags)

            clean_tags = []

            for left_bracket, entity_id, right_bracket in ptags:
                tag = f"{left_bracket}e{entity_id}{right_bracket}"

                if left_bracket and right_bracket:
                    clean_tags.append(tag)

                elif left_bracket:
                    entity_stacks[entity_id].append((word_idx, len(clean_tags)))
                    clean_tags.append(tag)

                elif right_bracket:
                    entity_stack = entity_stacks[entity_id]
                    if len(entity_stack) > 0:
                        entity_stacks[entity_id].pop()
                        clean_tags.append(tag)
                    else:
                        num_wrong_para += 1
                        clean_tags.append("(" + tag)

                else:
                    logging.debug(f"warning: completely invalid tag in: {word}")

            if clean_tags:
                clean_toks.append(f"{splits[0]}|{','.join(clean_tags)}")
            else:
                clean_toks.append(splits[0])

        else:
            logging.debug(f"warning: multiple pipes in word {word}- stripping tags")
            clean_toks.append(splits[0])

    # convert all unclosed entities to 1-word entities
    for entity, stack in entity_stacks.items():
        for word_idx, tag_idx in stack:
            try:
                num_wrong_para += 1

                token = clean_toks[word_idx]
                word, tags = token.split("|")

                tags = tags.split(",")

                assert tags[tag_idx] == f"(e{entity}", (
                    "Mismatched entity when correcting tags"
                )

                tags[tag_idx] = tags[tag_idx] + ")"

                clean_toks[word_idx] = f"{word}|{','.join(tags)}"

            except Exception as ex:
                logging.debug(f"{ex} while converting unclosed entitites")

    if num_wrong_para:
        sentence = " ".join(tok_sentence)
        logging.debug(
            f'{num_wrong_para} mismatched parantheses in sentence: "{sentence}"'
        )

    return clean_toks


def _word_level_edit_distance(words1, words2, tagged_words1):
    """
    Uses an edit-distance-like algorithm to match up the words between
    two versions of a document. Tagged words are used to carry over
    as many entity annotations as possible - any words that remain the
    same or can be tracked back to a "replace" operation keep their tags.
    """
    m, n = len(words1), len(words2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # initialize the first row and column
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # fill the dp table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if words1[i - 1] == words2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1

    # backtrack to extract sentence with appropriate tags.
    result = []
    word_problems = defaultdict(int)

    i, j = m, n

    while i > 0 and j > 0:
        if words1[i - 1] == words2[j - 1]:
            # same case - actually use tags
            result.append(tagged_words1[i - 1])
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j - 1] + 1:
            # replace case
            result.append(words2[j - 1])
            word_problems["replace"] += 1
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            # delete case
            word_problems["delete"] += 1
            i -= 1
        else:
            # insert case
            result.append(words2[j - 1])
            word_problems["insert"] += 1
            j -= 1

    while j > 0:
        result.append(words2[j - 1])
        word_problems["insert"] += 1
        j -= 1

    if word_problems:
        logger.debug(f"word_problems: {dict(word_problems)}")

    result.reverse()
    return result


def _clean_document(document, gold_tok2):
    """
    Applies both stages of cleaning on one document.
    """
    doc_words = document.split()

    stripped_doc = [word.split("|")[0] for word in doc_words]
    flattened_gold = list(chain(*gold_tok2))

    correct_words = _word_level_edit_distance(
        stripped_doc, flattened_gold, doc_words
    )

    final_sentences = []

    offset = 0
    for ref_sentence in gold_tok2:
        ln = len(ref_sentence)
        sentence = correct_words[offset : offset + ln]
        offset += ln

        correct_sentence = _correct_tags(sentence)
        final_sentences.append(" ".join(correct_sentence))

    return " ".join(final_sentences)


def read_conllu(filename: str, zero_mentions: bool) -> List[List[List[str]]]:
    """
    Parses a CoNLL-U file into a list structure. Only loads the minimal information
    needed to correct sentence structure.

    The list structure is as follows:
    - first outer list corresponds to documents
    - the next list corresponds to sentences
    - final inner list corresponds to word tokens

    The zero mentions switch determines whether zero mentions should be included
    (True) or skipped (False).
    """
    with open(filename, "r", encoding="utf-8") as f:
        gold = f.readlines()

        gold_docs_tok2 = []
        next_doc = []
        next_sent: List[str] = []

        for line in gold:
            if not line.strip():
                continue

            if line.startswith("#"):
                begins_new_doc = line.startswith("# newdoc id")

                if line.startswith("# sent_id") or begins_new_doc:
                    if next_sent:
                        next_doc.append(next_sent)
                    next_sent = []

                if begins_new_doc:
                    if next_doc:
                        gold_docs_tok2.append(next_doc)
                    next_doc = []

                continue

            number, word = line.split()[:2]

            if not zero_mentions and "." in number:
                continue  # skip sero mentions

            if "-" in number:
                continue  # always skip multitokens

            next_sent.append(word)

        next_doc.append(next_sent)
        gold_docs_tok2.append(next_doc)

    return gold_docs_tok2

def read_input_file(filename: str) -> List[str]:
    """
    Reads an input file as a list of documents.
    """
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]
        
def clean_data(
    docs: List[str], gold: List[List[List[str]]]
) -> List[str]:
    return [_clean_document(doc, gold_doc) for doc, gold_doc in zip(docs, gold)]


def clean_file(
    filename: str,
    gold_filename: str,
    output_filename: str | None = None,
    zero_mentions: bool = True,
):
    logging.info(f"Reading input file: {filename}")
    data = read_input_file(filename)

    logging.info(f"Reading gold file: {gold_filename}")
    gold_docs_tok2 = read_conllu(gold_filename, zero_mentions)

    logging.info("Cleaning data")
    clean = clean_data(data, gold_docs_tok2)

    if not output_filename:
        output_filename = filename.replace(".txt", "-cleaned.txt")

    logging.info(f"Writing output file: {output_filename}")
    with open(output_filename, "w", encoding="utf-8") as f:
        clean = [line + "\n" for line in clean]
        f.writelines(clean)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog="output_cleaner",
        description="LLM Output Cleaner for Coreference Resolution",
    )

    parser.add_argument("filename")
    parser.add_argument("gold_filename")
    parser.add_argument("-o", "--output_filename", default=None)
    parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions (implied pronouns) in output text.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
    )

    clean_file(**vars(args))
