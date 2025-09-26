# Add Fitness Events Script

This script creates 50 new fitness-oriented events in your Railway-deployed backend. It generates a diverse mix of 40 free events and 10 paid events with authentic fitness themes, perfect for testing your fitness event booking platform.

## Features

- **50 Fitness Events**: 40 free events + 10 paid events
- **BHAG Branding**: All events branded with BHAG Fitness Club
- **Diverse Activities**: Running, yoga, HIIT, marathons, and more
- **Realistic Data**: Proper dates, locations, and pricing
- **High-Quality Images**: Fitness-oriented banner images from Unsplash

## Event Categories

### Free Events (40 total)
- **Daily Runs**: Monday Free Run, Wednesday Free Run, Friday Free Run
- **BHAG Community Events**: BHAG Free Run, BHAG Morning Run, BHAG Evening Run
- **Fitness Classes**: Yoga Session, HIIT Class, Pilates Session, Zumba Class
- **Specialty Workouts**: Cardio Blast, Bodyweight Workout, Stretching Class
- **Weekend Activities**: Saturday Long Run, Sunday Recovery Run, Weekend Run

### Paid Events (10 total)
- **Marathon Series**: BHAG 5K Marathon, BHAG 10K Challenge, BHAG Half Marathon, BHAG 25K Marathon
- **Premium Classes**: Premium Yoga Workshop, Advanced HIIT Training
- **Elite Training**: BHAG Marathon Training, Professional Running Clinic, Elite Fitness Camp

## How It Works

1. **Generates Event Data**: Creates realistic fitness events with proper scheduling
2. **Random Distribution**: Events are randomly distributed across cities and venues
3. **Future Dating**: Events are scheduled from 1-60 days in the future
4. **API Integration**: Uses your existing POST /events endpoint
5. **Progress Tracking**: Shows real-time creation progress

## Usage

### Prerequisites

1. Install the required dependencies:
   ```bash
   pip install -r add_events_requirements.txt
   ```

### Running the Script

```bash
python add_fitness_events.py <RAILWAY_URL>
```

**Example:**
```bash
python add_fitness_events.py https://your-fitness-app.railway.app
```

### What Happens When You Run It

1. The script generates 50 fitness events with realistic data
2. Events are created one by one using your API
3. Progress is displayed in real-time
4. Final summary shows success/failure statistics

### Sample Output

```
🏃 Starting to create 50 fitness events at: https://your-app.railway.app
============================================================
📋 Created 50 events to add:
   • Free events: 40
   • Paid events: 10

🏃 Creating event 1/50: Monday Free Run #001 (FREE)
✅ Successfully created: Monday Free Run #001
🏃 Creating event 2/50: BHAG 5K Marathon #001 (PAID (₹450))
✅ Successfully created: BHAG 5K Marathon #001
...
============================================================
📈 Creation Summary:
   • Total events attempted: 50
   • Successfully created: 50
   • Failed to create: 0
   • Free events: 40
   • Paid events: 10
🎉 All 50 fitness events have been successfully created!
```

## Event Details

### Sample Free Event
```json
{
  "title": "BHAG Free Run #001",
  "description": "Join us for an invigorating bhag free run session. Perfect for all fitness levels!",
  "city": "Mumbai",
  "venue": "Marine Drive",
  "startAt": "2024-01-15T08:30:00",
  "endAt": "2024-01-15T10:00:00",
  "priceINR": 0,
  "bannerUrl": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
  "organizerName": "BHAG Fitness Club",
  "isActive": true
}
```

### Sample Paid Event
```json
{
  "title": "BHAG 25K Marathon #001",
  "description": "Experience the energy of bhag 25k marathon with fellow fitness enthusiasts. Let's get moving!",
  "city": "Delhi",
  "venue": "India Gate Grounds",
  "startAt": "2024-02-01T06:00:00",
  "endAt": "2024-02-01T12:00:00",
  "priceINR": 750,
  "bannerUrl": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=400&fit=crop",
  "organizerName": "BHAG Elite Fitness",
  "isActive": true
}
```

## Cities and Venues

**Cities** (with real coordinates):
- **Mumbai** (19.0760, 72.8777)
- **Delhi** (28.7041, 77.1025)
- **Bangalore** (12.9716, 77.5946)
- **Pune** (18.5204, 73.8567)
- **Chennai** (13.0827, 80.2707)
- **Hyderabad** (17.3850, 78.4867)
- **Kolkata** (22.5726, 88.3639)
- **Ahmedabad** (23.0225, 72.5714)

**Venues**:
- Central Park
- Marine Drive
- India Gate Grounds
- Cubbon Park
- Phoenix Mall Grounds
- Nehru Stadium
- City Sports Complex
- Riverside Park
- Fitness Hub Arena
- Community Center Grounds

## Banner Images

All events use high-quality fitness images from Unsplash:
- Running and jogging scenes
- Group fitness activities
- Yoga and stretching poses
- Marathon and racing events
- Gym and workout environments

## Pricing Strategy

- **Free Events**: ₹0 (community building, engagement)
- **Paid Events**: ₹100-1000 (premium experiences, marathons, workshops)

## Scheduling

- **Free Events**: 1-30 days in the future (regular classes)
- **Paid Events**: 7-60 days in the future (special events, more planning time)

## Safety Features

- **Rate Limiting**: 0.5-second delays between requests
- **Error Handling**: Continues processing even if individual events fail
- **Input Validation**: Validates Railway URL format
- **Timeout Protection**: 30-second timeout per request
- **Detailed Logging**: Comprehensive progress and error reporting

## Troubleshooting

### Common Issues

1. **"Failed to create event"**: Check your Railway app is running and accessible
2. **"Network timeout"**: Your server might be under heavy load
3. **"Invalid URL"**: Ensure your Railway URL starts with http:// or https://

### Getting Your Railway URL

1. Go to your Railway dashboard
2. Select your project
3. Copy the provided URL (e.g., `https://your-app.railway.app`)

## Use Cases

- **Testing**: Populate your app with realistic fitness events for testing
- **Demo Data**: Create sample events for demonstrations or presentations
- **Development**: Generate test data for frontend development
- **Load Testing**: Create multiple events to test app performance

## Integration

This script integrates seamlessly with your existing FastAPI backend:
- Uses the same event model structure
- Follows your API conventions
- Respects your database schema
- Works with your existing authentication and validation

Perfect for quickly populating your fitness event booking platform with realistic, diverse content!
