
import datetime



class test():
    
    def __init__(self):
        ret = {
            'today' : datetime.datetime(2022,3,11, 1,0,0), # 오늘
            # 'today': NOW,
            'checkDay' : 10, # 검침일
            'monthDays': 0, # 월일수
        }
        self._ret = ret
        self.calc_lengthDays()
    
    # 월별 동계, 하계 일수 구하기
    def calc_lengthUseDays(self) :
        checkDay = self._ret['checkDay']
        today = int(self._ret['today'].strftime('%m%d'))
        etc = 0
        winter = 0
        summer = 0
        # 하계(7~8월), 사용 일수 계산
        if (today > checkDay + 600) and (today <= checkDay + 900) :
            print('# 하계(7~8월), 사용 일수 계산')
            season = 'summer'
            if checkDay == 0: # 검침일이 말일일때
                print('  검침일이 말일일때')
                lastday = self.last_day_of_month(self._ret['today'])
                if lastday.month in [6,9] : # 6,9월일때
                    season = 'etc'
                    etc = lastday.day
                else : # 7,8월일때
                    summer = lastday.day
            elif today <= checkDay + 700 : # 검침일이 7월일때 
                print('  검침일이 7월일때 ')
                etc = 30 - checkDay
                summer = checkDay
            elif today <= checkDay + 800 : # 검침일이 8월일때 
                print('  검침일이 8월일때 ') 
                etc = 0
                summer = 31
            else : # 검침일이 9월일때 
                print('  검침일이 9월일때 ')
                etc = checkDay
                summer = 31 - checkDay
        # 동계(12~2월), 사용 일수 계산
        elif (today > checkDay + 1100) or (today <= checkDay + 300) :
            print('# 동계(12~2월), 사용 일수 계산')
            season = 'winter'
            if checkDay == 0: # 검침일이 말일일때
                print('  검침일이 말일일때')
                lastday = self.last_day_of_month(self._ret['today'])
                if lastday.month in [3,11] : # 3,11월일때
                    season = 'etc'
                    etc = lastday.day
                else : # 7,8월일때
                    winter = lastday.day
            elif today > checkDay + 1100 and today <= checkDay + 1200 : # 검침월이 11월일때 
                print('# 검침월이 11월일때')
                etc = 30 - checkDay
                winter = checkDay
            elif today > checkDay + 200 and today <= checkDay + 300 : # 검침월이 2월일때 
                # 210 > 28 + 100 and 210 <= 28 + 300
                print('# 검침일이 2월일때')
                lastday = self.last_day_of_month(self._ret['today'].replace(month=2,day=1))
                etc = checkDay
                winter = lastday.day - checkDay
            else : # 검침일이 12,1월일때
                print(f'{today} # 검침일이 12,1월일때 ')
                etc = 0
                winter = 31
        else : # 기타
            print('# 기타 시즌')
            season = 'etc'
            etc = self._ret['monthDays']

        print(f"시즌:{season}, 기타:{etc}, 동계:{winter}, 하계:{summer} ")
        print('============================================')




    # 달의 말일
    # last_day_of_month(datetime.date(2021, 12, 1))
    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
        return next_month - datetime.timedelta(days=next_month.day)


    # 월 사용일 구하기
    def calc_lengthDays(self) :
        today = self._ret['today']
        checkDay = self._ret['checkDay']
        if today.day > checkDay : # 오늘이 검침일보다 크면
            lastday = self.last_day_of_month(today) # 달의 마지막일이 전체 길이
            monthDays = lastday.day
        else : # 오늘이 검칠일과 같거나 작으면
            lastday = today - datetime.timedelta(days=today.day) # 전달의 마지막일이 전체 길이
            monthDays = lastday.day
        self._ret['monthDays'] = monthDays
        print(f"월일수:{monthDays}")
        # _LOGGER.debug(f'월일수: {monthDays}')

K2W = test()
K2W.calc_lengthUseDays()