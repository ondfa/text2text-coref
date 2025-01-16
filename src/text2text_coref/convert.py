import logging

import udapi
from udapi.block.corefud.movehead import MoveHead
from udapi.block.read.conllu import Conllu as ConlluReader
from udapi.block.write.conllu import Conllu as ConlluWriter
from udapi.core.coref import BridgingLinks

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def read_data(file):
    move_head = MoveHead()
    docs = ConlluReader(files=file, split_docs=True).read_documents()
    level = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    for doc in docs:
        move_head.run(doc)
    logging.getLogger().setLevel(level)
    return docs


def write_data(docs, f):
    level = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    writer = ConlluWriter(filehandle=f)
    for doc in docs:
        writer.before_process_document(doc)
        writer.process_document(doc)
    # writer.after_process_document(None)
    logging.getLogger().setLevel(level)


def convert_text_file_to_conllu(filename, skeleton_filename, output_filename, zero_mentions=True):
    if not output_filename:
        output_filename = filename.replace(".txt", ".conllu")
    with open(filename, encoding="utf-8") as f:
        text_docs = f.read().splitlines()
        convert_text_to_conllu(text_docs, skeleton_filename, output_filename, zero_mentions)


def convert_text_to_conllu(text_docs, conllu_skeleton_file, out_file, solve_empty_nodes=True):
    udapi_docs = read_data(conllu_skeleton_file)
    # udapi_docs2 = read_data(conllu_skeleton_file)
    move_head = MoveHead()
    for doc in udapi_docs:
        doc._eid_to_entity = {}
    assert len(udapi_docs) == len(text_docs)
    for text, udapi_doc in zip(text_docs, udapi_docs):
        if solve_empty_nodes:
            udapi_words = [word for word in udapi_doc.nodes_and_empty]
        else:
            udapi_words = [word for word in udapi_doc.nodes]
        for word in udapi_doc.nodes_and_empty:
            word.misc = {}
        words = text.split(" ")
        if len(udapi_words) != len(words):
            continue
        assert len(udapi_words) == len(words)
        mention_starts = {}
        entities = {}
        for i, (word, udapi_word) in enumerate(zip(words, udapi_words)):
            if word.split("|")[0] != udapi_word.form:
                logger.warning(f"WARNING: words do not match. DOC: {udapi_doc.meta['docname']}, word1: {word.split('|')[0]}, word2: {udapi_word.form}")
            if "|" in word:
                mentions = word.split("|")[1].replace("-", ",").split(",")
                for mention in mentions:
                    eid = mention.replace("(", "").replace(")", "")
                    if len(eid) == 0:
                        continue
                    if eid not in entities:
                        entities[eid] = udapi_doc.create_coref_entity(eid=eid)
                    if mention.startswith("("):
                        if eid in mention_starts:
                            logger.warning(f"WARNING: Multiple mentions of the same entity opened. DOC: {udapi_doc.meta['docname']}, EID: {eid}")
                            # continue
                        mention_starts[eid] = i
                    if mention[-1] == ")":
                        if eid not in mention_starts:
                            logger.warning(f"WARNING: Closing mention which was not opened. DOC: {udapi_doc.meta['docname']}, EID: {eid}")
                            continue
                        entities[eid].create_mention(words=udapi_words[mention_starts[eid]: i + 1])
                        del mention_starts[eid]
        udapi.core.coref.store_coref_to_misc(udapi_doc)
        move_head.run(udapi_doc)
    # debug_udapi(udapi_docs, udapi_docs2)
    with open(out_file, "w", encoding="utf-8") as f:
        write_data(udapi_docs, f)


def convert_conllu_file_to_text(filename, output_filename, zero_mentions, blind=False, sequential_ids=True):
    if not output_filename:
        output_filename = filename.replace(".conllu", ".txt")
    docs = read_data(filename)
    convert_to_text(docs, output_filename, zero_mentions, not blind, sequential_ids)


def convert_to_text(docs, out_file, solve_empty_nodes=True, mark_entities=True, sequential_ids=False):
    with open(out_file, "w", encoding="utf-8") as f:
        for doc in docs:
            eids = {}
            out_words = []
            if solve_empty_nodes:
                udapi_words = [word for word in doc.nodes_and_empty]
            else:
                udapi_words = [word for word in doc.nodes]
            for word in udapi_words:
                out_word = word.form
                if word.lemma.startswith("#") and solve_empty_nodes:
                    out_word += word.lemma
                mentions = []
                if mark_entities:
                    for mention in set(word.coref_mentions):
                        if sequential_ids:
                            if mention.entity.eid not in eids:
                                eids[mention.entity.eid] = f"e{len(eids) + 1}"
                            eid = eids[mention.entity.eid]
                        else:
                            eid = mention.entity.eid
                        span = mention.span
                        if "," in span:
                            span = span.split(",")[0]
                        mention_start = float(span.split("-")[0])
                        mention_end = float(span.split("-")[1]) if "-" in span else mention_start
                        if mention_start == float(word.ord) and mention_end == float(word.ord):
                            mentions.append(f"({eid})")
                        elif mention_start == float(word.ord):
                            mentions.append(f"({eid}")
                        elif mention_end == float(word.ord):
                            mentions.append(f"{eid})")
                if len(mentions) > 0:
                    out_words.append(f"{out_word}|{','.join(mentions)}")
                else:
                    out_words.append(out_word)
            f.write(" ".join(out_words) + "\n")


def debug_udapi(udapi_docs1, udapi_docs2):
    for doc1, doc2 in zip(udapi_docs1, udapi_docs2):
        for e1, e2 in zip(doc1.coref_entities, doc2.coref_entities):
            for m1, m2 in zip(e1.mentions, e2.mentions):
                if m1.span != m2.span:
                    logger.error("spans do not match")
