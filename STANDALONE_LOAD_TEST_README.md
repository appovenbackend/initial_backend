# 🚀 Standalone Load Testing Script

This is a **completely standalone** load testing script that you can run from anywhere to test your Railway-deployed Fitness Event Booking API.

## 📋 Features

- **🎯 600 Concurrent Users**: Simulates realistic load with 600+ concurrent users
- **⚡ Async Performance**: Uses asyncio for high-performance I/O operations
- **📊 Comprehensive Metrics**: Detailed statistics and error analysis
- **🔄 Realistic Patterns**: Weighted user behavior simulation
- **⏱️ Configurable**: Adjustable duration and user count
- **🚨 Error Tracking**: Detailed error categorization and reporting

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install -r standalone_requirements.txt
```

### 2. Run the Test
```bash
python standalone_load_test.py https://your-app.railway.app
```

### 3. Advanced Usage
```bash
# Custom users and duration
python standalone_load_test.py https://your-app.railway.app --users 1000 --duration 120

# Verbose logging
python standalone_load_test.py https://your-app.railway.app --verbose
```

## 📊 Test Scenarios

The script simulates realistic user behavior:

| Action | Weight | Description |
|--------|--------|-------------|
| **get_events** | 40% | List all events (most common) |
| **get_user_tickets** | 15% | Get user's tickets |
| **create_user** | 10% | User registration/login |
| **update_user** | 10% | Update user profile |
| **get_event_by_id** | 10% | Get specific event |
| **get_health** | 10% | Health check |
| **get_cache_stats** | 5% | Cache statistics |

## 📈 Sample Output

```
🚀 Fitness Event Booking API - Load Testing Tool
============================================================
🎯 Target URL: https://your-app.railway.app
👥 Users: 600
⏱️ Duration: 60 seconds
============================================================
🚀 Starting Load Test...
📊 Target: 600 concurrent users
⏱️ Duration: 60 seconds
🌐 Backend: https://your-app.railway.app
------------------------------------------------------------

============================================================
📈 LOAD TEST RESULTS
============================================================
⏱️ Test Duration: 60.12 seconds
📊 Total Requests: 8,547
✅ Successful: 8,432 (98.7%)
❌ Failed: 115 (1.3%)
⚡ Requests/sec: 142.1

📈 RESPONSE TIMES:
   Average: 0.234s
   Min: 0.045s
   Max: 1.892s
   95th percentile: 0.678s

🎯 ACTION BREAKDOWN:
   get_events: 3,412 (39.9%)
   get_user_tickets: 1,284 (15.0%)
   create_user: 856 (10.0%)
   update_user: 856 (10.0%)
   get_event_by_id: 856 (10.0%)
   get_health: 856 (10.0%)
   get_cache_stats: 427 (5.0%)

✅ No errors detected!

============================================================
🎉 EXCELLENT PERFORMANCE!
============================================================
```

## 🔧 Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `url` | **Required** | Your Railway backend URL |
| `--users` | 600 | Number of concurrent users |
| `--duration` | 60 | Test duration in seconds |
| `--verbose` | False | Enable detailed logging |

## 📋 Performance Benchmarks

| Metric | Excellent | Good | Acceptable | Poor |
|--------|-----------|------|------------|------|
| **Success Rate** | ≥99% | ≥95% | ≥90% | <90% |
| **95th Percentile** | <1.0s | <2.0s | <5.0s | ≥5.0s |
| **Requests/sec** | >100 | >50 | >20 | <20 |

## 🚨 Expected Results

For a properly configured Railway deployment:
- **Success Rate**: 95-99%+
- **Response Time**: 200-800ms average
- **Throughput**: 100-200 requests/second
- **Error Rate**: <5%

## 🔒 Security & Safety

- ✅ **No Data Storage**: Only makes HTTP requests
- ✅ **No External Dependencies**: Self-contained script
- ✅ **Safe for Production**: Won't affect your live data
- ✅ **Configurable**: Easy to adjust for different scenarios

## 📁 Files Included

- `standalone_load_test.py` - Main load testing script
- `standalone_requirements.txt` - Python dependencies
- `STANDALONE_LOAD_TEST_README.md` - This documentation

## 🎯 Usage Instructions

1. **Copy the files** to any directory
2. **Install dependencies**: `pip install -r standalone_requirements.txt`
3. **Run the test**: `python standalone_load_test.py https://your-app.railway.app`
4. **Analyze results** from the detailed output

## 🚀 Ready to Test!

This standalone script is completely independent and can be run from anywhere. Just provide your Railway URL and it will simulate 600 concurrent users testing your API's performance and concurrency handling.

**Perfect for testing your production deployment!** 🚀
