import re
import json

from llm_cstk.data.utils import *
from llm_cstk.data.utils import _RetrievalChatData


SUPPORT_FEEDBACK: str = 'support_feedback'
REPORT: str = 'report'


class ChatDataNatCS(_RetrievalChatData):
    DATA_SET_ID = 'natcs'
    SPLITS: List[str] = [DEV, TEST]

    DATA_FILE: str = 'dialogues.jsonl'
    DEV_DIR_REL_PATH: str = 'dstc11/development'
    TEST_DIR_REL_PATHS: List[str] = ['dstc11/test-banking', 'dstc11/test-finance']

    DIALOGUE_ID: str = 'dialogue_id'
    TURNS: str = 'turns'
    SPEAKER: str = 'speaker_role'
    TEXT: str = 'utterance'

    ABSTRACT_DEFAULT: str = 'Not available'

    def _preprocess_utterance(self, utt: Dict, *args, **kwargs) -> Dict[str, str]:
        utterance: Dict[str, str] = {
            SPEAKER: utt[self.SPEAKER], SYSTEM_FLAG: False, TEXT: self._preprocess_text(utt[self.TEXT])
        }

        return utterance

    def _preprocess_metadata(self, *args, **kwargs) -> str:
        return self.ABSTRACT_DEFAULT

    def _preprocess_dialogue(self, dialogue_data: Dict, *args, **kwargs) -> Dict[str, Union[str, Dict[str, Union[str, bool]]]]:
        # Compose dialogue dict
        dialogue: Dict[str, Union[str, Dict[str, str]]] = {
            SPLIT: self.split,  # TODO check this
            DATA_SET_ID: self.DATA_SET_ID,
            DIALOGUE_ID: dialogue_data[self.DIALOGUE_ID],
            INFO: self._preprocess_metadata(dialogue_data),
            UTTERANCES: [
                self._preprocess_utterance(utterance) for utterance in dialogue_data[self.TURNS]
            ],
            TITLE: f'NatCS Chat {dialogue_data[self.DIALOGUE_ID]}'
        }

        return dialogue

    def _load_jsonl(self) -> List[Dict]:
        data = []
        # Load dev split
        if self.split is None or self.split == DEV:
            with open(os.path.join(self.path, self.DEV_DIR_REL_PATH, self.DATA_FILE), 'r') as f:
                data += [json.loads(line) for line in f]
        # Load test split
        if self.split is None or self.split == TEST:
            for dir_rel_path in self.TEST_DIR_REL_PATHS:
                with open(os.path.join(self.path, dir_rel_path, self.DATA_FILE), 'r') as f:
                    data += [json.loads(line) for line in f]

        return data

    def _load_samples(self) -> List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]]:
        # Load samples from JSONL
        raw_data: List[Dict] = self._load_jsonl()
        # Preprocess dialogues
        with parallel_backend(self.JOBLIB_BACKEND, n_jobs=self.N_JOBS):
            data: List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]] = Parallel(verbose=self.VERBOSITY_LEVEL)(
                delayed(self._preprocess_dialogue)(dialogue_dict) for dialogue_dict in raw_data
            )

        return data

    def to_doc_chunk_collection(self, size: int, stride: int, path: Optional[str] = None) -> List[Dict]:
        with parallel_backend(self.JOBLIB_BACKEND, n_jobs=self.N_JOBS):
            docs: List[Dict] = Parallel(verbose=self.VERBOSITY_LEVEL)(
                delayed(self._sample_to_doc_chunk)(
                    sample, d_idx, c_idx, s_idx, min(s_idx + size, len(sample[UTTERANCES]))
                )
                for d_idx, sample in enumerate(self.data)
                for c_idx, s_idx in enumerate(range(0, len(sample[UTTERANCES]), stride))  # , start=1)
            )

        if path is not None:
            pd.DataFrame(docs).to_csv(path)

        return docs

    def drop_sys_messages(self):
        pass


class ChatDataTweetSumm(_RetrievalChatData):
    DATA_SET_ID = 'tweet_summ'

    METADATA_FILE_PATH: str = 'tweet_sum_data_files'
    METADATA_FILE_MAPPING: Dict[str, str] = {
        split: f'final_{split_id}_tweetsum.jsonl'
        for split, split_id in zip([TRAIN, VALIDATION, TEST], ['train', 'valid', 'test'])
    }
    DATA_FILE_PATH: str = 'twcs'
    DATA_FILE_NAME: str = 'twcs.csv'

    REF_REGEX: Pattern[str] = re.compile(r'@\w+')
    CUSTOMER_REGEX: Pattern[str] = re.compile(r'\d+')

    CUSTOMER_FORMAT: str = 'Customer {}'
    SUPPORT: str = 'Support'

    DIALOGUE_ID: str = 'conversation_id'
    SENTENCES: str = 'tweet_ids_sentence_offset'
    TWEET_ID: str = 'tweet_id'
    ANNOTATIONS: str = 'annotations'
    ABSTRACTIVE: str = 'abstractive'
    DATE: str = 'created_at'
    SPEAKER_NAME: str = 'author_id'
    TEXT: str = 'text'

    BRAND: str = 'brand'

    ABSTRACT_DEFAULT: str = 'Not available'

    def __init__(self, data_path, metadata_path, **kwargs):
        self.metadata_path = metadata_path
        super(ChatDataTweetSumm, self).__init__(data_path, **kwargs)

    def _preprocess_text(self, text: str) -> str:
        text = self.REF_REGEX.sub('', text)
        text = super(ChatDataTweetSumm, self)._preprocess_text(text)

        return text

    def _preprocess_utterance(self, utt: pd.Series, *args, **kwargs) -> Dict[str, str]:
        utterance: Dict[str, str] = {
            SPEAKER: (
                f'Customer {utt[self.SPEAKER_NAME]}'
                if self.CUSTOMER_REGEX.match(utt[self.SPEAKER_NAME]) is not None
                else utt[self.SPEAKER_NAME].replace('_', '')
            ),
            SYSTEM_FLAG: False,
            TEXT: self._preprocess_text(utt[self.TEXT])
        }

        return utterance

    def _preprocess_metadata(self, meta: Dict, *args, **kwargs) -> str:
        date = meta[self.DATE]
        brand: str = meta[self.BRAND].replace('_', ' ')
        abstract = self.ABSTRACT_DEFAULT
        idx = 0
        while idx < len(meta[self.ANNOTATIONS]) and abstract == self.ABSTRACT_DEFAULT:
            summ = meta[self.ANNOTATIONS][idx]
            if summ[self.ABSTRACTIVE] is not None and len(summ[self.ABSTRACTIVE]) > 0:
                abstract = '\n'.join(summ[self.ABSTRACTIVE])
            idx += 1

        metadata = f'Customer care on Twitter -- Date {date}\n\n' \
                   f'Brand: {brand}\n\n' \
                   f'Abstract:\n{abstract}'

        return metadata

    def _complete_metadata(self, partial_metadata: Dict, raw_data: pd.DataFrame) -> Dict:
        date = raw_data.iloc[0][self.DATE]
        brand = raw_data[
            ~raw_data.apply(lambda x: self.CUSTOMER_REGEX.match(x[self.SPEAKER_NAME]) is not None, axis=1)
        ].iloc[0][self.SPEAKER_NAME]
        metadata = partial_metadata | {self.DATE: date, self.BRAND: brand}

        return metadata

    def _preprocess_dialogue(
            self, metadata: Dict, raw_data: pd.DataFrame, *args, **kwargs
    ) -> Dict[str, Union[str, Dict[str, Union[str, bool]]]]:
        df = raw_data.loc[[tweet[self.TWEET_ID] for tweet in metadata[self.SENTENCES]]]
        metadata = self._complete_metadata(metadata, df)

        dialogue: Dict[str, Union[str, Dict[str, str]]] = {
            SPLIT: self.split,
            DATA_SET_ID: self.DATA_SET_ID,
            DIALOGUE_ID: metadata[self.DIALOGUE_ID],
            INFO: self._preprocess_metadata(metadata),
            UTTERANCES: [
                self._preprocess_utterance(utterance) for _, utterance in df.iterrows()
            ],
            TITLE: f'Customer Care Chat {metadata[self.DIALOGUE_ID]}'
        }

        return dialogue

    def _load_data_frame(self) -> pd.DataFrame:
        # Load data frame
        df = pd.read_csv(os.path.join(self.path, self.DATA_FILE_PATH, self.DATA_FILE_NAME), index_col=self.TWEET_ID)
        # TODO preprocess NaN values in a better way
        df[self.DATE] = pd.to_datetime(df[self.DATE], format='%a %b %d %H:%M:%S %z %Y')

        return df

    def _load_meta_jsonl(self) -> List[Dict]:
        metadata: List[Dict] = []
        for split, file_name in self.METADATA_FILE_MAPPING.items():
            if self.split is None or self.split == split:
                with open(os.path.join(self.metadata_path, self.METADATA_FILE_PATH, file_name)) as f:
                    metadata += [json.loads(line) for line in f]

        return metadata

    def _load_samples(self) -> List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]]:
        # Load JSONL
        metadata: List[Dict] = self._load_meta_jsonl()
        # Load data frame
        raw_data: pd.DataFrame = self._load_data_frame()
        # Preprocess dialogues
        with parallel_backend(self.JOBLIB_BACKEND, n_jobs=self.N_JOBS):
            data: List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]] = Parallel(verbose=self.VERBOSITY_LEVEL)(
                delayed(self._preprocess_dialogue)(dialogue_metadata, raw_data) for dialogue_metadata in metadata
            )

        return data

    def drop_sys_messages(self):
        pass


class ChatDataTeacherStudentChatroomCorpusV2(_RetrievalChatData):
    DATA_SET_ID = 'tsccv2'

    SEP = '\t'
    #
    METADATA_FILE: str = 'teacherStudentChatroomCorpusPublicMetadata.csv'
    FILE_NAME: str = 'filename'
    DIALOGUE_ID: str = 'chat.num'
    DATE: str = 'start.time'
    LEVEL: str = 'student.cefr.level'
    MOTHER_TONGUE: str = 'student.L1'
    #
    SPEAKER: str = 'role'
    TEXT: str = 'edited'

    def __init__(self, *args, holdout: Optional[Union[float, int]] = 0.1, **kwargs):
        super(ChatDataTeacherStudentChatroomCorpusV2, self).__init__(*args, holdout=holdout, **kwargs)

    def _preprocess_utterance(self, utt: pd.Series, *args, **kwargs) -> Dict[str, str]:
        utterance: Dict[str, str] = {
            SPEAKER: utt[self.SPEAKER].capitalize(), SYSTEM_FLAG: False, TEXT: self._preprocess_text(utt[self.TEXT])
        }

        return utterance

    def _preprocess_metadata(self, metadata: pd.Series, *args, **kwargs) -> str:
        date = metadata[self.DATE]
        lvl = metadata[self.LEVEL]
        lang = metadata[self.MOTHER_TONGUE]

        metadata = f'Teacher-student English study chat -- Date: {date}\n\n' \
                   f'Student info:\n' \
                   f'- Mother tongue: {lang}\n' \
                   f'- English certification level: {lvl}'


        return metadata

    def _preprocess_dialogue(
            self,  metadata: pd.Series, *args, **kwargs
    ) -> Dict[str, Union[str, Dict[str, Union[str, bool]]]]:
        df = pd.read_csv(os.path.join(self.path, metadata[self.FILE_NAME]), sep=self.SEP)

        dialogue: Dict[str, Union[str, Dict[str, str]]] = {
            SPLIT: self.split,
            DATA_SET_ID: self.DATA_SET_ID,
            DIALOGUE_ID: metadata[self.DIALOGUE_ID],
            INFO: self._preprocess_metadata(metadata),
            UTTERANCES: [
                self._preprocess_utterance(utterance) for _, utterance in df.iterrows()
            ],
            TITLE: f'Teacher-Student Chat {metadata[self.DIALOGUE_ID]}'
        }

        return dialogue

    def _load_meta_data_frame(self) -> pd.DataFrame:
        # Load data frame
        df = pd.read_csv(os.path.join(self.path, self.METADATA_FILE))
        df[self.DATE] = pd.to_datetime(df[self.DATE], format='%Y-%m-%d %H:%M:%S')

        return df

    def _load_samples(self) -> List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]]:
        # Load metadata data frame
        df: pd.DataFrame = self._load_meta_data_frame()
        # Get dialogue IDs
        dialogue_ids = df[self.DIALOGUE_ID].unique()
        # Select current split indices
        idxs: List[int] = self._get_split_indices(len(dialogue_ids))
        idxs = self._get_sample_indices(idxs)
        # Filter dialogue IDs
        dialogue_ids = dialogue_ids[idxs]
        df = df[df[self.DIALOGUE_ID].isin(dialogue_ids)]
        # Preprocess dialogues
        with parallel_backend(self.JOBLIB_BACKEND, n_jobs=self.N_JOBS):
            data: List[Dict[str, Union[str, Dict[str, Union[str, bool]]]]] = Parallel(verbose=self.VERBOSITY_LEVEL)(
                delayed(self._preprocess_dialogue)(metadata) for _, metadata in df.iterrows()
            )

        return data

    def drop_sys_messages(self):
        pass
