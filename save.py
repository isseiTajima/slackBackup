import urllib
import urllib.request
import urllib.error
import json
import sys
import jpholiday
import datetime
import time
import codecs

'''
Slackで保存しているURL付きの履歴をJSON形式でファイルに書き出す．
'''

# 定数
SLACK_CHANNEL = 'XXXXXXXXX'
TOKEN = '12345678'
CHANNEL1 = {'channelId': 'AAAAAAAA',
                    'channelName': 'test'}

# 新規チャンネルは定数をlistに追加する
channelList = []
channelList.extend([CHANNEL1)

# 直近の営業日を取得
def getEigyouDate(beforeDate):
    # 曜日(0~6,月~日)
    weekday = beforeDate.weekday()
    saveDate = beforeDate 
    # 休日判定
    if weekday == 6:
        # 前日が日曜なら金曜日の日付を設定
        saveDate = datetime.date.today() - datetime.timedelta(3)
        # 祝日判定
        if jpholiday.is_holiday(beforeDate):
            saveDate = datetime.date.today() - datetime.timedelta(4) 
        # 祝日判定
        if jpholiday.is_holiday(saveDate):
            saveDate = datetime.date.today() - datetime.timedelta(5) 
        # 祝日判定（5連休対応、これ以上は対応しない）
        if jpholiday.is_holiday(saveDate):
            saveDate = datetime.date.today() - datetime.timedelta(6) 
    # 祝日判定
    if jpholiday.is_holiday(beforeDate):
        saveDate = datetime.date.today() - datetime.timedelta(2)

    return saveDate


# メンバー一覧の取得
def getUser():

    params = {
        'token': TOKEN,
        'limit': 200
    }

    req = urllib.request.Request("https://slack.com/api/users.list")
    hist_params = urllib.parse.urlencode(params).encode('ascii')
    req.data = hist_params

    res = urllib.request.urlopen(req)

    body = res.read()
    decoded = json.loads(body)
    #必要なデータ(本文と投稿時間)のみ抽出
    results = {}
    for m in decoded['members']:

        d = {}
        d["name"] = m["name"]
        if 'real_name' in m:
            d["realName"] = m["real_name"]
        else:
            d["realName"] =''
        results[m["id"]] = d
    return results

# チャンネル履歴の取得
def getMessage(channel, count, users,fromData):

    # manyRequest対策でsleep追加
    print("待機中")
    time.sleep(20)

    #最高1000件ずつしか取得できない
    print(count)
    hist_params = {
        'channel': channel['channelId'],
        'token': TOKEN,
        'count': count
    }
    
    # apiから取得
    print(channel['channelName'])
    req = urllib.request.Request("https://slack.com/api/conversations.history")
    hist_params = urllib.parse.urlencode(hist_params).encode('ascii')
    req.data = hist_params

    res = urllib.request.urlopen(req)

    body = res.read()
    decoded = json.loads(body)
    #必要なデータ(本文と投稿時間)のみ抽出
    results = []

    # メインスレッド分繰り返し
    for m in reversed(decoded['messages']):
        d = {}
        d["text"] = m["text"]
        publishDatetime = datetime.datetime.fromtimestamp(float(m["ts"]))
        d["datetime"] = publishDatetime.strftime('%Y/%m/%d %H:%M:%S')
        user = ''
        if 'user' in m:
            user = m["user"]
            d["user"] = users[user]['realName']
        else:
            d["user"] = '名無し'
        # メンバー名の置き換え
        replaceText = d["text"]
        for user in users.keys() :
            if user in d["text"]:
                replaceText = replaceText.replace(
                    user, users[user]['realName'])
                d["text"] = replaceText


        # tsをキーにスレッド群を取得
        replieReq = urllib.request.Request("https://slack.com/api/conversations.replies")
        replie_params = {
            'channel': channel['channelId'],
            'token': TOKEN,
            'ts' : m["ts"]
        }
        replie_params = urllib.parse.urlencode(replie_params).encode('ascii')
        replieReq.data = replie_params
        replieRes = urllib.request.urlopen(replieReq)
        replieBody = replieRes.read()
        replieDecoded = json.loads(replieBody)

        # スレッド数分繰り返し
        for replieMs in reversed(replieDecoded['messages']):
            # manyRequest対策でsleep追加
            time.sleep(0.1)
            replieData = {}
            replieData["text"] = replieMs["text"]
            publishMsDatetime = datetime.datetime.fromtimestamp(float(replieMs["ts"]))
            replieData["datetime"] = publishMsDatetime.strftime('%Y/%m/%d %H:%M:%S')
            user = ''

            if 'user' in replieMs:
                user = replieMs["user"]
                replieData["user"] = users[user]['realName']
            else:
                replieData["user"] = '名無し'
            # メンバー名の置き換え
            replaceMsText = replieData["text"]
            for user in users.keys() :
                if user in replieData["text"]:
                    replaceMsText = replaceMsText.replace(
                        user, users[user]['realName'])
                    replieData["text"] = replaceMsText

            # 内容がもし同じだったら追記しない
            if replieData["text"] != d["text"]:
                # 本日だったら追記する
                if publishMsDatetime.date() == saveDate:
                    fromData.insert(0,replieData)
        # Ms後に追加する
        if publishDatetime.date() == saveDate:
            fromData.insert(0,d)

    #結果をファイルに保存
    f = codecs.open(
        '../files/' + channel['channelName'] + '.json', 'w', 'utf8')
    json.dump(fromData, f, ensure_ascii=False, indent=2)
    print(results)

    return results

# 元ファイルの読み込み


def getJson(channel):
    f = open("../files/" + channel['channelName'] +
             ".json", 'r', encoding="utf8")

    # JSON形式で読み込む
    json_data = json.load(f)

    return json_data

# main
users = getUser()
# 保存する日付
beforeDate = datetime.date.today() - datetime.timedelta(1)

saveDate = getEigyouDate(beforeDate)

print(saveDate)

for channel in channelList:
    data = getJson(channel)
    b = getMessage(channel, 100, users, data)