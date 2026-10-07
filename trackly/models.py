from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        user = self.model(
            email = self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save()

        return user
    

class User(AbstractUser):
    objects = UserManager()

    username = None
    first_name = None
    last_name = None
    email = models.EmailField(unique=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email


class Monitor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="monitor")
    url = models.URLField()
    check_interval = models.PositiveSmallIntegerField(default=60, validators=[MinValueValidator(1), MaxValueValidator(10080)]) # from 10 min to 7 days
    last_check = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_hash = models.CharField(max_length=64, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Snapshot(models.Model):
    monitor = models.ForeignKey(
        Monitor,
        on_delete=models.CASCADE,
        related_name="snapshots"
    )
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)