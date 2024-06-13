import sys
import logging
from datetime import datetime

from typing import Dict, List
from argparse import ArgumentParser, Namespace

import pandas as pd

import yaml

from me_project.data import ChatDataNatCS, ChatDataTweetSumm, ChatDataTeacherStudentChatroomCorpusV2
from me_project.web_utils.utils import *
from llm_cstk.retrieval import PTDocManager


SPLITS: List[str] = ['train', 'validation', 'test']
DATA_SET_MAPPING: Dict = {
    'natcs': ChatDataNatCS,
    'tweet_summ': ChatDataTweetSumm,
    'tsccv2': ChatDataTeacherStudentChatroomCorpusV2
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
    # Create document manager for retreival
    doc_manager = PTDocManager(configs['retrieval_data_dir_path'])
    # Iterate over corpora
    for corpus in configs['corpora']:
        logging.info(f'Pre-processing corpus `{corpus}`')
        # Iterate over splits
        for split in DATA_SET_MAPPING[corpus].SPLITS:
            logging.info(f'Pre-processing `{split}` split')
            # Prepare pre-processed data split
            data_set = DATA_SET_MAPPING[corpus](
                *configs['corpora'][corpus]['args'], split=split, **configs['corpora'][corpus].get('kwargs', dict())
            )
            data_set.serialise_data(configs['pre_processed_data_dir_path'])
        #
        logging.info(f'Indexing documents `{corpus}`')
        data_set = DATA_SET_MAPPING[corpus](
            *configs['corpora'][corpus]['args'], **(configs['corpora'][corpus].get('kwargs', dict()) | {'holdout': None})
        )
        data_set.drop_sys_messages()
        data_set_docs = data_set.to_doc_collection()
        data_set_doc_chunks = data_set.to_doc_chunk_collection(
            *configs['corpora'][corpus].get('chunking', (CHUNK_SIZE, CHUNK_STRIDE))
        )
        doc_manager.register_corpus(
            corpus, pd.DataFrame(data_set_docs), docs_chunked=pd.DataFrame(data_set_doc_chunks)
        )
        doc_manager.index_corpus(corpus, transformers=configs['index']['semantic'])
        logging.info(f'Completed pre-processing corpus `{corpus}`')
    # Conclude script
    logging.info("Process completed successfully")

    return 0


if __name__ == "__main__":
    # Instantiate argument parser
    args_parser: ArgumentParser = ArgumentParser(
        prog='pre_process_data',
        description='Script to pre-process the available data sets'
    )
    # Add arguments to parser
    args_parser.add_argument(
        '--config_file_path',
        type=str,
        help="Path to the YAML file containing the configuration for the execution."
    )
    # Run experiment
    main(args_parser.parse_args(sys.argv[1:]))
