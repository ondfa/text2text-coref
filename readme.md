# Data formatter for text-to-text coreference resolution

A Python tool that converts annotated coreference data in CoNLLu format into linear text format, cleans and validates tagged text output from Language Models (LLMs), and converts the output back to CoNLLu for evaluation. The script ensures proper word alignment with reference text and maintains correct entity tag formatting while preserving as many original annotations as possible.

## Usage

Assumes functional Python 3.10+, requires `udapi` package.

### Command Line Interface

The program has three commands:
  1) `conllu2text` - converts standard CorefUD CoNLLu format into linear text with eid annotations in the following form: `Los|[e1 jugadores de el Espanyol|[e2],e1] aseguraron hoy que ##|[e1] prefieren enfrentar se a el Barcelona|[e3]
en la|[e4 final de la|[e5 Copa de el Rey|e4],e5] en lugar de en las|[e6 semifinales|e6] , tras clasificar se ayer
ambos|[e7 equipos catalanes|e7] para esta|[e6 ronda|e6] .` 
  2) `clean` - For correcting the output of LLM.
  3) `text2conllu` - Converts corrected output back to CoNLLu for evaluation

The basic usage pattern is:
```bash
python -m text2text_coref action [options]
```

Note: you need to install the package first with `pip install .` in the root directory or directly from GitHub with `pip install git+https://github.com/ondfa/text2text-coref`

There are several usage scenarios:

### zero-shot prediction

1) Prepare blind text files: `text2text_coref conllu2text <input_file> --blind [--sequential_ids --zero_mentions]`
2) Run LLM on blind text file.
3) Clean the output of LLM: `text2text_coref clean <input_file> <conll_skeleton_file>`
4) Convert cleaned file back to CoNLLu: `text2text_coref text2conllu <input_file> <conll_skeleton_file>`
5) Run `CorefUD-scorer` on the output CoNLLu and the gold file.

### Fine-tuning

1) Prepare blind text files: `text2text_coref conllu2text <input_file> --blind -o input_data.txt`
2) Prepare gold inputs in text format: `text2text_coref conllu2text <input_file> -o gold_data.txt`
3) Fine-tune LLM
4) Run steps 2-5 from previous example.


### TIPS

- If you want to train a model to predict also the empty nodes and/or zero mentions add them to the train/test data with `--zero_mentions` option (`--blind --zero_mentions` generates just empty nodes) 
- Using `--sequential_ids` is recommended since LLm can learn increasing entity numbers from 1 per document but it cannot guess the shift when we have global EID like in CorefUD.

### Json Format
The tool also supports JSON format for input and output. Use the `--conllu2json` and `--json2conllu` commands convert inputs and outputs. The typical usage is similar to the text format:
```bash
python -m text2text_coref conllu2json <input_file> --blind [--zero_mentions] -o input_data.json
python -m text2text_coref json2conllu <predictions.json> <conll_skeleton_file> -o output_data.conllu
```

Here is an example of the JSON structure used:

```json
[
  {
    "doc_id": "CESS-CAST-A-20000217-13959", 
    "tokens": [
        "Los", "jugadores", "de", "el", "Espanyol", "aseguraron", "hoy", "que", 
        "prefieren", "##", "enfrentar", "se", "a", "el", "Barcelona", "en", "la", 
        "final", "de", "la", "Copa", "de", "el", "Rey", "en", "lugar", "de", "en", "las", 
        "semifinales", ",", "tras", "clasificar", "se", "ayer", "ambos", "equipos", 
        "catalanes", "para", "esta", "ronda"
    ], 
    "clusters_token_offsets": [
        [ [0, 4], [9, 9] ], 
        [ [4, 4] ], 
        [ [14, 14] ], 
        [ [16, 23] ], 
        [ [19, 23] ],
        [ [  28,  29 ], [39, 40] ], 
        [ [35, 37] ]
    ],
    "clusters_text_mentions": [
        ["Los jugadores de el Espanyol", "_"], 
        ["Espanyol"], 
        ["Barcelona"], 
        ["la final de la Copa de el Rey"], 
        ["la Copa de el Rey"], 
        ["las semifinales", "esta ronda"], 
        ["ambos equipos catalanes"]
    ]
    }]
```

### Python API

You can also use the cleaner programmatically:

```python
from src.text2text_coref.output_cleaner import clean_file

# Using the high-level interface
clean_file(
  filename="input.txt",
  gold_filename="reference.conllu",
  output_filename="cleaned.txt",
  zero_mentions=True
)

# Or process data directly
from src.text2text_coref.output_cleaner import read_input_file, read_conllu, clean_data

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
