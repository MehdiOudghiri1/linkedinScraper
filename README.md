````markdown
# LinkedIn Supercharged Scrapy Spider

A high-performance Scrapy crawler powered by Playwright, built to harvest LinkedIn profile data for individuals who studied in France within engineering, medical, or computer science fields.

---

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Project Structure](#project-structure)
7. [Data Model](#data-model)
8. [Error Handling & Retries](#error-handling--retries)
9. [Extending & Customization](#extending--customization)
10. [License](#license)

---

## Features

- **JavaScript Rendering**: Integrates Playwright for full-profile rendering.
- **Search Filtering**: Targets LinkedIn profiles with education in France and technical domains.
- **AutoThrottle & Caching**: Polite crawling with dynamic throttling and HTTP caching.
- **User-Agent Rotation**: RandomUserAgentMiddleware to minimize detection.
- **Signal Hooks**: Logs spider start/close events with total profiles scraped.
- **Exponential Backoff**: Custom errback with retry logic for robustness.
- **Structured Output**: Yields `LinkedInProfile` dataclass instances ready for pipelines.

---

## Prerequisites

- Python 3.8+
- Scrapy 2.5+
- scrapy-playwright
- scrapy-user-agents
- Playwright dependencies (`playwright install`)

---

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/linkedin-supercharged-spider.git
cd linkedin-supercharged-spider

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
````

---

## Configuration

* **Search URL**: Modify `LinkedInScraper.search_url` to adjust search keywords or filters.
* **Proxies**: Add HTTP(S) proxies to `custom_settings.DOWNLOADER_MIDDLEWARES` if required.
* **Throttle**: Tweak `AUTOTHROTTLE_START_DELAY`, `MAX_DELAY`, and `DOWNLOAD_DELAY` in `custom_settings`.

---

## Usage

```bash
# Run spider and output to JSON
scrapy crawl linkedinSpider -o profiles.json

# Sample: limit execution depth or set log level
scrapy crawl linkedinSpider --set LOG_LEVEL=INFO
```

Profiles will be saved as a list of JSON objects with fields defined in the `LinkedInProfile` dataclass.

---

## Project Structure

```
linkedin_supercharged/
├── linkedin_spider.py        # Main Scrapy spider with dataclass model
├── requirements.txt          # Python dependencies
├── README_LINKEDIN.md        # Project documentation
└── scrapy.cfg                # Scrapy configuration file
```

---

## Data Model

```python
@dataclass
class LinkedInProfile:
    name: str
    headline: str
    location: str
    current_position: str
    educations_in_france: List[Dict[str,str]]
    skills: List[str]
    profile_url: str
    scraped_at: str
```

Each yielded item adheres to this structure, simplifying downstream processing and analysis.

---

## Error Handling & Retries

* Custom `errback` implements exponential backoff (up to 3 retries).
* Failed requests are logged and optionally retried with increased delay.
* Spider closes cleanly if no profiles are scraped.

---

## Extending & Customization

* **Additional Fields**: Enhance `parse_profile` with new selectors for experience, certifications, etc.
* **Pipeline Integration**: Implement `ITEM_PIPELINES` for database storage or data validation.
* **Distributed Crawling**: Deploy on Scrapyd or integrate with AWS Fargate for large-scale scraping.

---

## License

MIT License © Oudghiri Mehdi
