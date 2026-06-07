import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

from .managers import UserManager


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    username = None

    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email