from django.urls import path

from . import views

app_name = "mintbuilderapp"
urlpatterns = [
    path("", views.index_view, name='index'),
    path("helloworld/", views.select_button_view, name='hw_view'),
    path("clear-section/", views.clear_section, name='clear_section'),
    path("<int:chat_id>/<int:group_id>", views.detail, name="detail"),
    path("<int:chat_id>/new_request", views.new_request, name="new_request"),
    path("<int:chat_id>/<int:group_id>/add_participant/", views.add_participant, name="add_participant"),
    #path("<int:chat_id>/<int:group_id>/remove_participant/", views.remove_participant, name="remove_participant"),
    path("<int:chat_id>/init", views.initialize, name="init"),
    path("<int:chat_id>/teams", views.generate_teams, name="teams"),
    path("<int:chat_id>/reroll_teams", views.reroll_teams, name="reroll_teams"),
    path("<int:chat_id>/result", views.result, name="result"),
    path("<int:chat_id>/<int:group_id>/button_unselected/", views.unselect_button_view, name='but_unselect'),
    path("<int:chat_id>/<int:group_id>/button_selected/", views.select_button_view, name='but_select'),
    path("<int:chat_id>/<int:group_id>/button_selected_locked/", views.select_lock_button_view, name='but_select_lock'),
]
