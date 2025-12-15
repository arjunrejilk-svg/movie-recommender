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
