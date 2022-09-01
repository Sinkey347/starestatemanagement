import requests
import ujson
from apscheduler.schedulers.background import BackgroundScheduler
from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import StopConsumer


class ServiceData(WebsocketConsumer):
    scheduler = BackgroundScheduler()

    def send_service_data(self):
        # 保存服务器运行数据
        with open('server_data.txt', 'a', encoding='utf-8') as f:
            # 获取当前时间、cpu使用率、内存使用率
            time = requests.get('http://localhost:61208/api/3/now')[17:19]
            cpu = requests.get('http://localhost:61208/api/3/cpu/total')[10:14]
            mem = requests.get('http://localhost:61208/api/3/mem/percent')[12:16]
            # 写入一条数据
            if time and cpu and mem:
                f.write(f'时间:{time}\tCPU使用率:{cpu}\t内存使用率:{mem}\n')
                # 编写响应体
                data = {
                    'time': time,
                    'cpu': cpu,
                    'mem': mem
                }
                # 返回数据
                self.send(text_data=ujson.dumps(data))

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

    def websocket_disconnect(self, message):
        '''
        客户端自动断开连接时触发
        :param message:
        :return:
        '''
        raise StopConsumer()
