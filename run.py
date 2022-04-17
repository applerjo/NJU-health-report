import random

from njupass import NjuUiaAuth
from dotenv import load_dotenv
import os
import json
import time
import logging
import datetime
from pytz import timezone

URL_JKDK_LIST = 'http://ehallapp.nju.edu.cn/xgfw/sys/yqfxmrjkdkappnju/apply/getApplyInfoList.do'
URL_JKDK_APPLY = 'http://ehallapp.nju.edu.cn/xgfw/sys/yqfxmrjkdkappnju/apply/saveApplyInfos.do'

auth = NjuUiaAuth()


def notify(msg):
    with open('email.txt', 'a+') as f:
        f.write(msg + '\n')
    return


def get_normalization_date(username):
    today = datetime.datetime.now(timezone('Asia/Shanghai'))
    date = datetime.datetime(2022, 4, 4 + (int(username[-1]) + 4) % 5, 8, 30)
    while (today.replace(tzinfo=None) - date).days >= 5:
        date += datetime.timedelta(days=5)
    return date


def get_zjhs_time(method='YESTERDAY', username=None, last_time=None):
    today = datetime.datetime.now(timezone('Asia/Shanghai'))
    yesterday = today + datetime.timedelta(-1)
    if method == 'YESTERDAY':
        return yesterday.strftime("%Y-%m-%d %-H")
    elif method == 'LAST':
        return last_time
    elif method == 'NORMALIZATION':
        return get_normalization_date(username).strftime("%Y-%m-%d %-H")
    elif method == 'NORMALIZATION&LAST':
        if get_normalization_date(username) < datetime.datetime(
                int(last_time[:4]),
                int(last_time[5:7]),
                int(last_time[8:10]),
                int(last_time[11:13])
        ):
            date = last_time
        else:
            date = get_normalization_date(username).strftime("%Y-%m-%d %-H")
        return date


if __name__ == "__main__":
    time.sleep(random.random()*1000)  # 随机等待0-16.6667min
    load_dotenv(verbose=True)
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    log = logging.getLogger()

    username = os.getenv('NJU_USERNAME')
    password = os.getenv('NJU_PASSWORD')
    location_info_from = os.getenv('LOCATION_INFO_FROM')
    method = os.getenv('COVID_TEST_METHOD')
    curr_location = ''
    zjhs_time = ''

    if location_info_from == '':
        location_info_from = 'LAST'
    if method == '':
        method = 'YESTERDAY'

    if username == '' or password == '' or (location_info_from == 'CONFIG' and curr_location == ''):
        log.error('账户、密码或地理位置信息为空！请检查是否正确地设置了 SECRET 项（GitHub Action）。')
        notify('账户、密码或地理位置信息为空！请检查是否正确地设置了 SECRET 项（GitHub Action）。')
        os._exit(1)

    log.info('尝试登录...')

    if auth.needCaptcha(username):
        log.info("统一认证平台需要输入验证码才能继续，尝试识别验证码...")

    ok = auth.tryLogin(username, password)
    if not ok:
        log.error("登录失败。可能是用户名或密码错误，或是验证码无法识别。")
        notify("登录失败。可能是用户名或密码错误，或是验证码无法识别。")
        os._exit(1)

    log.info('登录成功！')

    for count in range(10):
        log.info('尝试获取打卡列表信息...')
        r = auth.session.get(URL_JKDK_LIST)
        if r.status_code != 200:
            log.error('获取失败，一分钟后再次尝试...')
            time.sleep(60)
            continue
        dk_info = json.loads(r.text)['data']

        # 根据配置填写地址和核酸检测信息
        if location_info_from == 'CONFIG':
            curr_location = os.getenv('CURR_LOCATION')
        else:
            curr_location = dk_info[1]["CURR_LOCATION"]
        zjhs_time = get_zjhs_time(method, username, dk_info[1]['ZJHSJCSJ'])

        if dk_info[0]['TBZT'] == "0":
            wid = dk_info[0]['WID']
            data = "?WID={}&IS_TWZC=1&CURR_LOCATION={}&ZJHSJCSJ={}&JRSKMYS=1&IS_HAS_JKQK=1&JZRJRSKMYS=1&SFZJLN=0".format(
                wid, curr_location, zjhs_time)
            url = URL_JKDK_APPLY + data
            log.info('正在打卡')
            auth.session.get(url)
            time.sleep(1)
        else:
            log.info("打卡成功！")
            notify("打卡成功！")
            os._exit(0)

    log.error("打卡失败，请尝试手动打卡")
    notify("打卡失败，请手动打卡！")
    os._exit(-1)
