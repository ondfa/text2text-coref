import logging
from collections import defaultdict

import udapi
from udapi.block.corefud.movehead import MoveHead
from udapi.block.corefud.singleparent import SingleParent
from udapi.block.read.conllu import Conllu as ConlluReader
from udapi.block.write.conllu import Conllu as ConlluWriter
from udapi.core.coref import BridgingLinks

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def read_data(file):
    move_head = MoveHead()
    single_parent = SingleParent()
    docs = ConlluReader(files=file, split_docs=True).read_documents()
    level = logging.getLogger().level
    logging.getLogger().setLevel(logging.ERROR)
    for doc in docs:
        move_head.run(doc)
        single_parent.run(doc)
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


def convert_text_file_to_conllu(filename, skeleton_filename, output_filename, zero_mentions=False, break_mwt=False):
    if not output_filename:
        output_filename = filename.replace(".txt", ".conllu")
    with open(filename, encoding="utf-8") as f:
        text_docs = f.read().splitlines()
        convert_text_to_conllu(text_docs, skeleton_filename, output_filename, zero_mentions, break_mwt)


def remove_empty_node(node):
    """Delete this empty node."""
    for n in node.root.empty_nodes + node.root.descendants:
        if n.deps:
            n.deps = [x for x in n.deps if x["parent"] != node]
    to_reorder = [e for e in node.root.empty_nodes if node.ord < e.ord < node.ord + 1]
    for empty in to_reorder:
        empty.ord = round(empty.ord - 0.1, 1)
    try:
        node.root.empty_nodes.remove(node)
    except ValueError:
        return # self may be an already deleted node e.g. if n.remove() called twice

def is_mwt_start(node):
    return node.multiword_token and node.multiword_token.words[0] == node

def is_mwt_end(node):
    return node.multiword_token and node.multiword_token.words[-1] == node

def align_words_in_mwt(udapi_nodes, words):
    j = 0
    for i in range(len(udapi_nodes)):
        node = udapi_nodes[i]
        if is_mwt_start(node):
            mwt_length = len(node.multiword_token.words)
            for k in range(mwt_length - 1):
                words.insert(j+1, udapi_nodes[i + k].form)
                j += 1
            j += 1

def convert_text_to_conllu(text_docs, conllu_skeleton_file, out_file, use_gold_empty_nodes=True, break_mwt=False):
    udapi_docs = read_data(conllu_skeleton_file)
    # udapi_docs2 = read_data(conllu_skeleton_file)
    move_head = MoveHead()
    for doc in udapi_docs:
        doc._eid_to_entity = {}
    assert len(udapi_docs) == len(text_docs)
    x = 0
    for text, udapi_doc in zip(text_docs, udapi_docs):
        words = text.split(" ")
        udapi_words = [word for word in udapi_doc.nodes]
        # if x == 96:
        #     print("")
        for word in udapi_doc.nodes_and_empty:
            word.misc = {}
            # Remove empty nodes
            if not use_gold_empty_nodes and word.is_empty():
                remove_empty_node(word)
        j = 1
        for i in range(len(udapi_words)):
            word = udapi_words[i]
            if is_mwt_start(word):
                mwt_length = len(word.multiword_token.words)
                for k in range(1, mwt_length):
                    words.insert(j, udapi_words[i + k].form)
                    # j += 1
            while j < len(words) and not use_gold_empty_nodes and words[j].startswith("##"):
                word.create_empty_child("_", after=True)
                j += 1
            j += 1
        udapi_words = [word for word in udapi_doc.nodes_and_empty]
        # align_words_in_mwt(udapi_words, words)
        for i in range(len(udapi_words)):
            if udapi_words[i].form != words[i].split("|")[0]:
                logger.warning(f"WARNING: words do not match. DOC: {udapi_doc.meta['docname']}, word1: {words[i].split('|')[0]}, word2: {udapi_words[i].form}, i: {i}")
        # if len(udapi_words) != len(words):
        #     continue
        assert len(udapi_words) == len(words)
        mention_starts = defaultdict(list)
        entities = {}
        for i, (word, udapi_word) in enumerate(zip(words, udapi_words)):
            if word.split("|")[0] != udapi_word.form:
                logger.warning(f"WARNING: words do not match. DOC: {udapi_doc.meta['docname']}, word1: {word.split('|')[0]}, word2: {udapi_word.form}")
            if "|" in word:
                mentions = word.split("|")[1].replace("-", ",").split(",")
                for mention in mentions:
                    eid = mention.replace("[", "").replace("]", "")
                    if len(eid) == 0:
                        continue
                    if eid not in entities:
                        entities[eid] = udapi_doc.create_coref_entity(eid=eid)
                    if mention.startswith("["):
                        start = i
                        if not break_mwt and udapi_word.multiword_token:
                            start = i - udapi_word.ord + udapi_word.multiword_token.words[0].ord
                        mention_starts[eid].append(start)
                    if mention[-1] == "]":
                        if not mention_starts[eid]:
                            logger.warning(f"WARNING: Closing mention which was not opened. DOC: {udapi_doc.meta['docname']}, EID: {eid}")
                            continue
                        end = i
                        if not break_mwt and udapi_word.multiword_token:
                            end = i - udapi_word.ord + udapi_word.multiword_token.words[-1].ord
                        entities[eid].create_mention(words=udapi_words[mention_starts[eid][-1]: end + 1])
                        mention_starts[eid].pop()
        udapi.core.coref.store_coref_to_misc(udapi_doc)
        move_head.run(udapi_doc)
        x += 1
    # debug_udapi(udapi_docs, udapi_docs2)
    with open(out_file, "w", encoding="utf-8") as f:
        write_data(udapi_docs, f)


def convert_conllu_file_to_text(filename, output_filename, zero_mentions, blind=False, sequential_ids=True, break_mwt=False):
    if not output_filename:
        output_filename = filename.replace(".conllu", ".txt")
    docs = read_data(filename)
    convert_to_text(docs, output_filename, zero_mentions, not blind, sequential_ids, break_mwt)


def shift_empty_node(node, break_mwt=True):
    if not node.is_empty():
        return
    parent = node.deps[0]["parent"]
    if int(node.ord) == parent.ord:
        return
    if not break_mwt and parent.multiword_token:
        parent = parent.multiword_token.words[-1]
    new_ord = parent.ord + 0.1
    empties = parent.root.empty_nodes
    for empty in empties:
        if int(empty.ord) == parent.ord:
            new_ord += 0.1
    node.ord = new_ord
    parent.root.empty_nodes.sort()




def convert_to_text(docs, out_file, solve_empty_nodes=True, mark_entities=True, sequential_ids=False, break_mwt=False):
    with open(out_file, "w", encoding="utf-8") as f:
        for doc in docs:
            eids = {}
            out_words = []
            if solve_empty_nodes:
                for node in doc.nodes_and_empty:
                    if node.is_empty():
                        shift_empty_node(node, break_mwt)
                udapi_words = [word for word in doc.nodes_and_empty]
            else:
                udapi_words = [word for word in doc.nodes]
            for i, word in enumerate(udapi_words):
                if not break_mwt and word.multiword_token:
                    if is_mwt_start(word):
                        out_word = word.multiword_token.form.replace(" ", "_")
                        mwt_mentions = set()
                        mention_reprs = []
                else:
                    out_word = word.form.replace(" ", "_")
                if word.is_empty():
                    out_word = "##" + (out_word if out_word != "_" else "") # empty nodes start with ##
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
                            root = mention.words[0].root
                            for subspan in span.split(','):
                                subspan_words = udapi.core.coref.span_to_nodes(root, subspan)
                                if mention.head in subspan_words:
                                    mention.words = subspan_words
                                    span = subspan
                                    break
                        mention_start = float(span.split("-")[0])
                        mention_end = float(span.split("-")[1]) if "-" in span else mention_start
                        if not break_mwt and word.multiword_token:
                            if (mention_start, mention_end) not in mwt_mentions:
                                mwt_mentions.add((mention_start, mention_end))
                                if mention_start >= word.multiword_token.words[0].ord and mention_end <= word.multiword_token.words[-1].ord:
                                    mention_reprs.append(f"[{eid}]")
                                elif mention_start >= word.multiword_token.words[0].ord:
                                    mention_reprs.append(f"[{eid}")
                                elif mention_end <= word.multiword_token.words[-1].ord:
                                    mention_reprs.append(f"{eid}]")
                        else:
                            if mention_start == float(word.ord) and mention_end == float(word.ord):
                                mentions.append(f"[{eid}]")
                            elif mention_start == float(word.ord):
                                mentions.append(f"[{eid}")
                            elif mention_end == float(word.ord):
                                mentions.append(f"{eid}]")
                if is_mwt_end(word) and len(mention_reprs) > 0:
                    out_words[-1] = out_words[-1] + "|" + ','.join(sorted(mention_reprs))
                if word.multiword_token and not is_mwt_start(word) and not break_mwt:
                    continue
                if len(mentions) > 0:
                    out_words.append(f"{out_word}|{','.join(sorted(mentions))}")
                else:
                    out_words.append(out_word)
            f.write(" ".join(out_words) + "\n")


def debug_udapi(udapi_docs1, udapi_docs2):
    for doc1, doc2 in zip(udapi_docs1, udapi_docs2):
        for e1, e2 in zip(doc1.coref_entities, doc2.coref_entities):
            for m1, m2 in zip(e1.mentions, e2.mentions):
                if m1.span != m2.span:
                    logger.error("spans do not match")
