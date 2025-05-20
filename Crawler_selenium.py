#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pedestrian Safety Video Crawler
This script searches and downloads videos related to pedestrians in dangerous situations
for data collection and analysis purposes.
Uses Selenium to avoid blocking by YouTube.
"""

import os
import re
import csv
import time
import argparse
import requests
import json
import random
from bs4 import BeautifulSoup
from pytube import YouTube
from urllib.parse import urlparse, parse_qs
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PedestrianVideoCrawler")

class PedestrianVideoCrawler:
    """Crawler class for collecting videos of pedestrians in dangerous situations"""
    
    def __init__(self, output_dir="./downloaded_videos", max_videos=50, min_duration=5, 
                 max_duration=300, search_terms=None, headless=True):
        """
        Initialize the crawler with configuration parameters
        
        Args:
            output_dir (str): Directory to save downloaded videos
            max_videos (int): Maximum number of videos to download
            min_duration (int): Minimum video duration in seconds
            max_duration (int): Maximum video duration in seconds
            search_terms (list): List of search terms to use
            headless (bool): Whether to run the browser in headless mode
        """
        self.output_dir = output_dir
        self.max_videos = max_videos
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.headless = headless
        self.driver = None
        
        if search_terms is None:
            self.search_terms = [
                "pedestrian near miss video",
                "pedestrian accident footage",
                "pedestrian crossing danger cctv",
                "pedestrian safety violation video",
                "pedestrian hazard dashcam",
                "pedestrian traffic incident footage",
                "pedestrian close call video",
                "pedestrian intersection danger",
                "road safety pedestrian accident",
                "crosswalk safety violation"
            ]
        else:
            self.search_terms = search_terms
            
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
            
        # Create a metadata file
        self.metadata_file = os.path.join(output_dir, "video_metadata.csv")
        self._initialize_metadata_file()
        
    def _initialize_metadata_file(self):
        """Create or check the metadata CSV file"""
        file_exists = os.path.isfile(self.metadata_file)
        
        with open(self.metadata_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow([
                    "video_id", "title", "source", "url", "download_date", 
                    "duration_seconds", "search_term", "filename", "tags"
                ])
                logger.info(f"Created metadata file: {self.metadata_file}")
    
    def _initialize_selenium(self):
        """Initialize and configure Selenium WebDriver"""
        if self.driver is not None:
            return
            
        logger.info("Initializing Selenium WebDriver")
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            
        # Add additional options to make the browser less detectable
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Add a realistic user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Add experimental options to hide webdriver usage
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Apply stealth settings via JavaScript
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            
            logger.info("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise
    
    def _close_selenium(self):
        """Close the Selenium WebDriver"""
        if self.driver is not None:
            logger.info("Closing Selenium WebDriver")
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def search_youtube_selenium(self, query, max_results=30):
        """
        Search YouTube for videos matching the query using Selenium
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video URLs
        """
        video_urls = []
        search_url = f"https://www.youtube.com/results?search_query={'+'.join(query.split())}"
        
        try:
            if self.driver is None:
                self._initialize_selenium()
                
            logger.info(f"Searching YouTube for: {query}")
            self.driver.get(search_url)
            
            # Wait for the search results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "contents"))
            )
            
            # Scroll down to load more results
            for _ in range(3):  # Scroll a few times to load more videos
                self.driver.execute_script("window.scrollBy(0, 1000)")
                time.sleep(1)
            
            # Extract video links
            video_elements = self.driver.find_elements(By.CSS_SELECTOR, "a#video-title")
            logger.info(f"Found {len(video_elements)} video elements")
            
            for element in video_elements[:max_results]:
                href = element.get_attribute("href")
                if href and "watch?v=" in href:
                    video_urls.append(href)
                    
            # If we didn't find enough using the elements, try extracting from page source
            if len(video_urls) < 5:
                logger.info("Trying alternative extraction method")
                page_source = self.driver.page_source
                video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', page_source)
                unique_ids = list(dict.fromkeys(video_ids))
                video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in unique_ids[:max_results]]
            
            logger.info(f"Found {len(video_urls)} videos for query: {query}")
            return video_urls
            
        except Exception as e:
            logger.error(f"Error searching YouTube with Selenium: {e}")
            return []
    
    def get_video_info(self, url):
        """
        Get video information using Selenium to avoid 400 errors
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Video information or None if failed
        """
        try:
            if self.driver is None:
                self._initialize_selenium()
                
            logger.info(f"Getting video info for: {url}")
            self.driver.get(url)
            
            # Wait for the video page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "movie_player"))
            )
            
            # Let the page fully load
            time.sleep(2)
            
            # Extract video ID from URL
            parsed_url = urlparse(url)
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            
            # Extract title
            try:
                title_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title"))
                )
                title = title_element.text
            except:
                # Try alternative selectors if the first one fails
                try:
                    title = self.driver.find_element(By.CSS_SELECTOR, "h1#title").text
                except:
                    try:
                        title = self.driver.find_element(By.CSS_SELECTOR, "meta[property='og:title']").get_attribute("content")
                    except:
                        title = f"Video {video_id}"
            
            # Try to extract duration from the page
            # This is more complex and might need adjusting based on YouTube's current layout
            duration_seconds = 0
            try:
                # Try to get duration from page metadata
                page_source = self.driver.page_source
                
                # Look for duration in page source with different patterns
                duration_match = re.search(r'"lengthSeconds":"(\d+)"', page_source)
                if duration_match:
                    duration_seconds = int(duration_match.group(1))
                else:
                    duration_match = re.search(r'"lengthSeconds":(\d+)', page_source)
                    if duration_match:
                        duration_seconds = int(duration_match.group(1))
                    else:
                        # Try to find it in other formats
                        duration_match = re.search(r'"approxDurationMs":"(\d+)"', page_source)
                        if duration_match:
                            duration_seconds = int(int(duration_match.group(1)) / 1000)
            except Exception as e:
                logger.warning(f"Could not extract duration: {e}")
                duration_seconds = 0  # Default to 0 if extraction fails
            
            # Check if the video meets our criteria
            if duration_seconds > 0 and (duration_seconds < self.min_duration or duration_seconds > self.max_duration):
                logger.debug(f"Video duration ({duration_seconds}s) outside allowed range ({self.min_duration}-{self.max_duration}s)")
                return None
            
            return {
                "id": video_id,
                "title": title,
                "duration_seconds": duration_seconds,
                "url": url
            }
        
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def download_video(self, url, search_term):
        """
        Download a video from YouTube
        
        Args:
            url (str): YouTube video URL
            search_term (str): The search term that found this video
            
        Returns:
            tuple: (success (bool), metadata (dict))
        """
        max_retries = 3
        for retry in range(max_retries):
            try:
                # Add retry mechanism with backoff
                if retry > 0:
                    wait_time = 2 ** retry  # Exponential backoff: 2, 4, 8 seconds
                    logger.info(f"Retry attempt {retry+1}/{max_retries} for {url}, waiting {wait_time}s")
                    time.sleep(wait_time)
                
                # Get video info using Selenium first to validate
                video_info = self.get_video_info(url)
                if not video_info:
                    logger.info(f"Video {url} did not meet criteria or info couldn't be retrieved")
                    return False, None
                    
                video_id = video_info["id"]
                title = video_info["title"]
                duration_seconds = video_info["duration_seconds"]
                
                # Now use pytube to download the video
                try:
                    # Create a safe filename
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
                    filename = f"{video_id}_{safe_title[:50]}.mp4"
                    filepath = os.path.join(self.output_dir, filename)
                    
                    # Check if already downloaded
                    if os.path.exists(filepath):
                        logger.info(f"Video already downloaded: {filepath}")
                        return False, None
                    
                    # Try to download with pytube
                    yt = YouTube(
                        url,
                        use_oauth=False,
                        allow_oauth_cache=True,
                        on_progress_callback=None
                    )
                    
                    # Get all available streams and try different ones if necessary
                    streams = yt.streams.filter(progressive=True, file_extension="mp4")
                    if not streams or len(streams) == 0:
                        # Try non-progressive as fallback
                        streams = yt.streams.filter(file_extension="mp4")
                        
                    if not streams or len(streams) == 0:
                        logger.warning(f"No streams found for {url}")
                        continue  # Retry
                    
                    # Sort by resolution and try to download
                    streams = streams.order_by("resolution").desc()
                    stream = streams.first()
                    
                    if not stream:
                        logger.warning(f"No suitable stream found for {url}")
                        continue  # Retry
                    
                    # Download the video
                    logger.info(f"Downloading: {title} (Resolution: {stream.resolution})")
                    stream.download(output_path=self.output_dir, filename=filename)
                    
                except Exception as pytube_error:
                    logger.warning(f"PyTube error, trying alternative download method: {pytube_error}")
                    
                    # Try direct download using the requests library as a fallback
                    # Note: This is a simplified approach and may not work for all videos
                    try:
                        # We'll need to extract the direct video URL
                        if self.driver is None:
                            self._initialize_selenium()
                        
                        self.driver.get(url)
                        time.sleep(3)  # Wait for the page to load
                        
                        # Try to extract the video URL from the page source
                        page_source = self.driver.page_source
                        
                        # This is a simplified approach and might not always work
                        # A more robust solution would involve additional parsing
                        video_url_match = re.search(r'"url":"(https://[^"]*videoplayback[^"]*)"', page_source)
                        if not video_url_match:
                            logger.warning("Could not find video URL in page source")
                            continue
                            
                        video_url = video_url_match.group(1).replace('\\u0026', '&')
                        
                        # Download using requests
                        logger.info(f"Downloading video using requests fallback: {title}")
                        response = requests.get(video_url, stream=True, timeout=30)
                        response.raise_for_status()
                        
                        with open(filepath, 'wb') as video_file:
                            for chunk in response.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    video_file.write(chunk)
                    except Exception as direct_error:
                        logger.error(f"Direct download failed: {direct_error}")
                        continue
                
                # Verify file was actually downloaded
                if not os.path.exists(filepath) or os.path.getsize(filepath) < 10000:  # Less than 10KB
                    logger.warning(f"Downloaded file is too small or doesn't exist: {filepath}")
                    if os.path.exists(filepath):
                        os.remove(filepath)  # Remove corrupt/empty file
                    continue  # Retry
                
                # Create metadata
                metadata = {
                    "video_id": video_id,
                    "title": title,
                    "source": "youtube",
                    "url": url,
                    "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": duration_seconds,
                    "search_term": search_term,
                    "filename": filename,
                    "tags": ""  # No tags in this version
                }
                
                # Save metadata
                with open(self.metadata_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        metadata["video_id"],
                        metadata["title"],
                        metadata["source"],
                        metadata["url"],
                        metadata["download_date"],
                        metadata["duration_seconds"],
                        metadata["search_term"],
                        metadata["filename"],
                        metadata["tags"]
                    ])
                    
                logger.info(f"Successfully downloaded: {filepath}")
                return True, metadata
                
            except Exception as e:
                if "HTTP Error 429" in str(e):
                    logger.error(f"Rate limited by YouTube (429). Waiting longer before retry.")
                    time.sleep(30 + (30 * retry))  # Wait longer for rate limits
                elif "Video unavailable" in str(e):
                    logger.error(f"Video unavailable: {url}")
                    return False, None  # Don't retry for unavailable videos
                else:
                    logger.error(f"Error downloading {url} (attempt {retry+1}/{max_retries}): {e}")
                    if retry == max_retries - 1:
                        return False, None  # Give up after max retries
        
        return False, None  # Couldn't download after all retries
    
    def run(self):
        """
        Run the crawler to search and download videos
        """
        logger.info("Starting crawler...")
        downloaded_count = 0
        
        try:
            # Initialize Selenium
            self._initialize_selenium()
            
            # Process each search term
            for search_term in self.search_terms:
                if downloaded_count >= self.max_videos:
                    break
                    
                video_urls = self.search_youtube_selenium(search_term)
                logger.info(f"Found {len(video_urls)} videos for '{search_term}'")
                
                # Shuffle the URLs to get more variety
                random.shuffle(video_urls)
                
                # Process videos one by one 
                # (threading caused issues with Selenium in testing)
                for url in video_urls:
                    if downloaded_count >= self.max_videos:
                        break
                        
                    success, _ = self.download_video(url, search_term)
                    if success:
                        downloaded_count += 1
                        
                    # Add a small delay between downloads
                    time.sleep(random.uniform(1.0, 3.0))
                    
                # Pause between search terms to avoid being rate-limited
                time.sleep(random.uniform(5.0, 10.0))
                    
            logger.info(f"Crawler finished. Downloaded {downloaded_count} videos.")
            return downloaded_count
            
        finally:
            # Always close Selenium
            self._close_selenium()


def main():
    """Main function to run the crawler with command line arguments"""
    parser = argparse.ArgumentParser(description="Download pedestrian safety videos for data collection")
    
    parser.add_argument("--output", "-o", default="./downloaded_videos",
                        help="Directory to save downloaded videos")
    parser.add_argument("--max-videos", "-m", type=int, default=50,
                        help="Maximum number of videos to download")
    parser.add_argument("--min-duration", type=int, default=5,
                        help="Minimum video duration in seconds")
    parser.add_argument("--max-duration", type=int, default=300,
                        help="Maximum video duration in seconds")
    parser.add_argument("--search-terms", "-s", nargs="+",
                        help="Custom search terms to use (space separated)")
    parser.add_argument("--headless", action="store_true", default=True,
                        help="Run in headless mode (no browser UI)")
    parser.add_argument("--visible", dest="headless", action="store_false",
                        help="Show browser window while running")
    
    args = parser.parse_args()
    
    crawler = PedestrianVideoCrawler(
        output_dir=args.output,
        max_videos=args.max_videos,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        search_terms=args.search_terms,
        headless=args.headless
    )
    
    crawler.run()


if __name__ == "__main__":
    main()
