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
    
    def transformingLogDump(self):
        self.setLog('finish_time', datetime.datetime.now())
        self.setLog('elapsed_time', self.logStats['finish_time'] - self.logStats['start_time'])
        self.logStats = {key:val for key, val in self.logStats.items() if val != 0}
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
            cursor.execute(f"INSERT INTO {os.environ.get(self.db['dbNameGpes'])}.{os.environ.get(self.db['dbTableLogging'])} (logStats, finishTime) VALUES (%s, %s)", [self.stt, self.logStats['finish_time']])
            # dbconnection.commit() 
        except pymysql.Error as e:
            print(e)         
        finally:
            dbconnection.close()
            print(self.logStats)



class newsArtileParser(logStats):
    """Getting articles out of database, the using spacy to parse geopolitical entities and then dumping the results back into database."""

    def __init__(self, dbCredentials: dict, dbNames: dict, papers: dict, envPath=".env"):
        logStats.__init__(self)
        self.setLog('job', newsArtileParser.__name__)
        self.setLog('start_time', datetime.datetime.now())
        self.db = dbCredentials | dbNames
        self.papers = papers
        load_dotenv(envPath)
 
    def getHTMLs(self):
        self.results = []
        try:
            dbconnection = pymysql.connect(
                        host=os.environ.get(self.db['host']),
                        user=os.environ.get(self.db['user']),
                        password=os.environ.get(self.db['password']),
                        charset=os.environ.get(self.db['charset']),
                        cursorclass=pymysql.cursors.DictCursor,
                    )
            for key, value in self.papers.items():
                cursor = dbconnection.cursor()
                sqlQuery = f"""SELECT pageHtml, link, scrapeDate, '{key}' as paper FROM {os.environ.get(self.db['dbNameSource'])}.{os.environ.get(value['sourceTable'])} 
                            WHERE link NOT IN (SELECT link FROM {os.environ.get(self.db['dbNameDestination'])}.{os.environ.get(value['destinationTable'])}) LIMIT 1000;"""
                cursor.execute(sqlQuery)
                outputs = cursor.fetchall()
                for output in outputs:
                    self.results.append(output)
        except pymysql.Error as e:
            print(e)         
        finally:
            dbconnection.close()

    def parsing(self):
        for result in self.results:
            tree = html.fromstring(result['pageHtml'])
            
            xpath = self.papers[result['paper']]['xpath'] 

            headline = ''
            for element in tree.xpath(xpath['headline']):
                if element.text is not None: headline += element.text_content().strip() + ' '     
            if headline != '': 
                result['headlineParsed'] = headline

            subtext = ''
            for element in tree.xpath(xpath['subtext']):
                if element.text is not None: subtext += element.text_content().strip() + ' '      
            if subtext != '': 
                result['subtextParsed'] = subtext

            story = ''
            for element in tree.xpath(xpath['story']):
                if element.text is not None: story += element.text_content().strip() + ' '   
            if story != '': 
                result['storyParsed'] = story

            author = ''
            for element in tree.xpath(xpath['story']):
                if element.text is not None: author += element.text_content().strip() + ' '   
            if author != '': 
                result['authorParsed'] = author

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
            for article in self.parsed_data:
                cursor.execute(f'''
                    INSERT INTO {os.environ.get(self.db["dbNameGpes"])}.{os.environ.get(self.db['dbTableGpes'])}
                    (link,
                    paper,
                    author, 
                    gpes,
                    scrapeDate,
                    parseDate) 
                    VALUES 
                    (%s, %s, %s, %s, %s, NOW())''', 
                [article['link'], article['paper'], article['author'], article['gpe'], article['scrapeDate']])
                # dbconnection.commit()  
        except Exception as e:
            self.setLog('error', e)
            self.setLog('last_items_before_error', json.dumps(article, sort_keys=True, default=str))
            self.transformingLogDump()
        finally:
            dbconnection.close()
