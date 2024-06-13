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
from search.models import (
    DialogueNatCSUtteranceModel, DialogueTweetSummUtteranceModel, DialogueTeacherStudentChatroomUtteranceModel
)

import random
from django.db.models import Count, Q

from urllib.parse import urljoin
import json
import requests
from chat.models import (
    SuggestedDialogueNatCSUtteranceModel,
    SuggestedDialogueTweetSummUtteranceModel,
    SuggestedDialogueTeacherStudentChatroomUtteranceModel
)
from chat.models import EvalDialogueNatCSModel, EvalDialogueTweetSummModel, EvalDialogueTeacherStudentChatroomModel
from chat.views import (
    _gather_candidate_responses,
    _gather_relevant_examples,
    _gather_random_examples,
    _gather_relevant_docs
)


DATA_SET_MAPPING: Dict = {
    'natcs': ChatDataNatCS,
    'tweet_summ': ChatDataTweetSumm,
    'tsccv2': ChatDataTeacherStudentChatroomCorpusV2
}
EVAL_MAPPING: Dict = {
    'natcs': EvalDialogueNatCSModel,
    'tweet_summ': EvalDialogueTweetSummModel,
    'tsccv2': EvalDialogueTeacherStudentChatroomModel
}
DB_MAPPING: Dict = {
    'natcs': DialogueNatCSModel,
    'tweet_summ': DialogueTweetSummModel,
    'tsccv2': DialogueTeacherStudentChatroomModel
}


def get_natcs_queryset(n_samples):
    queryset = DialogueNatCSModel.objects.annotate(
        num_speakers=Count(
            'dialoguenatcsutterancegenericmodel__speaker',
            distinct=True,
            filter=Q(dialoguenatcsutterancegenericmodel__polymorphic_ctype__model='dialoguenatcsutterancemodel')
        ),
        num_support_speakers=Count(
            'dialoguenatcsutterancegenericmodel',
            filter=Q(
                dialoguenatcsutterancegenericmodel__polymorphic_ctype__model='dialoguenatcsutterancemodel'
            ) & Q(
                dialoguenatcsutterancegenericmodel__speaker='Agent'
            ) & ~Q(
                dialoguenatcsutterancegenericmodel__sys=True
            )
        )
    ).filter(num_speakers__gte=2, num_support_speakers__gte=3)

    return random.sample(list(queryset), n_samples)


def get_tweet_summ_queryset(n_samples):
    queryset = DialogueTweetSummModel.objects.annotate(
        num_speakers=Count(
            'dialoguetweetsummutterancegenericmodel__speaker',
            distinct=True,
            filter=Q(dialoguetweetsummutterancegenericmodel__polymorphic_ctype__model='dialoguetweetsummutterancemodel')
        ),
        num_support_speakers=Count(
            'dialoguetweetsummutterancegenericmodel',
            filter=Q(
                dialoguetweetsummutterancegenericmodel__polymorphic_ctype__model='dialoguetweetsummutterancemodel'
            ) & ~Q(
                dialoguetweetsummutterancegenericmodel__speaker__startswith='Customer'
            ) & ~Q(
                dialoguetweetsummutterancegenericmodel__sys=True
            )
        )
    ).filter(num_speakers__gte=2, num_support_speakers__gte=3)

    return random.sample(list(queryset), n_samples)


def get_tsccv2_queryset(n_samples):
    queryset = DialogueTeacherStudentChatroomModel.objects.annotate(
        num_speakers=Count(
            'dialogueteacherstudentchatroomutterancegenericmodel__speaker',
            distinct=True,
            filter=Q(dialogueteacherstudentchatroomutterancegenericmodel__polymorphic_ctype__model='dialogueteacherstudentchatroomutterancemodel')
        ),
        num_support_speakers=Count(
            'dialogueteacherstudentchatroomutterancegenericmodel',
            filter=Q(
                dialogueteacherstudentchatroomutterancegenericmodel__polymorphic_ctype__model='dialogueteacherstudentchatroomutterancemodel'
            ) & Q(
                dialogueteacherstudentchatroomutterancegenericmodel__speaker='Teacher'
            ) & ~Q(
                dialogueteacherstudentchatroomutterancegenericmodel__sys=True
            )
        )
    ).filter(num_speakers__gte=2, num_support_speakers__gte=3)

    return random.sample(list(queryset), n_samples)


def get_natcs_idx(dialogue_object: DialogueNatCSModel) -> int:
    dialogue_object.load_utterances()
    idx = random.choice([
        idx for idx, utterance in enumerate(dialogue_object.utterances)
        if utterance.speaker == 'Agent' and not utterance.sys and idx > 0 and len(utterance.text) > 16
    ])

    return idx


def get_tweet_summ_idx(dialogue_object: DialogueTweetSummModel) -> int:
    dialogue_object.load_utterances()
    idx = random.choice([
        idx for idx, utterance in enumerate(dialogue_object.utterances)
        if 'Customer' not in utterance.speaker and not utterance.sys and idx > 0 and len(utterance.text) > 16
    ])

    return idx


def get_tsccv2_idx(dialogue_object: DialogueTeacherStudentChatroomModel) -> int:
    dialogue_object.load_utterances()
    idx = random.choice([
        idx for idx, utterance in enumerate(dialogue_object.utterances)
        if utterance.speaker == 'Teacher' and not utterance.sys and idx > 0 and len(utterance.text) > 16
    ])

    return idx


def _gen_sample(model, chat_settings, dialogue_object, utterance_idx, lm_id, suggestion_model):
    # Gather data for
    dialogue_object.load_doc()
    dialogue_object.load_doc_chunks()
    dialogue = dialogue_object.to_chat_data()
    # Generate response
    params = {
        'utterances': dialogue['utterances'][:utterance_idx],
        'speaker': dialogue['utterances'][utterance_idx]['speaker'],
        'corpus': model.DATA_SET_ID,
        'info': dialogue['info']
    }
    query = reference_doc_ids = None
    if chat_settings['model'] == 'llm':
        # Gather additional data
        # Candidate responses
        if chat_settings['n_candidates'] > 0:
            candidates = _gather_candidate_responses(model, dialogue, utterance_idx, chat_settings['n_candidates'])
            params |= {'candidates': candidates}
        if chat_settings['n_shots'] > 0:
            examples = list(_gather_relevant_examples(
                model,
                dialogue_object,
                dialogue,
                utterance_idx,
                chat_settings['ranking'],
                chat_settings['reranking'],
                chat_settings['n_shots']
            ) if chat_settings.get('relevant_shots', DEFAULT_RELEVANT_SHOTS) else _gather_random_examples(
                model, dialogue_object, chat_settings['n_shots']
            ))
            for example in examples:
                example['utterances'] = example['utterances']
            params |= {'examples': examples}
        # Reference document passages
        if chat_settings['n_docs'] > 0:
            query, reference_doc_ids, reference_docs = _gather_relevant_docs(
                model,
                dialogue_object,
                dialogue,
                utterance_idx,
                chat_settings['ranking'],
                chat_settings['reranking'],
                chat_settings['doc_selection'],
                chat_settings['n_docs']
            )
            params |= {'relevant_documents': reference_docs}
        # Ask LLM for suggestion
        http_response = requests.post(
            urljoin(GENERATOR_SERVICE_URL, RESPONSE_SUGGESTIONS_LLM_PATH), data=json.dumps({'params': params})
        )
    else:
        # Ask fine-tuned (L)LM for suggestion
        http_response = requests.post(
            urljoin(GENERATOR_SERVICE_URL, RESPONSE_SUGGESTIONS_CUSTOM_LM_PATH), data=json.dumps({'params': params})
        )
    response = {'speaker': 'assistant', 'text': f'ERROR -- Message: {utterance_idx + 1}'}
    if http_response.status_code == 200:
        response, *_ = http_response.json()['candidates']

    # Register suggestion object
    suggestion = suggestion_model(
        dialogue_id=dialogue_object,
        utterance_id=utterance_idx,
        speaker=dialogue['utterances'][utterance_idx]['speaker'],
        text=response['text'],
        model=chat_settings['model'],
        n_shots=chat_settings['n_shots'],
        n_candidates=chat_settings['n_candidates'],
        n_docs=chat_settings['n_docs'],
        ranking=chat_settings['ranking'],
        reranking=chat_settings['reranking'],
        doc_selection=chat_settings['doc_selection'],
        relevant_shots=chat_settings.get('relevant_shots', DEFAULT_RELEVANT_SHOTS),
        model_id=lm_id
    )
    suggestion.save()

    return suggestion


def gen_sample_natcs(chat_settings, dialogue_object, utterance_idx, lm_id):
    return _gen_sample(
        DialogueNatCSModel, chat_settings, dialogue_object, utterance_idx, lm_id, SuggestedDialogueNatCSUtteranceModel
    )


def gen_sample_tweet_summ(chat_settings, dialogue_object, utterance_idx, lm_id):
    return _gen_sample(
        DialogueTweetSummModel, chat_settings, dialogue_object, utterance_idx, lm_id, SuggestedDialogueTweetSummUtteranceModel
    )


def gen_sample_tsccv2(chat_settings, dialogue_object, utterance_idx, lm_id):
    return _gen_sample(
        DialogueTeacherStudentChatroomModel, chat_settings, dialogue_object, utterance_idx, lm_id, SuggestedDialogueTeacherStudentChatroomUtteranceModel
    )


DB_VALID_CHATS_SELECTORS: Dict = {
    'natcs': get_natcs_queryset,
    'tweet_summ': get_tweet_summ_queryset,
    'tsccv2': get_tsccv2_queryset
}
DB_VALID_UTTERANCE_SELECTORS: Dict = {
    'natcs': get_natcs_idx,
    'tweet_summ': get_tweet_summ_idx,
    'tsccv2': get_tsccv2_idx
}
DB_SAMPLES_GENERATORS: Dict = {
    'natcs': gen_sample_natcs,
    'tweet_summ': gen_sample_tweet_summ,
    'tsccv2': gen_sample_tsccv2
}


def main(args: Namespace):
    # Init environment
    # Get date-time
    date_time = datetime.now()
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
        # Delete
        EVAL_MAPPING[corpus].objects.all().delete()
        # Gather dialogues
        dialogue_queryset = DB_VALID_CHATS_SELECTORS[corpus](configs['n_samples'])
        # Iterate over dialogues
        for idx, dialogue_object in enumerate(dialogue_queryset):
            dialogue_object.load_utterances()
            # Select utterance randomly
            utterance_idx = DB_VALID_UTTERANCE_SELECTORS[corpus](dialogue_object)
            # Create eval object
            eval_obj = EVAL_MAPPING[corpus](
                dialogue_id=dialogue_object,
                ground_truth_utterance_id=dialogue_object.utterances[utterance_idx],
                eval_created_at=date_time
            )
            eval_obj.save()
            eval_obj.utterance_ids.add(dialogue_object.utterances[utterance_idx])
            # Iterate over models
            for model in configs['models']:
                # Iterate over model configs
                for model_configs in configs['models'][model]['configs']:
                    # Generate suggestion
                    eval_obj.utterance_ids.add(
                        DB_SAMPLES_GENERATORS[corpus](
                            model_configs['chat_settings'] | {'model': model},
                            dialogue_object,
                            utterance_idx,
                            model_configs['config_id']
                        )
                    )
            eval_obj.save()
            logging.info(f"Completed example {idx + 1} / {len(dialogue_queryset)} (corpus {corpus})")
        logging.info(f"Completed processing corpus {corpus})")
    # Conclude script
    logging.info("Process completed successfully")

    return 0


if __name__ == "__main__":
    # Instantiate argument parser
    args_parser: ArgumentParser = ArgumentParser(
        prog='prepare_evaluation_data',
        description='Script to prepare the samples to use in the Django demo application DB'
    )
    # Add arguments to parser
    args_parser.add_argument(
        '--config_file_path',
        type=str,
        help="Path to the YAML file containing the configuration for the execution."
    )
    # Run experiment
    main(args_parser.parse_args(sys.argv[1:]))
