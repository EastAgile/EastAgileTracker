# api.py

import asyncio
import logging
import time

import aiohttp
from tqdm import tqdm

from config import Config
from exceptions import APIError


class RateLimiter:
    def __init__(self, rate, interval):
        self.rate = rate
        self.interval = interval
        self.allowance = rate
        self.last_check = time.time()

    async def acquire(self):
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        self.allowance += time_passed * (self.rate / self.interval)
        if self.allowance > self.rate:
            self.allowance = self.rate
        if self.allowance < 1:
            await asyncio.sleep(1 - self.allowance)
            self.allowance = 0
        else:
            self.allowance -= 1


class PivotalTrackerAPI:
    def __init__(self):
        self.base_url = Config.API_BASE_URL
        self.headers = {
            "X-TrackerToken": Config.API_TOKEN,
            "Content-Type": "application/json",
        }
        self.session = None
        self.rate_limiter = RateLimiter(rate=6, interval=5)  # 1.2 requests per second
        self.global_semaphore = asyncio.Semaphore(4)  # Max 4 concurrent requests

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}/{endpoint}"
        async with self.global_semaphore:
            await self.rate_limiter.acquire()
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientResponseError as e:
                logging.error(f"API request failed: {e}")
                raise APIError(f"API request failed: {e}")

    async def get_all_projects(self):
        return await self._request("GET", "projects")

    async def get_project(self, project_id):
        return await self._request("GET", f"projects/{project_id}")

    async def get_stories(self, project_id):
        return await self._paginate(f"projects/{project_id}/stories")

    async def get_comments(self, project_id, story_id):
        return await self._request(
            "GET",
            f"projects/{project_id}/stories/{story_id}/comments?fields=id,story_id,text,person_id,created_at,updated_at,file_attachments",
        )

    async def get_blockers(self, project_id, story_id):
        return await self._request(
            "GET", f"projects/{project_id}/stories/{story_id}/blockers"
        )

    async def get_tasks(self, project_id, story_id):
        return await self._paginate(f"projects/{project_id}/stories/{story_id}/tasks")

    async def get_labels(self, project_id):
        return await self._request("GET", f"projects/{project_id}/labels")

    async def get_epics(self, project_id):
        return await self._request("GET", f"projects/{project_id}/epics")

    async def get_project_memberships(self, project_id):
        return await self._request("GET", f"projects/{project_id}/memberships")

    async def get_project_current_velocity(self, project_id):
        return await self._request(
            "GET", f"projects/{project_id}?fields=current_velocity"
        )

    async def get_tasks(self, project_id, story_id):
        return await self._request(
            "GET", f"projects/{project_id}/stories/{story_id}/tasks"
        )

    async def get_iterations(self, project_id):
        return await self._paginate(
            f"projects/{project_id}/iterations?fields=number,start,finish,kind,velocity,team_strength,stories"
        )

    async def _paginate(self, endpoint, params=None):
        if params is None:
            params = {}

        params["limit"] = 100
        params["offset"] = 0

        all_items = []
        pbar = tqdm(desc=f"Fetching {endpoint.split('/')[-1]} ", unit="items")

        while True:
            items = await self._request("GET", endpoint, params=params)
            if isinstance(items, list):
                all_items.extend(items)
                pbar.update(len(items))
                if len(items) < params["limit"]:
                    break
                params["offset"] += params["limit"]
            else:
                # If the response is not a list, it's probably a single object
                # or doesn't support pagination
                pbar.close()
                return items

        pbar.close()
        return all_items

    async def download_file(self, url):
        async with self.global_semaphore:
            await self.rate_limiter.acquire()
            try:
                async with self.session.get(
                    f"https://www.pivotaltracker.com{url}"
                ) as response:
                    response.raise_for_status()
                    return await response.read()
            except aiohttp.ClientResponseError as e:
                logging.error(f"File download failed: {e}")
                raise APIError(f"File download failed: {e}")
