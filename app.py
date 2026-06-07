import os
import sqlite3
import csv

import os
import sqlite3
import csv

# 1. КОНФИГУРАЦИЯ ГРАФИЧЕСКОГО ДВИЖКА ДЛЯ WINDOWS
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.popup import Popup  
from kivy.clock import Clock      
from kivy.core.audio import SoundLoader
from kivymd.uix.list import TwoLineListItem
from kivy.properties import NumericProperty


# Абсолютные пути проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "mental_health.db")

# Статическая разметка Popup-плеера
POPUP_KV = '''
MDBoxLayout:
    orientation: 'vertical'
    padding: "20dp"
    spacing: "15dp"

    MDLabel:
        id: title_display
        text: ""
        font_style: "H6"
        halign: "center"
        size_hint_y: None
        height: "40dp"

    MDLabel:
        id: timer_display
        text: ""
        font_style: "H3"
        halign: "center"
        theme_text_color: "Primary"

    MDBoxLayout:
        orientation: 'horizontal'
        spacing: "15dp"
        size_hint_y: None
        height: "50dp"
        pos_hint: {"center_x": .5}

        MDRaisedButton:
            id: play_pause_btn
            text: "СТАРТ"
            on_press: app.toggle_timer()

        MDFlatButton:
            text: "ЗАКРЫТЬ"
            on_press: app.close_player_popup_request()
'''

# Разметка окна подтверждения прерывания медитации
CONFIRM_KV = '''
MDBoxLayout:
    orientation: 'vertical'
    padding: "16dp"
    spacing: "15dp"

    MDLabel:
        text: "Вы уверены, что хотите прервать практику? Текущий прогресс будет потерян."
        halign: "center"
        font_style: "Body1"

    MDBoxLayout:
        orientation: 'horizontal'
        spacing: "10dp"
        size_hint_y: None
        height: "45dp"
        pos_hint: {"center_x": .5}

        MDRaisedButton:
            text: "Да, прервать"
            md_bg_color: [0.8, 0, 0, 1]
            on_press: app.confirm_close_player()

        MDFlatButton:
            text: "Отмена"
            on_press: app.dismiss_confirm_popup()
'''

# === ФИЧА ДЛЯ ДИПЛОМА: ФИНАЛЬНАЯ РАЗМЕТКА ОКНА БИБЛИОТЕКИ МЕДИТАЦИЙ ===
ADD_MEDITATION_KV = '''
MDBoxLayout:
    orientation: 'vertical'
    padding: "20dp"
    spacing: "12dp"

    MDLabel:
        text: "Добавление новой практики"
        font_style: "H6"
        halign: "center"
        size_hint_y: None
        height: "35dp"

    MDTextField:
        id: new_title_field
        hint_text: "Название медитации (например: Вечерний сон)"
        mode: "rectangle"

    MDTextField:
        id: new_file_field
        hint_text: "Имя файла в audio/ (например: night.mp3)"
        mode: "rectangle"

    MDTextField:
        id: new_duration_field
        hint_text: "Длительность (в минутах)"
        input_filter: "int"
        mode: "rectangle"

    MDBoxLayout:
        orientation: 'horizontal'
        spacing: "15dp"
        size_hint_y: None
        height: "45dp"
        pos_hint: {"center_x": .5}

        MDRaisedButton:
            text: "ДОБАВИТЬ"
            md_bg_color: [0.0, 0.5, 0.5, 1]
            on_release: 
                # Вызываем твой готовый метод из низа app.py
                app.save_custom_meditation_to_library(new_title_field.text, new_file_field.text, new_duration_field.text)

        MDFlatButton:
            text: "ОТМЕНА"
            on_press: app.close_add_meditation_popup()
'''




# 3. ЛОГИКА БАЗЫ ДАННЫХ SQLITE
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Meditations (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, duration_min INTEGER, category TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mood_Tracker (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, score INTEGER, note TEXT, date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, meditation_id INTEGER, date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = cursor.fetchone()[0]
    if user_count == 0:
        cursor.execute("INSERT INTO Users (username) VALUES ('Студент')")
        
    cursor.execute("SELECT COUNT(*) FROM Meditations")
    med_count = cursor.fetchone()[0]
    if med_count == 0:
        meditations = [
            ('Утреннее расслабление', 1, 'Базовые'),  
            ('Снижение стресса', 15, 'Тревога'),
            ('Глубокий сон', 20, 'Сон')
        ]
        cursor.executemany("INSERT INTO Meditations (title, duration_min, category) VALUES (?, ?, ?)", meditations)
    conn.commit()
    conn.close()

def add_mood_record(score, note):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users LIMIT 1")
    user_row = cursor.fetchone()
    user_id = user_row[0] if user_row else 1
    cursor.execute("INSERT INTO Mood_Tracker (user_id, score, note) VALUES (?, ?, ?)", (int(user_id), int(score), str(note)))
    conn.commit()
    conn.close()

def log_meditation_session(med_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Users LIMIT 1")
    user_row = cursor.fetchone()
    user_id = user_row[0] if user_row else 1
    cursor.execute("INSERT INTO Sessions (user_id, meditation_id) VALUES (?, ?)", (int(user_id), int(med_id)))
    conn.commit()
    conn.close()

def get_mood_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(score), AVG(score) FROM Mood_Tracker")
    row = cursor.fetchone()
    conn.close()
    if not row or row[0] == 0:
        return 0, 0.0
    count = int(row[0])
    avg_score = round(float(row[1]), 1) if row[1] is not None else 0.0
    return count, avg_score

def get_mood_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT score, note, date_time FROM Mood_Tracker ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return data


# 4. КЛАССЫ ЭКРАНОВ
class HomeScreen(MDScreen):
    def on_enter(self, *args):
        """Автоматическая проверка при входе на экран медитаций"""
        # Если кнопки «Добавить свою практику» еще нет на экране, мы создаем её программно на Python
        if not hasattr(self, 'add_custom_btn_created'):
            from kivymd.uix.button import MDFloatingActionButton
            
            # Создаем красивую парящую круглую кнопку «+» в правом нижнем углу экрана медитаций
            add_btn = MDFloatingActionButton(
                icon="plus",
                md_bg_color=[0.0, 0.5, 0.5, 1],
                icon_color=[1, 1, 1, 1],
                pos_hint={"right": 0.95, "bottom": 0.05},
                size_hint=(None, None),
                size=("56dp", "56dp")
            )
            # Привязываем клик на кнопку к открытию нашего нового отдельного окна
            from kivy.app import App
            add_btn.bind(on_release=lambda x: App.get_running_app().open_add_meditation_window())
            
            # Добавляем её на живой экран медитаций поверх всей твоей готовой верстки
            self.add_widget(add_btn)
            self.add_custom_btn_created = True
            print("Дипломный модуль: Программная кнопка добавления практик успешно инжектирована.")

class TrackerScreen(MDScreen):
    pass

class ProfileScreen(MDScreen):
    pass



from kivy.properties import NumericProperty

# 5. ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ ПАТТЕРНА MVC
class PlayerMindApp(MDApp): 
    # Объявляем реактивное Kivy-свойство для плавной анимации холста сферы
    circle_radius = NumericProperty(40.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_score = None
        self.current_med_id = None
        self.time_left_seconds = 0
        self.timer_active = False
        self.popup = None
        self.confirm_popup = None
        self.popup_label = None
        self.btn_play_pause = None
        self.timer_event = None  
        self.current_sound = None  
        
        # Переменные дыхательного тренажера
        self.breath_popup = None
        self.breath_event = None
        self.breath_seconds = 4
        self.current_phase_index = 0
        self.breath_phases = ["ВДОХ (Расширение)", "ЗАДЕРЖКА", "ВЫДОХ (Сужение)", "ЗАДЕРЖКА"]

    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = (0.0, 0.5, 0.5, 1)
        
        init_db()
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        
        root = Builder.load_file(os.path.join(BASE_DIR, "mentalhealth.kv"))
        return root

    # ОБНОВЛЕНИЕ ДАННЫХ ПРОФИЛЯ, ГРАФИКА И ИИ ИЗ SQLITE
    def refresh_profile_data_direct(self, root_manager, *args):
        try:
            count, avg_score = get_mood_stats()
            
            if hasattr(root_manager, 'ids'):
                if 'ui_stats_count' in root_manager.ids:
                    root_manager.ids.ui_stats_count.text = f"Всего замеров: {count}"
                if 'ui_stats_avg' in root_manager.ids:
                    root_manager.ids.ui_stats_avg.text = f"Средний балл: {avg_score}"
                    
                if 'ui_history_list' in root_manager.ids:
                    list_widget = root_manager.ids.ui_history_list
                    list_widget.clear_widgets()
                    
                    history_data = get_mood_history()
                    for score, note, date_str in history_data:
                        short_date = date_str[:16] if date_str else "Неизвестно"
                        clean_note = note.strip() if note and note.strip() else "Без заметки"
                        item = TwoLineListItem(
                            text=f"Оценка: {score} / 5   ({short_date})", 
                            secondary_text=f"Заметка: {clean_note}"
                        )
                        list_widget.add_widget(item)
            
            # Подтягиваем последний балл для обновления блока ИИ-рекомендаций
            history = get_mood_history()
            last_score = history[0][0] if history else None
            self.update_ai_recommendation(last_score, root_manager)
            
            # Вызываем перерисовку низкоуровневого холста аналитики
            self.draw_analytics_chart(root_manager)
            
        except Exception as e:
            print(f"[Profile Sync Warning] {e}")

    # МОДУЛЬ УМНЫХ ИИ-РЕКОМЕНДАЦИЙ (ВЫЛИЗАННЫЙ ВИЗУАЛ)
    def update_ai_recommendation(self, score, root_manager):
        if not hasattr(root_manager, 'ids') or 'ai_rec_box' not in root_manager.ids:
            return
            
        container = root_manager.ids.ai_rec_box
        
        if 'ai_rec_lbl' in root_manager.ids:
            lbl = root_manager.ids.ai_rec_lbl
        else:
            return

        # Безопасный поиск иконки робота в файле .kv по её ID
        icon_widget = root_manager.ids.get('ai_rec_icon')

        if score is None:
            lbl.text = "Сделайте первый замер настроения во вкладке для получения персональной рекомендации."
            container.md_bg_color = [1, 1, 1, 1]
            if icon_widget:
                icon_widget.icon = "robot"
                icon_widget.text_color = [0.0, 0.5, 0.5, 1]
            return

        # Если настроение плохое (Стресс/Тревога)
        if score <= 2:
            lbl.text = f"Ваш последний балл: {score} (Стресс). Рекомендуем практику: Снижение стресса."
            container.md_bg_color = [1.0, 0.92, 0.93, 1]  # Легкий красный акцент
            if icon_widget:
                icon_widget.icon = "robot-confused"        # Робот погрустнел
                icon_widget.text_color = [0.8, 0.2, 0.2, 1] # Иконка стала красноватой

        # Если настроение нормальное
        elif score == 3:
            lbl.text = f"Ваш последний балл: {score} (Норма). Рекомендуем практику: Утреннее расслабление."
            container.md_bg_color = [0.92, 0.96, 1.0, 1]  # Легкий синий акцент
            if icon_widget:
                icon_widget.icon = "robot"                 # Стандартный робот
                icon_widget.text_color = [0.2, 0.5, 0.8, 1] # Синеватая иконка

        # Если настроение отличное
        else:
            lbl.text = f"Ваш последний балл: {score} (Отлично!). Рекомендуем практику: Глубокий сон в конце дня."
            container.md_bg_color = [0.93, 1.0, 0.94, 1]  # Легкий зеленый акцент
            if icon_widget:
                icon_widget.icon = "robot-happy"           # Робот улыбается!
                icon_widget.text_color = [0.2, 0.6, 0.3, 1] # Зеленоватая иконка

            # === МФ2: ИСПРАВЛЕННЫЙ МОДУЛЬ ДИНАМИЧЕСКОЙ ОТРИСОВКИ ГРАФИКА ===
    def draw_analytics_chart(self, root_manager):
        """Безопасная отрисовка графика, привязанная к реальным размерам виджета на экране"""
        if not hasattr(root_manager, 'ids') or 'chart_canvas_box' not in root_manager.ids:
            return
            
        box = root_manager.ids.chart_canvas_box
        
        # Защита от нулевых размеров при первой загрузке Kivy
        if box.width < 100 or box.height < 50:
            Clock.schedule_once(lambda dt: self.draw_analytics_chart(root_manager), 0.1)
            return

        # Отвязываем старые триггеры и очищаем холст
        try:
            box.unbind(pos=self.trigger_chart_redraw, size=self.trigger_chart_redraw)
        except Exception:
            pass
            
        box.canvas.before.clear()
        
        from kivy.graphics import Color, Rectangle

        # Извлечение актуального тренда из SQLite с распаковкой кортежей
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT score FROM Mood_Tracker ORDER BY id DESC LIMIT 7")
            rows = cursor.fetchall()
            conn.close()
            # Достаем чистые инты (row[0]) из кортежей базы
            chart_data = [row[0] for row in reversed(rows)] if rows else [3, 4, 2, 5, 4, 3, 5]
            while len(chart_data) < 7:
                chart_data.insert(0, 0)
        except Exception:
            chart_data = [3, 4, 2, 5, 4, 3, 5]

        # Отрисовка на низкоуровневом Canvas
        with box.canvas.before:
            # Фон подложки виджета
            Color(0.92, 0.94, 0.95, 1)
            Rectangle(pos=box.pos, size=box.size)
            
            padding_x = 40  # Увеличили боковые отступы, чтобы график не прилипал к краям
            padding_y = 20  # Увеличили нижний отступ
            available_w = box.width - (padding_x * 2)
            available_h = box.height - (padding_y * 2) - 10
            
            # Сделали фиксированные зазоры между столбцами побольше (20dp вместо 10dp)
            spacing = 20 
            col_width = (available_w - (spacing * 6)) / 7
            
            # Ограничили максимальную ширину столбца, чтобы они не становились огромными
            if col_width > 24:
                col_width = 24
                # Центрируем весь блок столбцов, если они зажаты максимальной шириной
                total_graph_w = (col_width * 7) + (spacing * 6)
                padding_x = (box.width - total_graph_w) / 2

            max_score = 5.0
            
            for i, val in enumerate(chart_data):
                # Рассчитываем координату X с учетом увеличенных зазоров
                col_x = box.x + padding_x + i * (col_width + spacing)
                col_y = box.y + padding_y
                
                ratio = val / max_score if val > 0 else 0.05
                col_h = available_h * ratio
                
                # Делаем цвет чуть более стильным (бирюзовый с легкой прозрачностью)
                Color(0.0, 0.5 * (val / 5.0 if val > 0 else 0.4), 0.5, 0.85)
                Rectangle(pos=(col_x, col_y), size=(col_width, col_h))

        # Подписываем виджет на изменение размеров и позиций (чтобы график не пропадал)
        box.bind(pos=self.trigger_chart_redraw, size=self.trigger_chart_redraw)

    def trigger_chart_redraw(self, instance, value):
        """Обязательный метод обратного вызова для пересчета координат Canvas при скролле"""
        if hasattr(self, 'root') and self.root:
            # Перерисовываем график, используя ссылку на корневой менеджер
            self.draw_analytics_chart(self.root)


    # === МФ3: ИНТЕРАКТИВНЫЙ ДЫХАТЕЛЬНЫЙ ТРЕНАЖЕР ===
    def open_breath_practice_ui(self):
        breath_kv_string = '''
MDBoxLayout:
    orientation: 'vertical'
    padding: "16dp"
    spacing: "10dp"
    
    MDLabel:
        id: breath_phase_lbl
        text: "ВДОХ (Расширение)"
        font_style: "H5"
        halign: "center"
        size_hint_y: None
        height: "40dp"
        
    MDLabel:
        id: breath_timer_lbl
        text: "4"
        font_style: "H3"
        halign: "center"
        size_hint_y: None
        height: "50dp"
        theme_text_color: "Primary"
        
    MDBoxLayout:
        id: circle_container
        size_hint_y: 1
        canvas.before:
            Color:
                rgba: [0.95, 0.95, 0.95, 1]
            Rectangle:
                pos: self.pos
                size: self.size
                
    MDRaisedButton:
        text: "ЗАВЕРШИТЬ"
        pos_hint: {"center_x": .5}
        md_bg_color: [0.8, 0, 0, 1]
        on_press: app.stop_breath_practice()
'''
        self.breath_seconds = 4
        self.current_phase_index = 0
        self.circle_radius = 40.0
        self.breath_phases = ["ВДОХ (Расширение)", "ЗАДЕРЖКА", "ВЫДОХ (Сужение)", "ЗАДЕРЖКА"]
        
        content = Builder.load_string(breath_kv_string)
        self.breath_popup = Popup(
            title="Практика осознанного дыхания",
            content=content,
            size_hint=(0.9, 0.6),
            auto_dismiss=False
        )
        self.breath_popup.open()
        
        self.breath_event = Clock.schedule_interval(self.breath_tick_processor, 1.0)
        Clock.schedule_once(self.draw_breath_circle, 0.1)

    def breath_tick_processor(self, dt):
        if not self.breath_popup:
            return
            
        self.breath_seconds -= 1
        
        if self.current_phase_index == 0:
            self.circle_radius += 12.0
        elif self.current_phase_index == 2:
            self.circle_radius -= 12.0
            
        if self.circle_radius < 10.0:
            self.circle_radius = 10.0
            
        if self.breath_seconds <= 0:
            self.breath_seconds = 4
            self.current_phase_index = (self.current_phase_index + 1) % 4
            
        self.breath_popup.content.ids.breath_phase_lbl.text = self.breath_phases[self.current_phase_index]
        self.breath_popup.content.ids.breath_timer_lbl.text = str(self.breath_seconds)
        self.draw_breath_circle()

    def draw_breath_circle(self, *args):
        if not self.breath_popup:
            return
            
        container = self.breath_popup.content.ids.circle_container
        container.canvas.clear()
        
        with container.canvas:
            from kivy.graphics import Color, Ellipse
            Color(0.0, 0.5, 0.5, 0.6)
            cc_x = container.x + container.width / 2 - self.circle_radius
            cc_y = container.y + container.height / 2 - self.circle_radius
            Ellipse(pos=(cc_x, cc_y), size=(self.circle_radius * 2, self.circle_radius * 2))

    def stop_breath_practice(self):
        if hasattr(self, 'breath_event') and self.breath_event:
            Clock.unschedule(self.breath_event)
        if hasattr(self, 'breath_popup') and self.breath_popup:
            self.breath_popup.dismiss()
            self.breath_popup = None

    # === ЭКСПОРТ В CSV С ПОДДЕРЖКОЙ WINDOWS EXCEL EXPORT ===
    def export_data_to_csv(self, root_manager):
        try:
            report_path = os.path.join(BASE_DIR, "mental_health_report.csv")
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Mood_Tracker.date_time, Mood_Tracker.score, Mood_Tracker.note, Users.username
                FROM Mood_Tracker
                JOIN Users ON Mood_Tracker.user_id = Users.id
                ORDER BY Mood_Tracker.id DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            with open(report_path, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(['Дата и время', 'Оценка состояния (1-5)', 'Заметка пользователя', 'Пользователь'])
                for row in rows:
                    writer.writerow(row)
            print(f"[Успешный экспорт] Данные сохранены в: {report_path}")
        except Exception as e:
            print(f"[Export Error] {e}")

# === КЛАССИЧЕСКИЙ СТАНДАРТНЫЙ ПЛЕЕР МЕДИТАЦИЙ ===
    def select_mood_score(self, score):
        self.selected_score = score
        print(f"[Mood Selected] Оценка: {score}")

    def save_mood_entry_from_ui(self, note_text, root_manager):
        if self.selected_score is None:
            return
        add_mood_record(self.selected_score, note_text)
        self.refresh_profile_data_direct(root_manager)
        
        # Обновление ИИ и Графика после добавления новой записи
        self.update_ai_recommendation(self.selected_score, root_manager)
        self.draw_analytics_chart(root_manager)
        self.selected_score = None

    def start_meditation_session_ui(self, med_id, title, duration_min):
        self.current_med_id = med_id
        self.time_left_seconds = int(duration_min) * 60
        self.timer_active = False
        
        popup_content = Builder.load_string(POPUP_KV)
        popup_content.ids.title_display.text = f"Практика: {title}"
        
        minutes = self.time_left_seconds // 60
        seconds = self.time_left_seconds % 60
        popup_content.ids.timer_display.text = f"{minutes:02d}:{seconds:02d}"
        
        self.popup_label = popup_content.ids.timer_display
        self.btn_play_pause = popup_content.ids.play_pause_btn
        
        self.popup = Popup(
            title="Медиаплеер сессии",
            content=popup_content,
            size_hint=(0.85, 0.5),
            auto_dismiss=False
        )
        self.popup.open()
        
        # === АВТОМАТИЧЕСКИЙ ФИКС ПЛЕЕРА ПОД .WAV ИЗ ПАПКИ AUDIO ===
        file_to_load = f"med_{med_id}.wav" if med_id != 99 else "med_1.wav"
        sound_path = os.path.join(BASE_DIR, "audio", file_to_load)
        
        if os.path.exists(sound_path):
            from kivy.core.audio import SoundLoader
            self.current_sound = SoundLoader.load(sound_path)
            print(f"[ПЛЕЕР] Звуковой движок успешно подгрузил файл: {sound_path}")
        else:
            print(f"[ОШИБКА ПЛЕЕРА] Аудиофайл не найден по пути: {sound_path}")

    def toggle_timer(self):
        if not self.timer_active:
            self.timer_active = True
            self.btn_play_pause.text = "ПАУЗА"
            self.timer_event = Clock.schedule_interval(self.update_timer_tick, 1.0)
            if hasattr(self, 'current_sound') and self.current_sound:
                self.current_sound.play()
        else:
            self.timer_active = False
            self.btn_play_pause.text = "СТАРТ"
            if hasattr(self, 'timer_event') and self.timer_event:
                Clock.unschedule(self.timer_event)
            if hasattr(self, 'current_sound') and self.current_sound:
                self.current_sound.stop()

    def update_timer_tick(self, dt):
        if self.time_left_seconds > 0:
            self.time_left_seconds -= 1
            minutes = self.time_left_seconds // 60
            seconds = self.time_left_seconds % 60
            self.popup_label.text = f"{minutes:02d}:{seconds:02d}"
        else:
            if hasattr(self, 'timer_event') and self.timer_event:
                Clock.unschedule(self.timer_event)
            if hasattr(self, 'current_sound') and self.current_sound:
                self.current_sound.stop()
                
            log_meditation_session(self.current_med_id)
            if self.popup:
                self.popup.dismiss()

    def close_player_popup_request(self):
        if self.timer_active or (self.time_left_seconds > 0 and self.popup):
            confirm_content = Builder.load_string(CONFIRM_KV)
            self.confirm_popup = Popup(
                title="Подтверждение",
                content=confirm_content,
                size_hint=(0.8, 0.35),
                auto_dismiss=False
            )
            self.confirm_popup.open()
        else:
            if self.popup:
                self.popup.dismiss()

    def confirm_close_player(self):
        if hasattr(self, 'timer_event') and self.timer_event:
            Clock.unschedule(self.timer_event)
        if hasattr(self, 'current_sound') and self.current_sound:
            self.current_sound.stop()
        if hasattr(self, 'confirm_popup') and self.confirm_popup:
            self.confirm_popup.dismiss()
        if self.popup:
            self.popup.dismiss()
        self.timer_active = False

    def dismiss_confirm_popup(self):
        if hasattr(self, 'confirm_popup') and self.confirm_popup:
            self.confirm_popup.dismiss()

    # === МЕТОДЫ ДЛЯ ДИПЛОМА: ОТДЕЛЬНОЕ ОКНО КОНСТРУКТОРА ПРАКТИК ===
    def open_add_meditation_window(self):
        """Программный вызов отдельного окна добавления медитаций"""
        popup_content = Builder.load_string(ADD_MEDITATION_KV)
        
        self.add_meditation_popup = Popup(
            title="Конструктор библиотеки медитаций",
            content=popup_content,
            size_hint=(0.85, 0.6),
            auto_dismiss=False
        )
        self.add_meditation_popup.open()
        print("[Дипломный модуль] Отдельное окно добавления практик успешно открыто.")

    def close_add_meditation_popup(self):
        """Закрытие окна добавления"""
        if hasattr(self, 'add_meditation_popup') and self.add_meditation_popup:
            self.add_meditation_popup.dismiss()

    def save_custom_meditation_to_library(self, title, filename, duration):
        """Валидация полей, запись в SQLite и запуск добавленного трека в твоем плеере"""
        title = title.strip()
        filename = filename.strip()
        duration = duration.strip()

        if not title or not filename or not duration:
            print("Ошибка: Все поля ввода обязательны для заполнения!")
            return

        try:
            # ЖЁСТКАЯ ЗАПИСЬ КАСТОМНОЙ ПРАКТИКИ В ТВОЮ БАЗУ ДАННЫХ SQLITE
            conn = sqlite3.connect(os.path.join(BASE_DIR, "mental_health.db"))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO meditations (title, duration_min, is_custom) VALUES (?, ?, 1)",
                (title, int(duration))
            )
            conn.commit()
            conn.close()
            print(f"[КОНСТРУКТОР] Практика '{title}' успешно вшита в SQLite базу данных!")
        except Exception as e:
            print(f"[КОНСТРУКТОР БД ОШИБКА] Не удалось сохранить запись: {e}")

        print(f"[Успешно добавлено] Практика: {title} ({duration} мин). Файл: {filename}")
        
        # 1. Закрываем форму ввода
        self.close_add_meditation_popup()
        
        # 2. Перенаправляем данные в твой родной рабочий плеер сессии
        self.start_meditation_session_ui(99, title, int(duration))


# ... Выше идут твои старые методы класса PlayerMindApp (например, build) ...

    # === МЕТКА ДЛЯ ДИПЛОМА: ПРАКТИКА ДЫХАНИЯ С ЖЕСТКОЙ АНИМАЦИЕЙ СФЕРЫ И КОНСТРУКТОР ===
    def open_breath_practice_ui(self):
        """Оригинальный дипломный модуль тренажера с анимированной сферой дыхания"""
        breath_kv_string = '''
MDBoxLayout:
    orientation: 'vertical'
    padding: "24dp"
    spacing: "24dp"
    md_bg_color: [0.96, 0.97, 0.98, 1]

    MDTopAppBar:
        title: "Осознанное дыхание"
        elevation: 0
        md_bg_color: [0.0, 0.5, 0.5, 1]
        left_action_items: [["arrow-left", lambda x: app.stop_breath_practice()]]

    MDBoxLayout:
        orientation: 'vertical'
        spacing: "20dp"
        pos_hint: {"center_x": .5, "center_y": .5}

        MDLabel:
            id: breath_instruction
            text: "Приготовьтесь..."
            font_style: "H5"
            halign: "center"
            theme_text_color: "Custom"
            text_color: [0.0, 0.5, 0.5, 1]

        # Контейнер для динамической отрисовки сферы
        Widget:
            id: breath_sphere_widget
            size_hint: (None, None)
            size: ("200dp", "200dp")
            pos_hint: {"center_x": .5}
            canvas:
                Color:
                    rgba: [0.0, 0.5, 0.5, 0.3]
                Ellipse:
                    # Жесткая привязка позиции и размера к NumericProperty circle_radius
                    pos: self.center_x - (app.circle_radius / 2), self.center_y - (app.circle_radius / 2)
                    size: app.circle_radius, app.circle_radius

        MDLabel:
            id: breath_timer
            text: "3"
            font_style: "H2"
            halign: "center"
            theme_text_color: "Primary"

        MDRaisedButton:
            text: "ЗАВЕРШИТЬ"
            pos_hint: {"center_x": .5}
            md_bg_color: [0.8, 0, 0, 1]
            on_press: app.stop_breath_practice()
'''
        from kivy.lang import Builder
        self.circle_radius = 60.0  # Сброс радиуса на старте сессии
        
        self.breath_popup_content = Builder.load_string(breath_kv_string)
        
        from kivy.uix.popup import Popup
        self.breath_popup = Popup(
            title="Техника 4-4-4-4",
            content=self.breath_popup_content,
            size_hint=(1, 1),
            auto_dismiss=False
        )
        self.breath_popup.open()
        
        # === АВТОМАТИЧЕСКИЙ ФИКС ЗВУКА ИЗ ПАПКИ AUDIO ===
        sound_path = os.path.join(BASE_DIR, "audio", "呼吸.wav")
        if os.path.exists(sound_path):
            from kivy.core.audio import SoundLoader
            self.breath_sound = SoundLoader.load(sound_path)
            if self.breath_sound:
                self.breath_sound.play()
        else:
            print(f"[ОШИБКА АУДИО] Файл не найден: {sound_path}")
        # ===============================================
        
        self.breath_count = 3
        self.breath_phase = "PREPARE"
        
        from kivy.clock import Clock
        # Тикаем каждые 0.02 секунды для максимальной плавности круга
        self.breath_event = Clock.schedule_interval(self.update_breath_tick, 0.02)
        self.time_accumulator = 0.0

    def update_breath_tick(self, dt):
        """Логика секундных фаз и автоматического расширения реактивной сферы"""
        try:
            if not hasattr(self, 'breath_popup_content') or not self.breath_popup_content:
                return
            
            self.time_accumulator += dt
            
            # Логика секундного обновления цифр

            if self.time_accumulator >= 1.0:
                self.time_accumulator = 0.0
                self.breath_count -= 1
                self.breath_popup_content.ids.breath_timer.text = str(self.breath_count)
                
                if self.breath_count <= 0:
                    self.breath_count = 4
                    if self.breath_phase == "PREPARE":
                        self.breath_phase = "ВДОХ"
                        self.breath_popup_content.ids.breath_instruction.text = "Сделайте ВДОХ"
                    elif self.breath_phase == "ВДОХ":
                        self.breath_phase = "ЗАДЕРЖКА"
                        self.breath_popup_content.ids.breath_instruction.text = "ЗАДЕРЖИТЕ ДЫХАНИЕ"
                    elif self.breath_phase == "ЗАДЕРЖКА":
                        self.breath_phase = "ВЫДОХ"
                        self.breath_popup_content.ids.breath_instruction.text = "Сделайте ВЫДОХ"
                    elif self.breath_phase == "ВЫДОХ":
                        self.breath_phase = "ПАУЗА"
                        self.breath_popup_content.ids.breath_instruction.text = "ЗАДЕРЖИТЕ НА ВЫДОХЕ"
                    elif self.breath_phase == "ПАУЗА":
                        self.breath_phase = "ВДОХ"
                        self.breath_popup_content.ids.breath_instruction.text = "Сделайте ВДОХ"

            # АНИМАЦИЯ КРУГА: Меняем circle_radius, Kivy сам мгновенно перерисует Ellipse
            if self.breath_phase == "ВДОХ":
                if self.circle_radius < 180.0:
                    self.circle_radius += 1.5
            elif self.breath_phase == "ВЫДОХ":
                if self.circle_radius > 60.0:
                    self.circle_radius -= 1.5
            elif self.breath_phase == "PREPARE":
                self.circle_radius = 60.0

        except Exception as e:
            print(f"Ошибка анимации сферы: {e}")

    def stop_breath_practice(self):
        """Корректное закрытие тренажера и выгрузка таймеров Clock"""
        if hasattr(self, 'breath_event') and self.breath_event:
            Clock.unschedule(self.breath_event)
        if hasattr(self, 'breath_popup') and self.breath_popup:
            self.breath_popup.dismiss()
        print("[Дипломный модуль] Сессия осознанного дыхания успешно завершена.")

    def open_add_meditation_window(self):
        from kivy.lang import Builder
        popup_content = Builder.load_string(ADD_MEDITATION_KV)
        self.add_meditation_content = popup_content
        from kivy.uix.popup import Popup
        self.add_meditation_popup = Popup(
            title="Конструктор библиотеки медитаций",
            content=popup_content,
            size_hint=(0.85, 0.55),
            auto_dismiss=True
        )
        self.add_meditation_popup.open()

    def close_add_meditation_popup(self):
        if hasattr(self, 'add_meditation_popup') and self.add_meditation_popup:
            self.add_meditation_popup.dismiss()

    def save_custom_meditation_to_library(self, title, filename, duration):
        title = title.strip()
        filename = filename.strip()
        duration = duration.strip()

        if not title or not filename or not duration:
            print("Ошибка: Все поля ввода обязательны для заполнения!")
            return

        self.close_add_meditation_popup()
        if hasattr(self, 'start_meditation_session_ui'):
            self.start_meditation_session_ui(99, title, int(duration))

# САМЫЙ КОНЕЦ ТВОЕГО ФАЙЛА APP.PY
if __name__ == '__main__':
    PlayerMindApp().run()
