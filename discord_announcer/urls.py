"""App URLs"""

# Django
from django.urls import path

# AA Example App
from discord_announcer import views

app_name: str = "discord_announcer"

urlpatterns = [
    path("", views.index, name="index"),
    path("check-tokens/", views.check_tokens, name="check_tokens"),
    path("send-latest/", views.send_latest, name="send_latest"),
]
