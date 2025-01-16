import logging

from .convert import convert_text_file_to_conllu, convert_conllu_file_to_text
from .output_cleaner import clean_file


def parse_args():
    from argparse import ArgumentParser
    main_parser = ArgumentParser(prog="text2text_coref",
                                 description="Coreference resolution plaintext convertor",)
    subparsers = main_parser.add_subparsers(required=True, dest='action')
    parser = subparsers.add_parser(
        "clean",
        prog="output_cleaner",
        help="LLM Output Cleaner for Coreference Resolution",
    )

    # parser.add_argument("command", type=Command, choices=list(Command))
    parser.add_argument("filename")
    parser.add_argument("gold_filename")
    parser.add_argument("-o", "--output_filename", default=None)
    parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions (implied pronouns) in output text.",
    )

    conllu2text_parser = subparsers.add_parser(
        "conllu2text",
        prog="conllu2text_convertor",
        help="converts conllu with coference annotations into linear text format"
    )

    conllu2text_parser.add_argument("filename")
    conllu2text_parser.add_argument("-o", "--output_filename", default=None)
    conllu2text_parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions (implied pronouns) in output text.",
    )

    conllu2text_parser.add_argument(
        "-b",
        "--blind",
        action="store_true",
        help="discard annotations",
    )

    conllu2text_parser.add_argument(
        "-s",
        "--sequential_ids",
        action="store_true",
        help="Renumber entity ids starting from 1",
    )

    text2conllu_parser = subparsers.add_parser(
        "text2conllu",
        prog="text2conll_convertor",
        help="converts text with coreference annotations into standard CoNLLu format"
    )

    text2conllu_parser.add_argument("filename")
    text2conllu_parser.add_argument("skeleton_filename")
    text2conllu_parser.add_argument("-o", "--output_filename", default=None)
    text2conllu_parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions (implied pronouns) in output text.",
    )

    return main_parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
    )
    if args.action == "clean":
        del args.action
        clean_file(**vars(args))
    elif args.action == "text2conllu":
        del args.action
        convert_text_file_to_conllu(**vars(args))
    else:
        del args.action
        convert_conllu_file_to_text(**vars(args))


if __name__ == "__main__":
    main()
