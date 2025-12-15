import pickle
import gzip
import os

# This script must be next to manage.py and similarity.pkl
print("Starting compression...")

if not os.path.exists('similarity.pkl'):
    print("ERROR: I cannot find similarity.pkl here!")
else:
    # 1. Load the heavy file
    with open('similarity.pkl', 'rb') as f_in:
        data = pickle.load(f_in)

    # 2. Save it as a compressed file
    with gzip.open('similarity.pkl.gz', 'wb') as f_out:
        pickle.dump(data, f_out)

    print("SUCCESS! Created 'similarity.pkl.gz'.")
