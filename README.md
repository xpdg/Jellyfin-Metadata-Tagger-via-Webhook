
# Jellyfin Metadata Tagger via Webhook

This Python application listens for incoming webhooks (e.g., from Jellyseerr) and updates metadata for media items in a Jellyfin server. The script identifies specific media based on TMDb, TVDb, IMDb IDs, or titles, applies a custom metadata tag, and locks the metadata field to prevent further modifications.

## Features

- Listens for webhook notifications via Flask.
- Validates and authenticates incoming webhook requests.
- Searches for media in Jellyfin using TMDb, TVDb, or IMDb IDs, or by title.
- Adds a custom metadata tag to the media item.
- Locks metadata fields to prevent unintended changes.

## Requirements

- Python 3.7+
- Jellyfin server & a valid API key.
- Flask for handling webhook requests.
- Jellyseer with webhook notifications.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/xpdg/jellyfin-metadata-tagger.git
   cd jellyfin-metadata-tagger
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - `JELLYFIN_API_KEY`: Your Jellyfin API key.
   - `JELLYFIN_SERVER_URL`: URL of your Jellyfin server.
   - `JELLYFIN_USER_ID=`: An administrator Jellyfin user-id.
   - `WEBHOOK_AUTH_TOKEN`: Token to authenticate incoming webhook requests.
   - `TARGET_USERNAME`: Username to filter webhook requests (optional).

4. Set your environment variables in the `.env` file.

5. Test the Flask app:
    ```bash
    python app.py
    ```
---
<details>
<summary><h3>Running as a Systemd Service</h3></summary>

To ensure the service runs continuously, you can create a systemd service file:

1. Create the service file:
    ```bash
    sudo nano /etc/systemd/system/jellyfin-tagging.service
    ```

2. Add the following content:
    ```ini
    [Unit]
    Description=Jellyfin Metadata Tagging Service
    After=network.target

    [Service]
    # Change main user if running service as non-root
    # User=your-user
    WorkingDirectory=/path/to/jellyfin-metadata-tagging
    ExecStart=/usr/bin/python3 app.py
    EnvironmentFile=/path/to/jellyfin-metadata-tagging/.env
    Environment="PYTHONUNBUFFERED=1"
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```

3. Save and close the file.

4. Reload the systemd daemon:
    ```bash
    sudo systemctl daemon-reload
    ```

5. Enable the service to start on boot:
    ```bash
    sudo systemctl enable jellyfin-tagging.service
    ```

6. Start the service:
    ```bash
    sudo systemctl start jellyfin-tagging.service
    ```

7. Check the service status:
    ```bash
    sudo systemctl status jellyfin-tagging.service
    ```
</details>

---

## Usage

### Sending Webhooks

This script listens for POST requests at `/webhook`. Ensure that your webhook source sends the following payload:

```json
{
  "notification_type": "MEDIA_AVAILABLE",
  "event": "Movie Request Now Available",
  "subject": "",
  "media": {
    "media_type": "",
    "tmdbId": "",
    "tvdbId": "",
    "imdbId": ""
  },
  "request": {
    "requestedBy_username": ""
  }
}
```

### Logging

Logs are written to the console and include:

- Details of incoming webhook payloads.
- Search results for matching media in Jellyfin.
- Success or error messages when updating metadata.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

