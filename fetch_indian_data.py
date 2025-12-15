import requests
import pandas as pd
import time
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
API_KEY = "481c93c9e108ef4c1728349f0fe4583c"
MOVIES_PER_LANGUAGE = 50
LANGUAGES = {
    'ml': 'Malayalam',
    'ta': 'Tamil',
    'hi': 'Hindi',
    'te': 'Telugu'
}

# --- 1. SETUP A "SMART" SESSION (Auto-Retry) ---
# This tells Python: "If the connection fails, wait a bit and try again 3 times."
session = requests.Session()
# Retry on connection errors (status 500, 502, etc.)
retry = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


def get_movie_details(movie_id):
    """Fetches full details including keywords and credits for a single movie"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&append_to_response=credits,keywords"
        # Use 'session.get' instead of 'requests.get' for stability
        response = session.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        # Extract Details
        genres = " ".join([g['name'] for g in data.get('genres', [])])
        keywords = " ".join([k['name'] for k in data.get(
            'keywords', {}).get('keywords', [])])
        cast_list = data.get('credits', {}).get('cast', [])[:3]
        cast = " ".join([c['name'] for c in cast_list])

        crew_list = data.get('credits', {}).get('crew', [])
        director = "Unknown"
        for c in crew_list:
            if c['job'] == 'Director':
                director = c['name']
                break

        return {
            'id': data['id'],
            'title': data['title'],
            'genres': genres,
            'overview': data.get('overview', ''),
            'keywords': keywords,
            'cast': cast,
            'crew': director
        }
    except Exception as e:
        print(f"Skipping ID {movie_id} due to error: {e}")
        return None


def fetch_movies_by_language(lang_code, lang_name):
    print(f"\n--- Fetching Top {MOVIES_PER_LANGUAGE} {lang_name} Movies ---")
    movies_collected = []
    page = 1

    while len(movies_collected) < MOVIES_PER_LANGUAGE:
        discover_url = f"https://api.themoviedb.org/3/discover/movie?api_key={API_KEY}&with_original_language={lang_code}&sort_by=vote_count.desc&page={page}"

        try:
            response = session.get(discover_url, timeout=10)
            data = response.json()

            if 'results' not in data:
                break

            for item in data['results']:
                if len(movies_collected) >= MOVIES_PER_LANGUAGE:
                    break

                print(f"Processing: {item['title']}...", end="\r")

                full_details = get_movie_details(item['id'])
                if full_details:
                    movies_collected.append(full_details)

                # --- IMPORTANT: SLEEP LONGER TO PREVENT CRASHES ---
                time.sleep(0.2)

            page += 1

        except Exception as e:
            print(f"Error on page {page}: {e}")
            time.sleep(3)  # Wait 3 seconds if internet hiccups
            continue

    print(f"\nDone! Collected {len(movies_collected)} {lang_name} movies.")
    return movies_collected


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    all_new_movies = []

    # 1. Fetch from API
    for code, name in LANGUAGES.items():
        lang_movies = fetch_movies_by_language(code, name)
        all_new_movies.extend(lang_movies)

    # 2. Load existing CSV safely
    print("\nSaving data...")

    # Check if file exists properly
    csv_file = 'movies.csv'
    if os.path.exists(csv_file):
        try:
            existing_df = pd.read_csv(csv_file)
            print(f"Loaded {len(existing_df)} existing movies.")
        except:
            print("Warning: Could not read existing movies.csv. Starting fresh.")
            existing_df = pd.DataFrame()
    else:
        existing_df = pd.DataFrame()

    # 3. Combine and Save
    if all_new_movies:
        new_df = pd.DataFrame(all_new_movies)

        if not existing_df.empty:
            # Filter out duplicates
            existing_ids = existing_df['id'].tolist()
            new_df = new_df[~new_df['id'].isin(existing_ids)]

        final_df = pd.concat([existing_df, new_df], ignore_index=True)
        final_df.to_csv(csv_file, index=False)

        print(f"\nSUCCESS! -----------------------------------")
        print(f"Added {len(new_df)} new movies.")
        print(f"Total Database Size: {len(final_df)} movies.")
        print("Now run: python build_model.py")
    else:
        print("\nNo new movies were fetched. Check your internet connection.")
