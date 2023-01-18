import os, pytz, re, time

import datetime as dt 
import pandas   as pd 

from selenium import webdriver

from selenium.webdriver.common.by      import By 
from selenium.webdriver.common.keys    import Keys
from selenium.webdriver.support.ui     import WebDriverWait      as wb 
from selenium.webdriver.support        import expected_conditions as ec
from selenium.webdriver.chrome.service import Service

class SharedUtilities:
    def __init__(self, driver_path: str, max_wait_time: int):    
        """
            기본 설정 용 method 

            Parameter 
                driver_path   : String 변수, chromedriver.exe 경로 + 파일명 입력 
                max_wait_time : int 변수, 화면 element 로딩 대기 시간 
        """
        self.driver_path    = driver_path
        self.max_wait_time = max_wait_time 
    
    def base_settings(self, timezone: str, output_path: str, url_lists: list[str]):
        """
            Youtube crawling 기본 설정 method, 채널별 적용할 설정이 달라 향후 분리할 예정

            Parameter
                timezone    : String 변수, 서버 / local 실행에 따라 dt.datetime.now()
                              결과 값이 한국시간이 아닌경우도 있어 'Asia/Seoul' 입력 필수
                output_path : String 변수, 저장 경로. 입력한 경로가 없으면 자동 생성되는 구조임 
                url_list    : list[String] 변수, 크롤링할 URL Link를 list에 저장하여 입력 
                
        """
        self.timezone    = timezone 
        self.output_path = output_path 
        self.url_lists   = url_lists

        if (os.path.exists(self.output_path) != True):
            os.makedirs(self.output_path)

        self.metadata = {
            "video_id"        : [], "video_title"         : [],
            "upload_date"     : [], "total_views"         : [],
            "total_comments"  : [], "total_likes"         : [],
            "extraction_date" : [], "duration_in_seconds" : []
        }

    def driver_settings(self, added_options: list[str] = None):
        """
            Selenium driver 기본 설정 method

            Parameters 
                added_options : list[String] 변수, chrome webdriver에 적용할 옵션을 list에 저장하여 입력.
                                기본 값이 None이므로 added_options 없이 실행가능
        """
        self.options = webdriver.ChromeOptions()
        self.service = Service(self.driver_path)

        options_list = [
            "window-size=1920x1080", 
            "disable-gpu",
            "start-maximized",
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"
        ]

        options_list = options_list + added_options if type(added_options) == list else options_list

        for i in options_list:
            self.options.add_argument(i)

        self.driver = webdriver.Chrome(options = self.options, service = self.service)
        
    def initiate_crawl(self):
        """
            initiate_crawl 실행함에 따라 crawling 프로세스가 실행됨 

            inner 함수                
                parse_url         : url부터 영상 ID 추출
                get_title         : 영상 title 추출 
                get_upload_date   : 영상 업로드 일시 추출 
                get_view_count    : 영상 조회수 추출 
                get_comment_count : 영상 댓글수 추출 
                get_likes_count   : 영상 좋아요수 추출 
        """
        def parse_url(link):
            video_id = link[link.index("watch?v="):].replace("watch?v=", "")
            self.metadata["video_id"].append(video_id)

        def get_title():
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.XPATH, "//*[@id='title']/h1/yt-formatted-string")))
            title_name = self.driver.find_element(By.XPATH, "//*[@id='title']/h1/yt-formatted-string").text
            self.metadata["video_title"].append(title_name)

        def get_upload_date():        
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.XPATH, "//*[@id='info']/span[3]")))
            date_string = ""
            date_list   = self.driver.find_element(By.XPATH, "//*[@id='info']/span[3]").text.replace(".", "").split(" ")

            for i in date_list:
                date_string += str(i).zfill(2) + "-"
            
            date_string = date_string[:-1]
            self.metadata["upload_date"].append(date_string)

        def get_view_count():
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.XPATH, "//*[@id='below']/ytd-watch-metadata")))
            view_count = self.driver.find_element(By.XPATH, "//*[@id='below']/ytd-watch-metadata").text.replace(",", "")
            view_count = view_count[view_count.index("조회수"):].replace("조회수", "")
            view_count = view_count[:view_count.index("회")]
            self.metadata["total_views"].append(int(view_count))

        def get_comment_count():
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.CLASS_NAME, "style-scope ytd-comments-header-renderer")))
            comment_count = self.driver.find_element(By.CLASS_NAME, "style-scope ytd-comments-header-renderer").text.replace(",", "")
            comment_count = int(re.search(r"[0-9]+", comment_count)[0])
            self.metadata["total_comments"].append(comment_count)

        def get_likes_count():
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.XPATH, "//*[@id='below']/ytd-watch-metadata")))
            element_text = self.driver.find_element(By.XPATH, "//*[@id='below']/ytd-watch-metadata").text
            element_text = element_text[element_text.index("구독\n"):].replace("구독\n", "")
            element_text = element_text[:element_text.index("\n공유")]
            self.metadata["total_likes"].append(element_text)

        """
            프로그램 로직: 
                url_list에 입력한 youtube url을 loop로 방문해서 parse_url ~ get_likes_count로 필요 정보 
                추출하여 전처리 후 self.metadata dictionary에 저장하는 구조임

                Step 01: Line 150 - 웹페이지 정보 추출 프로세스 시작 시간 저장
                Step 02: Line 151 - URL 방문 
                Step 03: Line 152 - 웹페이지 로딩 대기  
                Step 04: Line 153 - 웹페이지 밑으로 스콜링. 페이지를 밑으로 내려야 댓글수 정보를 추출할 수 있음 
                Step 05: Line 154 - 더보기 버튼 click. 더보기를 click 해야 업로드 시간 및 조회수 정보를 추출할 수 있음 
                Step 06: Line 155 - 영상 ID 추출 
                Step 07: Line 156 - 영상 이름 추출 
                Step 08: Line 157 - 영상 업로드 일시 추출 
                Step 09: Line 158 - 영상 조회수 추출 
                Step 10: Line 159 - 영상 댓글수 추출 
                Step 11: Line 160 - 영상 좋아요수 추출 
                Step 12: Line 161 - 데이터 추출 일시 저장 
                Step 13: Line 162 - 웹페이지 정보 추출 프로세스 종료 시간 저장 
                Step 14: Line 163 - 총 소요 시간 저장 
        """    
        for link in self.url_lists:
            start_time = time.time()
            self.driver.get(link)      
            wb(self.driver, self.max_wait_time).until(ec.presence_of_all_elements_located((By.XPATH, "//*[@id='title']/h1/yt-formatted-string")))
            self.driver.execute_script("window.scrollTo(0, 500)")
            self.driver.find_element(By.XPATH, "//*[@id='expand']").click()
            parse_url(link)
            get_title()
            get_upload_date()
            get_view_count()
            get_comment_count()
            get_likes_count()
            self.metadata["extraction_date"].append(str(dt.datetime.now(pytz.timezone(self.timezone)))[0:19])
            end_time = time.time()
            self.metadata["duration_in_seconds"].append(end_time - start_time)

        assert len(self.metadata["extraction_date"]) == len(self.url_lists)

    @staticmethod 
    def feb_days(year_value: int):
        return_value = 28

        if ((year_value % 4 == 0) & (year_value % 100 != 0) | (year_value % 400 == 0)):
            return_value = 29

        return return_value                

if __name__ == "__main__":
    su = SharedUtilities("./config/chromedriver.exe", 600)
    su.base_settings("Asia/Seoul", "./data/youtube", ["https://www.youtube.com/watch?v=yWL5utI75FA", "https://www.youtube.com/watch?v=u2tkyXrh7RU", "https://www.youtube.com/watch?v=rWJ2h52HnU4", "https://www.youtube.com/watch?v=nq4tT68UoCg", "https://www.youtube.com/watch?v=Rg0JtJMBb7Y", "https://www.youtube.com/watch?v=fJ_nXc6D1wE", "https://www.youtube.com/watch?v=-YpLhlIgTZ8", "https://www.youtube.com/watch?v=Yqu_MC5Lhng"])
    su.driver_settings()
    su.initiate_crawl()