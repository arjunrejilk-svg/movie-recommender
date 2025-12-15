from django.shortcuts import render
import joblib
import os
import requests  # <--- New library to fetch posters

# 1. Load the model once
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(base_dir, 'movie_recommender.pkl')

data = joblib.load(model_path)
similarity = data['similarity']
movies = data['movie_data']

# 2. Function to fetch poster from TMDB API
# Updated fetch_poster function


def fetch_poster(movie_id, title):  # <--- Note: We now accept 'title' too
    api_key = "481c93c9e108ef4c1728349f0fe4583c"  # Your Key
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
    try:
        response = requests.get(url)
        data = response.json()
        poster_path = data.get('poster_path')

        if poster_path:
            # Return the real poster if found
            return "https://image.tmdb.org/t/p/w500" + poster_path
        else:
            # Fallback 1: If API works but movie has no image, use colorful initials
            return f"https://ui-avatars.com/api/?name={title}&background=random&size=500"

    except:
        # Fallback 2: If API fails completely, use colorful initials
        return f"https://ui-avatars.com/api/?name={title}&background=random&size=500"


def index(request):
    # List of dictionaries: [{'title': 'Avatar', 'poster': 'http...'}, ...]
    recommendations = []
    selected_movie = ""

    if request.method == 'POST':
        selected_movie = request.POST.get('movie_name')

        if selected_movie in movies['title'].values:
            idx = movies[movies['title'] == selected_movie].index[0]
            scores = list(enumerate(similarity[idx]))
            scores = sorted(scores, key=lambda x: x[1], reverse=True)[
                1:19]  # Get top 6

            # Loop through the results and fetch data
            for i in scores:
                movie_id = movies.iloc[i[0]].id
                movie_title = movies.iloc[i[0]].title

                # Fetch the real poster
                poster_url = fetch_poster(movie_id, movie_title)

                # Add to list
                recommendations.append(
                    {'title': movie_title, 'poster': poster_url})

        else:
            # Handle case where movie isn't found
            selected_movie = "Movie not found"

    all_movies = movies['title'].values.tolist()

    return render(request, 'index.html', {
        'recommendations': recommendations,
        'all_movies': all_movies,
        'selected_movie': selected_movie
    })
