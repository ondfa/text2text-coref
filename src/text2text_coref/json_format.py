from .convert import shift_empty_node
import udapi
from collections import defaultdict
import logging
from .convert import read_data
import pprint
from compact_json import Formatter
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def convert_to_json(docs, out_file, solve_empty_nodes=True, mark_entities=True, sequential_ids=False):
    import json
    output_data = []
    for doc in docs:
        eids = {}
        out_words = []
        if solve_empty_nodes:
            for node in doc.nodes_and_empty:
                if node.is_empty():
                    shift_empty_node(node)
            udapi_words = [word for word in doc.nodes_and_empty]
        else:
            udapi_words = [word for word in doc.nodes]
        for word in udapi_words:
            out_word = word.form.replace(" ", "_")
            if word.is_empty():
                out_word = "##" + (out_word if out_word != "_" else "") # empty nodes start with ##
            out_words.append(out_word.replace('"', r'\"'))
            # out_words.append(out_word)
        clusters_token_offsets = None
        clusters_text_mentions = None
        if mark_entities:
            clusters_token_offsets = []
            clusters_text_mentions = []
            for entity in doc.coref_entities:
                entity_mentions = []
                entity_mention_offsets = []
                for mention in entity.mentions:
                    span_start = int(float(mention.span.split("-")[0])) - 1
                    span_end = int(float(mention.span.split("-")[1])) - 1 if "-" in mention.span else span_start
                    entity_mention_offsets.append([span_start, span_end])
                    entity_mentions.append(" ".join([word.form for word in mention.words]))
                if sequential_ids:
                    if entity.eid not in eids:
                        eids[entity.eid] = f"e{len(eids) + 1}"
                    eid = eids[entity.eid]
                else:
                    eid = entity.eid
                clusters_token_offsets.append(entity_mention_offsets)
                clusters_text_mentions.append(entity_mentions)
        output_data.append({
            "doc_id": doc.meta["docname"],
            "tokens": out_words,
            "clusters_token_offsets": clusters_token_offsets,
            "clusters_text_mentions": clusters_text_mentions
        })
    pretty_json_str = pprint.pformat(output_data, compact=True, sort_dicts=False).replace("'",'"')
    formatter = Formatter()
    formatter.dump(output_data, out_file)
    # with open(out_file, "w", encoding="utf-8") as f:
        # f.write(pretty_json_str)
        # json.dump(output_data, f, indent=2, ensure_ascii=False)

def convert_conllu_file_to_json(filename, output_filename, zero_mentions, blind=False, sequential_ids=True):
    if not output_filename:
        output_filename = filename.replace(".conllu", ".json")
    docs = read_data(filename)
    convert_to_json(docs, output_filename, zero_mentions, not blind, sequential_ids)

def convert_json_to_conllu(json_filename, conllu_skeleton_filename, output_filename, use_gold_empty_nodes=True):
    import json
    from .convert import read_data, write_data, remove_empty_node
    from udapi.core.document import Document
    from udapi.block.corefud.movehead import MoveHead

    with open(json_filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    udapi_docs = read_data(conllu_skeleton_filename)
    move_head = MoveHead()
    for doc in udapi_docs:
        doc._eid_to_entity = {}
    assert len(udapi_docs) == len(data)
    for doc, udapi_doc in zip(data, udapi_docs):
        words = doc["tokens"]
        udapi_words = [word for word in udapi_doc.nodes]
        for word in udapi_doc.nodes_and_empty:
            word.misc = {}
            # Remove empty nodes
            if not use_gold_empty_nodes and word.is_empty():
                remove_empty_node(word)
        if not use_gold_empty_nodes:
            j = 1
            for i in range(len(udapi_words)):
                word = udapi_words[i]
                while j < len(words) and words[j].startswith("##"):
                    word.create_empty_child("_", after=True)
                    j += 1
                j += 1
        udapi_words = [word for word in udapi_doc.nodes_and_empty]
        for i in range(len(udapi_words)):
            if udapi_words[i].form != words[i].split("|")[0]:
                logger.warning(f"WARNING: words do not match. DOC: {udapi_doc.meta['docname']}, word1: {words[i].split('|')[0]}, word2: {udapi_words[i].form}, i: {i}")
        # if len(udapi_words) != len(words):
        #     continue
        assert len(udapi_words) == len(words)
        mention_starts = defaultdict(list)
        entities = {}
        for entity in doc["clusters_token_offsets"]:
            eid = f"e{len(entities) + 1}"
            entities[eid] = udapi_doc.create_coref_entity(eid=eid)
            for mention_offsets in entity:
                span_start = mention_offsets[0]
                span_end = mention_offsets[1]
                entities[eid].create_mention(words=udapi_words[span_start: span_end + 1])
        udapi.core.coref.store_coref_to_misc(udapi_doc)
        move_head.run(udapi_doc)
    if not output_filename:
        output_filename = output_filename.replace(".json", ".conllu")
    with open(output_filename, "w", encoding="utf-8") as f:
        write_data(udapi_docs, f)

