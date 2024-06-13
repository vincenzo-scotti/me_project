from typing import Optional
import re


# APIs

RETRIEVAL_SERVICE_URL = 'http://me_retrieval:5000'

SEARCH_DOC_PATH = '/search/doc'
SEARCH_DOC_CHUNK_PATH = '/search/doc_chunk'
SEARCH_DOC_LONG_QUERY_PATH = '/search/doc_long_query'
SEARCH_DOC_CHUNK_LONG_QUERY_PATH = '/search/doc_chunk_long_query'

SNIPPET_GENERATE_PATH = '/snippet/generate'
SNIPPET_GENERATE_LONG_QUERY_PATH = '/snippet/generate_long_query'

GENERATOR_SERVICE_URL = 'http://me_generator:5000'

RESPONSE_SUGGESTIONS_CUSTOM_LM_PATH = '/generate/response_suggestion/custom_lm'
RESPONSE_SUGGESTIONS_LLM_PATH = '/generate/response_suggestion/llm'

INFO_EXTRACTION_PATH = '/generate/info_extraction'

QUERY_EXTRACTION = '/generate/query_extraction'
QUERY_RECOGNITION = '/generate/query_recognition'
RELEVANT_DOCUMENT_SELECTION = '/generate/relevant_document_selection'
KB_QA = '/generate/kb_qa'

# Forms data

MAX_CHAR_LEN: int = 128

DATA_SET_IDS = {
    'natcs': 'NatCS', 'tweet_summ': 'TweetSumm', 'tsccv2': 'Teacher-Student Chatroom'
}

RANKING_APPROACHES = {'semantic': 'Semantic', 'lexical': 'Lexical'}
RERANKING_APPROACHES = {None: '', 'semantic': 'Semantic', 'lexical': 'Lexical'}
DOC_SELECTION_APPROACHES = {'semantic': 'Semantic re-scoring', None: 'LLM'}

MODELS = {'llm': 'LLM', 'custom_lm': 'Custom LM'}

UNAME = 'user_name'
PWD = 'password'

EVAL_KEY = 'eval_feedback'

#

QA_CACHE_TIMEOUT = 600

TOP_K_DOCS: int = 8

CHUNK_SIZE: int = 3
CHUNK_STRIDE: int = 2

RELEVANCE_THRESHOLD = 0.5
MAX_REFERENCES = 3

# Session configs

DEFAULT_DATA_SET_ID: str = 'tweet_summ'
DEFAULT_MODEL: str = 'llm'

DEFAULT_RANKING: str = 'semantic'
DEFAULT_RERANKING: Optional[str] = None
DEFAULT_DOC_SELECTION: Optional[str] = 'semantic'

DEFAULT_N_DOCS_QA: int = 3
DEFAULT_N_EXAMPLES_CHAT: int = 3
DEFAULT_N_CANDIDATES_CHAT: int = 0
DEFAULT_N_DOCS_CHAT: int = 0
DEFAULT_RELEVANT_SHOTS: bool = False
