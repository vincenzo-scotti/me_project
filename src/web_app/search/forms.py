from django import forms

from typing import Dict

from me_project.web_utils.utils import *

from account.forms import LoginForm


class SearchSettingsForm(forms.Form):
    data_set_id = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'aria-label': 'Corpus'}),
        label='Data set ID',
        choices=DATA_SET_IDS.items()
    )
    ranking = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'aria-label': 'Search type'}),
        label='Scoring',
        choices=RANKING_APPROACHES.items()
    )
    reranking = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'aria-label': 'Search type'}),  # (),
        label='Re-scoring',
        choices=RERANKING_APPROACHES.items(),
        required=False
    )
    doc_selection = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'aria-label': 'QA'}),  # (),
        label='QA Document(s) selection',
        choices=DOC_SELECTION_APPROACHES.items()
    )

    def get_values_dict(self) -> Dict:
        return {
            'data_set_id': self.cleaned_data['data_set_id'],
            'ranking': self.cleaned_data['ranking'],
            'reranking': self.cleaned_data['reranking'] if len(self.cleaned_data['reranking']) > 0 else None,
            'doc_selection': self.cleaned_data['doc_selection']
        }


class TextSearchForm(forms.Form):
    query = forms.CharField(
        min_length=1,
        max_length=256,
        label=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control me-2', 'type': 'search', 'placeholder': 'Search', 'aria-label': 'Search'}
        )
    )


class RelatedDocsSearchForm(forms.Form):
    reference_doc = forms.IntegerField()


class Doc2DocRelevanceFeedbackForm(forms.Form):
    src_doc_id = forms.IntegerField()
    tgt_doc_id = forms.IntegerField()
    feedback = forms.IntegerField()


class Doc2QueryRelevanceFeedbackForm(forms.Form):
    search_id = forms.IntegerField()
    doc_id = forms.IntegerField()
    feedback = forms.IntegerField()
