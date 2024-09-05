var express = require('express');
var router = express.Router();

// CommonJs
const { createOpenAPI, createWebsocket } = require('qq-guild-bot');

const testConfig = {
  appID: '102351684', // 申请机器人时获取到的机器人 BotAppID
  token: 'VobRxweOEu374lu0pL5oerxOUbWCqULG', // 申请机器人时获取到的机器人 BotToken
  intents: ['PUBLIC_GUILD_MESSAGES'], // 事件订阅,用于开启可接收的消息类型
  sandbox: true // 沙箱支持，可选，默认false. v2.7.0+
};

// 创建 client
const client = createOpenAPI(testConfig);

// 创建 websocket 连接
const ws = createWebsocket(testConfig);

/* GET users listing. */
router.get('/', function (req, res, next) {
  res.send('respond with a resource');
});

function helloWorld(req, res, next) {
  res.send("Hello World!");
}

router.get('/hello', helloWorld);
exports.helloWorld = helloWorld;

module.exports = router;