from django.conf import settings
from django.db import models
from search.models import *

# Create your models here.


class SuggestedDialogueUtteranceSettingsModel(models.Model):
    model = models.CharField(choices=MODELS.items(), max_length=MAX_CHAR_LEN)
    n_shots = models.PositiveIntegerField(blank=True, null=True)
    n_candidates = models.PositiveIntegerField(blank=True, null=True)
    n_docs = models.PositiveIntegerField(blank=True, null=True)
    ranking = models.CharField(choices=RANKING_APPROACHES.items(), blank=True, null=True, max_length=MAX_CHAR_LEN)
    reranking = models.CharField(choices=RERANKING_APPROACHES.items(), blank=True, null=True, max_length=MAX_CHAR_LEN)
    doc_selection = models.CharField(DOC_SELECTION_APPROACHES.items(), blank=True, null=True, max_length=MAX_CHAR_LEN)
    relevant_shots = models.BooleanField(blank=True, null=True, default=DEFAULT_RELEVANT_SHOTS)

    model_id = models.CharField(blank=True, null=True, max_length=MAX_CHAR_LEN, default=None)

    class Meta:
        abstract = True


class SuggestedDialogueNatCSUtteranceModel(DialogueNatCSUtteranceGenericModel, SuggestedDialogueUtteranceSettingsModel):
    created_at = models.DateTimeField(auto_now_add=True)


class SuggestedDialogueTweetSummUtteranceModel(
    DialogueTweetSummUtteranceGenericModel, SuggestedDialogueUtteranceSettingsModel
):
    created_at = models.DateTimeField(auto_now_add=True)


class SuggestedDialogueTeacherStudentChatroomUtteranceModel(
    DialogueTeacherStudentChatroomUtteranceGenericModel, SuggestedDialogueUtteranceSettingsModel
):
    created_at = models.DateTimeField(auto_now_add=True)


class UtteranceFeedback(models.Model):
    utterance_id = models.ForeignKey('DialogueUtteranceModel', on_delete=models.CASCADE)
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    feedback = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UtteranceNatCSFeedback(UtteranceFeedback):
    utterance_id = models.ForeignKey('SuggestedDialogueNatCSUtteranceModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'utterance_id')
        ordering = ['user_id', 'utterance_id']
        indexes = [
            models.Index(fields=['user_id', 'utterance_id'],
                         name='user_utterance_feedback_natcs'),
        ]


class UtteranceTweetSummFeedback(UtteranceFeedback):
    utterance_id = models.ForeignKey('SuggestedDialogueTweetSummUtteranceModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'utterance_id')
        ordering = ['user_id', 'utterance_id']
        indexes = [
            models.Index(fields=['user_id', 'utterance_id'],
                         name='user_utterance_feedback_twt'),
        ]


class UtteranceTeacherStudentChatroomFeedback(UtteranceFeedback):
    utterance_id = models.ForeignKey('SuggestedDialogueTeacherStudentChatroomUtteranceModel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user_id', 'utterance_id')
        ordering = ['user_id', 'utterance_id']
        indexes = [
            models.Index(fields=['user_id', 'utterance_id'],
                         name='user_utterance_feedback_tsccv2'),
        ]


class EvalDialogueModel(models.Model):
    dialogue_id = models.ForeignKey('search.DialogueModel', on_delete=models.CASCADE)
    ground_truth_utterance_id = models.ForeignKey(
        'search.DialogueUtteranceModel', related_name='ground_truth', on_delete=models.CASCADE
    )
    utterance_ids = models.ManyToManyField('search.DialogueUtteranceModel', related_name='utterances')
    eval_created_at = models.DateTimeField()

    class Meta:
        abstract = True


class EvalDialogueNatCSModel(EvalDialogueModel):
    dialogue_id = models.ForeignKey('search.DialogueNatCSModel', on_delete=models.CASCADE)
    ground_truth_utterance_id = models.ForeignKey(
        'search.DialogueNatCSUtteranceModel', related_name='ground_truth', on_delete=models.CASCADE
    )
    utterance_ids = models.ManyToManyField('search.DialogueNatCSUtteranceGenericModel', related_name='utterances')


class EvalDialogueTweetSummModel(EvalDialogueModel):
    dialogue_id = models.ForeignKey('search.DialogueTweetSummModel', on_delete=models.CASCADE)
    ground_truth_utterance_id = models.ForeignKey(
        'search.DialogueTweetSummUtteranceModel', related_name='ground_truth', on_delete=models.CASCADE
    )
    utterance_ids = models.ManyToManyField('search.DialogueTweetSummUtteranceGenericModel', related_name='utterances')


class EvalDialogueTeacherStudentChatroomModel(EvalDialogueModel):
    dialogue_id = models.ForeignKey('search.DialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)
    ground_truth_utterance_id = models.ForeignKey(
        'search.DialogueTeacherStudentChatroomUtteranceModel', related_name='ground_truth', on_delete=models.CASCADE
    )
    utterance_ids = models.ManyToManyField(
        'search.DialogueTeacherStudentChatroomUtteranceGenericModel', related_name='utterances'
    )


class EvalFeedback(models.Model):
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    eval_dialogue_id = models.ForeignKey('EvalDialogueModel', on_delete=models.CASCADE)
    utterance_id = models.ForeignKey('search.DialogueUtteranceGenericModel', on_delete=models.CASCADE)
    feedback = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class EvalNatCSFeedback(EvalFeedback):
    eval_dialogue_id = models.ForeignKey('EvalDialogueNatCSModel', on_delete=models.CASCADE)
    utterance_id = models.ForeignKey('search.DialogueNatCSUtteranceGenericModel', on_delete=models.CASCADE)


class EvalTweetSummFeedback(EvalFeedback):
    eval_dialogue_id = models.ForeignKey('EvalDialogueTweetSummModel', on_delete=models.CASCADE)
    utterance_id = models.ForeignKey('search.DialogueTweetSummUtteranceGenericModel', on_delete=models.CASCADE)


class EvalTeacherStudentChatroomFeedback(EvalFeedback):
    eval_dialogue_id = models.ForeignKey('EvalDialogueTeacherStudentChatroomModel', on_delete=models.CASCADE)
    utterance_id = models.ForeignKey(
        'search.DialogueTeacherStudentChatroomUtteranceGenericModel', on_delete=models.CASCADE
    )
