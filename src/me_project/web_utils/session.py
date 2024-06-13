import logging
from .utils import *


def init_session(session, configs_file_path: str = './resources/configs/retrieval_s_old.yml'):
    # Load configs
    # with open(configs_file_path) as f:
    #     session['configs'] = yaml.full_load(f)
    # Search settings
    session['search_settings'] = {
        'data_set_id': DEFAULT_DATA_SET_ID,
        'ranking': DEFAULT_RANKING,
        'reranking': DEFAULT_RERANKING,
        'doc_selection': DEFAULT_DOC_SELECTION
    }
    session['chat_settings'] = {
        'model': DEFAULT_MODEL,
        'n_shots': DEFAULT_N_EXAMPLES_CHAT,
        'n_candidates': DEFAULT_N_CANDIDATES_CHAT,
        'n_docs': DEFAULT_N_DOCS_CHAT,
        'data_set_id': DEFAULT_DATA_SET_ID,
        'ranking': DEFAULT_RANKING,
        'reranking': DEFAULT_RERANKING,
        'doc_selection': DEFAULT_DOC_SELECTION
    }
    session['data_set_id'] = DEFAULT_DATA_SET_ID

    logging.basicConfig(level=logging.INFO)


def update_search_settings(session, settings_form):
    session['search_settings'] = settings_form.get_values_dict()
    session['data_set_id'] = session['search_settings']['data_set_id']


def get_initial_search_settings(session):
    return session['search_settings']


def update_chat_settings(session, settings_form):
    session['chat_settings'] = settings_form.get_values_dict()
    session['data_set_id'] = session['chat_settings']['data_set_id']


def get_initial_chat_settings(session):
    return session['chat_settings']
