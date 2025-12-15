import os
import django
import requests
import time
from urllib.parse import quote

# 1. Setup Django (MUST BE FIRST)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

API_KEY = '8265bd1679663a7ea12ac168da84d2e8'


def fix_movies():
    # --- IMPORT INSIDE FUNCTION TO PREVENT ERRORS ---
    from core.models import Movie

    # Find movies that are missing data (Director is 'Unknown')
    movies_to_fix = Movie.objects.filter(director="Unknown")
    total = movies_to_fix.count()

    print(f"Found {total} movies that need details...")
    print("Starting repairs. Press Ctrl+C to stop at any time.")

    count = 0
    for movie in movies_to_fix:
        count += 1
        try:
            # Fetch Data
            url = f'https://api.themoviedb.org/3/movie/{movie.tmdb_id}?api_key={API_KEY}&append_to_response=credits'
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()

                # 1. Get Poster
                poster_path = data.get('poster_path')
                if poster_path:
                    movie.poster_url = "https://image.tmdb.org/t/p/w500/" + poster_path

                # 2. Get Director
                credits = data.get('credits', {})
                for crew in credits.get('crew', []):
                    if crew['job'] == 'Director':
                        movie.director = crew['name']
                        break

                # 3. Get Cast
                cast_list = []
                for actor in credits.get('cast', [])[:5]:
                    cast_list.append(actor['name'])
                movie.cast = ", ".join(cast_list)

                # Save permanently
                movie.save()
                print(f"[{count}/{total}] Fixed: {movie.title}")
            else:
                print(
                    f"[{count}/{total}] Skipped: {movie.title} (Not found on TMDB)")

        except Exception as e:
            print(f"[{count}/{total}] Error fetching {movie.title}: {e}")

        # Sleep a tiny bit to be safe
        time.sleep(0.2)


if __name__ == '__main__':
    fix_movies()
