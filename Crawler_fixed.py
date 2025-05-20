#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pedestrian Safety Video Crawler
This script searches and downloads videos related to pedestrians in dangerous situations
for data collection and analysis purposes.
"""

import os
import re
import csv
import time
import argparse
import requests
from bs4 import BeautifulSoup
from pytube import YouTube
from urllib.parse import urlparse, parse_qs
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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
                 max_duration=300, search_terms=None):
        """
        Initialize the crawler with configuration parameters
        
        Args:
            output_dir (str): Directory to save downloaded videos
            max_videos (int): Maximum number of videos to download
            min_duration (int): Minimum video duration in seconds
            max_duration (int): Maximum video duration in seconds
            search_terms (list): List of search terms to use
        """
        self.output_dir = output_dir
        self.max_videos = max_videos
        self.min_duration = min_duration
        self.max_duration = max_duration
        
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
    
    def search_youtube(self, query, max_results=30):
        """
        Search YouTube for videos matching the query
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video URLs
        """
        # Use the YouTube search URL
        search_url = f"https://www.youtube.com/results?search_query={'+'.join(query.split())}"
        logger.info(f"Searching YouTube for: {query}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://www.youtube.com/",
            "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        
        try:
            # Use a session to handle cookies and retry mechanism
            session = requests.Session()
            retries = 3
            video_urls = []
            
            for attempt in range(retries):
                try:
                    response = session.get(search_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Try to extract video IDs using multiple patterns
                    # Pattern 1: Standard watch links
                    video_ids = re.findall(r"watch\?v=(\S{11})", response.text)
                    
                    # Pattern 2: From JSON data embedded in the page
                    json_matches = re.findall(r'"videoId":"([^"]{11})"', response.text)
                    if json_matches:
                        video_ids.extend(json_matches)
                    
                    if not video_ids:
                        # Try to find video renderer patterns in the YouTube response
                        renderer_matches = re.findall(r'"videoRenderer":{.*?"videoId":"([^"]{11})"', response.text)
                        if renderer_matches:
                            video_ids.extend(renderer_matches)
                    
                    # If we found some IDs, break the retry loop
                    if video_ids:
                        break
                        
                    logger.warning(f"No video IDs found in attempt {attempt+1}, retrying with delay...")
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                    
                except requests.RequestException as e:
                    logger.warning(f"Request failed on attempt {attempt+1}: {e}")
                    if attempt < retries - 1:  # Don't sleep on the last attempt
                        time.sleep(2 * (attempt + 1))
            
            # Remove duplicates and convert to URLs
            unique_ids = list(dict.fromkeys(video_ids))
            video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in unique_ids[:max_results]]
            
            if video_urls:
                logger.info(f"Found {len(video_urls)} videos for query: {query}")
            else:
                logger.warning(f"No videos found for query: {query} after {retries} attempts")
                
            return video_urls
            
        except Exception as e:
            logger.error(f"Error searching YouTube: {e}")
            return []
    
    def is_valid_video(self, yt):
        """
        Check if a YouTube video meets our criteria
        
        Args:
            yt (YouTube): YouTube object
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Get video details
            duration = yt.length
            
            # Check duration constraints
            if duration < self.min_duration or duration > self.max_duration:
                logger.debug(f"Video duration ({duration}s) outside allowed range ({self.min_duration}-{self.max_duration}s)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating video: {e}")
            return False
    
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
                
                # Create YouTube object with custom options
                yt = YouTube(
                    url,
                    use_oauth=False,
                    allow_oauth_cache=True,
                    on_progress_callback=None
                )
                
                # Give YouTube API time to initialize
                time.sleep(1)
                
                if not self.is_valid_video(yt):
                    logger.info(f"Video {url} did not meet criteria")
                    return False, None
                    
                # Get video ID
                parsed_url = urlparse(url)
                video_id = parse_qs(parsed_url.query).get('v', [None])[0]
                if not video_id:
                    logger.error(f"Could not extract video ID from URL: {url}")
                    return False, None
                
                # Create a safe filename
                safe_title = re.sub(r'[\\/*?:"<>|]', "", yt.title)
                filename = f"{video_id}_{safe_title[:50]}.mp4"
                filepath = os.path.join(self.output_dir, filename)
                
                # Check if already downloaded
                if os.path.exists(filepath):
                    logger.info(f"Video already downloaded: {filepath}")
                    return False, None
                
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
                logger.info(f"Downloading: {yt.title} (Resolution: {stream.resolution})")
                stream.download(output_path=self.output_dir, filename=filename)
                
                # Verify file was actually downloaded
                if not os.path.exists(filepath) or os.path.getsize(filepath) < 10000:  # Less than 10KB
                    logger.warning(f"Downloaded file is too small or doesn't exist: {filepath}")
                    if os.path.exists(filepath):
                        os.remove(filepath)  # Remove corrupt/empty file
                    continue  # Retry
                
                # Create metadata
                metadata = {
                    "video_id": video_id,
                    "title": yt.title,
                    "source": "youtube",
                    "url": url,
                    "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": yt.length,
                    "search_term": search_term,
                    "filename": filename,
                    "tags": ",".join(yt.keywords) if hasattr(yt, 'keywords') and yt.keywords else "",
                    "resolution": stream.resolution if stream.resolution else "unknown"
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
        
        # Process each search term
        for search_term in self.search_terms:
            if downloaded_count >= self.max_videos:
                break
                
            video_urls = self.search_youtube(search_term)
            logger.info(f"Found {len(video_urls)} videos for '{search_term}'")
            
            # Download videos with multiple threads
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for url in video_urls:
                    if downloaded_count >= self.max_videos:
                        break
                    futures.append(executor.submit(self.download_video, url, search_term))
                
                for future in futures:
                    success, _ = future.result()
                    if success:
                        downloaded_count += 1
                    
                    if downloaded_count >= self.max_videos:
                        break
                        
            # Pause between search terms to avoid being rate-limited
            time.sleep(5)
                
        logger.info(f"Crawler finished. Downloaded {downloaded_count} videos.")
        return downloaded_count


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
    parser.add_argument("--captcha-wait", type=int, default=60,
                        help="Wait time in seconds if a CAPTCHA is detected")
    parser.add_argument("--delay", type=int, default=2,
                        help="Delay between video downloads in seconds")
    
    args = parser.parse_args()
    
    crawler = PedestrianVideoCrawler(
        output_dir=args.output,
        max_videos=args.max_videos,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        search_terms=args.search_terms
    )
    
    crawler.run()


if __name__ == "__main__":
    main()
