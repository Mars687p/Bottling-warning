import flet as ft

from datetime import date, time, datetime
from decimal import Decimal

from app.logs import logger
from typing import TYPE_CHECKING, Optional, Dict
if TYPE_CHECKING:
    from app.database import asyncpg


class ReportLinePerDate:
    def __init__(self, line_id: int, line_name: str, date_day: date, 
                 end_time: time, consider_saturday: bool) -> None:
        self.line_id: int = line_id
        self.line_name: str = line_name
        self.date: date = date_day
        self.end_work_time: time = end_time
        self.consider_saturday = consider_saturday
        self.total_volume: Decimal = Decimal(0)
        self.volume_work: Decimal = Decimal(0)
        self.volume_overtime: Decimal = Decimal(0)

        self.total_bottles: int = 0
        self.bottles_work: int = 0
        self.bottles_overtime: int = 0
        self.history: list = []
        self.interv_data: Optional[asyncpg.Record] = None


    async def calculate_data(self):
        self.total_volume = sum([i['alko_volume'] for i in self.history])
        self.total_bottles = sum([i['bottles_count'] for i in self.history])
        
        # Если первый запуск после конца раб. дня, тогда пишем только в сверхурочное время
        if self.history[0]['beg_time'].time() > self.end_work_time:
            self.volume_overtime = self.total_volume
            self.bottles_overtime = self.total_bottles
            return
        
        # Если суббота - выходной, тогда пишем только в сверхурочно
        if self.consider_saturday:
            if self.date.isoweekday() == 6:
                self.volume_overtime = self.total_volume
                self.bottles_overtime = self.total_bottles
                return

        if self.interv_data != None:
            if self.interv_data['create_time'].hour > self.end_work_time.hour:
                for row in self.history:
                    if (row['start_time'].time() < self.end_work_time 
                            and row['end_time'].time() > self.end_work_time):
                        logger.warning(f'Нет промежуточных данных за {self.date} - {self.line_name}')
                        return

                    if row['end_time'].time() < self.end_work_time:
                        self.volume_work += row['alko_volume']
                    else:
                        self.volume_overtime += row['alko_volume']
            self.volume_overtime = ((self.history[-1]['over_alko_volume'] + self.history[-1]['alko_volume'])
                                                - self.interv_data['over_alko_volume'])
            self.volume_work = self.total_volume - self.volume_overtime
            self.bottles_overtime = ((self.history[-1]['over_bottles_counts'] + self.history[-1]['bottles_count'])
                                                - self.interv_data['over_bottles_counts'])
            self.bottles_work = self.total_bottles - self.bottles_overtime
        else:
            self.volume_work = self.total_volume
            self.bottles_work = self.total_bottles
            


class TimePeriod:
    def __init__(self, page: ft.Page, period_id: int) -> None:
        self.page = page
        self.id = period_id
        self.start_time: Optional[time] = None
        self.end_time: Optional[time]= None
        self.start_date: Optional[date] = None
        self.end_date: Optional[date] = None

                            # date, dict[line_id, ReportLinePerDate]
        self.data_per_dates: Dict[date, Dict[int, ReportLinePerDate]] = {}
        self.calculate_err: list[str] = []


    async def get_gui_row(self, func_del_work_time): 
        txt_work_time = ft.Text('Рабочее время:', text_align=ft.TextAlign.CENTER, size=20, 
                                     weight=ft.FontWeight.BOLD)
        
        txt_date = ft.Text('В период:', text_align=ft.TextAlign.CENTER, size=20, 
                                     weight=ft.FontWeight.BOLD)
   
        but_start_time, but_end_time = await self.get_time_picker()
        but_start_date, but_end_date = await self.get_date_picker()

        but_del_period = ft.IconButton(icon=ft.icons.DELETE, on_click=func_del_work_time,
                                        data=self.id)
        self.row_work_time = ft.Row([txt_work_time,
                                    but_start_time, but_end_time, 
                                txt_date,
                                    but_start_date, but_end_date,
                                but_del_period
                                ],
                        data=self)
        return self.row_work_time

    async def get_time_picker(self):
        async def change_start_time(e: ft.ControlEvent):
            but_start_time.text = start_time.value
            self.start_time = start_time.value
            self.page.update()
        
        async def change_end_time(e: ft.ControlEvent):
            but_end_time.text = end_time.value
            self.end_time = end_time.value
            self.page.update()

        start_time = ft.TimePicker(value=time(8, 0), on_change=change_start_time)
        end_time = ft.TimePicker(value=time(17, 0), on_change=change_end_time)
        
        self.start_time = start_time.value
        self.end_time = end_time.value

        self.page.overlay.append(start_time)
        self.page.overlay.append(end_time)
        but_start_time = ft.ElevatedButton(text=start_time.value, 
                                           data=start_time.value,
                                           on_click=lambda _: start_time.pick_time())
        but_end_time = ft.ElevatedButton(text=end_time.value, 
                                         data=end_time.value,
                                         on_click=lambda _: end_time.pick_time())
        
        return but_start_time, but_end_time
    
    async def get_date_picker(self):
        async def change_start_date(e):
            but_start_date.text = start_date.value.date()
            self.start_date = start_date.value
            self.page.update()

        async def change_end_date(e):
            date_on = datetime(end_date.value.year, end_date.value.month,
                               end_date.value.day, 23, 59, 59)
            but_end_date.text = end_date.value.date()
            self.end_date = date_on
            self.page.update()

        _now = date.today()
        date_now = datetime(_now.year, _now.month, _now.day, 23, 59, 59)
        start_date = ft.DatePicker(value=date(date_now.year, date_now.month, 1), on_change=change_start_date
                                   )
        end_date = ft.DatePicker(value=date_now, on_change=change_end_date
                                 )
        
        self.start_date = start_date.value.date()
        self.end_date = datetime(_now.year, _now.month, _now.day+1)

        self.page.overlay.append(start_date)
        self.page.overlay.append(end_date)
        but_start_date = ft.ElevatedButton(text=start_date.value.date(), 
                                           on_click=lambda _: start_date.pick_date())
        but_end_date = ft.ElevatedButton(text=end_date.value.date(), 
                                         on_click=lambda _: end_date.pick_date())
        
        return but_start_date, but_end_date