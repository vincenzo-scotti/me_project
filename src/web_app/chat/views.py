from django.shortcuts import render, redirect, HttpResponse
from urllib.parse import urljoin
import json
import requests

from django.contrib.auth.decorators import login_required

import random
from django.db.models import Count, Q

from .forms import ChatSettingsForm, LoginForm, ChatSuggestionFeedbackForm
from .models import DialogueModel, DialogueNatCSModel, DialogueTweetSummModel, DialogueTeacherStudentChatroomModel
from .models import DialogueUtteranceModel
from .models import (
    SuggestedDialogueNatCSUtteranceModel,
    SuggestedDialogueTweetSummUtteranceModel,
    SuggestedDialogueTeacherStudentChatroomUtteranceModel
)
from .models import (
    EvalDialogueNatCSModel, EvalDialogueTweetSummModel, EvalDialogueTeacherStudentChatroomModel
)
from .models import (
    UtteranceFeedback, UtteranceNatCSFeedback, UtteranceTweetSummFeedback, UtteranceTeacherStudentChatroomFeedback
)
from .models import EvalNatCSFeedback, EvalTweetSummFeedback, EvalTeacherStudentChatroomFeedback

from typing import Type, Dict

from me_project.web_utils import update_chat_settings, get_initial_chat_settings
from me_project.web_utils.utils import *


def _gather_candidate_responses(model, dialogue, utterance_idx, n_candidates):
    params = {
        'utterances': dialogue['utterances'][:utterance_idx],
        'speaker': dialogue['utterances'][utterance_idx]['speaker'],
        'corpus': model.DATA_SET_ID,
        'info': dialogue['info'],
        'n_samples': n_candidates
    }
    # Ask fine-tuned (L)LM for suggestion
    http_response = requests.post(
        urljoin(GENERATOR_SERVICE_URL, RESPONSE_SUGGESTIONS_CUSTOM_LM_PATH), data=json.dumps({'params': params})
    )
    if http_response.status_code == 200:
        response = http_response.json()['candidates']
    else:
        return None
    candidates = [utterance['text'] for utterance in response]

    return candidates


def _get_query_chunks(dialogue, utterance_idx):
    filtered_utterances = [
        utterance for utterance in dialogue['utterances'][:utterance_idx] if not utterance['sys']
    ]
    chunks = [dialogue['info']]
    for idx in range(0, len(filtered_utterances), CHUNK_STRIDE):
        chunk = dialogue['title'] + (
            '\n\n(...)\n\n' if idx > 0 else '\n\n'
        ) + '\n\n'.join(
            f"'- {utterance['speaker']}: {utterance['text']}'"
            for utterance in filtered_utterances[idx:idx + CHUNK_SIZE]
        ) + (
            '\n\n(...)' if idx + CHUNK_SIZE < len(filtered_utterances) else ''
        )
        chunks.append(chunk)

    return chunks


def _gather_relevant_examples(model, dialogue_model, dialogue, utterance_idx, ranking, reranking, n_shots):
    query = _get_query_chunks(dialogue, utterance_idx)
    params: Dict = {
        'query': query, 'corpus': model.DATA_SET_ID, 'ranking': ranking, 'reranking': reranking
    }
    url = urljoin(RETRIEVAL_SERVICE_URL, SEARCH_DOC_LONG_QUERY_PATH)
    # Run query
    http_response = requests.post(url, data=json.dumps({'params': params}))
    if http_response.status_code == 200:
        search_results = http_response.json()
        try:
            idx = search_results['docno'].index(dialogue_model.get_doc_id())
            search_results['docno'].pop(idx)
            search_results['score'].pop(idx)
        except ValueError:
            pass
    else:
        return None
    # Gather relevant examples
    dialogue_ids = search_results['docno'][:n_shots]

    # return dialogues
    return (model.get_from_doc_id(dialogue_id).to_chat_data() for dialogue_id in dialogue_ids)


def _gather_random_examples(model, dialogue_model, n_shots):
    # Gather random examples
    example_dialogue_queryset = model.objects.exclude(pk=dialogue_model.pk).order_by('?')[:n_shots]

    # return dialogues
    return (example_dialogue.to_chat_data() for example_dialogue in example_dialogue_queryset)


def _gather_relevant_docs(
        model, dialogue_model, dialogue, utterance_idx, ranking, reranking, doc_selection_reranking, n_docs
):
    # Run query extraction
    snippet = _get_query_chunks(dialogue, utterance_idx)[-1]
    params = {
        'snippet': snippet, 'corpus': model.DATA_SET_ID
    }
    http_response = requests.post(
        urljoin(GENERATOR_SERVICE_URL, QUERY_EXTRACTION), data=json.dumps({'params': params})
    )
    if http_response.status_code == 200:
        response = http_response.json()['response']

    else:
        return None, None, None
    if response['text'].strip() == 'None.':
        return None, None, None
    else:
        query = response['text']
    # Search relevant documents
    params = {
        'query': query,
        'corpus': model.DATA_SET_ID,
        'ranking': ranking,
        'reranking': doc_selection_reranking if doc_selection_reranking is not None else reranking
    }
    http_response = requests.post(
        urljoin(RETRIEVAL_SERVICE_URL, SEARCH_DOC_CHUNK_PATH), data=json.dumps({'params': params})
    )
    if http_response.status_code == 200:
        search_results = http_response.json()
        for doc_chunk_id in dialogue_model.get_doc_chunk_ids():
            try:
                idx = search_results['docno'].index(doc_chunk_id)
                search_results['docno'].pop(idx)
                search_results['score'].pop(idx)
            except ValueError:
                pass
    else:
        return None, None, None
    docnos = search_results['docno'][:TOP_K_DOCS]
    queryset = model.DOC_CHUNK_MODEL.objects.filter(docno__in=docnos)
    reference_docs = sorted(queryset, key=lambda obj: docnos.index(obj.docno))
    reference_doc_ids = [doc.dialogue_id for doc in reference_docs]
    reference_docs = [str(doc) for doc in reference_docs]
    # Select useful documents (if necessary)
    if doc_selection_reranking is None:
        mask = list()
        for doc in reference_docs:
            params = {'query': query, 'document': doc, 'corpus': model.DATA_SET_ID}
            http_response = requests.post(
                urljoin(GENERATOR_SERVICE_URL, RELEVANT_DOCUMENT_SELECTION), data=json.dumps({'params': params})
            )
            if http_response.status_code == 200:
                response = http_response.json()['response']
                mask.append(response['text'].strip() == 'Yes.')
            else:
                mask.append(False)
    else:
        mask = [score > RELEVANCE_THRESHOLD for score in search_results['score'][:TOP_K_DOCS]]
    reference_doc_ids = [doc_id for doc_id, flag in zip(reference_doc_ids, mask) if flag]
    reference_docs = [doc for doc, flag in zip(reference_docs, mask) if flag]
    reference_doc_ids = reference_doc_ids[:n_docs]
    reference_docs = reference_docs[:n_docs]

    return query if len(reference_docs) > 0 else None, reference_doc_ids, reference_docs


def _suggestion(model: Type[DialogueModel], request, dialogue_id, utterance_idx, suggestion_model):
    dialogue_id = int(dialogue_id)
    utterance_idx = int(utterance_idx)
    # Gather data for
    dialogue_model = model.objects.get(pk=dialogue_id)
    dialogue_model.load_doc()
    dialogue_model.load_doc_chunks()
    dialogue = dialogue_model.to_chat_data()
    #
    chat_settings = request.session['chat_settings']
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
                dialogue_model,
                dialogue,
                utterance_idx,
                chat_settings['ranking'],
                chat_settings['reranking'],
                chat_settings['n_shots']
            ) if chat_settings.get('relevant_shots', DEFAULT_RELEVANT_SHOTS) else _gather_random_examples(
                model, dialogue_model, chat_settings['n_shots']
            ))
            for example in examples:
                example['utterances'] = example['utterances']
            params |= {'examples': examples}
        # Reference document passages
        if chat_settings['n_docs'] > 0:
            query, reference_doc_ids, reference_docs = _gather_relevant_docs(
                model,
                dialogue_model,
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

    # Prepare dummy feedback forms
    positive_feedback_form = None
    negative_feedback_form = None
    if request.user.is_authenticated:
        # Register suggestion object
        suggestion = suggestion_model(
            dialogue_id=dialogue_model,
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
            relevant_shots=chat_settings.get('relevant_shots', DEFAULT_RELEVANT_SHOTS)
        )
        suggestion.save()
        # Prepare feedback forms
        positive_feedback_form = ChatSuggestionFeedbackForm(
            initial={
                'suggestion_id': suggestion.pk,
                'feedback': 1
            }
        )
        negative_feedback_form = ChatSuggestionFeedbackForm(
            initial={
                'suggestion_id': suggestion.pk,
                'feedback': -1
            }
        )
    # Finalise suggestion parameters
    context = {
        'utterance': {
            'speaker': dialogue['utterances'][utterance_idx]['speaker'],
            'text': response['text'],
            'query': query,
            'references': reference_doc_ids,
            'dialogue_id': dialogue_model.id,
            'idx': utterance_idx
        },
        'positive_feedback_form': positive_feedback_form,
        'negative_feedback_form': negative_feedback_form
    }

    return render(request, 'suggestion.html', context | {'data_set_id': request.session['data_set_id']})


def suggestion_natcs(request, dialogue_id, utterance_idx):
    return _suggestion(DialogueNatCSModel, request, dialogue_id, utterance_idx, SuggestedDialogueNatCSUtteranceModel)


def suggestion_tweet_summ(request, dialogue_id, utterance_idx):
    return _suggestion(
        DialogueTweetSummModel, request, dialogue_id, utterance_idx, SuggestedDialogueTweetSummUtteranceModel
    )


def suggestion_tsccv2(request, dialogue_id, utterance_idx):
    return _suggestion(
        DialogueTeacherStudentChatroomModel,
        request,
        dialogue_id,
        utterance_idx,
        SuggestedDialogueTeacherStudentChatroomUtteranceModel
    )


def _chat_random_url(model: Type[DialogueModel]) -> str:
    model_object = random.choice(model.objects.all())
    model_object.load_utterances()
    speakers = set(utterance.speaker for utterance in model_object.utterances if not utterance.sys)
    while len(speakers) < 2:
        model_object = random.choice(model_object.objects.all())
        model_object.load_utterances()
        speakers = set(utterance.speaker for utterance in model_object.utterances if not utterance.sys)

    return model_object.get_absolute_url()


def chat_random_natcs(request):
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

    return redirect(random.choice(list(queryset)).get_absolute_url())


def chat_random_tweet_summ(request):
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

    return redirect(random.choice(list(queryset)).get_absolute_url())


def chat_random_tsccv2(request):
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

    return redirect(random.choice(list(queryset)).get_absolute_url())


def _register_chat_feedback(
        model: Type[UtteranceFeedback],
        request,
        suggestion_model: Type[DialogueUtteranceModel]
):
    # Parameters
    feedback_form = ChatSuggestionFeedbackForm(request.POST)
    if not feedback_form.is_valid():
        return None
    #
    feedback, created = model.objects.get_or_create(
        utterance_id=suggestion_model.objects.get(pk=feedback_form.cleaned_data['suggestion_id']),
        user_id=request.user
    )
    if feedback.feedback is None or feedback.feedback != feedback_form.cleaned_data['feedback']:
        feedback.feedback = feedback_form.cleaned_data['feedback']
    else:
        feedback.feedback = None
    feedback.save()

    return HttpResponse(status=204)


@login_required
def register_chat_natcs_feedback(request):
    return _register_chat_feedback(UtteranceNatCSFeedback, request, SuggestedDialogueNatCSUtteranceModel)


@login_required
def register_chat_tweet_summ_feedback(request):
    return _register_chat_feedback(UtteranceTweetSummFeedback, request, SuggestedDialogueTweetSummUtteranceModel)


@login_required
def register_chat_tsccv2_feedback(request):
    return _register_chat_feedback(
        UtteranceTeacherStudentChatroomFeedback, request, SuggestedDialogueTeacherStudentChatroomUtteranceModel
    )


def _chat_example(model, request, eval_table):
    # TODO Add date filter to retrieve only most recent one
    """
    evaluated_dialogue_ids = set(
        [feedback_object.dialogue_id.pk for feedback_object in eval_model.objects.filter(user_id=request.user.pk)]
    )
    eval_dialogues_queryset = model.objects.exclude(dialogue_id__in=evaluated_dialogue_ids)
    """
    eval_dialogues_queryset = model.objects.annotate(
        num_user_feedbacks=Count(
            f'{eval_table}__user_id',
            distinct=True,
            filter=Q(**{f'{eval_table}__user_id': request.user.pk})
        )
    ).filter(num_user_feedbacks=0)
    #
    if len(eval_dialogues_queryset) == 0:
        return HttpResponse(status=204)
    #
    eval_dialogue_object = random.choice(eval_dialogues_queryset)
    # Reference dialogue
    reference_dialogue_object = eval_dialogue_object.dialogue_id
    # Context utterances
    reference_dialogue_object.load_utterances()
    context_utterances = reference_dialogue_object.utterances[:eval_dialogue_object.ground_truth_utterance_id.utterance_id]
    # Options
    suggestion_objects = list(eval_dialogue_object.utterance_ids.all())
    random.shuffle(suggestion_objects)
    #
    context = {
        'example_dialogue_id': eval_dialogue_object.pk,
        'object': reference_dialogue_object,
        'utterances': context_utterances,
        'suggestions': suggestion_objects
    }

    return render(request, 'eval.html', context | {'data_set_id': request.session['data_set_id']})


@login_required
def chat_example_natcs(request):
    return _chat_example(EvalDialogueNatCSModel, request, 'evalnactsfeedback')


@login_required
def chat_example_tweet_summ(request):
    return _chat_example(EvalDialogueTweetSummModel, request, 'evaltweetsummfeedback')


@login_required
def chat_example_tsccv2(request):
    return _chat_example(EvalDialogueTeacherStudentChatroomModel, request, 'evalteacherstudentchatroomfeedback')


def _register_chat_eval(model, request, example_id, eval_dialogue_model):
    example_id = int(example_id)
    #
    if request.method != 'POST':
        return None
    #
    selected_utterances = request.POST.getlist(EVAL_KEY)
    # Register feedbacks
    eval_dialogue_object = eval_dialogue_model.objects.get(pk=example_id)
    for utterance_object in eval_dialogue_object.utterance_ids.all():
        # Register feedback
        eval_feedback_model = model(
            user_id=request.user,
            eval_dialogue_id=eval_dialogue_object,
            utterance_id=utterance_object,
            feedback=int(request.POST[str(utterance_object.pk)])
        )
        eval_feedback_model.save()

    return HttpResponse(status=204)


@login_required
def register_chat_natcs_eval(request, example_id):
    return _register_chat_eval(EvalNatCSFeedback, request, example_id, EvalDialogueNatCSModel)


@login_required
def register_chat_tweet_summ_eval(request, example_id):
    return _register_chat_eval(EvalTweetSummFeedback, request, example_id, EvalDialogueTweetSummModel)


@login_required
def register_chat_tsccv2_eval(request, example_id):
    return _register_chat_eval(
        EvalTeacherStudentChatroomFeedback, request, example_id, EvalDialogueTeacherStudentChatroomModel
    )


# Create your views here.
def chat_home(request):
    # Create forms
    context = {
        'settings_form': ChatSettingsForm(initial=get_initial_chat_settings(request.session)),
        'login_form': LoginForm()
    }
    if request.method == 'POST':
        if request.POST & ChatSettingsForm.base_fields.keys():
            context['settings_form'] = ChatSettingsForm(request.POST)
        if context['settings_form'].is_valid():
            update_chat_settings(request.session, context['settings_form'])

    return render(request, 'chat.html', context | {'data_set_id': request.session['data_set_id']})
