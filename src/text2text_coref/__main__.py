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
        help="Map zero mentions in the output to the gold empty nodes in CoNLLu.",
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
        help="Include zero mentions in output text.",
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

    conllu2text_parser.add_argument(
        "-m",
        "--break_mwt",
        action="store_true",
        help="Break multi-word tokens into their component words in the output text.",
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
        help="Map zero mentions in the output to the gold empty nodes in CoNLLu.",
    )
    text2conllu_parser.add_argument(
        "-m",
        "--break_mwt",
        action="store_true",
        help="Break multi-word tokens into their component words in the output text.",
    )

    conllu2json_parser = subparsers.add_parser(
        "conllu2json",
        prog="conllu2json_convertor",
        help="converts conllu with coference annotations into clustered json format"
    )

    conllu2json_parser.add_argument("filename")
    conllu2json_parser.add_argument("-o", "--output_filename", default=None)
    conllu2json_parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions in output text.",
    )

    conllu2json_parser.add_argument(
        "-b",
        "--blind",
        action="store_true",
        help="discard annotations",
    )
    conllu2json_parser.add_argument(
        "-m",
        "--break_mwt",
        action="store_true",
        help="Break multi-word tokens into their component words in the output text.",
    )

    json2conllu_parser = subparsers.add_parser(
        "json2conllu",
        prog="json2conllu_convertor",
        help="converts clustered json format into conllu with coference annotations"
    )
    json2conllu_parser.add_argument("json_filename")
    json2conllu_parser.add_argument("conllu_skeleton_filename")
    json2conllu_parser.add_argument("-o", "--output_filename", default=None)
    json2conllu_parser.add_argument(
        "-g",
        "--use_gold_empty_nodes",
        action="store_true",
        help="Use gold empty nodes from the skeleton CoNLLu file.",
    )
    json2conllu_parser.add_argument(
        "-m",
        "--break_mwt",
        action="store_true",
        help="Break multi-word tokens into their component words in the output text.",
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
    elif args.action == "conllu2text":
        del args.action
        convert_conllu_file_to_text(**vars(args))
    elif args.action == "conllu2json":
        from .json_format import convert_conllu_file_to_json
        del args.action
        convert_conllu_file_to_json(**vars(args))
    elif args.action == "json2conllu":
        from .json_format import convert_json_to_conllu
        del args.action
        convert_json_to_conllu(**vars(args))



if __name__ == "__main__":
    main()
