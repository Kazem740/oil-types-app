from flet import *
import json
import datetime
from pathlib import Path
import sqlite3
import os
import shutil  # لنسخ قاعدة البيانات القديمة
import math
import logging
import sys
from typing import Optional, Tuple

# تهيئة نظام تسجيل الأخطاء
def init_logging():
    log_file = Path.home() / "ALKA_Data" / "alka_app.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

init_logging()
logging.info("تم بدء تشغيل تطبيق ALKA Oil Tracker")

# دوال معالجة الأخطاء
def log_error(error: Exception, context: str = "") -> str:
    """تسجيل الخطأ وإرجاع رسالة الخطأ"""
    error_msg = f"خطأ في {context}: {str(error)}"
    logging.error(error_msg)
    return error_msg

def show_error(page: Page, error: Exception, context: str = ""):
    """عرض رسالة الخطأ للمستخدم"""
    error_msg = log_error(error, context)
    show_snackbar(page, error_msg, ThemeColors.ERROR)

# إنشاء مجلد للبيانات إذا لم يكن موجوداً
data_dir = Path.home() / "ALKA_Data"
data_dir.mkdir(exist_ok=True)

# إنشاء قاعدة البيانات
db_path = data_dir / "alka_oil.db"

def init_db():
    # نسخ احتياطي لقاعدة البيانات القديمة إذا كانت موجودة
    if db_path.exists():
        backup_path = data_dir / f"alka_oil_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy(db_path, backup_path)
        db_path.unlink()  # حذف قاعدة البيانات القديمة

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # إنشاء الجداول مع الحقول الجديدة
    c.execute('''CREATE TABLE IF NOT EXISTS oil_types
                 (name TEXT PRIMARY KEY, max_distance INTEGER, 
                  remaining_distance INTEGER, image TEXT,
                  liter_capacity REAL, grade TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS oil_changes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  oil_type TEXT, change_date TEXT,
                  kilometer_reading INTEGER,
                  vehicle_type TEXT DEFAULT 'سيارة خاصة')''')
    
    # إضافة جدول السيارات
    c.execute('''CREATE TABLE IF NOT EXISTS vehicles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  car_type TEXT,
                  manufacture_year INTEGER,
                  current_mileage INTEGER,
                  last_oil_change_date TEXT,
                  next_oil_change_mileage INTEGER)''')
    
    # إضافة جدول الإطارات
    c.execute('''CREATE TABLE IF NOT EXISTS wheels
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  wheel_type TEXT,
                  install_date TEXT,
                  expected_life INTEGER)''')
    
    # إضافة البيانات الافتراضية
    default_oil_types = {
        "زيت 10W-40": {
            "max_distance": 5000,
            "remaining_distance": 5000,
            "image": "",
            "liter_capacity": 4,
            "grade": "10W-40"
        },
        "زيت 5W-30": {
            "max_distance": 6000,
            "remaining_distance": 6000,
            "image": "",
            "liter_capacity": 5,
            "grade": "5W-30"
        }
    }
    
    for name, data in default_oil_types.items():
        c.execute("""INSERT OR REPLACE INTO oil_types 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (name, data["max_distance"], data["remaining_distance"],
                  data["image"], data["liter_capacity"], data["grade"]))
    
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات
init_db()

# جدول لتخزين معلومات السيارة
def init_vehicle_table():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_type TEXT,
            manufacture_year INTEGER,
            current_mileage INTEGER,
            last_oil_change_date TEXT,
            next_oil_change_mileage INTEGER
        )
    ''')
    conn.commit()
    conn.close()

# دالة إضافة سيارة جديدة
def add_vehicle_dialog(page, show_snackbar):
    dialog = None  # تعريف الحوار كمتغير عام في الدالة
    
    # حقول إدخال معلومات السيارة
    car_type_field = TextField(
        label="نوع السيارة",
        width=350,
        prefix_icon=Icons.DIRECTIONS_CAR,
        border_color=ThemeColors.PRIMARY
    )
    
    year_field = TextField(
        label="سنة الصنع",
        width=350,
        prefix_icon=Icons.CALENDAR_MONTH,
        keyboard_type=KeyboardType.NUMBER,
        border_color=ThemeColors.PRIMARY
    )
    
    mileage_field = TextField(
        label="الكيلومترات الحالية",
        width=350,
        prefix_icon=Icons.SPEED,
        keyboard_type=KeyboardType.NUMBER,
        border_color=ThemeColors.PRIMARY
    )

    def close_dialog(e):
        page.overlay.remove(dialog)
        page.update()

    # دالة حفظ معلومات السيارة
    def save_vehicle(e):
        try:
            # التحقق من صحة الإدخال
            if not car_type_field.value or not year_field.value or not mileage_field.value:
                show_snackbar(page, "يرجى ملء جميع الحقول", color=Colors.RED)
                return

            # إضافة السيارة إلى قاعدة البيانات
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vehicles 
                (car_type, manufacture_year, current_mileage, last_oil_change_date, next_oil_change_mileage) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                car_type_field.value, 
                int(year_field.value), 
                int(mileage_field.value),
                datetime.datetime.now().strftime("%Y-%m-%d"),
                int(mileage_field.value) + 5000  # افتراضي 5000 كم للتغيير القادم
            ))
            conn.commit()
            conn.close()

            # إغلاق الحوار وعرض رسالة نجاح
            page.overlay.remove(dialog)
            show_snackbar(page, "تمت إضافة السيارة بنجاح", color=ThemeColors.SUCCESS)
            page.update()

        except ValueError:
            show_snackbar(page, "الرجاء التأكد من صحة البيانات المدخلة", color=Colors.RED)
        except Exception as ex:
            show_snackbar(page, f"خطأ: {str(ex)}", color=Colors.RED)

    # إنشاء الحوار
    dialog = AlertDialog(
        title=Text("إضافة سيارة جديدة", weight=FontWeight.BOLD),
        content=Column([
            car_type_field,
            year_field,
            mileage_field
        ], width=400, height=300),
        actions=[
            TextButton("حفظ", on_click=save_vehicle),
            TextButton("إلغاء", on_click=close_dialog)
        ]
    )
    
    page.overlay.clear()  # مسح أي حوارات سابقة
    page.overlay.append(dialog)
    page.update()

def show_wheel_dialog(page, e):
    try:
        def close_dlg(e):
            dlg_modal.open = False
            page.update()

        def save_wheel_info(e):
            try:
                # حفظ معلومات الإطارات في قاعدة البيانات
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute('''INSERT INTO wheels 
                            (wheel_type, install_date, expected_life) 
                            VALUES (?, ?, ?)''',
                         (wheel_type.value, install_date.value, int(expected_life.value)))
                conn.commit()
                conn.close()
                
                logging.info(f"تم حفظ معلومات الإطارات: {wheel_type.value}")
                dlg_modal.open = False
                page.update()
                show_snackbar(page, "تم حفظ معلومات الإطارات بنجاح", ThemeColors.SUCCESS)
            except Exception as ex:
                show_snackbar(page, f"خطأ: {str(ex)}", ThemeColors.ERROR)

        wheel_type = TextField(
            label="نوع الإطارات",
            prefix_icon=Icons.TIRE_REPAIR,
            width=300,
            border_color=ThemeColors.PRIMARY
        )
        
        install_date = TextField(
            label="تاريخ التركيب",
            prefix_icon=Icons.CALENDAR_TODAY,
            width=300,
            border_color=ThemeColors.PRIMARY
        )
        
        expected_life = TextField(
            label="العمر المتوقع (كم)",
            prefix_icon=Icons.SPEED,
            width=300,
            keyboard_type=KeyboardType.NUMBER,
            border_color=ThemeColors.PRIMARY
        )

        dlg_modal = AlertDialog(
            modal=True,
            title=Text("إضافة معلومات الإطارات", weight=FontWeight.BOLD),
            content=Container(
                content=Column(
                    [
                        wheel_type,
                        install_date,
                        expected_life
                    ],
                    tight=True,
                    spacing=20,
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                ),
                padding=padding.all(20),
            ),
            actions=[
                TextButton("إلغاء", on_click=close_dlg),
                ElevatedButton(
                    "حفظ",
                    on_click=save_wheel_info,
                    style=ButtonStyle(bgcolor=ThemeColors.PRIMARY)
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

        page.overlay.append(dlg_modal)
        dlg_modal.open = True
        page.update()

    except Exception as e:
        show_error(page, e, "عرض نافذة الإطارات")

def show_snackbar(page, message, color=None):
    snack = SnackBar(
        content=Text(message, color=Colors.WHITE),
        bgcolor=color,
        duration=3000,
        action="حسناً"
    )
    page.overlay.clear()
    page.overlay.append(snack)
    snack.open = True
    page.update()

# دالة استرجاع معلومات السيارة
def get_vehicle_info():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vehicles ORDER BY id DESC LIMIT 1')
    vehicle = cursor.fetchone()
    conn.close()
    
    return vehicle if vehicle else None

# القيم الافتراضية لأنواع الزيوت
default_oil_types = {
    "زيت 10W-40": {
        "max_distance": 5000,
        "remaining_distance": 5000,
        "image": "",
        "liter_capacity": 4,
        "grade": "10W-40"
    },
    "زيت 5W-30": {
        "max_distance": 6000,
        "remaining_distance": 6000,
        "image": "",
        "liter_capacity": 5,
        "grade": "5W-30"
    }
}

def load_oil_types():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT * FROM oil_types")
    rows = c.fetchall()
    conn.close()
    
    if not rows:  # إذا كانت قاعدة البيانات فارغة، أضف القيم الافتراضية
        save_default_oil_types()
        return default_oil_types
    
    return {row[0]: {
        "max_distance": row[1],
        "remaining_distance": row[2],
        "image": row[3],
        "liter_capacity": row[4],
        "grade": row[5]
    } for row in rows}

def save_default_oil_types():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    for name, data in default_oil_types.items():
        c.execute("""INSERT OR REPLACE INTO oil_types 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (name, data["max_distance"], data["remaining_distance"],
                  data["image"], data["liter_capacity"], data["grade"]))
    conn.commit()
    conn.close()

class ThemeColors:
    PRIMARY = Colors.BLUE
    SECONDARY = Colors.AMBER
    BACKGROUND = Colors.BLUE_GREY_50
    SURFACE = Colors.WHITE
    ERROR = Colors.RED_600
    SUCCESS = Colors.GREEN_600
    WARNING = Colors.ORANGE_600

def log_error(error: Exception, context: str = "") -> str:
    """تسجيل الخطأ وإرجاع رسالة الخطأ"""
    error_msg = f"خطأ في {context}: {str(error)}"
    logging.error(error_msg)
    return error_msg

def show_error(page: Page, error: Exception, context: str = ""):
    """عرض رسالة الخطأ للمستخدم"""
    error_msg = log_error(error, context)
    show_snackbar(page, error_msg, ThemeColors.ERROR)

def save_oil_reading(vehicle_id: int, reading_date: str, reading_km: int, oil_type: str) -> bool:
    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('''INSERT INTO oil_readings 
                    (vehicle_id, reading_date, reading_km, oil_type) 
                    VALUES (?, ?, ?, ?)''',
                 (vehicle_id, reading_date, reading_km, oil_type))
        conn.commit()
        conn.close()
        logging.info(f"تم حفظ قراءة الزيت: {reading_km}km, النوع: {oil_type}")
        return True
    except Exception as e:
        log_error(e, "حفظ قراءة الزيت")
        return False

def get_vehicle_info() -> Optional[tuple]:
    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('SELECT * FROM vehicles LIMIT 1')
        vehicle = c.fetchone()
        conn.close()
        return vehicle
    except Exception as e:
        log_error(e, "جلب معلومات السيارة")
        return None

def update_oil_info(oil_type: str):
    try:
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('SELECT * FROM oil_types WHERE name = ?', (oil_type,))
        oil_info = c.fetchone()
        conn.close()
        
        if oil_info:
            logging.info(f"تم تحديث معلومات الزيت: {oil_type}")
            return oil_info
        return None
    except Exception as e:
        log_error(e, "تحديث معلومات الزيت")
        return None

def main(page: Page):
    try:
        logging.info("بدء تهيئة الصفحة الرئيسية")
        
        # إعدادات الصفحة الأساسية
        page.title = "ALKA Oil Tracker"
        page.window.width = 340
        page.window.height = 720
        page.theme_mode = ThemeMode.LIGHT
        page.bgcolor = ThemeColors.BACKGROUND
        page.padding = 20
        page.scroll = ScrollMode.AUTO
        page.fonts = {
            "Cairo": "https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;700&display=swap"
        }
        page.theme = Theme(font_family="Cairo")
        
        logging.info("تم تهيئة إعدادات الصفحة بنجاح")

    except Exception as e:
        error_msg = log_error(e, "التهيئة الرئيسية")
        page.add(Text(error_msg, color="red"))
        page.update()

    # تحميل بيانات الزيوت
    oil_types = load_oil_types()

    # تحسين بطاقة المعلومات الرئيسية
    def create_pro_card(content, color=ThemeColors.SURFACE, elevation=5):
        return Container(
            content=content,
            width=350,
            bgcolor=color,
            border_radius=15,
            padding=20,
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=Colors.BLACK26,
                offset=Offset(0, 5),
            ),
            border=border.all(1, Colors.BLACK12),
            animate_scale=animation.Animation(300, AnimationCurve.DECELERATE),
            on_hover=lambda e: setattr(e.control, 'scale', 1.02 if e.data == 'true' else 1)
        )

    # شريط التطبيق المحسن مع تأثيرات بصرية
    page.appbar = AppBar(
        leading=Container(
            content=Icon(Icons.OIL_BARREL, color=Colors.WHITE, size=30),
            padding=10,
            border_radius=10,
            gradient=LinearGradient(
                begin=alignment.top_left,
                end=alignment.bottom_right,
                colors=[ThemeColors.PRIMARY, Colors.BLUE_600]
            )
        ),
        title=Text(
            "ALKA Oil Tracker",
            size=22,
            weight=FontWeight.BOLD,
            color=Colors.WHITE
        ),
        center_title=True,
        bgcolor=ThemeColors.PRIMARY,
        color=Colors.WHITE,
        actions=[
            IconButton(
                icon=Icons.MORE_VERT,
                icon_color=Colors.WHITE,
                on_click=lambda e: show_app_menu(e)
            )
        ]
    )

    # مؤشر المسافة المتبقية المحسن
    progress = ProgressRing(
        width=250,
        height=250,
        stroke_width=20,
        color=ThemeColors.PRIMARY,
        bgcolor=Colors.BLUE_50,
        rotate=Rotate(angle=math.pi/2),  # تدوير المؤشر
    )
    
    progress_text = Text(
        "5000 كم متبقية",
        size=24,
        weight=FontWeight.BOLD,
        color=ThemeColors.PRIMARY,
        text_align=TextAlign.CENTER
    )

    # قائمة اختيار نوع الزيت المحسنة
    oil_dropdown = Dropdown(
        width=350,
        label="نوع الزيت",
        hint_text="اختر نوع الزيت",
        prefix_icon=Icons.OIL_BARREL,
        options=[dropdown.Option(key=name, text=name) for name in oil_types.keys()],
        border_color=ThemeColors.PRIMARY,
        focused_border_color=ThemeColors.PRIMARY,
        focused_bgcolor=Colors.BLUE_50,
        border_radius=15,
        content_padding=15,
        animate_opacity=300,
    )

    # زر إضافة قراءة محسن
    add_reading_btn = ElevatedButton(
        "إضافة قراءة جديدة",
        icon=Icons.ADD_ROAD,
        style=ButtonStyle(
            bgcolor=ThemeColors.PRIMARY,
            color=Colors.WHITE,
            padding=15,
            animation_duration=500,
            shape=RoundedRectangleBorder(radius=15),
            overlay_color=Colors.WHITE10,
        ),
        width=350,
        height=60,
        animate_scale=True,
    )

    # معلومات الزيت مع تصميم محسن
    oil_info = create_pro_card(
        Column([
            Row([
                Icon(Icons.INFO_OUTLINE, color=ThemeColors.PRIMARY),
                Text("معلومات الزيت", weight=FontWeight.BOLD, size=18),
            ], alignment=MainAxisAlignment.START),
            Divider(height=1, color=Colors.BLACK12),
            Container(height=10),
            Row([
                Text("السعة:", weight=FontWeight.W_500),
                Text("-- لتر", color=Colors.GREY_700),
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            Row([
                Text("الدرجة:", weight=FontWeight.W_500),
                Text("--", color=Colors.GREY_700),
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
        ], spacing=10)
    )

    def show_snackbar(page, message, color=None):
        snack_bar = SnackBar(
            content=Text(message, color=Colors.WHITE),
            bgcolor=color,
            duration=3000,  # 3 ثواني
            action="حسناً",
            action_color=Colors.WHITE
        )
        page.overlay.clear()  # مسح أي رسائل سابقة
        page.overlay.append(snack_bar)
        snack_bar.open = True
        page.update()

    def create_card(content, width=None, height=None, color=ThemeColors.SURFACE):
        return Container(
            content=content,
            width=width,
            height=height,
            bgcolor=color,
            border_radius=10,
            padding=15,
            shadow=BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=Colors.BLACK12,
                offset=Offset(0, 2),
            ),
        )

    # شريط التطبيق المحسن
    page.appbar = AppBar(
        leading=Icon(Icons.OIL_BARREL, color=ThemeColors.PRIMARY, size=30),
        title=Text(
            "ALKA",
            size=22,
            weight=FontWeight.BOLD,
            color=ThemeColors.PRIMARY
        ),
        center_title=True,
        bgcolor=ThemeColors.SURFACE,
        actions=[
            PopupMenuButton(
                items=[
                    PopupMenuItem(
                        text="إضافة نوع زيت",
                        icon=Icons.ADD_CIRCLE_OUTLINE,
                        on_click=lambda e: show_add_oil_type_dialog()
                    ),
                    PopupMenuItem(
                        text="تحديث العداد",
                        icon=Icons.SPEED,
                        on_click=lambda e: show_add_km_dialog()
                    ),
                    PopupMenuItem(
                        text="سجل التغييرات",
                        icon=Icons.HISTORY,
                        on_click=lambda e: show_history_dialog()
                    ),
                    PopupMenuItem(),
                    PopupMenuItem(
                        text="النسخ الاحتياطي",
                        icon=Icons.BACKUP,
                        on_click=lambda e: export_data()
                    ),
                ]
            )
        ]
    )

    # مؤشر المسافة المتبقية المحسن
    progress = ProgressRing(
        width=200,
        height=200,
        stroke_width=15,
        color=ThemeColors.PRIMARY,
        bgcolor=Colors.BLUE_50,
    )
    
    progress_text = Text(
        "5000 كم متبقية",
        size=20,
        weight=FontWeight.BOLD,
        color=ThemeColors.PRIMARY,
    )

    # قائمة اختيار نوع الزيت المحسنة
    oil_dropdown = Dropdown(
        width=300,
        label="نوع الزيت",
        hint_text="اختر نوع الزيت",
        prefix_icon=Icons.OIL_BARREL,
        options=[dropdown.Option(key=name, text=name) for name in oil_types.keys()],
        border_color=ThemeColors.PRIMARY,
        focused_border_color=ThemeColors.PRIMARY,
        focused_bgcolor=Colors.BLUE_50,
    )

    def update_oil_info(selected_oil):
        if selected_oil in oil_types:
            remaining = oil_types[selected_oil]["remaining_distance"]
            max_distance = oil_types[selected_oil]["max_distance"]
            progress.value = remaining / max_distance
            progress_text.value = f"{int(remaining)} كم متبقية"
            
            # إضافة معلومات إضافية
            oil_info.content.controls[1].value = f"السعة: {oil_types[selected_oil]['liter_capacity']} لتر"
            oil_info.content.controls[2].value = f"الدرجة: {oil_types[selected_oil]['grade']}"
            page.update()

    def on_dropdown_change(e):
        if e.data:
            update_oil_info(e.data)
            page.update()

    # معلومات الزيت
    oil_info = create_card(
        Column([
            Text("معلومات الزيت", weight=FontWeight.BOLD, size=16),
            Text("السعة: -- لتر"),
            Text("الدرجة: --"),
        ], spacing=10)
    )

    # زر إضافة قراءة محسن
    add_reading_btn = ElevatedButton(
        "إضافة قراءة جديدة",
        icon=Icons.ADD_ROAD,
        style=ButtonStyle(
            bgcolor=ThemeColors.PRIMARY,
            color=ThemeColors.SURFACE,
            padding=15,
            animation_duration=500,
            shape=RoundedRectangleBorder(radius=10),
        ),
        width=300,
    )

    def show_add_reading_dialog():
        # التأكد من وجود نوع الزيت
        current_oil_type = oil_dropdown.value if oil_dropdown.value else list(oil_types.keys())[0]
        
        reading_input = TextField(
            label="أدخل قراءة العداد (كم)",
            keyboard_type=KeyboardType.NUMBER,
            prefix_icon=Icons.SPEED,
            width=300,
            border_color=get_kilometer_input_color(current_oil_type, 0),
            on_change=lambda e: setattr(
                e.control, 
                'border_color', 
                get_kilometer_input_color(current_oil_type, float(e.control.value or 0))
            )
        )
        
        vehicle_type = Dropdown(
            label="نوع العجلة",
            width=300,
            options=[
                dropdown.Option("سيارة خاصة"),
                dropdown.Option("سيارة نقل"),
                dropdown.Option("دراجة نارية"),
                dropdown.Option("شاحنة"),
                dropdown.Option("باص"),
            ],
            prefix_icon=Icons.DIRECTIONS_CAR,
        )

        dialog = AlertDialog(
            title=Text("إضافة قراءة جديدة", weight=FontWeight.BOLD),
            content=Container(
                content=Column([
                    reading_input,
                    Container(height=10),
                    vehicle_type,
                ], spacing=10),
                padding=20,
            ),
            actions=[
                TextButton("إلغاء", on_click=lambda e: close_dialog(e, dialog)),
                ElevatedButton(
                    "حفظ",
                    on_click=lambda e: save_reading(e, dialog, reading_input, vehicle_type),
                    style=ButtonStyle(bgcolor=ThemeColors.PRIMARY),
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def close_dialog(e, dialog):
        dialog.open = False
        page.update()

    def save_reading(e, dialog, reading_input, vehicle_type):
        try:
            new_reading = float(reading_input.value)
            vehicle = vehicle_type.value if vehicle_type.value else "سيارة خاصة"
            
            if new_reading > 0:
                selected_oil = oil_dropdown.value
                if selected_oil:
                    # تحديث المسافة المتبقية
                    remaining = oil_types[selected_oil]["remaining_distance"] - new_reading
                    oil_types[selected_oil]["remaining_distance"] = max(0, remaining)

                    # حفظ التحديث في قاعدة البيانات
                    conn = sqlite3.connect(str(db_path))
                    c = conn.cursor()
                    
                    # تحديث المسافة المتبقية في جدول أنواع الزيوت
                    c.execute("""UPDATE oil_types 
                                SET remaining_distance = ?
                                WHERE name = ?""",
                             (max(0, remaining), selected_oil))
                    
                    # إضافة القراءة الجديدة في سجل التغييرات
                    c.execute("""INSERT INTO oil_changes 
                                (oil_type, change_date, kilometer_reading, vehicle_type) 
                                VALUES (?, ?, ?, ?)""",
                             (selected_oil, datetime.datetime.now().isoformat(), new_reading, vehicle))
                    
                    conn.commit()
                    conn.close()

                    # تحديث الواجهة
                    update_oil_info(selected_oil)
                    
                    # عرض رسالة نجاح مع المسافة المتبقية
                    remaining_msg = f"تم تسجيل {int(new_reading)} كم. متبقي {int(max(0, remaining))} كم"
                    show_snackbar(page, remaining_msg, ThemeColors.SUCCESS)
                    
                    # إظهار تنبيه إذا اقتربت المسافة المتبقية من الصفر
                    if remaining <= 500 and remaining > 0:
                        show_oil_change_alert(f"تنبيه! متبقي {int(remaining)} كم فقط حتى موعد تغيير الزيت")
                    elif remaining <= 0:
                        show_oil_change_alert("يجب تغيير الزيت الآن!")
                    
                    dialog.open = False
                    page.update()
                else:
                    show_snackbar(page, "الرجاء اختيار نوع الزيت أولاً", ThemeColors.ERROR)
        except ValueError:
            show_snackbar(page, "الرجاء إدخال رقم صحيح", ThemeColors.ERROR)
            page.update()

    def show_oil_change_alert(message="حان موعد تغيير الزيت!"):
        alert = AlertDialog(
            title=Text("تنبيه!", color=ThemeColors.ERROR, weight=FontWeight.BOLD),
            content=Text(message, size=18),
            actions=[
                ElevatedButton(
                    "حسناً",
                    style=ButtonStyle(bgcolor=ThemeColors.ERROR),
                    on_click=lambda e: close_dialog(e, alert),
                ),
                TextButton(
                    "تصفير العداد",
                    on_click=lambda e: reset_oil_counter(e, alert),
                )
            ],
        )
        page.overlay.append(alert)
        alert.open = True
        page.update()

    def reset_oil_counter(e, dialog):
        selected_oil = oil_dropdown.value
        if selected_oil:
            # إعادة تعيين المسافة المتبقية إلى القيمة القصوى
            max_distance = oil_types[selected_oil]["max_distance"]
            oil_types[selected_oil]["remaining_distance"] = max_distance

            # تحديث قاعدة البيانات
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute("""UPDATE oil_types 
                        SET remaining_distance = ?
                        WHERE name = ?""",
                     (max_distance, selected_oil))
            conn.commit()
            conn.close()

            # تحديث الواجهة
            update_oil_info(selected_oil)
            show_snackbar(page, "تم تصفير العداد بنجاح", ThemeColors.SUCCESS)
            
        dialog.open = False
        page.update()

    def show_add_oil_type_dialog():
        name_input = TextField(
            label="نوع الزيت",
            prefix_icon=Icons.OIL_BARREL,
            width=300,
        )
        max_distance_input = TextField(
            label="المسافة القصوى (كم)",
            keyboard_type=KeyboardType.NUMBER,
            prefix_icon=Icons.SPEED,
            width=300,
        )
        capacity_input = TextField(
            label="سعة الزيت (لتر)",
            keyboard_type=KeyboardType.NUMBER,
            prefix_icon=Icons.WATER_DROP,
            width=300,
        )
        grade_input = TextField(
            label="درجة الزيت (مثال: 5W-30)",
            prefix_icon=Icons.GRADE,
            width=300,
        )

        dialog = AlertDialog(
            title=Text("إضافة نوع زيت جديد", weight=FontWeight.BOLD),
            content=Container(
                content=Column([
                    name_input,
                    max_distance_input,
                    capacity_input,
                    grade_input
                ], spacing=10),
                padding=20,
            ),
            actions=[
                TextButton("إلغاء", on_click=lambda e: close_dialog(e, dialog)),
                ElevatedButton(
                    "حفظ",
                    on_click=lambda e: save_new_oil_type(e, dialog, name_input, max_distance_input, capacity_input, grade_input),
                    style=ButtonStyle(bgcolor=ThemeColors.PRIMARY),
                ),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def save_new_oil_type(e, dialog, name_input, max_distance_input, capacity_input, grade_input):
        try:
            name = name_input.value.strip()
            max_distance = float(max_distance_input.value)
            capacity = float(capacity_input.value)
            grade = grade_input.value.strip()

            if not name or not grade:
                show_snackbar(page, "الرجاء ملء جميع الحقول", ThemeColors.ERROR)
                return

            if max_distance <= 0 or capacity <= 0:
                show_snackbar(page, "يجب أن تكون القيم أكبر من صفر", ThemeColors.ERROR)
                return

            # حفظ في قاعدة البيانات
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            c.execute("""INSERT INTO oil_types 
                        (name, max_distance, remaining_distance, image, liter_capacity, grade)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (name, max_distance, max_distance, "", capacity, grade))
            conn.commit()
            conn.close()

            # تحديث القائمة المنسدلة
            oil_types[name] = {
                "max_distance": max_distance,
                "remaining_distance": max_distance,
                "image": "",
                "liter_capacity": capacity,
                "grade": grade
            }
            
            oil_dropdown.options = [dropdown.Option(key=name, text=name) for name in oil_types.keys()]
            oil_dropdown.value = name
            update_oil_info(name)
            
            show_snackbar(page, "تم إضافة نوع الزيت بنجاح", ThemeColors.SUCCESS)
            dialog.open = False
            page.update()

        except ValueError:
            show_snackbar(page, "الرجاء إدخال أرقام صحيحة", ThemeColors.ERROR)
            page.update()

    def show_history_dialog():
        # جلب سجل التغييرات من قاعدة البيانات
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("""SELECT oil_type, change_date, kilometer_reading, vehicle_type 
                    FROM oil_changes 
                    ORDER BY change_date DESC
                    LIMIT 50""")
        history = c.fetchall()
        conn.close()

        # إنشاء عنوان جذاب
        title_row = Row(
            controls=[
                Icon(Icons.HISTORY, size=30, color=ThemeColors.PRIMARY),
                Text("سجل تغييرات الزيت", size=24, weight=FontWeight.BOLD, color=ThemeColors.PRIMARY),
            ],
            alignment=MainAxisAlignment.CENTER,
        )

        # إنشاء بطاقات لكل تغيير
        history_cards = []
        for oil_type, change_date, km_reading, vehicle_type in history:
            # تحويل التاريخ إلى صيغة مقروءة
            date_obj = datetime.datetime.fromisoformat(change_date)
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")

            # إنشاء بطاقة لكل تغيير
            card = Container(
                content=Column([
                    # صف العنوان مع الأيقونة
                    Row([
                        Icon(Icons.LOCAL_GAS_STATION, color=ThemeColors.PRIMARY),
                        Text(oil_type, weight=FontWeight.BOLD, size=16),
                    ], alignment=MainAxisAlignment.START),
                    
                    Divider(height=1, color=Colors.BLACK12),
                    
                    # معلومات التغيير
                    Container(
                        content=Column([
                            Row([
                                Icon(Icons.DIRECTIONS_CAR, color=Colors.BLUE_GREY_400, size=20),
                                Container(width=10),
                                Text(vehicle_type if vehicle_type else "سيارة خاصة", 
                                     color=Colors.BLUE_GREY_700),
                            ]),
                            Row([
                                Icon(Icons.CALENDAR_TODAY, color=Colors.BLUE_GREY_400, size=20),
                                Container(width=10),
                                Text(formatted_date, color=Colors.BLUE_GREY_700),
                            ]),
                            Row([
                                Icon(Icons.SPEED, color=Colors.BLUE_GREY_400, size=20),
                                Container(width=10),
                                Text(f"{int(km_reading)} كم", color=Colors.BLUE_GREY_700),
                            ]),
                        ], spacing=10),
                        padding=padding.only(left=10, right=10, top=10, bottom=10),
                    ),
                ]),
                border_radius=10,
                border=border.all(1, Colors.BLACK12),
                margin=margin.only(bottom=10),
                padding=10,
                ink=True,
                bgcolor=Colors.WHITE,
                shadow=BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=Colors.BLACK12,
                    offset=Offset(0, 2),
                ),
            )
            
            # إضافة تأثير التحويم
            card.on_hover = lambda e: apply_hover_effect(e)
            history_cards.append(card)

        # إذا لم يكن هناك سجلات
        if not history:
            content = Container(
                content=Column([
                    Icon(Icons.HISTORY_TOGGLE_OFF, size=50, color=Colors.GREY_400),
                    Container(height=20),
                    Text("لا يوجد سجل للتغييرات حتى الآن",
                         size=16, color=Colors.GREY_700,
                         weight=FontWeight.W_500),
                ], 
                horizontal_alignment=CrossAxisAlignment.CENTER,
                alignment=MainAxisAlignment.CENTER),
                padding=20,
            )
        else:
            content = Column([
                title_row,
                Container(height=20),
                # إضافة البطاقات في عمود قابل للتمرير
                Container(
                    content=Column(history_cards),
                    padding=padding.only(right=20),
                    scrollable=True,
                    height=400,
                )
            ])

        dialog = AlertDialog(
            content=Container(
                content=content,
                padding=20,
                width=450,
            ),
            actions=[
                Container(
                    content=ElevatedButton(
                        "إغلاق",
                        style=ButtonStyle(
                            color=Colors.WHITE,
                            bgcolor=ThemeColors.PRIMARY,
                            padding=15,
                        ),
                        on_click=lambda e: close_dialog(e, dialog)
                    ),
                    alignment=alignment.center,
                )
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def apply_hover_effect(e):
        if e.data == "true":  # عند التحويم
            e.control.elevation = 5
            e.control.scale = 1.02
        else:  # عند إزالة التحويم
            e.control.elevation = 0
            e.control.scale = 1
        e.control.update()

    def export_data():
        try:
            export_path = data_dir / f"alka_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'oil_types': oil_types,
                    'changes': load_changes_history()
                }, f, ensure_ascii=False, indent=2)
            show_snackbar(page, "تم تصدير البيانات بنجاح", ThemeColors.SUCCESS)
        except Exception as e:
            show_snackbar(page, f"خطأ في تصدير البيانات: {str(e)}", ThemeColors.ERROR)

    def load_changes_history():
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT * FROM oil_changes ORDER BY change_date DESC")
        history = c.fetchall()
        conn.close()
        return history

    def update_ui(e=None):
        if oil_dropdown.value:
            update_oil_info(oil_dropdown.value)
        page.update()

    def get_kilometer_input_color(oil_type, km):
        try:
            # التحقق من وجود نوع الزيت في القاموس
            if oil_type not in oil_types:
                return ThemeColors.PRIMARY
            
            # جلب كمية الزيت المتبقية
            remaining_oil = oil_types[oil_type]["liter_capacity"]
            
            # تحديد اللون بناءً على كمية الزيت المتبقية
            if remaining_oil <= 1:  # أقل من لتر واحد
                return ThemeColors.ERROR  # أحمر (خطأ)
            elif remaining_oil <= 2:  # بين لتر وليترين
                return ThemeColors.WARNING  # برتقالي (تحذير)
            
            return ThemeColors.PRIMARY  # أزرق (الحالة الطبيعية)
        except Exception as e:
            print(f"خطأ في حساب لون العداد: {e}")
            return ThemeColors.PRIMARY

    oil_dropdown.on_change = on_dropdown_change
    add_reading_btn.on_click = lambda e: show_add_reading_dialog()
    page.on_resized = update_ui
    
    # إضافة وظيفة إضافة نوع زيت جديد وعرض السجل للقائمة
    page.appbar.actions[0].items[0].on_click = lambda e: show_add_oil_type_dialog()
    page.appbar.actions[0].items[2].on_click = lambda e: show_history_dialog()
    
    # تحديث أولي للواجهة
    if len(oil_types) > 0:
        first_oil = list(oil_types.keys())[0]
        oil_dropdown.value = first_oil
        update_oil_info(first_oil)
    page.update()

    # إنشاء قسم المعلومات الرئيسي مع تصميم محسن
    def create_dashboard_section():
        # استرجاع معلومات السيارة
        vehicle = get_vehicle_info()
        
        # بطاقة معلومات السيارة
        vehicle_card = create_pro_card(
            Column([
                Row([
                    Icon(Icons.DIRECTIONS_CAR, color=ThemeColors.PRIMARY, size=30),
                    Text("معلومات السيارة", weight=FontWeight.BOLD, size=18),
                    IconButton(
                        icon=Icons.ADD,
                        icon_color=ThemeColors.PRIMARY,
                        on_click=lambda e: add_vehicle_dialog(page, show_snackbar)
                    ),
                    IconButton(
                        icon=Icons.TIRE_REPAIR,
                        icon_color=ThemeColors.PRIMARY,
                        tooltip="إضافة معلومات الإطارات",
                        on_click=lambda e: show_wheel_dialog(page, e)
                    )
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Divider(height=1, color=Colors.BLACK12),
                Container(height=10),
                Row([
                    Text("نوع السيارة:", weight=FontWeight.W_500),
                    Text(vehicle[1] if vehicle else "لم يتم إضافة سيارة", color=Colors.GREY_700),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Row([
                    Text("سنة الصنع:", weight=FontWeight.W_500),
                    Text(str(vehicle[2]) if vehicle else "غير محدد", color=Colors.GREY_700),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Row([
                    Text("الكيلومترات الحالية:", weight=FontWeight.W_500),
                    Text(f"{vehicle[3]} كم" if vehicle else "غير محدد", color=Colors.GREY_700),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            ], spacing=10)
        )

        # بطاقة التنبيهات والإشعارات
        notifications_card = create_notifications_card()

        # زر المزيد من التفاصيل
        more_details_btn = TextButton(
            "المزيد من التفاصيل",
            icon=Icons.ARROW_FORWARD_IOS,
            style=ButtonStyle(
                color=ThemeColors.PRIMARY,
                side=BorderSide(width=1, color=ThemeColors.PRIMARY),
                shape=RoundedRectangleBorder(radius=10)
            ),
            on_click=lambda e: show_details_dialog(e)
        )

        # إنشاء العمود الرئيسي
        return Column([
            vehicle_card,
            Container(height=20),
            notifications_card,
            Container(height=20),
            more_details_btn
        ])

    def create_notifications_card():
        try:
            notifications = []
            
            # فحص الزيت
            if oil_dropdown.value:
                remaining = oil_types[oil_dropdown.value]["remaining_distance"]
                if remaining <= 500:
                    notifications.append(
                        Row([
                            Icon(Icons.WARNING_AMBER, color=Colors.ORANGE, size=20),
                            Text("تغيير الزيت قريباً", color=Colors.ORANGE),
                        ], spacing=10)
                    )
            
            # إضافة تنبيهات أخرى حسب الحاجة
            notifications.append(
                Row([
                    Icon(Icons.TIRE_REPAIR, color=Colors.RED, size=20),
                    Text("فحص الإطارات مطلوب", color=Colors.RED),
                ], spacing=10)
            )
            
            return create_pro_card(
                Column([
                    Row([
                        Icon(Icons.NOTIFICATIONS, color=Colors.ORANGE, size=30),
                        Text("التنبيهات", weight=FontWeight.BOLD, size=18, color=Colors.ORANGE)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    Divider(height=1, color=Colors.BLACK12),
                    Container(height=10),
                    *notifications
                ], spacing=10)
            )
        except Exception as e:
            print(f"خطأ في إنشاء بطاقة التنبيهات: {e}")
            return Container()  # إرجاع حاوية فارغة في حالة الخطأ

    def show_details_dialog(e):
        details_dialog = AlertDialog(
            title=Text("تفاصيل إضافية", weight=FontWeight.BOLD),
            content=Column([
                Text("معلومات مفصلة عن السيارة والصيانة"),
                Divider(height=1),
                DataTable(
                    columns=[
                        DataColumn(Text("النوع")),
                        DataColumn(Text("القيمة"))
                    ],
                    rows=[
                        DataRow([
                            DataCell(Text("آخر تغيير زيت")),
                            DataCell(Text("15/03/2023"))
                        ]),
                        DataRow([
                            DataCell(Text("نوع الزيت")),
                            DataCell(Text("10W-40"))
                        ]),
                        DataRow([
                            DataCell(Text("الكيلومترات القادمة للتغيير")),
                            DataCell(Text("5000 كم"))
                        ])
                    ]
                )
            ], width=400, height=300),
            actions=[
                TextButton("إغلاق", on_click=lambda e: close_dialog(e, details_dialog))
            ]
        )
        page.overlay.append(details_dialog)
        details_dialog.open = True
        page.update()

    # إضافة قسم المعلومات الرئيسي للصفحة
    page.add(
        Column([
            create_dashboard_section()
        ])
    )

    # تنظيم الصفحة
    page.add(
        Column([
            create_pro_card(
                Column([
                    Image(
                        src="https://cdn-icons-png.flaticon.com/512/3202/3202926.png",
                        width=100,
                        height=100,
                        fit=ImageFit.CONTAIN,
                        border_radius=50,
                    ),
                    Text(
                        "ALKA Oil Tracker",
                        size=24,
                        weight=FontWeight.BOLD,
                        color=ThemeColors.PRIMARY,
                    ),
                    Text(
                        "تتبع صيانة سيارتك باحترافية",
                        size=16,
                        color=Colors.GREY_700,
                    ),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10)
            ),
            Container(height=20),
            create_pro_card(
                Column([
                    progress,
                    progress_text,
                ], horizontal_alignment=CrossAxisAlignment.CENTER)
            ),
            Container(height=20),
            oil_dropdown,
            Container(height=10),
            oil_info,
            Container(height=20),
            add_reading_btn,
        ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10)
    )

    def show_add_wheel_dialog(page, e):
        wheel_type = TextField(
            label="نوع الإطارات",
            prefix_icon=Icons.TIRE_REPAIR,
            width=300,
            border_color=ThemeColors.PRIMARY
        )
        install_date = TextField(
            label="تاريخ التركيب",
            prefix_icon=Icons.CALENDAR_TODAY,
            width=300,
            border_color=ThemeColors.PRIMARY
        )
        expected_life = TextField(
            label="العمر المتوقع (كم)",
            prefix_icon=Icons.SPEED,
            width=300,
            keyboard_type=KeyboardType.NUMBER,
            border_color=ThemeColors.PRIMARY
        )

        def close_dlg(e):
            dlg.open = False
            page.update()

        def save_wheel(e):
            try:
                conn = sqlite3.connect(str(db_path))
                c = conn.cursor()
                c.execute('''INSERT INTO wheels (wheel_type, install_date, expected_life) 
                            VALUES (?, ?, ?)''', 
                         (wheel_type.value, install_date.value, int(expected_life.value)))
                conn.commit()
                conn.close()
                dlg.open = False
                page.update()
                show_snackbar(page, "تم حفظ معلومات الإطارات بنجاح", ThemeColors.SUCCESS)
            except Exception as ex:
                show_snackbar(page, f"خطأ: {str(ex)}", ThemeColors.ERROR)

        dlg = AlertDialog(
            modal=True,
            title=Text("إضافة معلومات الإطارات"),
            content=Container(
                content=Column(
                    [wheel_type, install_date, expected_life],
                    tight=True,
                    spacing=20,
                ),
                padding=padding.all(20),
            ),
            actions=[
                TextButton("إلغاء", on_click=close_dlg),
                ElevatedButton(
                    "حفظ",
                    on_click=save_wheel,
                    style=ButtonStyle(bgcolor=ThemeColors.PRIMARY)
                )
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    page.appbar.actions[0].items[1].on_click = lambda e: show_add_wheel_dialog(page, e)

if __name__ == "__main__":
    try:
        app(target=main)
    except Exception as e:
        logging.error(f"خطأ حرج في التطبيق: {str(e)}")