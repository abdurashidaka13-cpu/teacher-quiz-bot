from aiogram.fsm.state import State, StatesGroup


# 1. Tizimga Yangi Kirgandagi Kirish va Ro'yxatdan O'tish Holatlari
class AuthStates(StatesGroup):
    # Student login holatlari
    waiting_for_quiz_code = State()
    waiting_for_student_login = State()
    waiting_for_student_password = State()

    # Moderator ro'yxatdan o'tish (ariza) holatlari
    waiting_for_moderator_name = State()
    waiting_for_moderator_org = State()


# 2. Moderatorlik Kabineti va Test Yaratish Holatlari
class TeacherStates(StatesGroup):
    # Test yaratish
    waiting_for_quiz_title = State()
    waiting_for_quiz_description = State()

    # Hujjatlarni yuklash
    waiting_for_docx_file = State()  # Word variantlarini yuklash
    waiting_for_excel_file = State()  # Studentlar ro'yxatini yuklash

    # Imtihon boshlash arafasida davomiyligini kiritish holati
    waiting_for_start_duration = State()

    # Kutish zali va jonli nazorat
    waiting_lobby = State()
    quiz_active_monitor = State()

    # Adminga murojaat yuborish
    waiting_for_support_message = State()


# 3. Student Test Topshirish Holatlari
class StudentStates(StatesGroup):
    waiting_to_start = State()  # Kutish zalida turgan holati
    solving_quiz = State()  # Test savollarini yechayotgan holati


# 4. Super Admin Boshqaruv Holatlari
class AdminStates(StatesGroup):
    # Global e'lon tarqatish
    waiting_for_broadcast_text = State()

    # Qayta aloqa ticketiga javob yozish
    waiting_for_ticket_reply = State()

    # Tarif sozlamalarini tahrirlash
    waiting_for_demo_limit = State()
    waiting_for_onetime_price = State()
    waiting_for_onetime_limit = State()
    waiting_for_monthly_price = State()
    waiting_for_monthly_limit = State()
    
    # Obuna berish
    waiting_for_user_id = State()
    waiting_for_sub_type = State()

    # Yangi Mod buyrug'i holatlari
    waiting_for_mod_id = State()
    waiting_for_mod_time = State()
    waiting_for_mod_tickets = State()
    waiting_for_mod_students_limit = State()
