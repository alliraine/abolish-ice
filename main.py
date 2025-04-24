import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from atproto import Client
from dotenv import load_dotenv

# --- Config ---
URL = 'https://www.ice.gov/identify-and-arrest/287g'
DATA_DIR = './data'
LOG_FILE = '287g_scraper.log'
PREV_FILES = {
    'participating': os.path.join(DATA_DIR, 'participating_prev.csv'),
    'pending': os.path.join(DATA_DIR, 'pending_prev.csv')
}

SUPPORT_TYPE_EXPLANATIONS = {
    'Jail Enforcement Model': "The Jail Enforcement Model is designed to identify and process removable aliens — with criminal or pending criminal charges — who are arrested by state or local law enforcement agencies.",
    'Task Force Model': "The Task Force Model serves as a force multiplier for law enforcement agencies to enforce limited immigration authority with ICE oversight during their routine police duties.",
    'Warrant Service Officer': "The Warrant Service Officer program allows ICE to train, certify and authorize state and local law enforcement officers to serve and execute administrative warrants on aliens in their agency’s jail."
}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Load .env if available ---
if os.path.exists('.env'):
    load_dotenv()

def get_excel_links():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = {}
    for button in soup.find_all('a', class_='usa-button'):
        href = button['href']
        if 'Participating Agencies' in button.text:
            links['participating'] = href
        elif 'Pending Agencies' in button.text:
            links['pending'] = href
    return links

def download_file(link, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    response = requests.get(link)
    with open(filename, 'wb') as f:
        f.write(response.content)

def load_excel(filepath):
    return pd.read_excel(filepath)

def normalize(df):
    df = df.dropna(how='all')
    df = df.copy()
    df.columns = [col.upper() for col in df.columns]

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

            # Only try datetime conversion on likely date columns
            if 'DATE' in col or 'SIGNED' in col:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception:
                    pass

    return df

def compare_data(new_df, old_df):
    new_df_norm = normalize(new_df)
    old_df_norm = normalize(old_df)

    # Use only common columns, sort, and reset index
    common_cols = list(set(new_df_norm.columns) & set(old_df_norm.columns))
    new_df_final = new_df_norm[common_cols].sort_values(by=common_cols).reset_index(drop=True)
    old_df_final = old_df_norm[common_cols].sort_values(by=common_cols).reset_index(drop=True)

    # Diff
    comparison = pd.concat([new_df_final, old_df_final]).drop_duplicates(keep=False)
    added = comparison[comparison.isin(new_df_final.to_dict(orient='list')).all(axis=1)]
    removed = comparison[comparison.isin(old_df_final.to_dict(orient='list')).all(axis=1)]

    return added, removed

def format_posts(added, removed, label):
    posts = []
    thread_info = []
    if label.lower() == 'participating':
        for _, row in added.iterrows():
            agency = row.get('LAW ENFORCEMENT AGENCY', 'Unknown Agency')
            state = row.get('STATE', 'Unknown State')
            support = row.get('SUPPORT TYPE', 'Unknown')
            posts.append(f"🚨 {agency} in {state} has been added to the 287(g) program. Their support type is {support}.")
            explanation = SUPPORT_TYPE_EXPLANATIONS.get(support)
            if explanation:
                thread_info.append(f"Explanation of {support}: {explanation}\nSource: https://www.ice.gov/identify-and-arrest/287g")

        for _, row in removed.iterrows():
            agency = row.get('LAW ENFORCEMENT AGENCY', 'Unknown Agency')
            state = row.get('STATE', 'Unknown State')
            support = row.get('SUPPORT TYPE', 'Unknown')
            posts.append(f"{agency} in {state} has been removed from the 287(g) program. Their support type was {support}.")
            explanation = SUPPORT_TYPE_EXPLANATIONS.get(support)
            if explanation:
                thread_info.append(f"Explanation of {support}: {explanation}\nSource: https://www.ice.gov/identify-and-arrest/287g")

    elif label.lower() == 'pending':
        for _, row in added.iterrows():
            agency = row.get('LAW ENFORCEMENT AGENCY', 'Unknown Agency')
            state = row.get('STATE', 'Unknown State')
            support = row.get('SUPPORT TYPE', 'Unknown')
            posts.append(f"🚨 {agency} in {state} has applied to the 287(g) program under the support type of {support}.")
            explanation = SUPPORT_TYPE_EXPLANATIONS.get(support)
            if explanation:
                thread_info.append(f"Explanation of {support}: {explanation}\nSource: https://www.ice.gov/identify-and-arrest/287g")

    return posts, thread_info

def post_to_bluesky(posts, threads, handle, password):
    try:
        client = Client()
        client.login(handle, password)
        thread_uri = None

        for i, post in enumerate(posts):
            logging.info("Posting to Bluesky: %s", post)
            if i == 0:
                response = client.send_post(text=post)
                thread_uri = response.uri
            else:
                client.send_post(text=post, reply_to=thread_uri)

        for post in threads:
            client.send_post(text=post, reply_to=thread_uri)

    except Exception as e:
        logging.error("Failed to post to Bluesky: %s", e)

def save_csv(df, path):
    df.to_csv(path, index=False)

# === MAIN WORKFLOW ===
links = get_excel_links()
logging.info("Found links: %s", links)

all_posts = []
all_threads = []

for key, url in links.items():
    current_path = os.path.join(DATA_DIR, f"{key}_current.xlsx")
    logging.info("Downloading file for %s from %s", key, url)
    download_file(url, current_path)
    current_df = load_excel(current_path)

    if os.path.exists(PREV_FILES[key]):
        prev_df = pd.read_csv(PREV_FILES[key])
        added, removed = compare_data(current_df, prev_df)
        logging.info("Found %d added and %d removed for %s", len(added), len(removed), key)
        posts, threads = format_posts(added, removed, key)
        all_posts.extend(posts)
        all_threads.extend(threads)
    else:
        logging.warning("No previous data for %s. Saving current version.", key)

    save_csv(current_df, PREV_FILES[key])

if all_posts:
    handle = os.environ.get('BSKY_HANDLE')
    password = os.environ.get('BSKY_PASSWORD')
    if handle and password:
        post_to_bluesky(all_posts, all_threads, handle, password)
    else:
        logging.error("Bluesky credentials not set in environment variables.")
else:
    logging.info("No changes detected. Nothing to post.")
