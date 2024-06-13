from django.urls import path
from . import views


urlpatterns = [
    path('', views.chat_home, name='chat'),
    path('random/natcs/', views.chat_random_natcs, name='random_natcs'),
    path('random/tweet_summ/', views.chat_random_tweet_summ, name='random_tweet_summ'),
    path('random/tsccv2/', views.chat_random_tsccv2, name='random_tsccv2'),
    path('suggestion/natcs/<dialogue_id>/<utterance_idx>/', views.suggestion_natcs, name='suggestion_natcs'),
    path('suggestion/tweet_summ/<dialogue_id>/<utterance_idx>/', views.suggestion_tweet_summ, name='suggestion_tweet_summ'),
    path('suggestion/tsccv2/<dialogue_id>/<utterance_idx>/', views.suggestion_tsccv2, name='suggestion_tsccv2'),
    path('feedback/natcs/', views.register_chat_natcs_feedback, name='feedback_natcs_chat'),
    path('feedback/tweet_summ/', views.register_chat_tweet_summ_feedback, name='feedback_tweet_summ_chat'),
    path('feedback/tsccv2/', views.register_chat_tsccv2_feedback, name='feedback_tsccv2_chat'),
    path('example/natcs/', views.chat_example_natcs, name='example_natcs'),
    path('example/tweet_summ/', views.chat_example_tweet_summ, name='example_tweet_summ'),
    path('example/tsccv2/', views.chat_example_tsccv2, name='example_tsccv2'),
    path('eval/natcs/<example_id>/', views.register_chat_natcs_eval, name='eval_natcs_chat'),
    path('eval/tweet_summ/<example_id>/', views.register_chat_tweet_summ_eval, name='eval_tweet_summ_chat'),
    path('eval/tsccv2/<example_id>/', views.register_chat_tsccv2_eval, name='eval_tsccv2_chat')
]
