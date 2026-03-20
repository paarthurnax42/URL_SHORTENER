# Load Testing Documentation

## Overview

This directory contains load testing scripts for the URL shortener API using Locust.

## Prerequisites

Install Locust:

```bash
pip install locust
```

## Running Load Tests

### Basic Load Test

Run the web UI:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089 in your browser.

### Headless Mode

Run without UI for automated testing:

```bash
# 100 users, spawn rate of 10 users/second, run for 60 seconds
locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s
```

### Staged Load Test

Run with gradually increasing load:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -t 300s
```

This will:
- Start with 10 users
- Gradually increase to 50 users
- Peak at 100 users
- Run for 5 minutes total

## User Types

The load test includes three user types:

1. **URLShortenerUser** - Regular authenticated user
   - Creates short links
   - Views link info
   - Performs redirects
   - Views statistics

2. **AnonymousUser** - Unauthenticated user
   - Performs redirects
   - Creates public links

3. **HeavyUser** - High-frequency user for stress testing
   - Rapidly creates links
   - Performs many redirects
   - Searches links

## Test Scenarios

### Scenario 1: Normal Load
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 -t 120s
```

### Scenario 2: Peak Load
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 200 -r 20 -t 180s
```

### Scenario 3: Stress Test
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000 --headless -u 500 -r 50 -t 300s
```

## Metrics to Monitor

- **Response Time**: Should be < 500ms for most requests
- **Requests/second**: Indicates throughput
- **Failure Rate**: Should be < 1%
- **Active Users**: Number of concurrent simulated users

## Output

Locust provides:
- Real-time web dashboard at http://localhost:8089
- CSV export option: `--csv=results/results`
- HTML report (with locust-html-report plugin)

## Tips

1. Start with small user counts to verify the test works
2. Monitor database and Redis during tests
3. Run tests in a staging environment, not production
4. Use `--headless` mode for CI/CD integration
