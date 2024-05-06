# news article parser

parsing html tags from news papers based on lxml. Dumping parsed data into database.

Setup:

- one .env file with MySQL credentials.
- two databases, one for articles in raw html and one as destination for parsed articles.

## Installing requirements

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Example .env file

```env
# .env
db_host=localhost
db_user=user
db_pass=password
db_charset=utf8mb

db_name_articles=news_articles      # database as source of articles htmls
nyt_articles=new_york_times_articles
zeit_articles=zeit_articles
scmp_articles=south_china_morning_post_articles

db_name_parsed=news_parsed      # database as destionation of parsed articles
nyt_parsed=new_york_times_parsed
zeit_parsed=zeit_parsed
scmp_parsed=south_china_morning_post_parsed
log=mainLogStat
```

## Running the parser

Notes regarding the dictionaries provieded when initializing the parser object:

- keys need to keep the same name as blow (except for papers names, ie 'nyt', 'zeit' and 'scmp')
- values need to be in line with the .env file

```python
# main.py
from newsArticleParser import newsArticleParser

# initializing the object with the relevant db credentials, db names, and db table names
parser = newsArticleParser(
    dbCredentials={'host':'db_host','user':'db_user','password':'db_pass','charset':'db_charset'},
    dbNamesTables={'dbNameDestination': 'db_name_parsed', 'dbNameSource':'db_name_articles', 'dbTableLogging':'log'},
    papers={
        'nyt':{
            'sourceTable': 'nyt_articles',
            'destinationTable': 'nyt_parsed',
            'xpath': {
                'headline': '//h1[@class="article-title"] | //*[@class="artikelBody"]//h1',
                'subtext':'//p[@class="article-subtitle"] | //*[@class="artikelBody"]/h2',
                'story':'//*[@class="article-body"]//p | //*[@class="artikelBody"]/ul',
                'author':'//*[@class="article-origins"]//* | //span[@class="author"]'
            },
        },
        'zeit':{
            'sourceTable': 'zeit_articles',
            'destinationTable': 'zeit_parsed',
            'xpath': {
                'headline': '//*[contains(@class, "box col-xs-12 c_title")]//h1',
                'subtext':'//*[contains(@class, "box col-xs-12 c_lead")]//p',
                'story':'//*[@class="article-body"]//p | //*[@class="artikelBody"]/ul | //*[@class="box col-xs-12 c_content"]//p',
                'author':'//*[contains(@class, "box col-xs-12 c_authorline")]'
            },
        },
        'scmp':{
            'sourceTable': 'south_china_morning_post_articles',
            'destinationTable': 'south_china_morning_post_parsed',
            'xpath': {
                'headline': '//h1[@class="vodl-region-article__title"] | //*[@class="article-header"]/h1',
                'subtext':'//div[@class="vodl-region-article__excerpt"] | //*[@class="wp-block-russmedia-nordstern-lead lead"]/h4',
                'story':'//*[@class="vodl-region-article__content-text"]//p',
            },
        },
    }
)

# retriving the articles
parser.gettingHTMLs()

# parsing provided elements per paper from articles
parser.parsing()

# dumping parsed elements into destination database
parser.dumping()

# dumping Log
parser.logging()

```

## Structure of mysql databases

```sql
use news_articles;
CREATE TABLE news_articles (
    id SERIAL,
    link VARCHAR(256),
    pageHTML TEXT,
    scrapeDate DATETIME,
);

use news_parsed;
CREATE TABLE new_york_times_parsed (
    id SERIAL,
    link VARCHAR(256);
    story TEXT;
    author TEXT;
    headline TEXT;
    subtext TEXT;
    scrapeDate DATETIME,
    parseDate DATETIME
);

-- same structure for tables of zeit and south_china_morning_post as for new_york_times just above

use news_parsed;
CREATE TABLE mainLogStats (
    id SERIAL,
    logStats JSON,
    finishTime DATETIME
);

```

## Example log

```bash
{
    "job": "newsArticleParser"
    "articles_parsed": 30,
    "articles_parsed/nyt": 8,
    "articles_parsed/zeit": 16,
    "db/dumped": 30,
    "db/dumped/nyt": 8,
    "db/dumped/zeit": 16,
    "elapsed_time": "0:07:04.601144",
    "finish_time": "2024-05-06 09:19:06.598180",
    "items": 110,
    "items/author": 24,
    "items/author/nyt": 5,
    "items/author/zeit": 16,
    "items/nyt": 29,
    "items/headline": 30,
    "items/headline/nyt": 8,
    "items/headline/zeit": 16,
    "items/zeit": 63,
    "items/story": 29,
    "items/story/nyt": 8,
    "items/story/zeit": 15,
    "items/subtext": 27,
    "items/subtext/nyt": 8,
    "none": 10,
    "none/author": 6,
    "none/author/nyt": 3,
    "none/zeit": 1,
    "none/story": 1,
    "none/story/zeit": 1,
    "none/subtext": 3,
    "start_time": "2024-05-06 09:12:01.997036"
}
```
