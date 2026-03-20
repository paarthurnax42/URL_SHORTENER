"""
Locust load testing script for URL shortener API.

Usage:
    locust -f locustfile.py --host=http://localhost:8000

Or for headless mode:
    locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s

Options:
    -u: Number of users to simulate
    -r: Spawn rate (users per second)
    -t: Test duration
"""
import random
import string
from locust import HttpUser, task, between, events
from datetime import datetime


class URLShortenerUser(HttpUser):
    """Simulated user for URL shortener load testing."""

    wait_time = between(0.5, 2)  # Wait 0.5-2 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts."""
        # Register a test user
        self.user_email = f"loadtest_{random.randint(1, 10000)}@example.com"
        self.user_password = "loadtestpassword123"

        register_response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.user_email,
                "password": self.user_password,
            },
        )

        if register_response.status_code == 201:
            self.token = register_response.json()["access_token"]
            self.client.headers["Authorization"] = f"Bearer {self.token}"
        else:
            # Try to login if user already exists
            login_response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": self.user_email,
                    "password": self.user_password,
                },
            )
            if login_response.status_code == 200:
                self.token = login_response.json()["access_token"]
                self.client.headers["Authorization"] = f"Bearer {self.token}"

        self.created_links = []

    @task(3)
    def create_short_link(self):
        """Create a new short link (weighted 3x)."""
        random_url = f"https://example.com/page/{random.randint(1, 10000)}"

        with self.client.post(
            "/api/v1/links/shorten",
            json={"original": random_url},
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.created_links.append(data["short"])
                response.success()
            else:
                response.failure(f"Failed to create link: {response.status_code}")

    @task(2)
    def get_link_info(self):
        """Get information about a link (weighted 2x)."""
        if self.created_links:
            short_code = random.choice(self.created_links)
            self.client.get(f"/api/v1/links/{short_code}/info")
        else:
            # Fallback to a known link pattern
            self.client.get("/api/v1/links/abc123/info")

    @task(2)
    def redirect_link(self):
        """Redirect through a short link (weighted 2x)."""
        if self.created_links:
            short_code = random.choice(self.created_links)
            self.client.get(f"/links/{short_code}", follow_redirects=False)

    @task(1)
    def get_my_links(self):
        """Get user's links."""
        self.client.get("/api/v1/links/my")

    @task(1)
    def get_stats(self):
        """Get link statistics."""
        if self.created_links:
            short_code = random.choice(self.created_links)
            self.client.get(f"/api/v1/links/{short_code}/stats")

    @task(1)
    def create_link_with_alias(self):
        """Create a link with custom alias."""
        random_url = f"https://example.com/aliased/{random.randint(1, 10000)}"
        random_alias = "".join(random.choices(string.ascii_lowercase, k=8))

        self.client.post(
            "/api/v1/links/shorten",
            json={
                "original": random_url,
                "alias": random_alias,
            },
        )


class AnonymousUser(HttpUser):
    """Anonymous user (unauthenticated) for load testing public endpoints."""

    wait_time = between(1, 3)

    @task(3)
    def redirect_link(self):
        """Redirect through a short link."""
        # Try common short codes
        codes = ["abc123", "xyz789", "test", "demo"]
        short_code = random.choice(codes)
        self.client.get(f"/links/{short_code}", follow_redirects=False)

    @task(1)
    def create_public_link(self):
        """Create a public link (no auth required)."""
        random_url = f"https://example.com/public/{random.randint(1, 10000)}"

        self.client.post(
            "/api/v1/links/shorten",
            json={"original": random_url},
        )


class HeavyUser(HttpUser):
    """Heavy user for stress testing."""

    wait_time = between(0.1, 0.5)  # Very short wait time

    def on_start(self):
        """Start with authentication."""
        self.user_email = f"heavy_{random.randint(1, 1000)}@example.com"
        self.user_password = "heavypassword123"

        register_response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.user_email,
                "password": self.user_password,
            },
        )

        if register_response.status_code == 201:
            self.token = register_response.json()["access_token"]
            self.client.headers["Authorization"] = f"Bearer {self.token}"

        self.created_links = []

    @task(5)
    def rapid_create_links(self):
        """Rapidly create links."""
        for _ in range(3):
            random_url = f"https://example.com/heavy/{random.randint(1, 100000)}"
            response = self.client.post(
                "/api/v1/links/shorten",
                json={"original": random_url},
            )
            if response.status_code == 201:
                self.created_links.append(response.json()["short"])

    @task(3)
    def rapid_redirects(self):
        """Rapidly redirect through links."""
        if self.created_links:
            for _ in range(3):
                short_code = random.choice(self.created_links)
                self.client.get(f"/links/{short_code}", follow_redirects=False)

    @task(2)
    def search_links(self):
        """Search for links."""
        self.client.get("/api/v1/links/search?original_url=example.com")


# Event handlers for custom reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Log slow requests."""
    if response_time > 1000:  # More than 1 second
        print(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 50)
    print("Load test starting...")
    print(f"Target host: {environment.host}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("=" * 50)
    print("Load test completed!")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failed requests: {environment.stats.total.num_failures}")
    print("=" * 50)


# Custom shape class for staged load testing
class StagedLoadShape(HttpUser):
    """
    Staged load test shape.
    
    Gradually increases load to test system behavior under increasing pressure.
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},    # Ramp up to 10 users
        {"duration": 120, "users": 50, "spawn_rate": 5},   # Ramp up to 50 users
        {"duration": 180, "users": 100, "spawn_rate": 10}, # Ramp up to 100 users
        {"duration": 240, "users": 100, "spawn_rate": 0},  # Stay at 100 users
        {"duration": 300, "users": 0, "spawn_rate": 10},   # Ramp down
    ]

    def tick(self):
        """Return user count and spawn rate for current time."""
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None
