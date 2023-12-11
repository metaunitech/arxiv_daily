import time
from enum import Enum
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz


class TIMEINTERVAL(Enum):
    CURRENT = -2
    NONE = -1
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    QUARTERLY = 3
    YEARLY = 4
    DUALDAYS = 5

    @property
    def startTS(self):
        return self._startTS

    @property
    def endTS(self):
        return self._endTS

    @property
    def update(self):
        current_datetime = datetime.now()
        timezone = pytz.timezone('Asia/Shanghai')  # 用你所在的时区替换

        if self == TIMEINTERVAL.CURRENT:
            start_time = end_time = timezone.localize(current_datetime)
        elif self == TIMEINTERVAL.DAILY:
            start_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        elif self == TIMEINTERVAL.WEEKLY:
            week_start = current_datetime - timedelta(days=7)
            start_time = timezone.localize(datetime(week_start.year, week_start.month, week_start.day, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        elif self == TIMEINTERVAL.MONTHLY:
            start_time = timezone.localize(datetime(current_datetime.year, current_datetime.month, 1, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        elif self == TIMEINTERVAL.QUARTERLY:
            quarter_start_month = ((current_datetime.month - 1) // 3) * 3 + 1
            start_time = timezone.localize(datetime(current_datetime.year, quarter_start_month, 1, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        elif self == TIMEINTERVAL.YEARLY:
            start_time = timezone.localize(datetime(current_datetime.year, 1, 1, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        elif self == TIMEINTERVAL.DUALDAYS:
            two_days_ago = current_datetime - timedelta(days=2)
            start_time = timezone.localize(datetime(two_days_ago.year, two_days_ago.month, two_days_ago.day, 0, 0, 0))
            end_time = timezone.localize(
                datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
        else:
            raise ValueError("Invalid TIMEINTERVAL")

        self._startTS = start_time
        self._endTS = end_time
        return start_time, end_time


if __name__ == "__main__":
    # 示例用法
    for i in range(5):
        duration = TIMEINTERVAL["CURRENT"]
        start_time, end_time = duration.update
        print(f"{duration.name} start time: {start_time}")
        print(f"{duration.name} end time: {end_time}")
        time.sleep(2)
