from django.contrib import admin
from .models import Movie, Watchlist, Favorite, Review, Vote


class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'tmdb_id', 'genres')
    search_fields = ('title',)


admin.site.register(Movie, MovieAdmin)
admin.site.register(Watchlist)
admin.site.register(Favorite)
admin.site.register(Review)
admin.site.register(Vote)  # Added Vote here
