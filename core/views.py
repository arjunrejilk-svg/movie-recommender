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
        pkl_path = os.path.join(settings.BASE_DIR, 'movie_recommender.pkl')
        sim_path = os.path.join(settings.BASE_DIR, 'similarity.pkl.gz')
        movies_dict = pickle.load(open(pkl_path, 'rb'))
        with gzip.open(sim_path, 'rb') as f:
            similarity = pickle.load(f)
        return pd.DataFrame(movies_dict), similarity
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


new_df, similarity = load_data()

# --- 2. HELPER: SAFE POSTER FETCH ---


def safe_fetch_poster(tmdb_id, title):
    try:
        db_movie = Movie.objects.filter(tmdb_id=tmdb_id).first()
        if db_movie and db_movie.poster_url:
            return db_movie.poster_url
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

# --- 3. HELPER: GET FULL MOVIE DATA ---


def get_movie_data(movie_obj):
    if movie_obj.poster_url and movie_obj.director != "Unknown":
        return movie_obj.poster_url, movie_obj.director, movie_obj.cast
    try:
        url_credits = f'https://api.themoviedb.org/3/movie/{movie_obj.tmdb_id}/credits?api_key={API_KEY}&language=en-US'
        data_cred = requests.get(url_credits, timeout=3).json()
        director = "Unknown"
        for crew in data_cred.get('crew', []):
            if crew['job'] == 'Director':
                director = crew['name']
                break
        cast_str = ", ".join([a['name']
                             for a in data_cred.get('cast', [])[:5]])

        url_movie = f'https://api.themoviedb.org/3/movie/{movie_obj.tmdb_id}?api_key={API_KEY}&language=en-US'
        data_mov = requests.get(url_movie, timeout=3).json()
        poster_path = data_mov.get('poster_path')
        final_poster = "https://image.tmdb.org/t/p/w500/" + \
            poster_path if poster_path else f"https://ui-avatars.com/api/?name={quote(movie_obj.title)}&background=333&color=fff"

        movie_obj.poster_url = final_poster
        movie_obj.director = director
        movie_obj.cast = cast_str
        movie_obj.save()
        return final_poster, director, cast_str
    except Exception:
        return f"https://ui-avatars.com/api/?name={quote(movie_obj.title)}&background=333&color=fff", "Unknown", "Unknown"

# --- 4. AUTH VIEWS ---


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
            return redirect('/admin/') if user.is_superuser else redirect('/')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/login/')

# --- 5. SEARCH & SUGGESTIONS ---


@login_required
def exact_search(request):
    query = request.GET.get('q')
    if query:
        movie = Movie.objects.filter(title__iexact=query).first(
        ) or Movie.objects.filter(title__icontains=query).first()
        if movie:
            return redirect('movie_detail', movie_id=movie.tmdb_id)
    return redirect('/')


def search_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        movies = Movie.objects.filter(title__icontains=query)[:5]
        return JsonResponse({'results': [{'title': m.title, 'id': m.tmdb_id} for m in movies]})
    return JsonResponse({'results': []})

# --- 6. UPGRADED HOME PAGE ---


@login_required(login_url='/login/')
def index(request):
    movie_list = new_df['title'].values if new_df is not None else []
    selected_movie = None
    search_query = ""
    recommendations = []
    trending_movies = []

    # 1. Inputs
    selected_category = request.GET.get(
        'category') or request.POST.get('category', 'All')

    # 2. Strict Language Map
    lang_map = {
        'Hollywood': ('en', ['english', 'usa', 'uk', 'hollywood']),
        'Bollywood': ('hi', ['hindi', 'india', 'bollywood']),
        'Mollywood': ('ml', ['malayalam', 'kerala', 'mollywood']),
        'Kollywood': ('ta', ['tamil', 'chennai', 'kollywood']),
        'Tollywood': ('te', ['telugu', 'hyderabad', 'tollywood'])
    }
    target_data = lang_map.get(selected_category)

    # 3. Mood Map
    mood_map = {
        'sad': 'Drama', 'cry': 'Drama', 'depressed': 'Drama', 'upset': 'Drama',
        'happy': 'Comedy', 'funny': 'Comedy', 'laugh': 'Comedy', 'joke': 'Comedy',
        'romantic': 'Romance', 'love': 'Romance', 'date': 'Romance', 'crush': 'Romance',
        'scary': 'Horror', 'fear': 'Horror', 'ghost': 'Horror', 'creepy': 'Horror',
        'exciting': 'Action', 'adventure': 'Adventure', 'fight': 'Action', 'war': 'War',
        'bored': 'Thriller', 'mystery': 'Mystery', 'suspense': 'Thriller',
        'kids': 'Animation', 'cartoon': 'Animation', 'family': 'Family'
    }

    # Strict Language Check Helper
    def check_language_strict(idx, target_data):
        if selected_category == 'All' or target_data is None:
            return True
        target_code, target_keywords = target_data

        if 'original_language' in new_df.columns:
            movie_lang = new_df.iloc[idx]['original_language']
            if movie_lang == target_code:
                return True
            if movie_lang != target_code:
                return False  # Strict reject

        row_tags = str(new_df.iloc[idx]['tags']).lower()
        for keyword in target_keywords:
            if keyword in row_tags:
                return True
        return False

    if request.method == 'POST':
        search_query = request.POST.get('movie_name', '').strip()
        user_input = search_query

        # --- SEARCH LOGIC (Same as before, perfectly strict) ---
        if user_input in new_df['title'].values:
            selected_movie = f"Because you watched {user_input}"
            if selected_category != 'All':
                selected_movie += f" ({selected_category})"

            movie_index = new_df[new_df['title'] == user_input].index[0]
            distances = sorted(
                list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])

            count = 0
            for i in distances[1:200]:
                if count >= 12:
                    break
                idx = i[0]
                if check_language_strict(idx, target_data):
                    movie_data = new_df.iloc[idx]
                    poster = safe_fetch_poster(
                        int(movie_data.id), movie_data.title)
                    recommendations.append(
                        {'title': movie_data.title, 'poster': poster, 'id': movie_data.id})
                    count += 1
            if not recommendations:
                selected_movie = f"No {selected_category} movies found similar to '{user_input}'"

        elif user_input:
            found_genre = None
            input_lower = user_input.lower()
            for mood, genre in mood_map.items():
                if mood in input_lower:
                    found_genre = genre
                    break

            if found_genre:
                selected_movie = f"Mood: {found_genre}"
                if selected_category != 'All':
                    selected_movie += f" ({selected_category})"
                condition = new_df['tags'].str.contains(
                    found_genre, case=False, na=False)
                if target_data:
                    target_code, target_keywords = target_data
                    if 'original_language' in new_df.columns:
                        condition = condition & (
                            new_df['original_language'] == target_code)
                    else:
                        condition = condition & new_df['tags'].str.contains(
                            '|'.join(target_keywords), case=False, na=False)

                mood_movies = new_df[condition]
                if not mood_movies.empty:
                    mood_movies = mood_movies.sample(
                        n=min(12, len(mood_movies)))
                    for _, row in mood_movies.iterrows():
                        poster = safe_fetch_poster(
                            int(row['id']), row['title'])
                        recommendations.append(
                            {'title': row['title'], 'poster': poster, 'id': row['id']})
                if not recommendations:
                    selected_movie = f"No {selected_category} {found_genre} movies found."

            else:
                selected_movie = f"Results for: {user_input}"
                condition = new_df['tags'].str.contains(
                    user_input, case=False, na=False)
                if target_data:
                    target_code, target_keywords = target_data
                    if 'original_language' in new_df.columns:
                        condition = condition & (
                            new_df['original_language'] == target_code)
                    else:
                        condition = condition & new_df['tags'].str.contains(
                            '|'.join(target_keywords), case=False, na=False)

                text_movies = new_df[condition].head(12)
                for _, row in text_movies.iterrows():
                    poster = safe_fetch_poster(int(row['id']), row['title'])
                    recommendations.append(
                        {'title': row['title'], 'poster': poster, 'id': row['id']})
                if not recommendations:
                    selected_movie = f"No {selected_category} movies found for '{user_input}'"

    # --- SHOW MIXED TRENDING (New Logic) ---
    else:
        if new_df is not None:
            # Create a Diverse Mix
            frames = []
            langs_to_mix = ['en', 'hi', 'ml', 'ta', 'te']

            if 'original_language' in new_df.columns:
                # Try to take 3 from each language
                for lang in langs_to_mix:
                    lang_group = new_df[new_df['original_language'] == lang]
                    if not lang_group.empty:
                        frames.append(lang_group.sample(
                            n=min(3, len(lang_group))))

                # Fill the rest with random movies to reach 18
                frames.append(new_df.sample(n=18))

                # Combine, Shuffle, and Pick Top 18
                mixed_df = pd.concat(
                    frames).drop_duplicates().sample(frac=1).head(18)
            else:
                # Fallback if no language column
                mixed_df = new_df.sample(n=18)

            for _, row in mixed_df.iterrows():
                poster = safe_fetch_poster(int(row['id']), row['title'])
                trending_movies.append(
                    {'title': row['title'], 'poster': poster, 'id': row['id']})

    return render(request, 'index.html', {
        'all_movies': movie_list,
        'selected_movie': selected_movie,
        'search_query': search_query,
        'recommendations': recommendations,
        'trending_movies': trending_movies,
        'selected_category': selected_category,
        'user': request.user
    })

# --- 7. MOVIE DETAIL PAGE ---


@login_required
def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    if request.method == 'POST' and 'rating' in request.POST:
        Review.objects.create(user=request.user, movie=movie, rating=float(
            request.POST['rating']), text=request.POST['review_text'])
        return redirect('movie_detail', movie_id=movie_id)
    poster, director, cast = get_movie_data(movie)
    return render(request, 'movie_detail.html', {
        'movie': movie, 'poster': poster, 'director': director, 'cast': cast,
        'in_watchlist': Watchlist.objects.filter(user=request.user, movie=movie).exists(),
        'in_favorites': Favorite.objects.filter(user=request.user, movie=movie).exists(),
        'reviews': Review.objects.filter(movie=movie).order_by('-created_at'),
        'likes_count': Vote.objects.filter(movie=movie, vote_type='LIKE').count(),
        'dislikes_count': Vote.objects.filter(movie=movie, vote_type='DISLIKE').count(),
        'current_vote': (Vote.objects.filter(user=request.user, movie=movie).first().vote_type if Vote.objects.filter(user=request.user, movie=movie).first() else None)
    })

# --- 8. ACTION BUTTONS ---


@login_required
def toggle_watchlist(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    Watchlist.objects.get(user=request.user, movie=movie).delete() if Watchlist.objects.filter(
        user=request.user, movie=movie).exists() else Watchlist.objects.create(user=request.user, movie=movie)
    get_movie_data(movie)
    return redirect('movie_detail', movie_id=movie_id)


@login_required
def toggle_favorite(request, movie_id):
    movie = get_object_or_404(Movie, tmdb_id=movie_id)
    Favorite.objects.get(user=request.user, movie=movie).delete() if Favorite.objects.filter(
        user=request.user, movie=movie).exists() else Favorite.objects.create(user=request.user, movie=movie)
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
    user_list = Watchlist.objects.filter(user=request.user)
    saved_movies = [{'title': item.movie.title, 'poster': get_movie_data(
        item.movie)[0], 'id': item.movie.tmdb_id} for item in user_list]
    return render(request, 'index.html', {'trending_movies': saved_movies, 'selected_movie': None, 'all_movies': [], 'recommendations': []})

# --- 10. NEW USER PROFILE FEATURES ---


@login_required
def profile_view(request): return render(
    request, 'profile.html', {'user': request.user})


@login_required
def my_lists(request, list_type):
    if list_type == 'watchlist':
        items = Watchlist.objects.filter(user=request.user)
        page_title = "My Watchlist"
    elif list_type == 'favorites':
        items = Favorite.objects.filter(user=request.user)
        page_title = "My Favorites"
    elif list_type == 'likes':
        items = Vote.objects.filter(user=request.user, vote_type='LIKE')
        page_title = "Movies I Liked"
    return render(request, 'my_lists.html', {'movies': [{'id': item.movie.tmdb_id, 'title': item.movie.title, 'poster': safe_fetch_poster(item.movie.tmdb_id, item.movie.title)} for item in items], 'page_title': page_title})


@login_required
def my_reviews(request):
    reviews = Review.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_reviews.html', {'reviews': [{'id': r.id, 'movie_title': r.movie.title, 'rating': r.rating, 'text': r.text, 'date': r.created_at, 'poster': safe_fetch_poster(r.movie.tmdb_id, r.movie.title)} for r in reviews]})


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


def about(request): return render(request, 'about.html')
