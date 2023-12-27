from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("test", views.test, name="test"),
    path("updating", views.updating, name="updating"),
    path("scores", views.kbp_scores, name="scores"),
    path("games", views.games, name="games"),
    path("picks", views.picks, name="picks"),
    path("margins", views.margins, name="margins"),
    path("official", views.official_scores, name="official"),
]