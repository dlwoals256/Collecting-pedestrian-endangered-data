# Pedestrian Safety Video Crawler

This project contains three versions of a web crawler designed to collect video data about pedestrians in dangerous situations. These videos can be used for data analysis, training AI models, or safety research.

## Crawlers

### 1. Original Crawler (`Crawler.py`)

The original crawler uses direct HTTP requests and PyTube for downloading YouTube videos. However, it may encounter 400 errors due to YouTube's bot prevention.

### 2. Selenium-based Crawler (`Crawler_selenium.py`)

The Selenium-based crawler uses a web browser automation to navigate YouTube more like a human user. This approach is more likely to avoid the 400 errors that the original crawler encounters.

### 3. YouTube API Crawler (`Crawler_api.py`) - RECOMMENDED

The API-based crawler uses the official YouTube Data API v3 to search for videos. This is the most reliable method as it follows YouTube's terms of service and doesn't require web scraping. However, it requires a free API key from Google Cloud Console.

## Installation

Before using the crawlers, install the required Python packages:

```bash
# For the original crawler
pip install requests beautifulsoup4 pytube

# For the Selenium-based crawler (additional dependencies)
pip install selenium webdriver-manager

# For the API-based crawler (additional dependencies)
pip install google-api-python-client
```

You also need:
- Chrome browser installed on your system for the Selenium crawler
- YouTube Data API key for the API-based crawler (get it from [Google Cloud Console](https://console.cloud.google.com/))

## Usage

### Original Crawler:

```powershell
python Crawler.py --max-videos 10 --min-duration 10 --max-duration 180
```

### Selenium Crawler:

```powershell
python Crawler_selenium.py --max-videos 10 --min-duration 10 --max-duration 180
```

If you want to see the browser in action (not headless mode):

```powershell
python Crawler_selenium.py --max-videos 10 --visible
```

### API-based Crawler (Recommended):

```powershell
python Crawler_api.py --api-key YOUR_API_KEY --max-videos 10 --min-duration 10 --max-duration 180
```

Replace `YOUR_API_KEY` with your actual YouTube Data API key.

## Command Line Options

All crawlers support these common command-line arguments:

- `--output` or `-o`: Directory to save downloaded videos (default: "./downloaded_videos")
- `--max-videos` or `-m`: Maximum number of videos to download (default: 50)
- `--min-duration`: Minimum video duration in seconds (default: 5)
- `--max-duration`: Maximum video duration in seconds (default: 300)
- `--search-terms` or `-s`: Custom search terms to use (space separated)

The Selenium crawler additionally supports:

- `--headless`: Run in headless mode (no browser UI) - this is the default
- `--visible`: Show browser window while running

The API crawler additionally requires:

- `--api-key`: Your YouTube Data API key (required)

## Search Terms

By default, both crawlers will search for videos using these search terms:
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

1. **Downloaded Videos**: All videos will be saved in the specified output directory with filenames that include the video ID and title.

2. **Metadata CSV**: A CSV file named "video_metadata.csv" is created in the output directory with detailed information about each downloaded video.

3. **Log File**: A log file named "crawler_log.txt" tracks all operations and any errors.

## Troubleshooting

If you encounter many 400 errors with the original crawler, try the Selenium-based crawler or API-based crawler instead.

### Recommended Approach

1. **Best option**: Use the API-based crawler (`Crawler_api.py`). This is the most reliable method as it follows YouTube's terms of service and uses their official API.

2. **Second best**: Try the Selenium-based crawler (`Crawler_selenium.py`) which better simulates human browser interaction.

3. **Last resort**: Fall back to the original crawler (`Crawler.py`) with added delays between requests.

### Additional Troubleshooting Steps

If all methods fail, you may need to:
1. Use a VPN to change your IP address
2. Try different search terms
3. Decrease the number of videos you attempt to download in one session
4. Add longer delays between requests (modify the code)
5. For the API crawler, check if you've exceeded your API quota for the day

## Getting a YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create credentials (API key)
5. Use the API key with the `Crawler_api.py` script
