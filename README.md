# 📦 Ad Vault — Meta Ad Archiver

Paste any Facebook Ad Library URL → scrapes all details + downloads images/videos locally. Ads are saved forever, even if the original gets taken down.

## Requirements

- Python 3.8+
- pip (Python package manager)

## Setup (one-time)

```bash
pip install flask playwright
playwright install chromium
```

## Run

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

## How to use

1. Go to [Facebook Ad Library](https://www.facebook.com/ads/library/)
2. Find an ad you want to archive
3. Copy the URL (e.g. `https://www.facebook.com/ads/library/?id=25735814926036478`)
4. Paste it into Ad Vault and click **Archive Ad**
5. The tool will scrape all details and download media to your Mac/PC

## Where are ads saved?

All ads are saved to:
- **Mac/Linux:** `~/MetaAdArchive/`
- **Windows:** `C:\Users\YourName\MetaAdArchive\`

Each ad gets its own folder with:
- `ad_meta.json` — all scraped details (page name, status, start date, platforms, ad copy)
- `screenshot.png` — full page screenshot
- `image_01.jpg`, `image_02.jpg` etc. — all images
- `video_01.mp4` etc. — any video creatives

## Tips

- Ads that have been running a long time = likely good performers
- Check the "Started Running" date in the archived metadata
- Use the **Local Archive** section in the UI to browse all saved ads
- Click any archived ad to open its folder in Finder/Explorer

## Note on Facebook login

Some ads in the Ad Library are visible without login. If an ad requires login to view, you may need to add your Facebook session cookies. The tool uses a real Chromium browser so it behaves like a normal user.
