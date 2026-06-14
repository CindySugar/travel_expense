from django.urls import path

from . import views

urlpatterns = [
    path('auth/register/', views.register_view),
    path('auth/login/', views.login_view),
    path('auth/wechat-login/', views.wechat_login_view),
    path('auth/logout/', views.logout_view),
    path('auth/me/', views.me_view),
    path('trips/', views.trips_view),
    path('trips/<int:trip_id>/', views.trip_detail_view),
    path('trips/<int:trip_id>/members/', views.members_view),
    path('members/<int:member_id>/', views.member_detail_view),
    path('trips/<int:trip_id>/expenses/', views.expenses_view),
    path('expenses/<int:expense_id>/', views.expense_detail_view),
    path('trips/<int:trip_id>/summary/', views.summary_view),
    path('trips/<int:trip_id>/settlements/', views.settlements_view),
    path('settlements/<int:settlement_id>/', views.settlement_detail_view),
]
