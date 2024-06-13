import os
import sys
from argparse import ArgumentParser, Namespace
import logging

import yaml

from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer, CrossEncoder

from typing import Dict


def main(args: Namespace):
    # Init environment
    # Load configs
    with open(args.config_file_path) as f:
        configs: Dict = yaml.full_load(f)
    # Init logging
    logging.basicConfig(level='INFO')
    # Start Logging info
    logging.info("Script started and configuration file loaded")
    # HuggingFace pre-trained models
    if 'models' in configs:
        for model_id, model in configs['models'].items():
            AutoTokenizer.from_pretrained(
                model, use_auth_token=configs.get('use_auth_token')
            ).save_pretrained(os.path.join(configs['model_dir_path'], model_id))
            AutoModelForCausalLM.from_pretrained(
                model, use_auth_token=configs.get('use_auth_token')
            ).save_pretrained(os.path.join(configs['model_dir_path'], model_id))
            logging.info(f"Completed `{model}`")
    # Sentence transformers pre-trained models
    if 'sentence_models' in configs:
        if 'bienc' in configs['sentence_models']:
            for model_id, model in configs['sentence_models']['bienc'].items():
                SentenceTransformer(model).save(os.path.join(configs['model_dir_path'], model_id))
                logging.info(f"Completed `{model}`")
        if 'xenc' in configs['sentence_models']:
            for model_id, model in configs['sentence_models']['xenc'].items():
                CrossEncoder(model).save(os.path.join(configs['model_dir_path'], model_id))
                logging.info(f"Completed `{model}`")
    # PyTorch weights checkpoints
    if 'checkpoints' in configs:
        for model_id, model_urls in configs['checkpoints'].items():
            if not os.path.exists(os.path.join(configs['model_dir_path'], model_id)):
                os.mkdir(os.path.join(configs['model_dir_path'], model_id))
            for model_url in model_urls:
                os.system(f"wget {model_url} -P {os.path.join(configs['model_dir_path'], model_id)}")
            logging.info(f"Completed `{model_id}`")
    # Conclude script
    logging.info("Process completed successfully")

    return 0


if __name__ == "__main__":
    # Instantiate argument parser
    args_parser: ArgumentParser = ArgumentParser(
        prog='pre_trained_model_downloader',
        description='Script to download pre-trained large language models'
    )
    # Add arguments to parser
    args_parser.add_argument(
        '--config_file_path',
        type=str,
        help="Path to the YAML file containing the configuration for the execution."
    )
    # Run script
    main(args_parser.parse_args(sys.argv[1:]))
