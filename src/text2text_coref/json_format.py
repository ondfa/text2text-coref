from .convert import shift_empty_node, reduce_discontinuous_mention, is_mwt_start, align_words
import udapi
import json
from udapi.block.corefud.movehead import MoveHead
import logging
from .convert import read_data, write_data
from compact_json import Formatter
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()

def convert_to_json(docs, out_file, solve_empty_nodes=True, mark_entities=True, break_mwt=False):
    output_data = []
    for doc in docs:
        out_words = []
        if solve_empty_nodes:
            for node in doc.nodes_and_empty:
                if node.is_empty():
                    shift_empty_node(node, break_mwt)
            udapi_words = [word for word in doc.nodes_and_empty]
        else:
            udapi_words = [word for word in doc.nodes]
        for word in udapi_words:
            if not break_mwt and word.multiword_token:
                if is_mwt_start(word):
                    out_word = word.multiword_token.form.replace(" ", "_")
                else:
                    continue
            else:
                out_word = word.form.replace(" ", "_")
            if word.is_empty():
                out_word = "##" + (out_word if out_word != "_" else "")  # empty nodes start with ##
            out_words.append(out_word)
        clusters_token_offsets = None
        clusters_text_mentions = None
        if mark_entities:
            udapi_words = [word for word in udapi_words if break_mwt or not word.multiword_token or is_mwt_start(word)]
            node2id = {node: i for i, node in enumerate(udapi_words)}
            clusters_token_offsets = []
            clusters_text_mentions = []
            for entity in doc.coref_entities:
                entity_mentions = []
                entity_mention_offsets = []
                for mention in entity.mentions:
                    if "," in mention.span:
                        reduce_discontinuous_mention(mention)
                    start_node = mention.words[0]
                    if start_node.multiword_token and not break_mwt:
                        start_node = start_node.multiword_token.words[0]
                    end_node = mention.words[-1]
                    if end_node.multiword_token and not break_mwt:
                        end_node = end_node.multiword_token.words[0]
                    span_start = node2id[start_node]
                    span_end = node2id[end_node]
                    entity_mention_offsets.append([span_start, span_end])
                    entity_mentions.append(" ".join([word.form.replace(" ", "_") for word in mention.words]))
                clusters_token_offsets.append(entity_mention_offsets)
                clusters_text_mentions.append(entity_mentions)
        output_data.append({
            "doc_id": doc.meta["docname"],
            "tokens": out_words,
            "clusters_token_offsets": clusters_token_offsets,
            "clusters_text_mentions": clusters_text_mentions
        })
    formatter = Formatter()
    formatter.ensure_ascii = False
    formatter.dump(output_data, out_file)

def convert_conllu_file_to_json(filename, output_filename, zero_mentions, blind=False, break_mwt=False):
    if not output_filename:
        output_filename = filename.replace(".conllu", ".json")
    docs = read_data(filename)
    convert_to_json(docs, output_filename, zero_mentions, not blind, break_mwt)

def convert_json_to_conllu(json_filename, conllu_skeleton_filename, output_filename, use_gold_empty_nodes=True, break_mwt=False):
    with open(json_filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    udapi_docs = read_data(conllu_skeleton_filename)
    move_head = MoveHead()
    for doc in udapi_docs:
        doc._eid_to_entity = {}
    assert len(udapi_docs) == len(data)
    for doc, udapi_doc in zip(data, udapi_docs):
        words = doc["tokens"]
        align_words(udapi_doc, words, use_gold_empty_nodes, break_mwt)
        udapi_words_without_mwt = [word for word in udapi_doc.nodes_and_empty if not word.multiword_token or break_mwt or is_mwt_start(word)]
        entities = {}
        for entity in doc["clusters_token_offsets"]:
            eid = f"e{len(entities) + 1}"
            entities[eid] = udapi_doc.create_coref_entity(eid=eid)
            for mention_offsets in entity:
                span_start = udapi_words_without_mwt[mention_offsets[0]]
                if span_start.multiword_token and not break_mwt:
                    span_start = span_start.multiword_token.words[0]
                span_end = udapi_words_without_mwt[mention_offsets[1]]
                if span_end.multiword_token and not break_mwt:
                    span_end = span_end.multiword_token.words[-1]
                entities[eid].create_mention(span=f"{span_start.ord}-{span_end.ord}", head=span_start)
        udapi.core.coref.store_coref_to_misc(udapi_doc)
        move_head.run(udapi_doc)
    if not output_filename:
        output_filename = output_filename.replace(".json", ".conllu")
    with open(output_filename, "w", encoding="utf-8") as f:
        write_data(udapi_docs, f)
