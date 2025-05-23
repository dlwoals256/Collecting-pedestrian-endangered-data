# YouTube Pedestrian Safety Video Crawler

A reliable and efficient tool to collect YouTube videos related to pedestrian safety and dangerous situations. These videos can be valuable for data analysis, training AI models, or conducting safety research.

## Features

- **YouTube API Integration**: Uses the official YouTube Data API for efficient and compliant searching
- **yt-dlp for Reliable Downloads**: Implements yt-dlp to overcome YouTube's download restrictions
- **Fallback Methods**: Includes multiple download approaches to ensure high success rates
- **Customizable Search**: Supports custom search terms and video filtering options
- **Comprehensive Metadata**: Stores detailed information about each downloaded video
- **Robust Error Handling**: Implements retries and fallbacks to handle various error scenarios

## Installation

1. Install required Python packages:

```powershell
pip install -r requirements.txt
```

2. Requirements:
   - Python 3.6+
   - YouTube Data API key from [Google Cloud Console](https://console.cloud.google.com/)
   - yt-dlp (automatically installed via requirements.txt)

## Usage

Run the crawler using:

```powershell
python YoutubeCrawler.py --api-key YOUR_API_KEY --max-videos 10 --min-duration 10 --max-duration 180
```

This will search YouTube for pedestrian safety videos and download them using the most reliable methods available.

## Command Line Arguments

The crawler supports various command-line options to customize its behavior:


- `--api-key`: Your YouTube Data API key (required)
- `--output` or `-o`: Directory to save downloaded videos (default: "./downloaded_videos")
- `--max-videos` or `-m`: Maximum number of videos to download (default: 50)
- `--min-duration`: Minimum video duration in seconds (default: 5)
- `--max-duration`: Maximum video duration in seconds (default: 300)
- `--search-terms` or `-s`: Custom search terms to use (space separated)

Example with custom search terms:

```powershell
python YoutubeCrawler.py --api-key YOUR_API_KEY --max-videos 5 --search-terms "pedestrian near miss" "crosswalk accident"
```

## How It Works

The crawler addresses YouTube download restrictions using a multi-layered approach:

1. **yt-dlp Integration**: Uses the robust yt-dlp library for downloading, which actively maintains workarounds for YouTube's restrictions
2. **Fallback System**: If yt-dlp encounters issues, falls back to direct URL extraction methods
3. **Retry Mechanism**: Implements exponential backoff for retries when downloads fail

This approach provides several advantages:
- Higher success rate than libraries like PyTube (which frequently encounter HTTP 400/403 errors)
- No need for browser automation like Selenium (which is resource-intensive)
- Stays up-to-date with YouTube's changing systems through yt-dlp updates

## Default Search Terms

The crawler will search for videos using these search terms by default:
- pedestrian near miss video
- pedestrian accident footage
- pedestrian crossing danger cctv
- pedestrian safety violation video
- pedestrian hazard dashcam
- pedestrian traffic incident footage
- pedestrian close call video
- pedestrian intersection danger
- road safety pedestrian accident
- crosswalk safety violation

## Output

The crawler generates three main types of output:

1. **Downloaded Videos**: All videos are saved in the specified output directory with filenames that include the video ID and title.

2. **Metadata CSV**: A CSV file named "video_metadata.csv" is created in the output directory with detailed information about each downloaded video:
   - Video ID and title
   - URL and channel name
   - Duration and view count
   - Published date
   - Search term used to find the video

3. **Log File**: A file named "youtube_crawler_log.txt" tracks all operations and any errors encountered during the crawling process.

## Getting a YouTube Data API Key

To use this crawler, you'll need a YouTube Data API key:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create credentials (API key)
5. Use the API key with the `YoutubeCrawler.py` script

## Troubleshooting

If you encounter any issues:

1. **Check API Limits**: The YouTube Data API has daily quotas - ensure you haven't exceeded yours
2. **Network Issues**: Verify your internet connection and try using a VPN if you encounter regional restrictions
3. **Update yt-dlp**: YouTube frequently changes its systems - ensure you have the latest version with `pip install -U yt-dlp`
4. **Rate Limiting**: Add longer delays between requests by modifying the random delay values in the code
5. **Permissions**: Ensure the script has permission to write to the output directory
