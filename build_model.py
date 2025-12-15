import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

print("1. Loading data...")
try:
    movies = pd.read_csv('movies.csv')
    print(f"   - Loaded {len(movies)} movies.")
except FileNotFoundError:
    print("   - Error: movies.csv not found!")
    exit()

# --- THE MISSING STEP: COOKING THE DATA ---
print("2. Processing data (Creating 'tags')...")

# Fill missing values with empty strings to prevent errors
features = ['overview', 'genres', 'keywords', 'cast', 'crew']
for feature in features:
    if feature in movies.columns:
        movies[feature] = movies[feature].fillna('')
    else:
        # If a column is missing, create it as empty
        movies[feature] = ''

# Create the 'tags' column by combining everything
# This is what was missing!
movies['tags'] = (movies['overview'] + ' ' +
                  movies['genres'] + ' ' +
                  movies['keywords'] + ' ' +
                  movies['cast'] + ' ' +
                  movies['crew'])

# --- END OF COOKING STEP ---

print("3. Vectorizing data (Converting text to numbers)...")
# We use 'tags' now that we have created it
cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(movies['tags']).toarray()

print("4. Calculating Similarity (The AI Brain)...")
similarity = cosine_similarity(vectors)

print("5. Saving files...")
pickle.dump(movies.to_dict(), open('movie_recommender.pkl', 'wb'))
pickle.dump(similarity, open('similarity.pkl', 'wb'))

print("------------------------------------------------")
print("SUCCESS! System is repaired.")
print("Created: movie_recommender.pkl")
print("Created: similarity.pkl")
print("------------------------------------------------")
