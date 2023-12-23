from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("test", views.test, name="test"),
    path("updating", views.updating, name="updating"),
    path("scores", views.kbp_scores, name="scores")
]