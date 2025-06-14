#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Scrapy Spider - Supercharged Edition
---------------------------------------------
An advanced Scrapy spider using Playwright for JavaScript rendering,
built to extract LinkedIn profiles of individuals who studied in France
within engineering, medical, or computer science domains.

"""
import logging
import random
import time
import signal
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Generator

import scrapy
from scrapy import Request, signals
from scrapy.selector import Selector
from scrapy.exceptions import CloseSpider

# Dataclass for structured profile data
@dataclass
class LinkedInProfile:
    name: str
    headline: str
    location: str
    current_position: str
    educations_in_france: List[Dict[str, str]]
    skills: List[str] = field(default_factory=list)
    profile_url: str = ""
    scraped_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

class LinkedInScraper(scrapy.Spider):  # type: ignore
    name: str = "linkedin"
    allowed_domains: List[str] = ["linkedin.com"]
    search_url: str = (
        "https://www.linkedin.com/search/results/people/"
        "?keywords=France%20AND%20%28engineering%20OR%20medical%20OR%20%22computer%20science%22%29"
        "&origin=GLOBAL_SEARCH_HEADER"
    )

    # Custom settings for Playwright, throttling, cache, etc.
    custom_settings: Dict[str, Any] = {
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.PlaywrightDownloadHandler",
            "https": "scrapy_playwright.PlaywrightDownloadHandler"
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 10,
        "HTTPCACHE_ENABLED": True,
        "CONCURRENT_REQUESTS": 6,
        "DOWNLOAD_DELAY": 0.5,
        "RETRY_ENABLED": False,  # using custom backoff in errback
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
            "scrapy_playwright.middleware.PlaywrightMiddleware": 800,
        },
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.logger: logging.Logger = logging.getLogger(self.name)
        self.total_profiles: int = 0
        # Connect signals
        self.crawler.signals.connect(self.on_spider_opened, signals.spider_opened)
        self.crawler.signals.connect(self.on_spider_closed, signals.spider_closed)

    def on_spider_opened(self, spider: scrapy.Spider) -> None:
        self.logger.info(f"[spider_opened] {spider.name} started at {time.strftime('%H:%M:%S')}")

    def on_spider_closed(self, spider: scrapy.Spider) -> None:
        self.logger.info(f"[spider_closed] {spider.name} finished; profiles scraped: {self.total_profiles}")
        if self.total_profiles == 0:
            raise CloseSpider("No profiles scraped — shutting down")

    def start_requests(self) -> Generator[Request, None, None]:
        """
        Initiate search page request with Playwright rendering
        and wait for the main result container to load.
        """
        yield Request(
            self.search_url,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    ("wait_for_selector", "ul.reusable-search__result-list")
                ],
                "playwright_context": "default"
            },
            callback=self.parse_search,
            errback=self.errback
        )

    def parse_search(self, response: scrapy.http.Response) -> None:
        """
        Parse search results, enqueue profile pages, handle pagination.
        """
        sel: Selector = Selector(response)
        results = sel.css("ul.reusable-search__result-list li div.entity-result__item")
        for entry in results:
            profile_link = entry.css("a.app-aware-link::attr(href)").get()
            if profile_link:
                yield response.follow(
                    profile_link,
                    callback=self.parse_profile,
                    meta={"playwright": True},
                    errback=self.errback
                )
        # Pagination via Playwright click
        next_button = sel.css("button[aria-label='Next']").get()
        if next_button:
            yield Request(
                response.url,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        ("click", "button[aria-label='Next']"),
                        ("wait_for_selector", "ul.reusable-search__result-list")
                    ]
                },
                callback=self.parse_search,
                errback=self.errback
            )

    def parse_profile(self, response: scrapy.http.Response) -> LinkedInProfile:
        """
        Extract detailed profile information and return a dataclass.
        """
        sel: Selector = Selector(response)
        name = sel.css("li.inline.t-24.t-black.t-normal.break-words::text").get(default="").strip()
        headline = sel.css("h2.mt1.t-18.t-black.t-normal.break-words::text").get(default="").strip()
        location = sel.css("li.t-16.t-black.t-normal.inline-block::text").get(default="").strip()
        current_position = sel.css(
            "section#experience-section li.pv-entity__position-group-pager h3.t-16.t-black.t-bold a::text"
        ).get(default="").strip()
        # Education filter for France entries
        educations: List[Dict[str, str]] = []
        for edu in sel.css("section#education-section li.education__list-item"):
            school = edu.css("h3.pv-entity__school-name::text").get(default="").strip()
            degree = edu.css("p.pv-entity__degree-name span::text").get(default="").strip()
            period = edu.css("p.pv-entity__dates span:nth-child(2)::text").get(default="").strip()
            if "France" in school or "France" in period:
                educations.append({"school": school, "degree": degree, "period": period})
        # Skills extraction (if available)
        skills = sel.css("section.pv-skill-categories-section span.pv-skill-category-entity__name-text::text").getall()
        profile = LinkedInProfile(
            name=name,
            headline=headline,
            location=location,
            current_position=current_position,
            educations_in_france=educations,
            skills=[s.strip() for s in skills],
            profile_url=response.url
        )
        self.total_profiles += 1
        self.logger.info(f"[scraped] {profile.name} | {profile.profile_url}")
        yield profile

    def errback(self, failure: Any) -> None:
        """
        Handle request failures with backoff and logging.
        """
        request = failure.request
        self.logger.error(f"[error] Request failed: {request.url}")
        # Exponential backoff retry
        retries = request.meta.get('retry_times', 0)
        if retries < 3:
            backoff = 2 ** retries
            self.logger.debug(f"[retry] Retrying {request.url} after {backoff}s")
            time.sleep(backoff)
            req = request.copy()
            req.meta['retry_times'] = retries + 1
            yield req
        else:
            self.logger.warning(f"[giveup] {request.url} after {retries} retries")

# Graceful shutdown on SIGINT
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
