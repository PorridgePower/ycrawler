# ycrawler

Simple scrips processing top N posts on [Hacker News](news.ycombinator.com) and downloads link in comments.
Saved results are located in directories according to post IDs.

## Usage
```
usage: crawler.py [-h] [--period period] [--amount amount]
                  [--directory directory]

Analyses Nginx log for most requested URLs and generate report

optional arguments:
  -h, --help            show this help message and exit
  --period period       Poll period in seconds. Defaults to 2 minutes
  --amount amount       Number of posts to parse, Defaults to 30
  --directory directory
                        Download directory
```

## Output
```
$  python3 crawler.py --period 120 --direcroty ./downloads 
[2023.05.31 10:05:40] INFO Starting new iteration...
[2023.05.31 10:05:46] INFO Collecting links for post 36137530
[2023.05.31 10:05:46] INFO Collecting links for post 36138224
...
[2023.05.31 10:05:55] INFO Saving https://zealdocs.org/ to /home/user/other_projects/14_asyncio/downloads/36135955/v6ddkf0u91
[2023.05.31 10:05:55] INFO Saving item?id=36138224 to /home/user/other_projects/14_asyncio/downloads/36138224/7cdbce6yy7
[2023.05.31 10:05:55] ERROR Exception while downloading item?id=36138224
[2023.05.31 10:05:55] INFO Saving https://www.colorado.edu/today/2023/05/24/these-tiny-medical-robots-could-one-day-travel-through-your-body to /home/user/other_projects/14_asyncio/downloads/36137530/ppzulaxe6b
[2023.05.31 10:06:00] INFO Saving https://torrentfreak.com/iconic-torrent-site-rarbg-shuts-down-all-content-releases-stop-230531/ to /home/user/other_projects/14_asyncio/downloads/36137773/ym6v6uzdc0
...
[2023.05.31 10:07:40] INFO Starting new iteration...
[2023.05.31 10:07:46] INFO Post 36137530 had already previously saved. Skipping...
[2023.05.31 10:07:46] INFO Post 36135955 had already previously saved. Skipping...
...
[2023.05.31 10:07:46] INFO Post 36128082 had already previously saved. Skipping...
[2023.05.31 10:07:46] INFO Post 36102464 had already previously saved. Skipping...
[2023.05.31 10:07:46] INFO Collecting links for post 36135241
^C[2023.05.31 10:07:54] INFO Shutting down - received keyboard interrupt
```