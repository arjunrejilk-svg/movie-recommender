import os
import django
import pandas as pd

# 1. Unlock the library (Django Setup)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

# 2. Define the script


def import_movies():
    # We import the model INSIDE the function so it doesn't break
    from core.models import Movie

    print("Reading CSV file...")
    try:
        df = pd.read_csv('movies.csv')
        # Fill NaN values to prevent errors
        df = df.fillna('')

        movies_to_create = []
        print("Preparing data...")

        # Check existing IDs to avoid duplicates
        existing_ids = set(Movie.objects.values_list('tmdb_id', flat=True))

        for index, row in df.iterrows():
            if row['id'] not in existing_ids:
                movies_to_create.append(
                    Movie(
                        title=row['title'],
                        overview=row['overview'],
                        tmdb_id=row['id'],
                        genres=row['genres']
                    )
                )
                existing_ids.add(row['id'])

        if movies_to_create:
            Movie.objects.bulk_create(movies_to_create)
            print(
                f"Success! Added {len(movies_to_create)} new movies to the database.")
        else:
            print("No new movies to add (all already exist).")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    import_movies()
