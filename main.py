import os
import sqlite3

# 1. КОНФИГУРАЦИЯ ГРАФИЧЕСКОГО ДВИЖКА (Для Windows)
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineListItem
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivy.uix.popup import Popup  
from kivy.clock import Clock      

# Автоматический расчет абсолютного пути к папке проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "mental_health.db")

# 2. ПОЛНАЯ РАЗМЕТКА ИНТЕРФЕЙСА (Интеграция списков, кнопок и ID)
KV_INTERFACE = '''
ScreenManager:
    id: main_manager
    MDScreen:
        MDBoxLayout:
            orientation: 'vertical'
            md_bg_color: [0.95, 0.95, 0.95, 1]

            MDTopAppBar:
                title: "Ментальный Баланс"
                elevation: 4

            MDBottomNavigation:
                
                # Вкладка 1: Каталог медитаций с плеером
                MDBottomNavigationItem:
                    name: 'screen_home'
                    text: 'Медитации'
                    icon: 'share-variant'
                    
                    HomeScreen:
                        MDBoxLayout:
                            orientation: 'vertical'
                            padding: "16dp"
                            spacing: "10dp"
                            
                            MDLabel:
                                text: "Выберите практику для запуска:"
                                font_style: "H6"
                                size_hint_y: None
                                height: "50dp"

                            MDScrollView:
                                MDList:
                                    id: meditations_list

                # Вкладка 2: Дневник контроля настроения (1-5)
                MDBottomNavigationItem:
                    name: 'screen_tracker'
                    text: 'Трекер'
                    icon: 'heart'
                    
                    TrackerScreen:
                        MDBoxLayout:
                            orientation: 'vertical'
                            padding: "24dp"
                            spacing: "15dp"
                            
                            MDLabel:
                                text: "Как вы себя чувствуете?"
                                font_style: "H5"
                                halign: "center"
                            
                            # Линейка кнопок шкалы Ликерта
                            MDBoxLayout:
                                orientation: 'horizontal'
                                spacing: "10dp"
                                size_hint_y: None
                                height: "50dp"
                                pos_hint: {"center_x": .5}
                                
                                MDRaisedButton:
                                    text: "1"
                                    on_press: app.select_score_button(1, main_manager)
                                MDRaisedButton:
                                    text: "2"
                                    on_press: app.select_score_button(2, main_manager)
                                MDRaisedButton:
                                    text: "3"
                                    on_press: app.select_score_button(3, main_manager)
                                MDRaisedButton:
                                    text: "4"
                                    on_press: app.select_score_button(4, main_manager)
                                MDRaisedButton:
                                    text: "5"
                                    on_press: app.select_score_button(5, main_manager)

                            MDLabel:
                                id: global_score_label
                                text: "Выбранная оценка: не выбрано"
                                halign: "center"
                                font_style: "Subtitle1"

                            MDTextField:
                                id: global_mood_note
                                hint_text: "What do you feel? (optional)"
                                mode: "rectangle"

                            MDRaisedButton:
                                text: "Сохранить запись"
                                pos_hint: {"center_x": .5}
                                on_press: app.save_mood_button(main_manager)

                            MDLabel:
                                id: global_status_label
                                text: ""
                                halign: "center"
                                font_style: "Body2"
                                theme_text_color: "Custom"
                                text_color: [0, 0.6, 0, 1]

                # Вкладка 3: Личный кабинет, Статистика и Журнал истории
                MDBottomNavigationItem:
                    name: 'screen_profile'
                    text: 'Профиль'
                    icon: 'account'
                    
                    ProfileScreen:
                        MDBoxLayout:
                            orientation: 'vertical'
                            padding: "16dp"
                            spacing: "10dp"
                            
                            MDLabel:
                                text: "Личный кабинет"
                                font_style: "H5"
                                halign: "center"
                                size_hint_y: None
                                height: "40dp"
                                
                            MDLabel:
                                text: "Пользователь: Студент"
                                font_style: "H6"
                                size_hint_y: None
                                height: "30dp"

                            MDLabel:
                                id: global_stats_count_label
                                text: "Всего замеров: 0"
                                font_style: "Body1"
                                size_hint_y: None
                                height: "25dp"

                            MDLabel:
                                id: global_stats_avg_label
                                text: "Средний балл: 0.0"
                                font_style: "Body1"
                                size_hint_y: None
                                height: "25dp"

                            MDLabel:
                                text: "История вашего настроения:"
                                font_style: "Subtitle1"
                                size_hint_y: None
                                height: "30dp"
                            
                            MDScrollView:
                                MDList:
                                    id: history_list
'''

# 3. ЛОГИКА БАЗЫ ДАННЫХ SQLITE (СТРУКТУРА ТАБЛИЦ ДИПЛОМА)
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Meditations (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, duration_min INTEGER, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mood_Tracker (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, score INTEGER, note TEXT, date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, meditation_id INTEGER, date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone() == 0:
        cursor.execute("INSERT INTO Users (username) VALUES ('Студент')")
        
    cursor.execute("SELECT COUNT(*) FROM Meditations")
    if cursor.fetchone() == 0:
        meditations = [
            ('Утреннее расслабление', 1, 'Базовые'),  
            ('Снижение стресса', 15, 'Тревога'),
            ('Глубокий сон', 20, 'Сон')
        ]
        cursor.executemany("INSERT INTO Meditations (title, duration_min, category) VALUES (?, ?, ?)", meditations)
    conn.commit()
    conn.close()

def get_meditations():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, duration_min, category FROM Meditations")
    data = cursor.fetchall()
    conn.close()
    return data

def add_mood_record(score, note):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users LIMIT 1")
    user_row = cursor.fetchone()
    user_id = user_row if user_row else 1
    cursor.execute("INSERT INTO Mood_Tracker (user_id, score, note) VALUES (?, ?, ?)", (int(user_id), int(score), str(note)))
    conn.commit()
    conn.close()

def log_meditation_session(med_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users LIMIT 1")
    user_row = cursor.fetchone()
    user_id = user_row if user_row else 1
    cursor.execute("INSERT INTO Sessions (user_id, meditation_id) VALUES (?, ?)", (int(user_id), int(med_id)))
    conn.commit()
    conn.close()

def get_mood_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(score), AVG(score) FROM Mood_Tracker")
    row = cursor.fetchone()
    conn.close()
    if not row or row == 0 or row is None:
        return 0, 0.0
    return int(row), round(float(row), 1)

def get_mood_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT score, note, date_time FROM Mood_Tracker ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return data


# 4. КЛАССЫ ЭКРАНОВ И ОБНОВЛЕНИЕ ДИНАМИЧЕСКИХ СПИСКОВ
class HomeScreen(MDScreen):
    def on_enter(self):
        app = MDApp.get_running_app()
        if hasattr(app.root, 'ids') and 'meditations_list' in app.root.ids:
            app.root.ids.meditations_list.clear_widgets()
            meditations = get_meditations()
            for med_id, title, duration, cat in meditations:
                item = TwoLineListItem(
                    text=f"🧘 {title} — [{cat}]",
                    secondary_text=f"Длительность: {duration} мин. (Нажмите для запуска)",
                    on_release=lambda x, m_id=med_id, t=title, d=duration: app.open_player_popup(m_id, t, d)
                )
                app.root.ids.meditations_list.add_widget(item)

class TrackerScreen(MDScreen):
    pass

class ProfileScreen(MDScreen):
    def on_enter(self):
        count, avg_score = get_mood_stats()
        app = MDApp.get_running_app()
        
        if hasattr(app.root, 'ids') and 'global_stats_count_label' in app.root.ids:
            app.root.ids.global_stats_count_label.text = f"Всего замеров: {count}"
            app.root.ids.global_stats_avg_label.text = f"Средний балл: {avg_score}"
            
        if hasattr(app.root, 'ids') and 'history_list' in app.root.ids:
            app.root.ids.history_list.clear_widgets()
            history_data = get_mood_history()
            for score, note, date_str in history_data:
                short_date = date_str[:16] if date_str else "Неизвестно"
                clean_note = note if note.strip() else "Без заметки"
                item = TwoLineListItem(text=f"Оценка: {score} / 5   ({short_date})", secondary_text=f"Заметка: {clean_note}")
                app.root.ids.history_list.add_widget(item)


# 5. ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ И АСИНХРОННЫЙ КОНТРОЛЛЕР ТАЙМЕРА ПЛЕЕРА
class PlayerMindApp(MDApp): # Изменили имя класса для сброса кэша
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_score = None
        
        self.current_med_id = None
        self.time_left_seconds = 0
        self.timer_active = False
        self.popup = None
        self.popup_label = None
        self.btn_play_pause = None

    def build(self):
        init_db()
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        return Builder.load_string(KV_INTERFACE)

    def open_player_popup(self, med_id, title, duration_min):
        self.current_med_id = med_id
        self.time_left_seconds = duration_min * 60  
        self.timer_active = False

        content = Builder.load_string(f'''
MDBoxLayout:
    orientation: 'vertical'
    padding: "20dp"
    spacing: "15dp"

    MDLabel:
        text: "{title}"
        font_style: "H6"
        halign: "center"
        size_hint_y: None
        height: "40dp"

    MDLabel:
        id: timer_display
        text: "{duration_min}:00"
        font_style: "H3"
        halign: "center"
        theme_text_color: "Primary"

    MDBoxLayout:
        orientation: 'horizontal'
        spacing: "15dp"
        size_hint_y: None
        height: "50dp"
        pos_hint: {{"center_x": .5}}

        MDRaisedButton:
            id: play_pause_btn
            text: "СТАРТ"
            on_press: app.toggle_timer()

        MDFlatButton:
            text: "ЗАКРЫТЬ"
            on_press: app.close_player_popup()
''')
        
        self.popup_label = content.ids.timer_display
        self.btn_play_pause = content.ids.play_pause_btn

        self.popup = Popup(
            title="Медитативная сессия", 
            content=content, 
            size_hint=(0.85, 0.45), 
            auto_dismiss=False
        )
        self.popup.open()
        
        Clock.schedule_interval(self.update_timer_tick, 1.0)

    def toggle_timer(self):
        self.timer_active = not self.timer_active
        if self.timer_active:
            self.btn_play_pause.text = "ПАУЗА"
        else:
            self.btn_play_pause.text = "СТАРТ"

    def update_timer_tick(self, dt):
        if not self.timer_active or self.time_left_seconds <= 0:
            return

        self.time_left_seconds -= 1
        
        mins = self.time_left_seconds // 60
        secs = self.time_left_seconds % 60
        self.popup_label.text = f"{mins}:{secs:02d}"

        if self.time_left_seconds == 0:
            self.timer_active = False
            self.popup_label.text = "ПРАКТИКА ЗАВЕРШЕНА"
            self.popup_label.theme_text_color = "Custom"
            self.popup_label.text_color = [0, 0.6, 0, 1]  
            self.btn_play_pause.disabled = True
            log_meditation_session(self.current_med_id)

    def close_player_popup(self):
        self.timer_active = False
        Clock.unschedule(self.update_timer_tick)
        if self.popup:
            self.popup.dismiss()

    def select_score_button(self, score, root_manager):
        self.selected_score = int(score)
        root_manager.ids.global_score_label.text = f"Выбранная оценка: {self.selected_score}"
        root_manager.ids.global_status_label.text = ""

    def save_mood_button(self, root_manager):
        if self.selected_score is None:
            root_manager.ids.global_status_label.text_color = [0.8, 0, 0, 1]
            root_manager.ids.global_status_label.text = "Ошибка: сначала выберите оценку!"
            return

        note_text = root_manager.ids.global_mood_note.text
        add_mood_record(self.selected_score, note_text)
        
        root_manager.ids.global_status_label.text_color = [0, 0.6, 0, 1]
        root_manager.ids.global_status_label.text = "Запись успешно сохранена в базу SQLite!"
        
        self.selected_score = None
        root_manager.ids.global_score_label.text = "Выбранная оценка: не выбрано"
        root_manager.ids.global_mood_note.text = ""

if __name__ == '__main__':
    PlayerMindApp().run()