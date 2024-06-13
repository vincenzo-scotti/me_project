from django import forms

from typing import Dict
from me_project.web_utils.utils import *

from account.forms import LoginForm


class ChatSettingsForm(forms.Form):
    model = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'aria-label': 'Model'}),
        label='Model',
        choices=MODELS.items()
    )
    n_shots = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 4}),
        label='No. Shots (examples)'
    )
    n_candidates = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 4}),
        label='No. Candidates'
    )
    n_docs = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-range', 'type': 'range', 'min': 0, 'max': 3}),
        label='No. Documents'
    )
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
            'model': self.cleaned_data['model'],
            'n_shots': self.cleaned_data['n_shots'],
            'n_candidates': self.cleaned_data['n_candidates'],
            'n_docs': self.cleaned_data['n_docs'],
            'data_set_id': self.cleaned_data['data_set_id'],
            'ranking': self.cleaned_data['ranking'],
            'reranking': self.cleaned_data['reranking'] if len(self.cleaned_data['reranking']) > 0 else None,
            'doc_selection': self.cleaned_data['doc_selection']
        }


class ChatSuggestionFeedbackForm(forms.Form):
    suggestion_id = forms.IntegerField()
    feedback = forms.IntegerField()
