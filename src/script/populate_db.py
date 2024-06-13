import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'web_app.settings'
django.setup()

import sys
import logging
from datetime import datetime

from typing import Dict
from argparse import ArgumentParser, Namespace

import yaml

from me_project.data import ChatDataNatCS, ChatDataTweetSumm, ChatDataTeacherStudentChatroomCorpusV2
from me_project.web_utils.utils import *
from llm_cstk.data.utils import UTTERANCES
from search.models import DialogueNatCSModel, DialogueTweetSummModel, DialogueTeacherStudentChatroomModel


DATA_SET_MAPPING: Dict = {
    'natcs': ChatDataNatCS,
    'tweet_summ': ChatDataTweetSumm,
    'tsccv2': ChatDataTeacherStudentChatroomCorpusV2
}
DB_MAPPING: Dict = {
    'natcs': DialogueNatCSModel,
    'tweet_summ': DialogueTweetSummModel,
    'tsccv2': DialogueTeacherStudentChatroomModel
}


def main(args: Namespace):
    # Init environment
    # Get date-time
    date_time: str = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
    # Load configs
    with open(args.config_file_path) as f:
        configs: Dict = yaml.full_load(f)
    # Init logging
    logging.basicConfig(level=configs.get('log_level', 'INFO'))
    # Start Logging info
    logging.info("Script started and configuration file loaded")
    # Iterate over corpora
    for corpus in configs['corpora']:
        logging.info(f'Processing corpus `{corpus}`')
        # Drop existing data
        DB_MAPPING[corpus].objects.all().delete()
        DB_MAPPING[corpus].UTTERANCE_MODEL.objects.all().delete()
        DB_MAPPING[corpus].DOC_MODEL.objects.all().delete()
        DB_MAPPING[corpus].DOC_CHUNK_MODEL.objects.all().delete()
        # Load and pre-process data
        data_set = DATA_SET_MAPPING[corpus](
            *configs['corpora'][corpus]['args'], **configs['corpora'][corpus].get('kwargs', dict())
        )
        # Store structured dialogues
        dialogues = list()
        # Dialogue
        for sample in data_set.data:
            record = DB_MAPPING[corpus](**DB_MAPPING[corpus].parse_sample(sample))
            record.save()
            dialogues.append(record)
        # Dialogue utterances
        for d_idx, sample in enumerate(data_set.data):
            for u_idx, utterance in enumerate(sample[UTTERANCES]):
                record = DB_MAPPING[corpus].UTTERANCE_MODEL(
                    dialogue_id=dialogues[d_idx], utterance_id=u_idx, **utterance
                )
                record.save()
        # Store dialogue documents
        data_set.drop_sys_messages()
        # Docs
        for doc in data_set.to_doc_collection():
            record = DB_MAPPING[corpus].DOC_MODEL(
                dialogue_id=dialogues[doc['docid']], **DB_MAPPING[corpus].DOC_MODEL.parse_sample(doc)
            )
            record.save()
        # Doc chunks
        for doc_chunk in data_set.to_doc_chunk_collection(
                *configs['corpora'][corpus].get('chunking', (CHUNK_SIZE, CHUNK_STRIDE))
        ):
            record = DB_MAPPING[corpus].DOC_CHUNK_MODEL(
                dialogue_id=dialogues[doc_chunk['docid']],
                chunk_id=int(doc_chunk['docno'].split('%p', 1)[1]),
                **DB_MAPPING[corpus].DOC_CHUNK_MODEL.parse_sample(doc_chunk)
            )
            record.save()
    # Conclude script
    logging.info("Process completed successfully")

    return 0


if __name__ == "__main__":
    # Instantiate argument parser
    args_parser: ArgumentParser = ArgumentParser(
        prog='populate_db',
        description='Script to populate the Django demo application DB'
    )
    # Add arguments to parser
    args_parser.add_argument(
        '--config_file_path',
        type=str,
        help="Path to the YAML file containing the configuration for the execution."
    )
    # Run experiment
    main(args_parser.parse_args(sys.argv[1:]))
