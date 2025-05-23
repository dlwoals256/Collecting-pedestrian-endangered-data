#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Final Enhanced Crawler for Pedestrian Safety Videos
This version combines YouTube Data API search with yt-dlp for reliable video downloading
to overcome YouTube download restrictions.
"""

import os
import re
import csv
import json
import time
import random
import logging
import argparse
import subprocess
from datetime import datetime
import requests
from urllib.parse import parse_qs, urlparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import yt-dlp for reliable video downloads
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FinalPedestrianCrawler")

# Check for yt-dlp
if not YTDLP_AVAILABLE:
    logger.warning("yt-dlp not installed. Install with: pip install yt-dlp")
    logger.warning("Falling back to less reliable download methods")


class YtDlpDownloader:
    """A downloader that uses yt-dlp for reliable YouTube downloads"""
    
    def __init__(self):
        """Initialize the yt-dlp downloader"""
        self.available = YTDLP_AVAILABLE
        if not self.available:
            logger.warning("YtDlpDownloader initialized but yt-dlp is not available")
    
    def download_video(self, video_url, output_dir=".", filename=None, fmt='mp4'):
        """
        Download a YouTube video using yt-dlp
        
        Args:
            video_url (str): The YouTube video URL
            output_dir (str): Directory to save the video
            filename (str): Optional specific filename to use (without extension)
            fmt (str): Video format (default: mp4)
            
        Returns:
            tuple: (success (bool), filepath (str))
        """
        if not self.available:
            logger.error("yt-dlp is not available")
            return False, None
            
        logger.info(f"Attempting to download {video_url} with yt-dlp")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        try:
            # Extract video ID to use for the filename if needed
            video_id = self._extract_video_id(video_url)
            if not video_id:
                logger.error(f"Could not extract video ID from URL: {video_url}")
                return False, None
                
            # Set output template
            if filename:
                # Make sure we don't have the extension in the filename
                if filename.endswith(f".{fmt}"):
                    filename = filename[:-len(f".{fmt}")]
                output_template = os.path.join(output_dir, f"{filename}.{fmt}")
            else:
                output_template = os.path.join(output_dir, f"{video_id}.%(title)s.{fmt}")
                
            # Set up yt-dlp options
            ydl_opts = {
                'format': f'best[ext={fmt}]/best',  # Try to get best quality mp4, fallback to best available
                'outtmpl': output_template,
                'noplaylist': True,
                'quiet': False,
                'no_warnings': False,
                'ignoreerrors': False,
                'geo_bypass': True,  # Try to bypass geo-restrictions
                'noprogress': True,  # Don't show the download progress bar
            }
            
            # Add a progress hook to log progress
            ydl_opts['progress_hooks'] = [self._progress_hook]
            
            # Run the download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading video with yt-dlp: {video_url}")
                info = ydl.extract_info(video_url, download=True)
                
                # Get the actual filename after download
                if 'requested_downloads' in info and info['requested_downloads']:
                    filepath = info['requested_downloads'][0]['filepath']
                else:
                    # Fallback: construct filepath from information we have
                    _title = info.get('title', 'unknown')
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", _title)
                    filepath = os.path.join(output_dir, f"{video_id}_{safe_title[:50]}.{fmt}")
                
                # Verify the file exists and has proper size
                if not os.path.exists(filepath):
                    logger.error(f"Download failed: File {filepath} does not exist")
                    return False, None
                    
                file_size = os.path.getsize(filepath)
                if file_size < 10000:  # Less than 10KB
                    logger.error(f"Downloaded file is too small: {file_size} bytes")
                    os.remove(filepath)
                    return False, None
                    
                logger.info(f"Successfully downloaded to {filepath} ({file_size/(1024*1024):.2f} MB)")
                return True, filepath
                
        except Exception as e:
            logger.error(f"yt-dlp download error: {str(e)}")
            return False, None
    
    def _extract_video_id(self, url):
        """Extract the YouTube video ID from a URL"""
        if not url:
            return None
        
        # Extract video ID from various URL formats
        if 'youtu.be' in url:
            return urlparse(url).path.strip('/')
        else:
            query = parse_qs(urlparse(url).query)
            return query.get('v', [None])[0]
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp to log download progress"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'unknown')
            speed = d.get('_speed_str', 'unknown speed')
            eta = d.get('_eta_str', 'unknown ETA')
            logger.info(f"Download progress: {percent} at {speed}, ETA: {eta}")
        elif d['status'] == 'finished':
            logger.info(f"Download finished, now processing file")

class SimpleYouTubeDownloader:
    """Simple client for downloading YouTube videos using basic techniques"""
    
    def __init__(self):
        """Initialize the downloader with common headers"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        })
    
    def extract_video_id(self, url):
        """Extract the YouTube video ID from a URL"""
        if not url:
            return None
        
        # Extract video ID from various URL formats
        if 'youtu.be' in url:
            return urlparse(url).path.strip('/')
        else:
            query = parse_qs(urlparse(url).query)
            return query.get('v', [None])[0]
    
    def get_info_page(self, video_id):
        """Get the YouTube page HTML containing video info"""
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error getting video page: {e}")
            return None
    
    def extract_video_info(self, html):
        """Extract the player response from the YouTube page HTML"""
        pattern = r'var ytInitialPlayerResponse\s*=\s*({.+?});'
        match = re.search(pattern, html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None
    
    def get_download_url(self, video_info):
        """Extract the download URL from the video info"""
        if not video_info:
            return None
            
        # Try to find a progressive stream (audio+video)
        formats = video_info.get('streamingData', {}).get('formats', [])
        if formats:
            # Get the highest quality format
            formats.sort(key=lambda x: x.get('height', 0), reverse=True)
            url = formats[0].get('url')
            if url:
                return url
        
        # If no progressive formats, try adaptive formats
        formats = video_info.get('streamingData', {}).get('adaptiveFormats', [])
        if formats:
            # Filter for video formats
            video_formats = [f for f in formats if f.get('mimeType', '').startswith('video/mp4')]
            if video_formats:
                video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
                url = video_formats[0].get('url')
                if url:
                    return url
                    
        return None
    
    def download_video(self, youtube_url, output_dir=".", filename=None):
        """
        Download a YouTube video
        
        Args:
            youtube_url (str): The YouTube video URL
            output_dir (str): Directory to save the video
            filename (str): Optional specific filename to use
            
        Returns:
            tuple: (success (bool), filepath (str))
        """
        logger.info(f"Attempting to download {youtube_url}")
        
        # Extract video ID
        video_id = self.extract_video_id(youtube_url)
        if not video_id:
            logger.error(f"Could not extract video ID from URL: {youtube_url}")
            return False, None
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Get the YouTube page
        logger.info(f"Fetching video page for {video_id}")
        html = self.get_info_page(video_id)
        if not html:
            logger.error("Failed to get video page")
            return False, None
            
        # Extract video info
        logger.info("Extracting video info")
        video_info = self.extract_video_info(html)
        if not video_info:
            logger.error("Failed to extract video info")
            return False, None
            
        # Get video title
        title = video_info.get('videoDetails', {}).get('title', 'unknown_video')
        logger.info(f"Video title: {title}")
        
        # Create safe filename
        if not filename:
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            filename = f"{video_id}_{safe_title[:50]}.mp4"
        filepath = os.path.join(output_dir, filename)
        
        # Check if already downloaded
        if os.path.exists(filepath):
            logger.info(f"Video already downloaded: {filepath}")
            return True, filepath
            
        # Get download URL
        logger.info("Getting download URL")
        download_url = self.get_download_url(video_info)
        if not download_url:
            logger.error("Failed to get download URL")
            return False, None
            
        # Download the video
        logger.info(f"Downloading video to {filepath}")
        try:
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()
            
            # Get content length if available
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress occasionally
                        if total_size > 0 and downloaded % (total_size // 10) < 8192:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {percent:.1f}%")
            
            # Verify download
            if os.path.getsize(filepath) < 10000:  # Less than 10KB
                logger.error("Downloaded file is too small")
                os.remove(filepath)
                return False, None
                
            logger.info(f"Successfully downloaded to {filepath} ({os.path.getsize(filepath)/(1024*1024):.2f} MB)")
            return True, filepath
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return False, None


class FinalPedestrianCrawler:
    """Final enhanced crawler for collecting pedestrian safety videos"""
    def __init__(self, api_key, output_dir="./downloaded_videos", max_videos=50, 
                min_duration=5, max_duration=300, search_terms=None):
        """
        Initialize the crawler
        
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
        
        # Initialize YouTube API client
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Initialize our downloaders in order of preference
        self.ytdlp_downloader = YtDlpDownloader() if YTDLP_AVAILABLE else None
        self.downloader = SimpleYouTubeDownloader()  # Fallback downloader
        
        # Default search terms if none provided
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
    
    def test_api_connection(self):
        """Test the API connection before starting the crawler"""
        try:
            # Make a simple request to test the API key
            logger.info("Testing API connection...")
            masked_key = self.api_key[:4] + '...' + self.api_key[-4:] if len(self.api_key) > 8 else "****"
            logger.info(f"Using API key: {masked_key}")
            
            # Test with a simple request - getting video details for a known video
            test_response = self.youtube.videos().list(
                part="snippet",
                id="dQw4w9WgXcQ"  # A well-known video ID
            ).execute()
            
            logger.info("✅ API connection test successful!")
            return True
        except HttpError as e:
            logger.error(f"❌ API connection test failed: {e.resp.status} - {e.content.decode('utf-8')}")
            # Print more debugging information
            logger.error(f"API Key might be invalid or restricted incorrectly")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error testing API connection: {str(e)}")
            return False
    
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
        Download a video from YouTube using multiple methods in fallback order:
        1. yt-dlp (most reliable)
        2. Simple downloader (fallback)
        
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
        
        # Maximum retries for all download methods
        max_retries = 3
        success = False
        actual_filepath = None
        
        # METHOD 1: Try with yt-dlp (most reliable)
        if self.ytdlp_downloader and self.ytdlp_downloader.available:
            logger.info(f"Attempting download with yt-dlp: {url}")
            
            for retry in range(max_retries):
                try:
                    # Add retry mechanism with backoff
                    if retry > 0:
                        wait_time = 2 ** retry  # Exponential backoff: 2, 4, 8 seconds
                        logger.info(f"yt-dlp retry attempt {retry+1}/{max_retries} for {url}, waiting {wait_time}s")
                        time.sleep(wait_time)
                    
                    # Try to download with yt-dlp
                    success, actual_filepath = self.ytdlp_downloader.download_video(
                        url,
                        output_dir=self.output_dir,
                        filename=os.path.splitext(filename)[0]  # Remove .mp4 extension
                    )
                    
                    if success:
                        logger.info(f"yt-dlp download succeeded: {actual_filepath}")
                        break
                        
                except Exception as e:
                    logger.error(f"yt-dlp download error (attempt {retry+1}/{max_retries}): {str(e)}")
                    if "429" in str(e):
                        logger.error(f"Rate limited (429). Waiting longer before retry.")
                        time.sleep(30 + (30 * retry))  # Wait longer for rate limits
        
        # METHOD 2: Fall back to simple downloader if yt-dlp failed
        if not success:
            logger.info(f"yt-dlp download failed or not available, trying simple downloader: {url}")
            
            for retry in range(max_retries):
                try:
                    # Add retry mechanism with backoff
                    if retry > 0:
                        wait_time = 2 ** retry  # Exponential backoff: 2, 4, 8 seconds
                        logger.info(f"Simple downloader retry attempt {retry+1}/{max_retries} for {url}, waiting {wait_time}s")
                        time.sleep(wait_time)
                    
                    # Try to download with simple downloader
                    success, actual_filepath = self.downloader.download_video(
                        url,
                        output_dir=self.output_dir,
                        filename=filename
                    )
                    
                    if success:
                        logger.info(f"Simple downloader succeeded: {actual_filepath}")
                        break
                        
                except Exception as e:
                    if "429" in str(e):
                        logger.error(f"Rate limited (429). Waiting longer before retry.")
                        time.sleep(30 + (30 * retry))  # Wait longer for rate limits
                    else:
                        logger.error(f"Error with simple downloader (attempt {retry+1}/{max_retries}): {e}")
        
        # If any method succeeded, save metadata and return success
        if success and actual_filepath:
            # Get the actual filename that was used (might be different from our original)
            actual_filename = os.path.basename(actual_filepath)
            
            # Create metadata
            metadata = {
                "video_id": video_id,
                "title": title,
                "source": "youtube",
                "url": url,
                "download_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": video_data["duration_seconds"],
                "search_term": search_term,
                "filename": actual_filename,
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
                
            logger.info(f"Successfully downloaded: {actual_filepath}")
            return True, metadata
        
        # All download methods failed
        logger.error(f"All download methods failed for {url}")
        return False, None
    
    def run(self):
        """
        Run the crawler to search and download videos
        """
        logger.info("Starting final enhanced crawler...")
        downloaded_count = 0
        
        try:
            # Test API connection before proceeding
            if not self.test_api_connection():
                logger.error("API connection test failed. Exiting...")
                return downloaded_count
            
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
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Download pedestrian safety videos using yt-dlp and other reliable methods")
    
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
    
    # Check if yt-dlp is available
    if not YTDLP_AVAILABLE:
        print("\nWARNING: yt-dlp is not installed. Install it with: pip install yt-dlp")
        print("Falling back to less reliable download methods which may fail with HTTP 403 errors.\n")
        
    crawler = FinalPedestrianCrawler(
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
