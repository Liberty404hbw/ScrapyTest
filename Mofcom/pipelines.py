# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import pymongo
import hashlib
import json
import arrow

class MongoDBPipeline:
    def __init__(self):
        self.total_count = 0
        self.total_duplicate_count = 0
    def open_spider(self, spider):
        self.conn =  pymongo.MongoClient('mongodb://liberty:liberty8964@127.0.0.1:27017/?connectTimeoutMS=30000&socketTimeoutMS=30000')
        self.db = self.conn['carte']
        self.coll = self.db['MACRO_DATA']

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        md5 = hashlib.md5(json.dumps(item).encode("utf-8")).hexdigest()
        query = {"MD5": md5}
        update_data = {
            "$set": {
                "MD5": md5,
                "MARK": "0",
                "REQUEST_TIME": arrow.get(arrow.now().shift(years=0).format("YYYY-MM-DD HH:mm:ss.SSS")).datetime,
                "CONTENT": item,
                "DATASOURCE": "中华人民共和国商务部日度监测数据"
            }
        }
        # 存储到 MongoDB 中
        result = self.coll.update_many(query, update_data, upsert=True)
        if result.upserted_id is not None:
            self.total_count += 1
        else:
            self.total_duplicate_count += 1

        return item

    def get_stats(self):
        return {
            'total_count': self.total_count,
            'total_duplicate_count': self.total_duplicate_count
        }




