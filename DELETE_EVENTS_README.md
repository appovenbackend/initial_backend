# Delete All Events Script

This script allows you to delete all existing events from your Railway-deployed backend by deactivating them. Since the API doesn't have a direct "delete all events" endpoint, this script uses the existing PATCH endpoint to set `isActive: false` for all events.

## How it works

1. **Fetches all events** from the `/events` endpoint
2. **Deactivates each event** by making PATCH requests to `/events/{event_id}` with `{"isActive": false}`
3. **Provides detailed feedback** on the operation progress and results

## Usage

### Prerequisites

1. Install the required dependencies:
   ```bash
   pip install -r delete_events_requirements.txt
   ```

### Running the script

```bash
python delete_all_events.py <RAILWAY_URL>
```

**Example:**
```bash
python delete_all_events.py https://your-app.railway.app
```

### What happens when you run it

1. The script will display the Railway URL it's connecting to
2. It will fetch all events from your backend
3. For each event found, it will:
   - Display the event name and ID
   - Attempt to deactivate the event
   - Show success/failure status
4. Finally, it will display a summary of the operation

### Sample Output

```
🔄 Starting to delete all events from: https://your-app.railway.app
==================================================
📋 Fetching all events...
📊 Found 5 events to process
🔄 Processing event 1/5: Summer Fitness Workshop (ID: evt_abc123def4)
✅ Successfully deactivated: Summer Fitness Workshop
🔄 Processing event 2/5: Yoga Session (ID: evt_xyz789ghi0)
✅ Successfully deactivated: Yoga Session
...
==================================================
📈 Operation Summary:
   • Total events found: 5
   • Successfully deactivated: 5
   • Failed to deactivate: 0
🎉 All events have been successfully deactivated!
```

## Important Notes

- **Deactivation vs Deletion**: This script **deactivates** events rather than permanently deleting them. Deactivated events won't show up in the active events list but remain in the database.
- **No Undo**: Once events are deactivated, they cannot be easily reactivated through this script. You'd need to manually update each event's `isActive` field in the database.
- **Rate Limiting**: The script includes a 0.5-second delay between requests to avoid overwhelming your server.
- **Error Handling**: If any events fail to deactivate, the script will continue with the remaining events and report all errors at the end.

## Troubleshooting

### Common Issues

1. **"Failed to fetch events"**: Check that your Railway URL is correct and the app is running
2. **"Failed to deactivate event"**: Check the error messages - this might be due to network issues or server problems
3. **"No events found"**: Your backend might not have any events, or there might be a connectivity issue

### Getting your Railway URL

1. Go to your Railway dashboard
2. Select your project
3. The URL will be displayed in the format: `https://your-app.railway.app`

## Safety Features

- **Input validation**: Ensures the provided URL is valid
- **Error handling**: Continues processing even if individual events fail
- **Detailed logging**: Shows exactly what's happening at each step
- **Timeout protection**: Requests timeout after 30 seconds to prevent hanging
- **Rate limiting**: Small delays between requests to avoid overwhelming the server

## Alternative: Manual Deactivation

If you prefer to deactivate events manually, you can:

1. Get all events: `GET /events`
2. For each event, make a PATCH request: `PATCH /events/{event_id}` with `{"isActive": false}`

This script automates that process for convenience.
