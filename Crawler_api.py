#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pedestrian Safety Video Crawler using YouTube Data API
This script searches and downloads videos related to pedestrians in dangerous situations
using the official YouTube Data API, which is more reliable than web scraping.

NOTE: Requires a YouTube Data API key from Google Cloud Console
(https://console.cloud.google.com/)
"""

import os
import re
import csv
import time
import argparse
import requests
import json
import random
from pytube import YouTube
from urllib.parse import urlparse, parse_qs
import logging
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

class PedestrianVideoCrawlerAPI:
    """Crawler class for collecting videos of pedestrians in dangerous situations using YouTube API"""
    
    def __init__(self, api_key, output_dir="./downloaded_videos", max_videos=50, min_duration=5, 
                 max_duration=300, search_terms=None):
        """
        Initialize the crawler with configuration parameters
        
        Args:
            api_key (str): YouTube Data API key
            output_dir (str): Directory to save downloaded videos
            max_videos (int): Maximum number of videos to download
            min_duration (int): Minimum video duration in seconds
            max_duration (int): Maximum video duration in seconds
            search_terms (list): List of search terms to use
        """
        self.api_key = api_key
        self.output_dir = output_dir
        self.max_videos = max_videos
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
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
                    "duration_seconds", "search_term", "filename", "tags",
                    "description", "channel", "view_count", "published_at"
                ])
                logger.info(f"Created metadata file: {self.metadata_file}")
    
    def search_youtube_api(self, query, max_results=30):
        """
        Search YouTube using the Data API
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video metadata
        """
        logger.info(f"Searching YouTube API for: {query}")
        videos = []
        
        try:
            # Call the search.list method to retrieve results matching the specified query term
            search_response = self.youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=max_results,
                type="video",
                videoEmbeddable="true",  # Only return embeddable videos
                videoSyndicated="true",  # Only return videos that can be played outside youtube.com
                safeSearch="moderate"
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in search_response["items"]]
            
            if not video_ids:
                logger.warning(f"No videos found for query: {query}")
                return []
                
            # Get detailed info for all videos in a single request
            videos_response = self.youtube.videos().list(
                id=",".join(video_ids),
                part="snippet,contentDetails,statistics"
            ).execute()
            
            for video in videos_response["items"]:
                try:
                    # Parse duration from ISO 8601 format (PT#M#S)
                    duration_str = video["contentDetails"]["duration"]
                    hours = re.search(r'(\d+)H', duration_str)
                    minutes = re.search(r'(\d+)M', duration_str)
                    seconds = re.search(r'(\d+)S', duration_str)
                    
                    duration_seconds = 0
                    if hours:
                        duration_seconds += int(hours.group(1)) * 3600
                    if minutes:
                        duration_seconds += int(minutes.group(1)) * 60
                    if seconds:
                        duration_seconds += int(seconds.group(1))
                        
                    # Check duration constraints
                    if duration_seconds < self.min_duration or duration_seconds > self.max_duration:
                        continue
                        
                    # Extract view count (if available)
                    view_count = 0
                    if "statistics" in video and "viewCount" in video["statistics"]:
                        view_count = int(video["statistics"]["viewCount"])
                    
                    video_data = {
                        "id": video["id"],
                        "title": video["snippet"]["title"],
                        "description": video["snippet"]["description"],
                        "channel": video["snippet"]["channelTitle"],
                        "published_at": video["snippet"]["publishedAt"],
                        "duration_seconds": duration_seconds,
                        "url": f"https://www.youtube.com/watch?v={video['id']}",
                        "view_count": view_count,
                        "thumbnails": video["snippet"]["thumbnails"]
                    }
                    
                    videos.append(video_data)
                    
                except Exception as e:
                    logger.error(f"Error processing video {video['id']}: {e}")
                    continue
            
            logger.info(f"Found {len(videos)} suitable videos for query: {query}")
            return videos
            
        except HttpError as e:
            logger.error(f"API Error ({e.resp.status}): {e.content.decode('utf-8')}")
            return []
        except Exception as e:
            logger.error(f"Error searching YouTube API: {e}")
            return []
    
    def download_video(self, video_data, search_term):
        """
        Download a video from YouTube
        
        Args:
            video_data (dict): Video information from the API
            search_term (str): The search term that found this video
            
        Returns:
            tuple: (success (bool), metadata (dict))
        """
        url = video_data["url"]
        video_id = video_data["id"]
        title = video_data["title"]
        
        # Create a safe filename
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
        filename = f"{video_id}_{safe_title[:50]}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        # Check if already downloaded
        if os.path.exists(filepath):
            logger.info(f"Video already downloaded: {filepath}")
            return False, None
        
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
                    "duration_seconds": video_data["duration_seconds"],
                    "search_term": search_term,
                    "filename": filename,
                    "tags": "",
                    "description": video_data.get("description", ""),
                    "channel": video_data.get("channel", ""),
                    "view_count": video_data.get("view_count", 0),
                    "published_at": video_data.get("published_at", "")
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
                        metadata["tags"],
                        metadata["description"],
                        metadata["channel"],
                        metadata["view_count"],
                        metadata["published_at"]
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
        logger.info("Starting crawler with YouTube Data API...")
        downloaded_count = 0
        
        try:
            # Process each search term
            for search_term in self.search_terms:
                if downloaded_count >= self.max_videos:
                    break
                    
                videos = self.search_youtube_api(search_term)
                logger.info(f"Found {len(videos)} suitable videos for '{search_term}'")
                
                # Shuffle the videos to get more variety
                random.shuffle(videos)
                
                # Process videos
                for video in videos:
                    if downloaded_count >= self.max_videos:
                        break
                        
                    success, _ = self.download_video(video, search_term)
                    if success:
                        downloaded_count += 1
                        
                    # Add a small delay between downloads
                    time.sleep(random.uniform(1.0, 3.0))
                    
                # Pause between search terms to avoid API limits
                time.sleep(random.uniform(2.0, 5.0))
                    
            logger.info(f"Crawler finished. Downloaded {downloaded_count} videos.")
            return downloaded_count
            
        except Exception as e:
            logger.error(f"Error in crawler execution: {e}")
            return downloaded_count


def main():
    """Main function to run the crawler with command line arguments"""
    parser = argparse.ArgumentParser(description="Download pedestrian safety videos for data collection")
    
    parser.add_argument("--api-key", required=True,
                        help="YouTube Data API key (required)")
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
    
    args = parser.parse_args()
    
    crawler = PedestrianVideoCrawlerAPI(
        api_key=args.api_key,
        output_dir=args.output,
        max_videos=args.max_videos,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        search_terms=args.search_terms
    )
    
    crawler.run()


if __name__ == "__main__":
    main()
