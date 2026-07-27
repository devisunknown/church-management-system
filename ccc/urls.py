from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('members/', views.members_view, name='members'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('calendar/', views.calandar, name='calandar'),
    path('events/', views.events_view, name='events'),
    path('events/add/', views.addevent, name='addevent'),
    path('money',views.money,name='money'),
    path('money/add/', views.addmoney, name='addmoney'),
    path('member/addmember',views.addmember,name='addmember'),
    path('member/edit/<str:member_id>',views.editmember,name='editmember'),
    path('attendance/', views.attendance_landing, name='attendance'),
    path('attendance/<int:event_id>/', views.take_attendance, name='take_attendance'),
    path('history/', views.history_view, name='history'),
    path('attendance/<int:event_id>/summary/', views.attendance_summary, name='attendance_summary'),
    path('members/search/', views.member_search, name='member_search'),
]
