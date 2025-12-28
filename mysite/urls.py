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
    path('review/edit/<int:review_id>/', views.edit_review, name='edit_review'),
    path('search/exact/', views.exact_search, name='exact_search'),
    path('search-suggestions/', views.search_suggestions,
         name='search_suggestions'),
    path('about/', views.about, name='about'),
    # Core App
    path('', views.index, name='index'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),

    # Actions
    path('watchlist/add/<int:movie_id>/',
         views.toggle_watchlist, name='toggle_watchlist'),
    path('favorite/add/<int:movie_id>/',
         views.toggle_favorite, name='toggle_favorite'),
    path('vote/<int:movie_id>/<str:vote_type>/',
         views.toggle_vote, name='toggle_vote'),

    # --- NEW PROFILE PAGES ---
    path('profile/', views.profile_view, name='profile'),
    path('my-lists/<str:list_type>/', views.my_lists, name='my_lists'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    # Admin Panel Paths
    path('dashboard/', views.custom_admin, name='custom_admin'),
    path('dashboard/delete-user/<int:user_id>/',
         views.delete_user_admin, name='delete_user_admin'),
    path('dashboard/delete-review/<int:review_id>/',
         views.delete_review_admin, name='delete_review_admin'),
    # Add this path for the login redirect
    path('login-redirect/', views.login_dispatch, name='login_dispatch'),
]
