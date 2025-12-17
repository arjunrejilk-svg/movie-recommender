import gzip
import os
import pickle
import pandas as pd
import requests
from urllib.parse import quote

# Django Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.conf import settings

# App Imports
from .models import Movie, Watchlist, Favorite, Review, Vote
from .forms import SignUpForm

# --- 1. SETUP DATA ---
API_KEY = '8265bd1679663a7ea12ac168da84d2e8'


def load_data():
    try:
        # Construct the full paths to files
        pkl_path = os.path.join(settings.BASE_DIR, 'movie_recommender.pkl')
        sim_path = os.path.join(settings.BASE_DIR, 'similarity.pkl.gz')

        # Load Movies
        movies_dict = pickle.load(open(pkl_path, 'rb'))

        # Load Similarity (Compressed)
        with gzip.open(sim_path, 'rb') as f:
            similarity = pickle.load(f)

        return pd.DataFrame(movies_dict), similarity
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


new_df, similarity = load_data()

# --- 2. HELPER: SAFE POSTER FETCH (Prevents Crashes) ---


def safe_fetch_poster(tmdb_id, title):
    try:
        # Check DB first (Fastest & Safest)
        db_movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if db_movie and db_movie.poster_url:
            return db_movie.poster_url

        # Try Internet
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={API_KEY}',
            timeout=2
        )
        if response.status_code == 200:
            path = response.json().get('poster_path')
            if path:
                return "https://image.tmdb.org/t/p/w500/" + path

        raise ValueError("No poster")
    except Exception:
        return f"https://ui-avatars.com/api/?name={quote(title)}&background=333&color=fff"

# --- 3. HELPER: GET FULL MOVIE DATA (Saves to DB) ---


def get_movie_data(movie_obj):
    if movie_obj.poster_url and movie_obj.director != "Unknown":
        return movie_obj.poster_url, movie_obj.director, movie_obj.cast

    try:
        url_credits = f'https://api.themoviedb.org/3/movie/{movie_obj.tmdb_id}/credits?api_key={API_KEY}&language=en-US'
        resp_cred = requests.get(url_credits, timeout=3)
        data_cred = resp_cred.json()

        director = "Unknown"
        for crew in data_cred.get('crew', []):
            if crew['job'] == 'Director':
                director = crew['name']
                break

        cast_list = []
        for actor in data_cred.get('cast', [])[:5]:
            cast_list.append(actor['name'])
        cast_str = ", ".join(cast_list)

        url_movie = f'https://api.themoviedb.org/3/movie/{movie_obj.tmdb_id}?api_key={API_KEY}&language=en-US'
        resp_mov = requests.get(url_movie, timeout=3)
        data_mov = resp_mov.json()
        poster_path = data_mov.get('poster_path')

        if poster_path:
            final_poster = "https://image.tmdb.org/t/p/w500/" + poster_path
        else:
            final_poster = f"https://ui-avatars.com/api/?name={quote(movie_obj.title)}&background=333&color=fff"

        movie_obj.poster_url = final_poster
        movie_obj.director = director
        movie_obj.cast = cast_str
        movie_obj.save()

        return final_poster, director, cast_str
    except Exception:
        return f"https://ui-avatars.com/api/?name={quote(movie_obj.title)}&background=333&color=fff", "Unknown", "Unknown"

# --- 4. AUTH VIEWS (UPDATED FOR ADMIN) ---


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # --- FIX: Check if user is Admin or Normal User ---
            if user.is_superuser:
                return redirect('/admin/')  # Go to Admin Dashboard
            else:
                return redirect('/')        # Go to Home Page
            # -------------------------------------------------
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/login/')

# --- 5. NEW: EXACT SEARCH & SUGGESTIONS ---


@login_required
def exact_search(request):
    query = request.GET.get('q')
    if query:
        movie = Movie.objects.filter(title__iexact=query).first()
        if not movie:
            movie = Movie.objects.filter(title__icontains=query).first()
        if movie:
            return redirect('movie_detail', movie_id=movie.tmdb_id)
    return redirect('/')


def search_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        movies = Movie.objects.filter(title__icontains=query)[:5]
        results = [{'title': m.title, 'id': m.tmdb_id} for m in movies]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})

# --- 6. UPGRADED HOME PAGE ---


@login_required(login_url='/login/')
def index(request):
    movie_list = new_df['title'].values if new_df is not None else []
    selected_movie = None
    recommendations = []
    trending_movies = []

    mood_map = {
        'sad': 'Drama', 'cry': 'Drama', 'depressed': 'Drama',
        'happy': 'Comedy', 'funny': 'Comedy', 'laugh': 'Comedy',
        'romantic': 'Romance', 'love': 'Romance', 'relationship': 'Romance',
        'scary': 'Horror', 'fear': 'Horror', 'ghost': 'Horror',
        'exciting': 'Action', 'adventure': 'Adventure', 'fight': 'Action',
        'bored': 'Thriller', 'mystery': 'Mystery'
    }

    if request.method == 'POST':
        user_input = request.POST.get('movie_name')
        selected_movie = user_input

        if user_input in new_df['title'].values:
            movie_index = new_df[new_df['title'] == user_input].index[0]
            distances = sorted(
                list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])
            for i in distances[1:19]:
                movie_data = new_df.iloc[i[0]]
                poster = safe_fetch_poster(
                    int(movie_data.id), movie_data.title)
                recommendations.append(
                    {'title': movie_data.title, 'poster': poster, 'id': movie_data.id})

        else:
            found_genre = None
            input_lower = user_input.lower()
            for mood, genre in mood_map.items():
                if mood in input_lower:
                    found_genre = genre
                    break

            if found_genre:
                selected_movie = f"Mood: {found_genre}"
                mood_movies = new_df[new_df['tags'].str.contains(
                    found_genre, case=False, na=False)].head(18)
                for _, row in mood_movies.iterrows():
                    poster = safe_fetch_poster(int(row['id']), row['title'])
                    recommendations.append(
                        {'title': row['title'], 'poster': poster, 'id': row['id']})
            else:
                text_movies = new_df[new_df['tags'].str.contains(
                    user_input, case=False, na=False)].head(18)
                if not text_movies.empty:
                    selected_movie = f"Results for: {user_input}"
                    for _, row in text_movies.iterrows():
                        poster = safe_fetch_poster(
                            int(row['id']), row['title'])
                        recommendations.append(
                            {'title': row['title'], 'poster': poster, 'id': row['id']})
                else:
                    selected_movie = "No movies found for that mood/name."

    else:
        if new_df is not None:
            trending_samples = new_df.sample(n=18)
            for _, row in trending_samples.iterrows():
                poster = safe_fetch_poster(int(row['id']), row['title'])
                trending_movies.append(
                    {'title': row['title'], 'poster': poster, 'id': row['id']})

    return render(request, 'index.html', {
        'all_movies': movie_list,
        'selected_movie': selected_movie,
        'recommendations': recommendations,
        'trending_movies': trending_movies,
        'user': request.user
    })

# --- 7. MOVIE DETAIL PAGE ---


@login_required
def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)

    if request.method == 'POST' and 'rating' in request.POST:
        rating = float(request.POST.get('rating'))
        text = request.POST.get('review_text')
        Review.objects.create(
            user=request.user, movie=movie, rating=rating, text=text)
        return redirect('movie_detail', movie_id=movie_id)

    poster, director, cast = get_movie_data(movie)
    in_watchlist = Watchlist.objects.filter(
        user=request.user, movie=movie).exists()
    in_favorites = Favorite.objects.filter(
        user=request.user, movie=movie).exists()

    likes_count = Vote.objects.filter(movie=movie, vote_type='LIKE').count()
    dislikes_count = Vote.objects.filter(
        movie=movie, vote_type='DISLIKE').count()
    user_vote = Vote.objects.filter(user=request.user, movie=movie).first()
    current_vote = user_vote.vote_type if user_vote else None

    reviews = Review.objects.filter(movie=movie).order_by('-created_at')

    return render(request, 'movie_detail.html', {
        'movie': movie, 'poster': poster, 'director': director, 'cast': cast,
        'in_watchlist': in_watchlist, 'in_favorites': in_favorites,
        'reviews': reviews, 'likes_count': likes_count, 'dislikes_count': dislikes_count,
        'current_vote': current_vote
    })

# --- 8. ACTION BUTTONS ---


@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    item = Watchlist.objects.filter(user=request.user, movie=movie)
    if item.exists():
        item.delete()
    else:
        Watchlist.objects.create(user=request.user, movie=movie)
    get_movie_data(movie)
    return redirect('movie_detail', movie_id=movie_id)


@login_required
def toggle_favorite(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    item = Favorite.objects.filter(user=request.user, movie=movie)
    if item.exists():
        item.delete()
    else:
        Favorite.objects.create(user=request.user, movie=movie)
    get_movie_data(movie)
    return redirect('movie_detail', movie_id=movie_id)


@login_required
def toggle_vote(request, movie_id, vote_type):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    vote = Vote.objects.filter(user=request.user, movie=movie).first()
    if vote:
        if vote.vote_type == vote_type:
            vote.delete()
        else:
            vote.vote_type = vote_type
            vote.save()
    else:
        Vote.objects.create(user=request.user, movie=movie,
                            vote_type=vote_type)
    get_movie_data(movie)
    return redirect('movie_detail', movie_id=movie_id)

# --- 9. OLD WATCHLIST PAGE ---


@login_required
def my_watchlist(request):
    user = request.user
    user_list = Watchlist.objects.filter(user=user)
    saved_movies = []
    for item in user_list:
        poster, _, _ = get_movie_data(item.movie)
        saved_movies.append(
            {'title': item.movie.title, 'poster': poster, 'id': item.movie.tmdb_id})
    return render(request, 'index.html', {'trending_movies': saved_movies, 'selected_movie': None, 'all_movies': [], 'recommendations': []})

# --- 10. NEW USER PROFILE FEATURES ---


@login_required
def profile_view(request):
    return render(request, 'profile.html', {'user': request.user})


@login_required
def my_lists(request, list_type):
    user = request.user
    movies_data = []
    page_title = ""

    if list_type == 'watchlist':
        items = Watchlist.objects.filter(user=user)
        page_title = "My Watchlist"
    elif list_type == 'favorites':
        items = Favorite.objects.filter(user=user)
        page_title = "My Favorites"
    elif list_type == 'likes':
        items = Vote.objects.filter(user=user, vote_type='LIKE')
        page_title = "Movies I Liked"

    for item in items:
        poster = safe_fetch_poster(item.movie.tmdb_id, item.movie.title)
        movies_data.append(
            {'id': item.movie.tmdb_id, 'title': item.movie.title, 'poster': poster})

    return render(request, 'my_lists.html', {'movies': movies_data, 'page_title': page_title})


@login_required
def my_reviews(request):
    reviews = Review.objects.filter(user=request.user).order_by('-created_at')
    reviews_data = []
    for review in reviews:
        poster = safe_fetch_poster(review.movie.tmdb_id, review.movie.title)
        reviews_data.append({
            'id': review.id, 'movie_title': review.movie.title,
            'rating': review.rating, 'text': review.text,
            'date': review.created_at, 'poster': poster
        })
    return render(request, 'my_reviews.html', {'reviews': reviews_data})


@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    if request.method == 'POST':
        review.rating = float(request.POST.get('rating'))
        review.text = request.POST.get('review_text')
        review.save()
        return redirect('my_reviews')
    return render(request, 'edit_review.html', {'review': review})

# --- 11. ABOUT PAGE ---


def about(request):
    return render(request, 'about.html')
