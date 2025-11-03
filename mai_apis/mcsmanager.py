import requests


class McsManager:
    ERROR_LIST = ["实例未处于关闭状态，无法再进行启动", "实例未处于运行中状态，无法进行停止."]
    def __init__(self, api_key):
        self.endpoint = "https://mc.aleafy.top:8000/api"
        self.api_key = api_key
        self.instanceId = "9d8e1b72ebf0497bb5cbafe726bdff8c"
        self.daemonId = "51f68d79f5f14e4aa3a52ac2b12f0c19"

    def get_daemons(self):
        url = self.endpoint + "/overview"
        res = requests.get(url, params={
            "apikey": self.api_key
        })
        data = res.json()
        return data['data']['remote'][0]["uuid"]

    def get_instances(self):
        url = self.endpoint + "/service/remote_service_instances"
        res = requests.get(url, params={
            "apikey": self.api_key
        })
        return res

    def start_instance(self):
        uuid = self.instanceId
        daemonId = self.daemonId
        url = self.endpoint + "/protected_instance/open"
        res = requests.get(url, params={
            "uuid": uuid,
            "daemonId": daemonId,
            "apikey": self.api_key
        })
        return res

    def execute_command(self, command):
        url = self.endpoint + "/protected_instance/command"
        res = requests.get(url, params={
            "uuid": self.instanceId,
            "daemonId": self.daemonId,
            "apikey": self.api_key,
            "command": command
        })
        return res

    def restart_instance(self):
        url = self.endpoint + "/protected_instance/restart"
        res = requests.get(url, params={
            "apikey": self.api_key,
            "uuid": self.instanceId,
            "daemonId": self.daemonId
        })
        return res