import json
from lxml import html
import pymysql
from dotenv import load_dotenv
import os
import datetime



class logStats():
    """Custom logging and dumping logs into database."""

    def __init__(self):
        self.logStats = {}


    def incLog(self, key, value=1):
        if key not in self.logStats:
            self.logStats[key] = value
        else:
            self.logStats[key] += value
        

    def setLog(self, key, value):
        self.logStats[key] = value
    

    def logging(self):
        self.setLog('finish_time', datetime.datetime.now())
        self.setLog('elapsed_time', self.logStats['finish_time'] - self.logStats['start_time'])
        self.stt = json.dumps(self.logStats, sort_keys=True, default=str)
        try:
            dbconnection = pymysql.connect(
                        host=os.environ.get(self.db['host']),
                        user=os.environ.get(self.db['user']),
                        password=os.environ.get(self.db['password']),
                        charset=os.environ.get(self.db['charset']),
                        cursorclass=pymysql.cursors.DictCursor,
                    )
            cursor = dbconnection.cursor()
            cursor.execute(f"INSERT INTO {os.environ.get(self.db['dbNameDestination'])}.{os.environ.get(self.db['dbTableLogging'])} (logStats, finishTime) VALUES (%s, %s)", [self.stt, self.logStats['finish_time']])
            dbconnection.commit() 
        except pymysql.Error as e:
            print(e)         
        finally:
            dbconnection.close()
            print(self.logStats)



class newsArticleParser(logStats):
    """Getting articles out of database, the using lxml to parse headline, subtext, story and author. Then dumping the results back into database."""

    def __init__(self, dbCredentials: dict, dbNamesTables: dict, papers: dict, envPath=".env"):
        logStats.__init__(self)
        self.setLog('job', newsArticleParser.__name__)
        self.setLog('start_time', datetime.datetime.now())
        self.db = dbCredentials | dbNamesTables
        self.papers = papers
        load_dotenv(envPath)
 

    def gettingHTMLs(self):
        self.results = []
        try:
            dbconnection = pymysql.connect(
                        host=os.environ.get(self.db['host']),
                        user=os.environ.get(self.db['user']),
                        password=os.environ.get(self.db['password']),
                        charset=os.environ.get(self.db['charset']),
                        cursorclass=pymysql.cursors.DictCursor,
                    )
            cursor = dbconnection.cursor()

            for key, value in self.papers.items():
                cursor = dbconnection.cursor()
                sqlQuery = f"""SELECT link, '{key}' as paper FROM {os.environ.get(self.db['dbNameSource'])}.{os.environ.get(value['sourceTable'])} 
                            WHERE link NOT IN (SELECT link FROM {os.environ.get(self.db['dbNameDestination'])}.{os.environ.get(value['destinationTable'])}) LIMIT 500;"""
                cursor.execute(sqlQuery)
                outputs = cursor.fetchall()

                for output in outputs:
                    sqlQuery = f"""SELECT pageHtml, scrapeDate FROM {os.environ.get(self.db['dbNameSource'])}.{os.environ.get(value['sourceTable'])} WHERE link = '{output['link']}';"""
                    cursor.execute(sqlQuery)
                    enhance = cursor.fetchall()
                    output = output | enhance[0]
                    self.results.append(output)

        except pymysql.Error as e:
            print(e)         
        finally:
            dbconnection.close()


    def parsing(self):
        for result in self.results:
            tree = html.fromstring(result['pageHtml'])
            for key, val in self.papers[result['paper']]['xpath'].items():
                content = ''
                for element in tree.xpath(val):
                    if element.text is not None: content += element.text_content().strip() + ' '
                if content != '':
                    result[f'{key}Parsed'] = content
            del result['pageHtml']


    def dumping(self):
        try:
            dbconnection = pymysql.connect(
                        host=os.environ.get(self.db['host']),
                        user=os.environ.get(self.db['user']),
                        password=os.environ.get(self.db['password']),
                        charset=os.environ.get(self.db['charset']),
                        cursorclass=pymysql.cursors.DictCursor,
                    )
            cursor = dbconnection.cursor()
            for result in self.results:
                cursor.execute(f'''INSERT INTO {os.environ.get(self.db["dbNameDestination"])}.{os.environ.get(self.papers[result["paper"]]["destinationTable"])} 
                                (link, story, author, headline, subtext, scrapeDate, parseDate)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW()) ''',
                                [result.get('link', 'NULL'), 
                                 result.get('storyParsed', 'NULL'), 
                                 result.get('authorParsed', 'NULL'), 
                                 result.get('headlineParsed', 'NULL'), 
                                 result.get('subtextParsed', 'NULL'), 
                                 result.get('scrapeDate', 'NULL')
                            ]
                           )
                dbconnection.commit()  
                self.incLog('db/dumped')
                self.incLog(f'db/dumped/{result["paper"]}')
                if any(key in result for key in ['headlineParsed', 'subtextParsed', 'storyParsed', 'authorParsed']):
                    self.incLog('articles_parsed')
                    self.incLog(f'articles_parsed/{result["paper"]}')
                    for key in ['headlineParsed', 'subtextParsed', 'storyParsed', 'authorParsed']:
                        if key in result.keys():
                            self.incLog('items')
                            self.incLog(f'items/{result["paper"]}')
                            self.incLog(f'items/{key[:-6]}')
                            self.incLog(f'items/{key[:-6]}/{result["paper"]}')
                        else:
                            self.incLog('none')
                            self.incLog(f'none/{result["paper"]}')
                            self.incLog(f'none/{key[:-6]}')
                            self.incLog(f'none/{key[:-6]}/{result["paper"]}')
                else:
                    self.incLog('articles_null_parsed')
                    self.incLog(f'articles_null_parsed/{result["paper"]}')
                    for key in ['headlineParsed', 'subtextParsed', 'storyParsed', 'authorParsed']:
                        self.incLog('none')
                        self.incLog(f'none/{result["paper"]}')
                        self.incLog(f'none/{key[:-6]}')
                        self.incLog(f'none/{key[:-6]}/{result["paper"]}')
        except Exception as e:
            self.setLog('error', e)
            self.setLog('last_items_before_error', json.dumps(result, sort_keys=True, default=str))
            self.transformingLogDump()
        finally:
            dbconnection.close()
