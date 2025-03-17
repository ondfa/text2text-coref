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
    debug_args(subparsers)
    return main_parser.parse_args()

def debug_args(subparsers):

    move_zeros_parser = subparsers.add_parser(
        "debug_move_zero",
        prog="conllu2text_convertor",
        help="Runs the move_zeros function on a file"
    )

    move_zeros_parser.add_argument("filename")
    move_zeros_parser.add_argument("-o", "--output_filename", default=None)

    rw_parser = subparsers.add_parser(
        "debug_read_write",
        prog="conllu2text_convertor",
        help="Runs the read and write functions on a file"
    )

    rw_parser.add_argument("filename")
    rw_parser.add_argument("-o", "--output_filename", default=None)

    copy_coref_parser = subparsers.add_parser(
        "debug_copy_coref",
        prog="conllu2text_convertor",
        help="Copies coreference annotations from one file to another"
    )

    copy_coref_parser.add_argument("filename")
    copy_coref_parser.add_argument("-o", "--output_filename", default=None)
    copy_coref_parser.add_argument(
        "-z",
        "--zero_mentions",
        action="store_true",
        help="Include zero mentions in output text.",
    )

    deprel_parser = subparsers.add_parser(
        "debug_deprel",
        prog="conllu2text_convertor",
        help="Removes deprels from empty nodes"
    )

    deprel_parser.add_argument("filename")
    deprel_parser.add_argument("-o", "--output_filename", default=None)

    form_lemma_parser = subparsers.add_parser(
        "debug_form_lemma",
        prog="conllu2text_convertor",
        help="Removes form and lemma from empty nodes"
    )

    form_lemma_parser.add_argument("filename")
    form_lemma_parser.add_argument("-o", "--output_filename", default=None)

    continuous_subspan_parser = subparsers.add_parser(
        "debug_continuous_subspan",
        prog="conllu2text_convertor",
        help="Selects continuous subspans from coref mentions"
    )

    continuous_subspan_parser.add_argument("filename")
    continuous_subspan_parser.add_argument("-o", "--output_filename", default=None)

    remove_mention_head_parser = subparsers.add_parser(
        "debug_remove_mention_head",
        prog="conllu2text_convertor",
        help="Removes mention heads"
    )

    remove_mention_head_parser.add_argument("filename")
    remove_mention_head_parser.add_argument("-o", "--output_filename", default=None)

def debug(args):
    if args.action == "debug_move_zero":
        from .convert import shift_empty_node, read_data, write_data
        data = read_data(args.filename)
        for doc in data:
            for node in doc.nodes_and_empty:
                if node.is_empty():
                    shift_empty_node(node)
        with open(args.output_filename, "w") as f:
            write_data(data, f)
    elif args.action == "debug_read_write":
        from .convert import read_data, write_data
        data = read_data(args.filename)
        with open(args.output_filename, "w") as f:
            write_data(data, f)
    elif args.action == "debug_deprel":
        from .convert import read_data, write_data
        data = read_data(args.filename)
        for doc in data:
            for node in doc.nodes_and_empty:
                if node.is_empty():
                    for dep in node.deps:
                        dep["deprel"] = "_"
        with open(args.output_filename, "w") as f:
            write_data(data, f)
    elif args.action == "debug_form_lemma":
        from .convert import read_data, write_data
        data = read_data(args.filename)
        for doc in data:
            for node in doc.nodes_and_empty:
                if node.is_empty():
                    node.form = "_"
                    node.lemma = "_"
        with open(args.output_filename, "w") as f:
            write_data(data, f)
    elif args.action == "debug_copy_coref":
        copy_coref(args)
    elif args.action == "debug_continuous_subspan":
        select_continuous_subspans(args)
    elif args.action == "debug_remove_mention_head":
        from .convert import read_data, write_data
        data = read_data(args.filename)
        from udapi.block.corefud.movehead import MoveHead
        move_head = MoveHead()
        move_head.process_start()
        for doc in data:
            for mention in doc.coref_mentions:
                mention.head = mention.words[0]
            move_head.apply_on_document(doc)
        move_head.process_end()
        with open(args.output_filename, "w") as f:
            write_data(data, f)

def copy_coref(args):
    from .convert import read_data, write_data, remove_empty_node, shift_empty_node
    from collections import defaultdict
    from udapi.block.corefud.movehead import MoveHead
    different_heads = 0
    move_head = MoveHead()
    move_head.process_start()
    src_data = read_data(args.filename)
    dst_data = read_data(args.filename)
    for doc in dst_data:
        doc._eid_to_entity = {}
    assert len(dst_data) == len(src_data)
    for dest, udapi_doc in zip(dst_data, src_data):
        words = [word for word in dest.nodes_and_empty]
        udapi_words = [word for word in udapi_doc.nodes_and_empty]
        assert len(words) == len(udapi_words)
        mention_starts = defaultdict(list)
        entities = {}
        for word, gold_word in zip(dest.nodes_and_empty, udapi_doc.nodes_and_empty):
            # word.misc = {}
            # Remove empty nodes
            if word.is_empty() and args.zero_mentions:
                remove_empty_node(word)
                shift_empty_node(gold_word)
        if args.zero_mentions:
            words = [word for word in dest.nodes_and_empty]
            udapi_words = [word for word in udapi_doc.nodes_and_empty]
            j = 1
            for i in range(len(words)):
                word = words[i]
                while j < len(udapi_words) and udapi_words[j].is_empty():
                    word.create_empty_child("_", after=True)
                    j += 1
                j += 1
            words = [word for word in dest.nodes_and_empty]
            udapi_words = [word for word in udapi_doc.nodes_and_empty]
            assert len(words) == len(udapi_words)
        for i, (word, udapi_word) in enumerate(zip(words, udapi_words)):
            assert word.form == udapi_word.form or word.is_empty()
            mentions = udapi_word.coref_mentions
            for mention in mentions:
                eid = mention.entity.eid
                if eid not in entities:
                    entities[eid] = dest.create_coref_entity(eid=eid)
                if mention.words[0].ord == word.ord:
                    mention_starts[eid].append(i)
                if mention.words[-1].ord == word.ord:
                    entities[eid].create_mention(words=words[mention_starts[eid][-1]: i + 1])
                    mention_starts[eid].pop()
        move_head.apply_on_document(dest)
        # for mention_a, mention_b in zip(dest.coref_mentions, udapi_doc.coref_mentions):
            # assert mention_a.span == mention_b.span
            # if mention_a.head.ord != mention_b.head.ord:
            #     different_heads += 1
                # mention_a.head = mention_a.words[mention_b.head.ord - mention_b.words[0].ord]
            # assert mention_a.head.ord == mention_b.head.ord
            # assert mention_a.words[0].form == mention_b.words[0].form
            # assert mention_a.words[-1].form == mention_b.words[-1].form
            # assert mention_a.words[0].ord == mention_b.words[0].ord
            # assert mention_a.words[-1].ord == mention_b.words[-1].ord
    move_head.process_end()
    with open(args.output_filename, "w") as f:
        write_data(dst_data, f)


def select_continuous_subspans(args):
    from .convert import read_data, write_data
    from udapi.core.coref import span_to_nodes
    data = read_data(args.filename)
    for doc in data:
        for mention in doc.coref_mentions:
            span = mention.span
            if "," in span:
                root = mention.words[0].root
                for subspan in span.split(','):
                    subspan_words = span_to_nodes(root, subspan)
                    if mention.head in subspan_words:
                        mention.words = subspan_words
                        break
    with open(args.output_filename, "w") as f:
        write_data(data, f)



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
    else:
        debug(args)


if __name__ == "__main__":
    main()
