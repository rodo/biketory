from django.urls import path

from referrals import views

urlpatterns = [
    path("referrals/", views.referral_list, name="referral_list"),
    path("referrals/<int:pk>/delete/", views.referral_delete, name="referral_delete"),
]
