from django.urls import path
from . import views


urlpatterns = [
    path('', views.search_home, name='search'),
    path('results/natcs/', views.DialogueNatCSListView.as_view(), name='results_natcs'),
    path('results/tweet_summ/', views.DialogueTweetSummListView.as_view(), name='results_tweet_summ'),
    path('results/tsccv2/', views.DialogueTeacherStudentChatroomListView.as_view(), name='results_tsccv2'),
    path('details/natcs/<int:pk>', views.DialogueNatCSDetailView.as_view(), name='details_natcs'),
    path('details/tweet_summ/<int:pk>', views.DialogueTweetSummDetailView.as_view(), name='details_tweet_summ'),
    path('details/tsccv2/<int:pk>', views.DialogueTeacherStudentChatroomDetailView.as_view(), name='details_tsccv2'),
    path('qa/natcs/', views.qa_natcs, name='qa_natcs'),
    path('qa/tweet_summ/', views.qa_tweet_summ, name='qa_tweet_summ'),
    path('qa/tsccv2/', views.qa_tsccv2, name='qa_tsccv2'),
    path('feedback/natcs/d2q', views.register_d2q_natcs_feedback, name='feedback_natcs_d2q'),
    path('feedback/natcs/d2d', views.register_d2d_natcs_feedback, name='feedback_natcs_d2d'),
    path('feedback/tweet_summ/d2q', views.register_d2q_tweet_summ_feedback, name='feedback_tweet_summ_d2q'),
    path('feedback/tweet_summ/d2d', views.register_d2d_tweet_summ_feedback, name='feedback_tweet_summ_d2d'),
    path('feedback/tsccv2/d2q', views.register_d2q_tsccv2_feedback, name='feedback_tsccv2_d2q'),
    path('feedback/tsccv2/d2d', views.register_d2d_tsccv2_feedback, name='feedback_tsccv2_d2d')
]
