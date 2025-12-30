from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Movie(models.Model):
    title = models.CharField(max_length=200)
    overview = models.TextField()
    tmdb_id = models.IntegerField(unique=True)
    genres = models.CharField(max_length=500, blank=True)

    # LONG-TERM MEMORY
    poster_url = models.CharField(max_length=500, blank=True, null=True)
    director = models.CharField(max_length=200, default="Unknown")
    cast = models.CharField(max_length=500, default="Unknown")
    # --- ADD THIS LINE ---
    description = models.TextField(default="No description available")

    def __str__(self):
        return self.title

# --- USER INTERACTIONS ---


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - Watchlist - {self.movie.title}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} - Favorite - {self.movie.title}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    rating = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(10.0)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.movie.title} ({self.rating})"

# --- NEW: LIKE / DISLIKE SYSTEM ---


class Vote(models.Model):
    VOTE_CHOICES = (
        ('LIKE', 'Like'),
        ('DISLIKE', 'Dislike')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)

    class Meta:
        unique_together = ('user', 'movie')  # One vote per movie per user

    def __str__(self):
        return f"{self.user.username} - {self.vote_type} - {self.movie.title}"

# --- ADD THIS AT THE BOTTOM OF models.py ---

# 1. Model to track the user's ONE active session


class UserSession(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.user.username

# 2. Signal: Run this every time ANYONE logs in


@receiver(user_logged_in)
def remove_other_sessions(sender, user, request, **kwargs):
    # Save the current session key so we can compare later
    if not request.session.session_key:
        request.session.create()
    new_session_key = request.session.session_key

    # Check if this user has an old session stored in DB
    try:
        user_session = UserSession.objects.get(user=user)
        old_session_key = user_session.session_key

        # If an old session exists and it's different from the new one...
        if old_session_key and old_session_key != new_session_key:
            # DELETE the old session from Django's database (Kicks the other device)
            try:
                Session.objects.get(session_key=old_session_key).delete()
            except Session.DoesNotExist:
                pass  # It was already expired/deleted

        # Update with the new key
        user_session.session_key = new_session_key
        user_session.save()

    except UserSession.DoesNotExist:
        # First time login for this user, create the record
        UserSession.objects.create(user=user, session_key=new_session_key)
