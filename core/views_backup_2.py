from django.shortcuts import render
import pandas as pd
import pickle
import requests
import os
from urllib.parse import quote

# --- FIX: ROBUST PATH FINDING ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_data():
    try:
        # Try finding the file in the current folder (Standard)
        movies_dict = pickle.load(open('movie_recommender.pkl', 'rb'))
        similarity = pickle.load(open('similarity.pkl', 'rb'))
        return pd.DataFrame(movies_dict), similarity
    except FileNotFoundError:
        try:
            # Try finding it one folder up (Backup)
            path_movies = os.path.join(base_dir, 'movie_recommender.pkl')
            path_sim = os.path.join(base_dir, 'similarity.pkl')
            movies_dict = pickle.load(open(path_movies, 'rb'))
            similarity = pickle.load(open(path_sim, 'rb'))
            return pd.DataFrame(movies_dict), similarity
        except:
            print("CRITICAL ERROR: Could not find .pkl files!")
            return None, None


# Load the data safely
new_df, similarity = load_data()

# --- UPDATED HELPER FUNCTION: Fetch Poster or Letter Tile ---
# We now pass the title too, so we can use it if the poster fails.


def fetch_poster(movie_id, movie_title):
    try:
        response = requests.get(
            f'https://api.themoviedb.org/3/movie/{movie_id}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US',
            timeout=3  # Short timeout so it doesn't hang
        )
        data = response.json()
        poster_path = data.get('poster_path')

        if poster_path:
            # Success: Found a real poster
            return "https://image.tmdb.org/t/p/w500/" + poster_path
        else:
            raise ValueError("No poster path found in API response")

    except:
        # Fallback: Generate a Letter Tile based on the Movie Title
        # We encode the title to handle spaces and special characters nicely in the URL
        safe_title = quote(movie_title)
        # Creates a dark grey tile with white text (matches Netflix theme)
        return f"https://ui-avatars.com/api/?name={safe_title}&background=333&color=fff&size=500&font-size=0.4&length=1"


def index(request):
    # SAFETY CHECK: If data didn't load, show an error
    if new_df is None:
        return render(request, 'index.html', {'error': 'Database problem. Check console.'})

    movie_list = new_df['title'].values
    selected_movie = None
    recommendations = []
    trending_movies = []

    # CASE 1: User clicked "Get Recommendations"
    if request.method == 'POST':
        selected_movie = request.POST.get('movie_name')

        if selected_movie in new_df['title'].values:
            movie_index = new_df[new_df['title'] == selected_movie].index[0]
            distances = sorted(
                list(enumerate(similarity[movie_index])), reverse=True, key=lambda x: x[1])

            # Get Top 18 Recommendations
            for i in distances[1:19]:
                movie_data = new_df.iloc[i[0]]
                recommendations.append({
                    'title': movie_data.title,
                    # Pass both ID and Title to the fetcher
                    'poster': fetch_poster(movie_data.id, movie_data.title)
                })
        else:
            selected_movie = "Movie not found"

    # CASE 2: Home Page (Show Trending)
    else:
        # Pick 12 Random movies
        trending_samples = new_df.sample(n=12)

        for index, row in trending_samples.iterrows():
            trending_movies.append({
                'title': row['title'],
                # Pass both ID and Title to the fetcher
                'poster': fetch_poster(row['id'], row['title'])
            })

    return render(request, 'index.html', {
        'all_movies': movie_list,
        'selected_movie': selected_movie,
        'recommendations': recommendations,
        'trending_movies': trending_movies
    })
