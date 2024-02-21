import numpy as np
import scrapy
import json
import re
import arrow
from fake_useragent import UserAgent
from scrapy.exceptions import CloseSpider
import pandas as pd
'''

'''
class MofcomspiderSpider(scrapy.Spider):
    name = 'mofcomspider'
    allowed_domains = ['cif.mofcom.gov.cn']
    start_urls = ['https://cif.mofcom.gov.cn/cif/resDataIndex/js/riduData.js']
    ua = UserAgent()

    def __init__(self, *args, **kwargs):
        super(MofcomspiderSpider, self).__init__(*args, **kwargs)
        self.stats = kwargs.get('stats')

    def parse(self, response):
        data = response.text
        FUData = self.parse_FData(data)
        for item in FUData:
            yield scrapy.Request(url=self.get_data_url(item['code']), callback=self.parse_SData,
                                 meta={'Fname': item['Fname']}, headers={'User-Agent': self.ua.random})

    def parse_FData(self, data):
        jsondata_fixed = re.sub(r'(\w+):', r'"\1":', data)
        jsondatan = str(jsondata_fixed).replace('\'', '\"').split('=')[1].strip().rstrip(';')
        jsondatann = re.sub(r',]', ']', str(re.sub(r'\s+', '', jsondatan))).replace(',}', '}')
        Json_Data = json.loads(jsondatann)
        result = Json_Data['categoryDatas']
        for category_name, category_list in result.items():
            for item in category_list:
                FData = {'Fname': category_name, 'code': item['id']}
                yield FData

    def get_data_url(self, cateId):
        date_y = arrow.now().shift(days=-1).format("YYYY-MM-DD")
        Surl = f"https://cif.mofcom.gov.cn/cif/getEnterpriseListForDate.fhtml?cateId={cateId}&searchDate={date_y}"
        return Surl

    def parse_SData(self, response):
        data = response.text
        Json_Data = json.loads(data)
        date = Json_Data['date']
        result2 = Json_Data['datas']
        DataList = []
        for key in result2:
            PRICE2 = key.get('PRICE2', None)
            COMMDITYNAME = key.get('COMMDITYNAME', None)
            NAME = key.get('NAME', None)
            Row = {
                'DATADATE': date,
                'NUMERICALVALUE': PRICE2,
                'DATATYPE': COMMDITYNAME,
                'VALUETYPE': NAME,
                'Fname': response.meta['Fname']
            }
            DataList.append(Row)
        cleaned_data = self.clean_data(DataList)
        # return cleaned_data
        yield from cleaned_data  #clean_data 函数生成了一个列表，而 yield from cleaned_data 则将该列表中的每个元素作为单独的数据项进行生成

    def clean_data(self,paredata):
        df = pd.DataFrame(paredata)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('max_colwidth', 10000)
        pd.set_option('display.width', 10000)
        def custom_mapping(column_values, mapping):
            return [mapping.get(value, value) for value in column_values]
        report_type_mapping = {
            'liangyou': '粮油',
            'roulei': '肉类',
            'qindan': '禽蛋',
            'shucai': '蔬菜'
        }
        df['PRICETYPE'] = custom_mapping(df['Fname'], report_type_mapping)
        df = df.drop(axis=1, columns=['Fname'])
        df = df.fillna('').replace("nan", '')
        df['NUMERICALVALUE'] = df['NUMERICALVALUE'].replace('',np.NaN)
        df = df.dropna(axis=0, subset=["NUMERICALVALUE"])
        df = df.astype(str)
        df = df.apply(lambda x: x.str.strip())
        df['PRODUCTNAME'] = '日度监测数据'
        df['DELIVERY'] = '当日价格'
        df['UNIT'] = '元/公斤'
        df['UPDATEFREQUENCY'] = '1'
        df['REGION'] = '全国'
        df['COUNTRY'] = '中国'
        df['WEB'] = 'https://cif.mofcom.gov.cn/cif/html/dataCenter/index.html?jgnfcprd'
        df['DATASOURCE'] = '中华人民共和国商务部'
        list1 = df.to_dict('records')
        return list1

    def closed(self, reason):
        self.logger.info('Spider closed: %s', reason)
        if self.stats:
            stats_info = self.stats.get_stats()
            self.logger.info(f"Total count: {stats_info['total_count']}")
            self.logger.info(f"Total duplicate count: {stats_info['total_duplicate_count']}")
        if reason != 'finished':
            raise CloseSpider(reason)

