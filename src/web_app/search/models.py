import logging
from django.conf import settings

from django.db import models
from polymorphic.models import PolymorphicModel
from django.shortcuts import reverse

from datetime import datetime

from typing import List, Dict, Pattern

from me_project.data.corpora import DATA_SET_ID, DIALOGUE_ID, INFO, UTTERANCES, SUPPORT_FEEDBACK, REPORT
from me_project.data.corpora import SPEAKER, SYSTEM_FLAG
from me_project.data.corpora import DOCNO, DOCID, TITLE, BODY, TEXT

from me_project.web_utils.utils import *


# Create your models here.


class QueryModel(models.Model):
    text = models.CharField(max_length=MAX_CHAR_LEN, unique=True)


class SearchModel(models.Model):
    DATA_SET_ID = None

    query_id = models.ForeignKey('QueryModel', on_delete=models.CASCADE)
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class SearchNatCSModel(SearchModel):
    DATA_SET_ID = 'natcs'

    class Meta:
        unique_together = ('query_id', 'user_id')
        ordering = ['query_id', 'user_id']
        indexes = [
            models.Index(fields=['query_id', 'user_id'], name='query_user_natcs'),
        ]


class SearchTweetSummModel(SearchModel):
    DATA_SET_ID = 'tweet_summ'

    class Meta:
        unique_together = ('query_id', 'user_id')
        ordering = ['query_id', 'user_id']
        indexes = [
            models.Index(fields=['query_id', 'user_id'], name='query_user_tweet_summ'),
        ]


class SearchTeacherStudentChatroomModel(SearchModel):
    DATA_SET_ID = 'tsccv2'

    class Meta:
        unique_together = ('query_id', 'user_id')
        ordering = ['query_id', 'user_id']
        indexes = [
            models.Index(fields=['query_id', 'user_id'], name='query_user_tsccv2'),
        ]


class RelevanceFeedback(models.Model):
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    feedback = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Doc2DocRelevanceFeedback(RelevanceFeedback):
    src_dialogue_id = models.ForeignKey('DialogueModel', related_name='src_doc', on_delete=models.CASCADE)
    tgt_dialogue_id = models.ForeignKey('DialogueModel', related_name='tgt_doc', on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Doc2DocNatCSRelevanceFeedback(Doc2DocRelevanceFeedback):
    src_dialogue_id = models.ForeignKey('DialogueNatCSModel', related_name='src_doc', on_delete=models.CASCADE)
    tgt_dialogue_id = models.ForeignKey('DialogueNatCSModel', related_name='tgt_doc', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'src_dialogue_id', 'tgt_dialogue_id')
        ordering = ['user_id', 'src_dialogue_id', 'tgt_dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'src_dialogue_id', 'tgt_dialogue_id'],
                         name='user_dialogue_sim_feedback_ncs'),
        ]


class Doc2DocTweetSummRelevanceFeedback(Doc2DocRelevanceFeedback):
    src_dialogue_id = models.ForeignKey('DialogueTweetSummModel', related_name='src_doc', on_delete=models.CASCADE)
    tgt_dialogue_id = models.ForeignKey('DialogueTweetSummModel', related_name='tgt_doc', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'src_dialogue_id', 'tgt_dialogue_id')
        ordering = ['user_id', 'src_dialogue_id', 'tgt_dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'src_dialogue_id', 'tgt_dialogue_id'],
                         name='user_dialogue_sim_feedback_twt'),
        ]


class Doc2DocTeacherStudentChatroomRelevanceFeedback(Doc2DocRelevanceFeedback):
    src_dialogue_id = models.ForeignKey('DialogueTeacherStudentChatroomModel', related_name='src_doc', on_delete=models.CASCADE)
    tgt_dialogue_id = models.ForeignKey('DialogueTeacherStudentChatroomModel', related_name='tgt_doc', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'src_dialogue_id', 'tgt_dialogue_id')
        ordering = ['user_id', 'src_dialogue_id', 'tgt_dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'src_dialogue_id', 'tgt_dialogue_id'],
                         name='user_dialogue_sim_feedback_tsc'),
        ]


class Doc2QueryRelevanceFeedback(RelevanceFeedback):
    search_id = models.ForeignKey('SearchModel', on_delete=models.CASCADE)
    dialogue_id = models.ForeignKey('DialogueModel', on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Doc2QueryNatCSRelevanceFeedback(Doc2QueryRelevanceFeedback):
    search_id = models.ForeignKey('SearchNatCSModel', on_delete=models.CASCADE)
    dialogue_id = models.ForeignKey('DialogueNatCSModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'search_id', 'dialogue_id')
        ordering = ['user_id', 'search_id', 'dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'search_id', 'dialogue_id'],
                         name='user_query_dialogue_feedbk_ncs'),
        ]


class Doc2QueryTweetSummRelevanceFeedback(Doc2QueryRelevanceFeedback):
    search_id = models.ForeignKey('SearchTweetSummModel', on_delete=models.CASCADE)
    dialogue_id = models.ForeignKey('DialogueTweetSummModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'search_id', 'dialogue_id')
        ordering = ['user_id', 'search_id', 'dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'search_id', 'dialogue_id'],
                         name='user_query_dialogue_feedbk_twt'),
        ]


class Doc2QueryTeacherStudentChatroomRelevanceFeedback(Doc2QueryRelevanceFeedback):
    search_id = models.ForeignKey('SearchTeacherStudentChatroomModel', on_delete=models.CASCADE)
    dialogue_id = models.ForeignKey('DialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'search_id', 'dialogue_id')
        ordering = ['user_id', 'search_id', 'dialogue_id']
        indexes = [
            models.Index(fields=['user_id', 'search_id', 'dialogue_id'],
                         name='user_query_dialogue_feedbk_tsc'),
        ]


class DialogueUtteranceModel(models.Model):
    dialogue_id = models.ForeignKey('DialogueModel', on_delete=models.CASCADE)
    utterance_id = models.IntegerField()
    speaker = models.CharField(max_length=MAX_CHAR_LEN)
    text = models.TextField()
    sys = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def to_chat_data(self):
        return {
            SPEAKER: self.speaker, SYSTEM_FLAG: self.sys, TEXT: self.text
        }


class DialogueNatCSUtteranceGenericModel(PolymorphicModel, DialogueUtteranceModel):
    dialogue_id = models.ForeignKey('search.DialogueNatCSModel', on_delete=models.CASCADE)


class DialogueNatCSUtteranceModel(DialogueNatCSUtteranceGenericModel):
    pass


class DialogueTweetSummUtteranceGenericModel(PolymorphicModel, DialogueUtteranceModel):
    dialogue_id = models.ForeignKey('search.DialogueTweetSummModel', on_delete=models.CASCADE)


class DialogueTweetSummUtteranceModel(DialogueTweetSummUtteranceGenericModel):
    pass


class DialogueTeacherStudentChatroomUtteranceGenericModel(PolymorphicModel, DialogueUtteranceModel):
    dialogue_id = models.ForeignKey('search.DialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)


class DialogueTeacherStudentChatroomUtteranceModel(DialogueTeacherStudentChatroomUtteranceGenericModel):
    pass


class DialogueDocModel(models.Model):
    dialogue_id = models.ForeignKey('DialogueModel', on_delete=models.CASCADE)
    docno = models.CharField(max_length=16, unique=True)
    docid = models.IntegerField()
    title = models.TextField()
    body = models.TextField()

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.title}\n\n{self.body}'

    @classmethod
    def parse_sample(cls, sample: Dict):
        return {
            'docno': str(sample[DOCNO]),
            'docid': sample[DOCID],
            'title': sample[TITLE],
            'body': sample[BODY]
        }

    def to_struct_data(self):
        return {
            DOCNO: self.docno,
            DOCID: self.docid,
            TEXT: str(self),
            TITLE: self.title,
            BODY: self.body
        }


class DialogueNatCSDocModel(DialogueDocModel):
    dialogue_id = models.ForeignKey('DialogueNatCSModel', on_delete=models.CASCADE)


class DialogueTweetSummDocModel(DialogueDocModel):
    dialogue_id = models.ForeignKey('DialogueTweetSummModel', on_delete=models.CASCADE)


class DialogueTeacherStudentChatroomDocModel(DialogueDocModel):
    dialogue_id = models.ForeignKey('DialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)


class DialogueDocChunkModel(DialogueDocModel):
    chunk_id = models.IntegerField()

    class Meta:
        abstract = True


class DialogueNatCSDocChunkModel(DialogueDocChunkModel):
    dialogue_id = models.ForeignKey('DialogueNatCSModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('dialogue_id', 'chunk_id')
        ordering = ['dialogue_id', 'chunk_id']
        indexes = [
            models.Index(fields=['dialogue_id', 'chunk_id'], name='dialogue_chunk_id_natcs'),
        ]


class DialogueTweetSummDocChunkModel(DialogueDocChunkModel):
    dialogue_id = models.ForeignKey('DialogueTweetSummModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('dialogue_id', 'chunk_id')
        ordering = ['dialogue_id', 'chunk_id']
        indexes = [
            models.Index(fields=['dialogue_id', 'chunk_id'], name='dialogue_chunk_id_tweet_summ'),
        ]


class DialogueTeacherStudentChatroomDocChunkModel(DialogueDocChunkModel):
    dialogue_id = models.ForeignKey('DialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('dialogue_id', 'chunk_id')
        ordering = ['dialogue_id', 'chunk_id']
        indexes = [
            models.Index(fields=['dialogue_id', 'chunk_id'], name='dialogue_chunk_id_tsccv2'),
        ]


class DialogueModel(models.Model):
    UTTERANCE_MODEL = DialogueUtteranceModel
    DOC_MODEL = DialogueDocModel
    DOC_CHUNK_MODEL = DialogueDocChunkModel

    DATA_SET_ID = None

    DATA_SET_ID_CHOICES = {
        'S': 'S', 'N': 'N', 'L': 'L', 'natcs': 'natcs', 'tweet_summ': 'tweet_summ', 'tsccv2': 'tsccv2'
    }

    data_set_id = models.CharField(max_length=16, choices=DATA_SET_ID_CHOICES.items())
    date = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #
        self.utterances: Optional[List[DialogueUtteranceModel]] = None
        self.doc: Optional[DialogueDocModel] = None
        self.doc_chunks: Optional[List[DialogueDocChunkModel]] = None
        # Placeholders for additional info
        self.score: Optional[float] = None
        self.rank: Optional[int] = None
        self.snippet: Optional[str] = None

    def get_absolute_url(self):
        return reverse('details', args=[str(self.pk)])

    @classmethod
    def parse_sample(cls, sample: Dict) -> Dict:
        raise NotImplementedError()

    @classmethod
    def get_from_doc_id(cls, docno: str):
        return cls.objects.get(pk=cls.DOC_MODEL.objects.filter(docno=docno)[0].dialogue_id.pk)

    def get_doc_id(self):
        self.load_doc()

        return self.doc.docno

    @classmethod
    def get_from_doc_chunk_id(cls, docno: str):
        return cls.objects.get(pk=cls.DOC_CHUNK_MODEL.objects.filter(docno=docno)[0].dialogue_id.pk)

    def get_doc_chunk_ids(self):
        self.load_doc_chunks()

        return [chunk.docno for chunk in self.doc_chunks]

    def load_utterances(self):
        if self.utterances is None:
            self.utterances = self.UTTERANCE_MODEL.objects.filter(dialogue_id=self.pk)

    def load_doc(self):
        if self.doc is None:
            self.doc = self.DOC_MODEL.objects.filter(dialogue_id=self.pk)[0]

    def load_doc_chunks(self):
        if self.doc_chunks is None:
            self.doc_chunks = self.DOC_CHUNK_MODEL.objects.filter(dialogue_id=self.pk)

    def to_chat_data(self) -> Dict:
        raise NotImplementedError()

    def to_doc(self) -> str:
        self.load_doc()

        return str(self.doc)

    def to_doc_chunks(self) -> List[str]:
        self.load_doc_chunks()

        return [str(doc_chunk) for doc_chunk in self.doc_chunks]


class DialogueNatCSModel(DialogueModel):
    UTTERANCE_MODEL = DialogueNatCSUtteranceModel
    DOC_MODEL = DialogueNatCSDocModel
    DOC_CHUNK_MODEL = DialogueNatCSDocChunkModel

    DATA_SET_ID = 'natcs'

    _INFO_REGEX: Pattern[str] = re.compile(
        r'(NatCS Chat (.+))'
    )

    dialogue_id = models.CharField(max_length=16, unique=True)
    dialogue_title = models.TextField()

    def get_absolute_url(self):
        return reverse('details_natcs', args=[str(self.pk)])

    @classmethod
    def parse_sample(cls, sample: Dict):
        dialogue_title, dialogue_id = cls._INFO_REGEX.findall(sample[TITLE])[0]
        date = None

        return {
            'data_set_id': cls.DATA_SET_ID,
            'date': date,
            'dialogue_id': dialogue_id,
            'dialogue_title': dialogue_title
        }

    def to_chat_data(self):
        self.load_utterances()
        info = None

        return {
            DATA_SET_ID: self.data_set_id,
            DIALOGUE_ID: self.dialogue_id,
            INFO: info,
            UTTERANCES: [utterance.to_chat_data() for utterance in self.utterances],
            TITLE: self.dialogue_title,
        }


class DialogueTweetSummModel(DialogueModel):
    UTTERANCE_MODEL = DialogueTweetSummUtteranceModel
    DOC_MODEL = DialogueTweetSummDocModel
    DOC_CHUNK_MODEL = DialogueTweetSummDocChunkModel

    DATA_SET_ID = 'tweet_summ'

    _INFO_REGEX: Pattern[str] = re.compile(
        r'Customer care on Twitter -- Date (.+)\n\n'
        r'Brand: ([\w\W]+)\n\n'
        r'Abstract:\n([\w\W]+)'
    )

    dialogue_id = models.CharField(max_length=64, unique=True)
    dialogue_title = models.TextField()
    brand = models.CharField(max_length=16)
    abstract = models.TextField()

    def get_absolute_url(self):
        return reverse('details_tweet_summ', args=[str(self.pk)])

    @classmethod
    def parse_sample(cls, sample: Dict):
        dialogue_id = sample[DIALOGUE_ID]
        dialogue_title = sample[TITLE]
        date, brand, abstract = cls._INFO_REGEX.findall(sample[INFO])[0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S%z')

        return {
            'data_set_id': cls.DATA_SET_ID,
            'date': date,
            'dialogue_id': dialogue_id,
            'dialogue_title': dialogue_title,
            'brand': brand,
            'abstract': abstract
        }

    def to_chat_data(self):
        self.load_utterances()
        info = f'Customer care on Twitter -- Date {self.date}\n\n' \
               f'Brand: {self.brand}\n\n' \
               f'Abstract:\n{self.abstract}'

        return {
            DATA_SET_ID: self.data_set_id,
            DIALOGUE_ID: self.dialogue_id,
            INFO: info,
            UTTERANCES: [utterance.to_chat_data() for utterance in self.utterances],
            TITLE: self.dialogue_title
        }


class DialogueTeacherStudentChatroomModel(DialogueModel):
    UTTERANCE_MODEL = DialogueTeacherStudentChatroomUtteranceModel
    DOC_MODEL = DialogueTeacherStudentChatroomDocModel
    DOC_CHUNK_MODEL = DialogueTeacherStudentChatroomDocChunkModel

    DATA_SET_ID = 'tsccv2'

    _INFO_REGEX: Pattern[str] = re.compile(
        r'Teacher-student English study chat -- Date: (.+)\n\n'
        r'Student info:\n'
        r'- Mother tongue: ([\w\W]+)\n'
        r'- English certification level: ([\w\W]+)'
    )

    dialogue_id = models.CharField(max_length=16, unique=True)
    dialogue_title = models.TextField()
    lang = models.CharField(max_length=16)
    lvl = models.CharField(max_length=16)

    def get_absolute_url(self):
        return reverse('details_tsccv2', args=[str(self.pk)])

    @classmethod
    def parse_sample(cls, sample: Dict):
        dialogue_id = sample[DIALOGUE_ID]
        dialogue_title = sample[TITLE]
        date, lang, lvl = cls._INFO_REGEX.findall(sample[INFO])[0]
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

        return {
            'data_set_id': cls.DATA_SET_ID,
            'date': date,
            'dialogue_id': dialogue_id,
            'dialogue_title': dialogue_title,
            'lang': lang,
            'lvl': lvl
        }

    def to_chat_data(self):
        self.load_utterances()
        info = f'Teacher-student English study chat -- Date: {self.date}\n\n' \
               f'Student info:\n' \
               f'- Mother tongue: {self.lang}\n' \
               f'- English certification level: {self.lvl}'

        return {
            DATA_SET_ID: self.data_set_id,
            DIALOGUE_ID: self.dialogue_id,
            INFO: info,
            UTTERANCES: [utterance.to_chat_data() for utterance in self.utterances],
            TITLE: self.dialogue_title,
        }

