from django.contrib.auth.models import User


def make_user(username="alice", password="pass", email=None):
    if email is None:
        email = f"{username}@test.local"
    return User.objects.create_user(username=username, email=email, password=password)
