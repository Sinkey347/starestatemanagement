import json
import csv
import os
from utils.constant import *
from apscheduler.schedulers.background import BackgroundScheduler
from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import StopConsumer


class ServiceData(WebsocketConsumer):
    scheduler = BackgroundScheduler()

    def send_service_data(self):
        f = open(DATA_FILE_PATH, 'r')
        if len(f.readlines()):
            new_data = list(csv.reader(f))[-1]
            data = {
                'time': new_data[0][11:],
                'cpu': float(new_data[1]),
                'mem': float(new_data[67])
            }
            self.send(text_data=json.dumps(data))
        f.close()

    def websocket_connect(self, message):
        '''
        客户端向服务端发送连接请求时触发
        :param message:
        :return:
        '''

        # 接收请求，创建连接
        self.accept()
        # 创建定时任务，每10s执行一次
        self.scheduler.add_job(self.send_service_data, 'interval', seconds=10)
        # 开始定时任务
        self.scheduler.start()

    def websocket_receive(self, message):
        '''
        客户端向服务端发送信息时触发
        :param message:
        :return:
        '''
        # 如果接收到客户端的exit则说明要断开连接
        if message.get('text') == 'exit':
            self.close()
            #self.scheduler.shutdown()

    def websocket_disconnect(self, message):
        '''
        客户端自动断开连接时触发
        :param message:
        :return:
        '''
        raise StopConsumer()
