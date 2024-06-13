from django.shortcuts import render, HttpResponse
from django.views import generic
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

from urllib.parse import urljoin
import json
import requests

from typing import Dict, Union, List, Type

from .forms import (
    SearchSettingsForm,
    TextSearchForm,
    RelatedDocsSearchForm,
    LoginForm,
    Doc2DocRelevanceFeedbackForm,
    Doc2QueryRelevanceFeedbackForm
)
from .models import DialogueModel, DialogueNatCSModel, DialogueTweetSummModel, DialogueTeacherStudentChatroomModel
from .models import QueryModel, SearchModel, SearchNatCSModel, SearchTweetSummModel, SearchTeacherStudentChatroomModel
from .models import (
    Doc2DocRelevanceFeedback,
    Doc2DocNatCSRelevanceFeedback,
    Doc2DocTweetSummRelevanceFeedback,
    Doc2DocTeacherStudentChatroomRelevanceFeedback
)
from .models import (
    Doc2QueryRelevanceFeedback,
    Doc2QueryNatCSRelevanceFeedback,
    Doc2QueryTweetSummRelevanceFeedback,
    Doc2QueryTeacherStudentChatroomRelevanceFeedback
)
from me_project.web_utils import update_search_settings, get_initial_search_settings
from me_project.web_utils.utils import *


# Create your views here.


def _qa(model: Type[DialogueModel], request):
    # Parameters
    text_search_form = TextSearchForm(request.GET)
    if text_search_form.is_valid():
        query = text_search_form.cleaned_data['query']
    else:
        return None
    ranking = request.session['search_settings']['ranking']
    reranking = request.session['search_settings']['reranking']
    doc_selection_reranking = request.session['search_settings']['doc_selection']
    # Cache
    qa_cache_key = f'search_results:{hash(query)}:' \
                   f'{model.DATA_SET_ID}:' \
                   f'{ranking}:' \
                   f'{reranking}:' \
                   f'{doc_selection_reranking}'
    context = cache.get(qa_cache_key)
    if context is not None:
        return render(request, 'answer.html', context | {'data_set_id': request.session['data_set_id']})
    # Run query recognition
    params = {'query': query, 'corpus': model.DATA_SET_ID}
    http_response = requests.post(
        urljoin(GENERATOR_SERVICE_URL, QUERY_RECOGNITION), data=json.dumps({'params': params})
    )
    if http_response.status_code == 200:
        response = http_response.json()['response']
    else:
        return None
    if response['text'].strip() != 'Yes.':
        return HttpResponse(status=204)
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
    else:
        return None
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
    if len(reference_docs) == 0:
        return HttpResponse(status=204)
    else:
        reference_doc_ids = reference_doc_ids[:MAX_REFERENCES]
        reference_docs = reference_docs[:MAX_REFERENCES]
    # Get answer
    params = {'question': query, 'reference_documents': reference_docs, 'corpus': model.DATA_SET_ID}
    http_response = requests.post(
        urljoin(GENERATOR_SERVICE_URL, KB_QA), data=json.dumps({'params': params})
    )
    response = {'speaker': 'assistant', 'text': None}
    if http_response.status_code == 200:
        response = http_response.json()['response']
    answer = response['text']
    # Compose response context
    context: Dict = {
        'question': query, 'answer': answer, 'references': reference_doc_ids
    }
    cache.set(qa_cache_key, context, timeout=QA_CACHE_TIMEOUT)

    return render(request, 'answer.html', context | {'data_set_id': request.session['data_set_id']})


def qa_natcs(request):
    return _qa(DialogueNatCSModel, request)


def qa_tweet_summ(request):
    return _qa(DialogueTweetSummModel, request)


def qa_tsccv2(request):
    return _qa(DialogueTeacherStudentChatroomModel, request)


class DialogueListView(generic.ListView):
    SEARCH_RESULTS_CACHE_TIMEOUT: int = 600  # Ten minutes
    RELATED_DOC_RESULTS_ID_SUFFIX: str = '_relevant_docs'

    CHUNKED_SEARCH: int = True

    SNIPPET_CHUNK_SIZE: int = 64
    SNIPPET_STRIDE_SIZE: int = 48

    # https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/Generic_views
    # Structure
    model = DialogueModel

    search_model = SearchModel

    template_name = 'results.html'
    paginate_by = 8

    def __init__(self, *args, **kwargs):
        super().__init__()
        #
        self.params: Optional[Dict] = None
        self.search_results: Optional[Dict[str, Union[str, List[str], List[float]]]] = None
        self.text_search_form: Optional[TextSearchForm] = None
        self.related_doc_search_form: Optional[RelatedDocsSearchForm] = None
        self.ids_suffix: str = ''

        self.search: Optional[SearchModel] = None
        self.reference_doc: Optional[DialogueModel] = None

    @staticmethod
    def _get_search_forms(request):
        text_search_form = TextSearchForm(request.GET)
        related_doc_search_form = RelatedDocsSearchForm(request.GET)

        return text_search_form, related_doc_search_form

    def _postprocess_page_obj(self, page_obj):
        # Get query
        url = RETRIEVAL_SERVICE_URL
        snippet_results_cache_key = None
        tgt_search_results = {
            'docno': self.search_results['docno'][page_obj.start_index() - 1:page_obj.end_index()],
            'score': self.search_results['score'][page_obj.start_index() - 1:page_obj.end_index()],
        }
        if self.text_search_form.is_valid():
            url = urljoin(url, SNIPPET_GENERATE_PATH)
            snippet_results_cache_key = f'snippet_results:{hash(self.params["query"])}:' \
                                        f'{self.params["corpus"]}' \
                                        f'{self.params["ranking"]}:' \
                                        f'{self.params["reranking"]}:' \
                                        f'{page_obj.number}'
        elif self.related_doc_search_form.is_valid():
            url = urljoin(url, SNIPPET_GENERATE_LONG_QUERY_PATH)
            snippet_results_cache_key = f'snippet_results:{hash(tuple(self.params["query"]))}:' \
                                        f'{self.params["corpus"]}' \
                                        f'{self.params["ranking"]}:' \
                                        f'{self.params["reranking"]}:' \
                                        f'{page_obj.number}'
            # self.ids_suffix = self.RELATED_DOC_RESULTS_ID_SUFFIX
        params = self.params | {
            'search_results': tgt_search_results
        } | {
            'doc_chunk_size': self.SNIPPET_CHUNK_SIZE, 'doc_chunk_stride': self.SNIPPET_STRIDE_SIZE
        }
        snippet_results = cache.get(snippet_results_cache_key)
        if snippet_results is None:
            http_response = requests.post(url, data=json.dumps({'params': params}))
            if http_response.status_code == 200:
                snippet_results = http_response.json()
                cache.set(snippet_results_cache_key, snippet_results, timeout=self.SEARCH_RESULTS_CACHE_TIMEOUT)
            else:
                for obj, score, rank in zip(
                        page_obj.object_list,
                        tgt_search_results['score'],
                        range(page_obj.start_index(), page_obj.end_index() + 1)
                ):
                    obj.score = score
                    obj.rank = rank

                return page_obj
        # Add missing info
        for obj, score, rank, summary in zip(
                page_obj.object_list,
                snippet_results['score'],
                range(page_obj.start_index(), page_obj.end_index() + 1),
                snippet_results['summary']
        ):
            obj.score = score
            obj.rank = rank
            obj.snippet = summary

        return page_obj

    def get_queryset(self):
        # Load forms
        self.text_search_form, self.related_doc_search_form = self._get_search_forms(self.request)
        # Search options
        ranking = self.request.session['search_settings']['ranking']
        reranking = self.request.session['search_settings']['reranking']
        # Parse request
        url = RETRIEVAL_SERVICE_URL
        search_results_cache_key = None
        tgt_docno = None
        if self.text_search_form.is_valid():
            #
            query = self.text_search_form.cleaned_data['query']
            self.params: Dict = {
                'query': query,
                'corpus': self.model.DATA_SET_ID,
                'ranking': ranking,
                'reranking': reranking
            }
            url = urljoin(url, SEARCH_DOC_PATH)
            search_results_cache_key = f'search_results:{hash(query)}:{self.model.DATA_SET_ID}:{ranking}:{reranking}'
            # Add query to DB if necessary
            query_obj, created = QueryModel.objects.get_or_create(text=query)
            # Add search if user is logged
            if self.request.user.is_authenticated:
                self.search, created = self.search_model.objects.get_or_create(
                    query_id=query_obj, user_id=self.request.user
                )
        elif self.related_doc_search_form.is_valid():
            #
            self.ids_suffix = self.RELATED_DOC_RESULTS_ID_SUFFIX
            #
            document_id = self.related_doc_search_form.cleaned_data['reference_doc']
            self.reference_doc = self.model.objects.get(pk=document_id)
            self.reference_doc.load_doc()
            self.reference_doc.load_doc_chunks()
            tgt_docno = self.reference_doc.doc.docno
            query = self.reference_doc.to_doc_chunks()
            self.params: Dict = {
                'query': query,
                'corpus': self.model.DATA_SET_ID,
                'ranking': ranking,
                'reranking': reranking
            }
            url = urljoin(url, SEARCH_DOC_LONG_QUERY_PATH)
            search_results_cache_key = f'search_results:{hash(tuple(query))}:' \
                                       f'{self.model.DATA_SET_ID}:' \
                                       f'{ranking}:' \
                                       f'{reranking}'
            #
        # Run query
        qset = None
        if self.params is not None:
            #
            self.search_results = cache.get(search_results_cache_key)
            if self.search_results is None:
                http_response = requests.post(
                    url, data=json.dumps({'params': self.params | {'chunk': self.CHUNKED_SEARCH}})
                )
                if http_response.status_code == 200:
                    self.search_results = http_response.json()
                    # Remove same document from results
                    if tgt_docno is not None:
                        idx = self.search_results['docno'].index(tgt_docno)
                        self.search_results['docno'].pop(idx)
                        self.search_results['score'].pop(idx)
                    cache.set(search_results_cache_key, self.search_results, timeout=self.SEARCH_RESULTS_CACHE_TIMEOUT)
                else:
                    return qset
            # Get queryset
            qset = [self.model.get_from_doc_id(dialogue_id) for dialogue_id in self.search_results['docno']]

        return qset

    def get_context_data(self, **kwargs):
        # NOTE: This can be used to add the snippet to the search results
        # Call the base implementation first to get the context
        context = super(DialogueListView, self).get_context_data(**kwargs)
        # Create any data and add it to the context
        context.update({
            'page_obj': self._postprocess_page_obj(context['page_obj']),
            'search_id': self.search.pk if self.search is not None else None,
            'reference_doc_id': self.reference_doc.pk if self.reference_doc is not None else None,
            'ids_suffix': self.ids_suffix,
            'data_set_id': self.model.DATA_SET_ID,
            'text_search_form': TextSearchForm(self.request.GET),
            'related_doc_search_form': RelatedDocsSearchForm(self.request.GET)
        })

        return context


class DialogueNatCSListView(DialogueListView):
    model = DialogueNatCSModel
    search_model = SearchNatCSModel


class DialogueTweetSummListView(DialogueListView):
    model = DialogueTweetSummModel
    search_model = SearchTweetSummModel


class DialogueTeacherStudentChatroomListView(DialogueListView):
    model = DialogueTeacherStudentChatroomModel
    search_model = SearchTeacherStudentChatroomModel


class DialogueDetailView(generic.DetailView):
    RELATED_DOC_RESULTS_ID_SUFFIX = '_relevant_docs'

    # Structure
    model = DialogueModel
    d2d_feedback_model = Doc2DocRelevanceFeedback
    d2q_feedback_model = Doc2QueryRelevanceFeedback
    # Visualisation
    template_name = 'details.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super(DialogueDetailView, self).get_context_data(**kwargs)
        # Prepare context data
        self.object.load_utterances()
        ids_suffix = ''
        action = None
        previous_feedback = 0
        positive_feedback_form = None
        negative_feedback_form = None
        # Search feedback
        if self.request.user.is_authenticated and self.request.GET.get('search') is not None:
            action = 'd2q'
            positive_feedback_form = Doc2QueryRelevanceFeedbackForm(
                initial={'search_id': self.request.GET.get('search'), 'doc_id': self.object.pk, 'feedback': 1}
            )
            negative_feedback_form = Doc2QueryRelevanceFeedbackForm(
                initial={'search_id': self.request.GET.get('search'), 'doc_id': self.object.pk, 'feedback': -1}
            )
            try:
                previous_feedback = self.d2q_feedback_model.objects.get(
                    search_id=self.request.GET.get('search'), dialogue_id=self.object.pk, user_id=self.request.user
                ).feedback
            except self.d2q_feedback_model.DoesNotExist:
                pass

        # Document similarity feedback
        if self.request.user.is_authenticated and self.request.GET.get('reference_doc') is not None:
            ids_suffix = self.RELATED_DOC_RESULTS_ID_SUFFIX
            action = 'd2d'
            positive_feedback_form = Doc2DocRelevanceFeedbackForm(
                initial={
                    'src_doc_id': self.request.GET.get('reference_doc'),
                    'tgt_doc_id': self.object.pk,
                    'feedback': 1
                }
            )
            negative_feedback_form = Doc2DocRelevanceFeedbackForm(
                initial={
                    'src_doc_id': self.request.GET.get('reference_doc'),
                    'tgt_doc_id': self.object.pk,
                    'feedback': -1
                }
            )
            try:
                previous_feedback = self.d2d_feedback_model.objects.get(
                    src_dialogue_id=self.request.GET.get('reference_doc'),
                    tgt_dialogue_id=self.object.pk,
                    user_id=self.request.user
                ).feedback
            except self.d2d_feedback_model.DoesNotExist:
                pass

        # Create any data and add it to the context
        context.update({
            'utterances': self.object.utterances,
            'ids_suffix': ids_suffix,
            'action': action,
            'previous_feedback': previous_feedback,
            'positive_feedback_form': positive_feedback_form,
            'negative_feedback_form': negative_feedback_form
        })

        return context


class DialogueNatCSDetailView(DialogueDetailView):
    # Structure
    model = DialogueNatCSModel
    d2d_feedback_model = Doc2DocNatCSRelevanceFeedback
    d2q_feedback_model = Doc2QueryNatCSRelevanceFeedback


class DialogueTweetSummDetailView(DialogueDetailView):
    # Structure
    model = DialogueTweetSummModel
    d2d_feedback_model = Doc2DocTweetSummRelevanceFeedback
    d2q_feedback_model = Doc2QueryTweetSummRelevanceFeedback


class DialogueTeacherStudentChatroomDetailView(DialogueDetailView):
    # Structure
    model = DialogueTeacherStudentChatroomModel
    d2d_feedback_model = Doc2DocTeacherStudentChatroomRelevanceFeedback
    d2q_feedback_model = Doc2QueryTeacherStudentChatroomRelevanceFeedback


def _register_d2d_feedback(model: Type[Doc2DocRelevanceFeedback], request, doc_model: Type[DialogueModel]):
    # Parameters
    feedback_form = Doc2DocRelevanceFeedbackForm(request.POST)
    if not feedback_form.is_valid():
        return None
    #
    feedback, created = model.objects.get_or_create(
        src_dialogue_id=doc_model.objects.get(pk=feedback_form.cleaned_data['src_doc_id']),
        tgt_dialogue_id=doc_model.objects.get(pk=feedback_form.cleaned_data['tgt_doc_id']),
        user_id=request.user
    )
    if feedback.feedback is None or feedback.feedback != feedback_form.cleaned_data['feedback']:
        feedback.feedback = feedback_form.cleaned_data['feedback']
    else:
        feedback.feedback = None
    feedback.save()

    return HttpResponse(status=204)


@login_required
def register_d2d_natcs_feedback(request):
    return _register_d2d_feedback(Doc2DocNatCSRelevanceFeedback, request, DialogueNatCSModel)


@login_required
def register_d2d_tweet_summ_feedback(request):
    return _register_d2d_feedback(Doc2DocTweetSummRelevanceFeedback, request, DialogueTweetSummModel)


@login_required
def register_d2d_tsccv2_feedback(request):
    return _register_d2d_feedback(
        Doc2DocTeacherStudentChatroomRelevanceFeedback, request, DialogueTeacherStudentChatroomModel
    )


def _register_d2q_feedback(
        model: Type[Doc2QueryRelevanceFeedback],
        request,
        search_model: Type[SearchModel],
        doc_model: Type[DialogueModel]
):
    # Parameters
    feedback_form = Doc2QueryRelevanceFeedbackForm(request.POST)
    if not feedback_form.is_valid():
        return None
    #
    feedback, created = model.objects.get_or_create(
        search_id=search_model.objects.get(pk=feedback_form.cleaned_data['search_id']),
        dialogue_id=doc_model.objects.get(pk=feedback_form.cleaned_data['doc_id']),
        user_id=request.user
    )
    if feedback.feedback is None or feedback.feedback != feedback_form.cleaned_data['feedback']:
        feedback.feedback = feedback_form.cleaned_data['feedback']
    else:
        feedback.feedback = None
    feedback.save()

    return HttpResponse(status=204)


@login_required
def register_d2q_natcs_feedback(request):
    return _register_d2q_feedback(Doc2QueryNatCSRelevanceFeedback, request, SearchNatCSModel, DialogueNatCSModel)


@login_required
def register_d2q_tweet_summ_feedback(request):
    return _register_d2q_feedback(
        Doc2QueryTweetSummRelevanceFeedback, request, SearchTweetSummModel, DialogueTweetSummModel
    )


@login_required
def register_d2q_tsccv2_feedback(request):
    return _register_d2q_feedback(
        Doc2QueryTeacherStudentChatroomRelevanceFeedback,
        request,
        SearchTeacherStudentChatroomModel,
        DialogueTeacherStudentChatroomModel
    )


def search_home(request):
    # Create forms
    context = {
        'settings_form': SearchSettingsForm(initial=get_initial_search_settings(request.session)),
        'text_search_form': TextSearchForm(request.GET),
        'login_form': LoginForm()
    }
    if request.method == 'POST':
        if request.POST & SearchSettingsForm.base_fields.keys():
            context['settings_form'] = SearchSettingsForm(request.POST)
        if context['settings_form'].is_valid():
            update_search_settings(request.session, context['settings_form'])

    return render(request, 'search.html', context | {'data_set_id': request.session['data_set_id']})
