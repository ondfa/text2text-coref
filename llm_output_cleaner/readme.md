# LLM Output Cleaner for Coreference Resolution

A Python tool that cleans and validates tagged text output from Language Models (LLMs) for coreference resolution tasks. The script ensures proper word alignment with reference text and maintains correct entity tag formatting while preserving as many original annotations as possible.

## Usage

Assumes functional Python 3.7+, there are no additional dependencies.

### Command Line Interface

The basic usage pattern is:

```bash
python output_cleaner.py <input_file> <gold_file> [options]
```

Arguments:
- `input_file`: Path to the file containing LLM tagged output
- `gold_file`: Path to the reference CoNLL-U file
- `-o, --output_filename`: Optional output file path (default: input_filename-cleaned.txt)
- `-z, --zero_mentions`: Include zero mentions/implied pronouns in output (default: False)

Example:
```bash
python output_cleaner.py sample_data/en_gum_dev_4o_mini.txt sample_data/en_gum-corefud-dev.conllu
```

### Python API

You can also use the cleaner programmatically:

```python
from output_cleaner import clean_file, clean_data

# Using the high-level interface
clean_file(
    filename="input.txt",
    gold_filename="reference.conllu",
    output_filename="cleaned.txt",
    zero_mentions=True
)

# Or process data directly
from output_cleaner import read_input_file, read_conllu, clean_data

input_docs = read_input_file("input.txt")
gold_docs = read_conllu("reference.conllu", zero_mentions=True)
cleaned_docs = clean_data(input_docs, gold_docs)
```

## Understanding Logging Output

The script logs various events at different severity levels:

**INFO**: Basic progress information (file reading/writing)

**DEBUG**: Detailed processing information including:
- Word alignment problems per document: Shows edit distance operations needed to align input with target text.
    - For example, `word_problems: {'insert': 260, 'replace': 2, 'delete': 1}` indicates 260 words needed to be inserted, in this case the model's generation was cut off due to output token limits.
- Mismatched parentheses counts per sentence: Reports entity tag mismatches in the context of CoNLL-U sentence boundaries.
    - Note that valid cross-sentence entity spans will be reported as errors since the evaluator requires strict sentence breaks.
- Invalid tag formats: Captures various parsing issues including multiple pipe delimiters, malformed entity tags, and other structural problems that could affect downstream processing.

Debug logs can be safely ignored during normal operation. They are primarily useful for diagnosing issues with the input format or understanding the cleaning process.

## Technical Details

### Input/Output Functions

When using the Python interface, you only need to handle two main aspects:
1. Provide gold data using `read_conllu`
2. Pass your results as a list of document strings

Each dataset corresponds to a separate function call, unless you manually concatenate the datasets.

#### `read_conllu(filename, zero_mentions)`
Parses CoNLL-U format files into a nested list structure:
- Outer list: documents
- Middle list: sentences
- Inner list: words/tokens

#### `read_input_file(filename)`
Reads the input file as a list of documents.

### Core Functions

The cleaning process involves several key steps:

#### `_clean_document(document, gold_tok2)`
Main cleaning function that coordinates the entire process for a single document.

#### `_word_level_edit_distance(words1, words2, tagged_words1)`
Aligns input text with reference text using a modified edit distance algorithm to preserve entity tags where possible. This is done on the document level and takes the bulk of the processing time due to the `O(|words1| * |words2|)` complexity.

#### `_correct_tags(tok_sentence)`
Validates and corrects entity tag formatting, ensuring all tags are properly opened and closed. A simple stack is used for each entity.
