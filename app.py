import requests
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

def create_response(message, status_code):
    """Reusable function to create JSON responses."""
    return jsonify(message), status_code

app = Flask(__name__)

# Jellyfin Server Configuration
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")
JELLYFIN_SERVER_URL = os.getenv("JELLYFIN_SERVER_URL")
TARGET_USERNAME = os.getenv("TARGET_USERNAME")
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN")
JELLYFIN_USER_ID = os.getenv("JELLYFIN_USER_ID")

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    auth_header = request.headers.get("Authorization")
    print(f"Received Authorization header: {auth_header}")

    if WEBHOOK_AUTH_TOKEN and auth_header != f"Bearer {WEBHOOK_AUTH_TOKEN}":
        return create_response({"error": "Unauthorized"}, 401)

    if not request.is_json:
        return create_response({"error": "Invalid JSON payload"}, 400)

    data = request.get_json()
    print(f"Received JSON payload: {data}")

    request_data = data.get("request")
    if not request_data:
        return handle_missing_payload("Request data missing in payload")

    requested_by_username = request_data.get("requestedBy_username")
    if requested_by_username != TARGET_USERNAME:
        print(f"Info: Ignored request by user {requested_by_username}")
        return create_response({"status": "Ignored - Not the target user"}, 200)

    media_data = data.get("media")
    if not media_data:
        return handle_missing_payload("Media data missing in payload")

    media_id = media_data.get("tmdbId")
    tvdb_id = media_data.get("tvdbId")
    imdb_id = media_data.get("imdbId")
    media_type = media_data.get("media_type")
    title = data.get("subject")

    if not media_id and not tvdb_id and not imdb_id and not media_type:
        return handle_missing_payload("Invalid media data")

    jellyfin_item_id = get_jellyfin_item_id(media_id, tvdb_id, imdb_id, media_type, title)
    if not jellyfin_item_id:
        return create_response({"error": "Item not found in Jellyfin"}, 404)

    success = add_tag_and_lock_metadata(jellyfin_item_id)
    if success:
        return create_response({"status": "Tag added and metadata locked"}, 204)
    else:
        return create_response({"error": "Failed to update metadata"}, 500)

def handle_missing_payload(error_message):
    print(f"Error: {error_message}")
    return create_response({"error": error_message}, 400)

def get_jellyfin_item_id(tmdb_id, tvdb_id, imdb_id, media_type, title):
    headers = {"X-Emby-Token": JELLYFIN_API_KEY}
    search_url = f"{JELLYFIN_SERVER_URL}/Items"

    def log_results(items, method):
        print(f"{method} search returned {len(items)} items:")
        for item in items:
            print(f"- ID: {item['Id']}, Name: {item['Name']}")

    params = {
        "fields": "ProviderIds,BasicSyncInfo",
        "userId": JELLYFIN_USER_ID,
        "IncludeItemTypes": "Movie" if media_type == "movie" else "Series",
        "Recursive": "true",
    }

    for provider_id, id_value in [("Imdb", imdb_id), ("Tmdb", tmdb_id), ("Tvdb", tvdb_id)]:
        if id_value:
            params["AnyProviderIdEquals"] = id_value
            response = requests.get(search_url, headers=headers, params=params)
            if response.status_code == 200:
                items = response.json().get("Items", [])
                log_results(items, f"{provider_id} ID")
                for item in items:
                    if item["ProviderIds"].get(provider_id) == id_value:
                        return item["Id"]

    if title:
        title_without_year = title.rsplit("(", 1)[0].strip()
        params["SearchTerm"] = title_without_year
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json().get("Items", [])
            log_results(items, "Title")
            for item in items:
                if item["Name"].lower() == title_without_year.lower():
                    return item["Id"]

    print(f"Error: No item found for TMDB ID: {tmdb_id}, TVDB ID: {tvdb_id}, IMDb ID: {imdb_id}, or Title: {title}")
    return None

def add_tag_and_lock_metadata(item_id):
    headers = {"X-Emby-Token": JELLYFIN_API_KEY}
    metadata_url = f"{JELLYFIN_SERVER_URL}/Items/{item_id}?userId={JELLYFIN_USER_ID}"
    metadata_response = requests.get(metadata_url, headers=headers)

    if metadata_response.status_code != 200:
        print(f"Error: Failed to fetch metadata for item ID {item_id} - Status: {metadata_response.status_code} - Response: {metadata_response.text}")
        return False

    metadata = metadata_response.json()
    title = metadata.get("Name", "Unknown Title")

    if "Tags" not in metadata or not metadata["Tags"]:
        metadata["Tags"] = []
    if "cr_shared" not in metadata["Tags"]:
        metadata["Tags"].append("cr_shared")

    if "LockedFields" not in metadata or not metadata["LockedFields"]:
        metadata["LockedFields"] = []
    if "Tags" not in metadata["LockedFields"]:
        metadata["LockedFields"].append("Tags")

    # Debugging instead of updating
    # print("DEBUG: This is what would be sent to Jellyfin:")
    # print(f"URL: {JELLYFIN_SERVER_URL}/Items/{item_id}")
    # print(f"Headers: {headers}")
    # print(f"Payload: {metadata}")

    # Un(comment) these 2 lines to make/stop actual changes for debugging
    update_url = f"{JELLYFIN_SERVER_URL}/Items/{item_id}"
    update_response = requests.post(update_url, headers=headers, json=metadata)

    if update_response.status_code in [200, 204]:
        print(f"Successfully updated metadata for item ID {item_id} ({title}) - Status: {update_response.status_code}")
        return True
    else:
        print(f"Error: Failed to update metadata for item ID {item_id} ({title}) - Status: {update_response.status_code} - Response: {update_response.text}")
        return False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
