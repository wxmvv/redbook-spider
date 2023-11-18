# selenium 4
from gettext import find
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time
from scrapy import Selector
import json
import re
import os

from tortoise import fields

# TODO 错误处理
# TODO 下载图片视频

class RedbookSpider:
    # 基础方法
    def __init__(self, dev=False, headless=False) -> None:
        self.options = webdriver.ChromeOptions()
        if dev:
            self.options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        if headless:
            self.options.add_argument("--headless")
        self.driver = webdriver.Chrome(
            options=self.options, service=ChromeService(ChromeDriverManager().install())
        )
        self.cookies = None

    def get_local_cookies(self):
        with open("./cookies.txt", "r+", encoding="utf-8") as f:
            r = f.read()
        self.cookies = eval(r)
        for a in self.cookies:
            self.driver.add_cookie(a)
        return self.cookies

    def close(self):
        self.driver.quit()

    def read_url_fromcsv(self, filename: str):
        print("Current working directory:", os.getcwd())
        # 判断是绝对地址还是相对地址
        if filename.find("/") != 0:
            filename = os.getcwd() + "/" + filename
        df = pd.read_csv(filename)
        return df["url"].values.tolist()

    def get_userPostedFeeds(self, profileUrl):
        # 初始化
        d = self.driver
        d.get(profileUrl)
        exploreList = []
        bannerheight = 400
        lastscollheight = 0
        scollheight = 0
        exploreListcsv = []
        # 开始循环滚动&读取列表，直到滚动到底部
        while 1 == 1:
            s = Selector(text=d.page_source)
            list1 = s.css("#userPostedFeeds section").extract()
            avatar = s.css(".user-name::text").extract_first()
            for a in list1:
                sa = Selector(text=a)
                title = sa.css(".title span::text").extract_first()
                href = sa.css("a[href^='/explore/']::attr(href)").extract_first()
                url = "https://www.xiaohongshu.com" + href
                imgurl = sa.css(".cover.ld.mask::attr(style)").re_first(
                    r'url\("([^"]+)"\)'
                )
                like_count = sa.css(".like-wrapper .count::text").extract_first()
                # print("title:{} url:{} imgurl:{} like_count:{}".format(title,url,imgurl,like_count))
                # 去重
                if url in exploreList:
                    # print("重复")
                    continue
                else:
                    exploreListcsv.append([title, href, url, imgurl, like_count])
                    exploreList.append(url)
            listheight = int(
                s.css("#userPostedFeeds")
                .attrib["style"]
                .split("height:")[1]
                .split("px")[0]
            )
            scollheight = listheight + bannerheight
            d.execute_script("window.scrollTo(0,{})".format(scollheight))
            if lastscollheight == scollheight:
                print("获取列表结束")
                explorecsv = pd.DataFrame(
                    exploreListcsv,
                    columns=["title", "href", "url", "imgurl", "like_count"],
                ).to_csv("{}/redbook/{}-postlist.csv".format(os.getcwd(), avatar))
                print("存入csv成功 文件名：./redbook/{}-postlist.csv".format(avatar))
                return exploreList
            else:
                print("获取列表中 {} {}".format(lastscollheight, scollheight))
                lastscollheight = scollheight
                time.sleep(4)
        return exploreList

    def get_detail_fromlist(self, urllist: list[str]):
        exploreDetailList = []
        count = 0
        for a in urllist:
            count += 1
            e = self.get_detail(url=a, to_csv=False)
            exploreDetailList.append(e)
            print("获取详情中 {} {}".format(count, a))
            if count % 20 == 0:
                time.sleep(10)
            else:
                time.sleep(3)
        avatar = exploreDetailList[0][0]
        pd.DataFrame(
            exploreDetailList,
            columns=["avatar", "url", "title", "desc", "tag", "imgurls", "videourl"],
        ).to_csv("{}/redbook/{}-postlist-detail.csv".format(os.getcwd(), avatar))
        return exploreDetailList

    def get_detail(self, url: str, to_csv=True):
        d = self.driver
        d.get(url=url)
        s = Selector(text=d.page_source)
        avatar = s.css(".username::text").extract_first()
        title = s.css("#detail-title::text").extract_first()
        desc = s.css("#detail-desc>span::text").extract_first()
        tag = s.css("#hash-tag::text").extract()  # list
        imgurls = s.css(".swiper-wrapper .swiper-slide::attr(style)").re(
            r".*?background-image:\s*url\((.*?)\)"
        )
        videourl = s.css(".player-container>div>video::attr(src)").extract_first()
        if to_csv:
            pd.DataFrame(
                [[avatar, url, title, desc, tag, imgurls, videourl]],
                columns=[
                    "avatar",
                    "url",
                    "title",
                    "desc",
                    "tag",
                    "imgurls",
                    "videourl",
                ],
            ).to_csv(
                "{}/redbook/{}-{}-post-detail.csv".format(os.getcwd(), avatar, title)
            )
        return [avatar, title, desc, tag, imgurls]

    def run(self, url: str, local_cookies=False):
        if local_cookies:
            self.get_local_cookies()
        if url.find("https") >= 0 & url.find("profile") >= 0:
            list = self.get_userPostedFeeds(url)
            time.sleep(3)
        elif url.find("https:") >= 0 & url.find("explore") >= 0:
            self.get_detail(url)
            time.sleep(3)
        elif url.find("csv") >= 0 & url.find("postlist") >= 0:
            list = self.read_url_fromcsv(url)
            self.get_detail_fromlist(list)
            time.sleep(3)
        else:
            print("url error")
            time.sleep(3)


if __name__ == "__main__":
    print(
        """
        开始前请先使用命令 `sh redbook/start_chrome.sh` 启动chrome
        
        1.输入个人主页url 获取所有笔记的链接，并保存csv 
            (https://www.xiaohongshu.com/user/profile/)
        2.输入笔记url 获取笔记的内容，并保存csv 
            (https://www.xiaohongshu.com/explore/)
        3.输入个人主页csv文件名，获取所有笔记的内容，并保存csv 
            (redbook/xxoo.csv)
        """
    )
    _url = input("请输入url或者文件名:")
    spider = RedbookSpider(dev=True)
    print(_url)
    spider.run(_url)
    time.sleep(3)
    spider.close()
    print("程序结束,请关闭浏览器")
