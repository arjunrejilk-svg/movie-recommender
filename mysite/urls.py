from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    # --- FIX: Hijack Admin Logout (Must be first!) ---
    path('admin/logout/', views.logout_view, name='admin_logout'),

    # Admin & Auth
    path('admin/login/', views.login_view),
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # Core App
    path('', views.index, name='index'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('search/exact/', views.exact_search, name='exact_search'),
    path('search-suggestions/', views.search_suggestions,
         name='search_suggestions'),
    path('about/', views.about, name='about'),

    # Actions
    path('watchlist/add/<int:movie_id>/',
         views.toggle_watchlist, name='toggle_watchlist'),
    path('favorite/add/<int:movie_id>/',
         views.toggle_favorite, name='toggle_favorite'),
    path('vote/<int:movie_id>/<str:vote_type>/',
         views.toggle_vote, name='toggle_vote'),
    path('review/edit/<int:review_id>/', views.edit_review, name='edit_review'),

    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('my-lists/<str:list_type>/', views.my_lists, name='my_lists'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),

    # --- NEW ADMIN PANEL PATHS (Fixed to match new views.py) ---
    path('dashboard/', views.custom_admin, name='custom_admin'),
    # We replaced the 2 old delete paths with this 1 new universal path
    path('dashboard/delete/<str:model_type>/<int:item_id>/',
         views.delete_item_admin, name='delete_item_admin'),

    # Login Redirect (Traffic Controller)
    path('login-redirect/', views.login_dispatch, name='login_dispatch'),
    path('magic-import/', views.db_fix_import_movies, name='db_fix'),
]
