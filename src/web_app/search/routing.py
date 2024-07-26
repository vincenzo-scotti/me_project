from django.urls import path
from .consumers import DialogueNatCSDocConsumer, DialogueTweetSummDocConsumer, DialogueTeacherStudentChatroomDocConsumer

# Should be `websocket_urlpatterns`
websocket_urlpatterns = [
    path('ME-Demo/analysis/natcs/<int:dialogue_id>', DialogueNatCSDocConsumer.as_asgi()),
    path('ME-Demo/analysis/tweet_summ/<int:dialogue_id>', DialogueTweetSummDocConsumer.as_asgi()),
    path('ME-Demo/analysis/tsccv2/<int:dialogue_id>', DialogueTeacherStudentChatroomDocConsumer.as_asgi())
]
