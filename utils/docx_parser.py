import io
from typing import Optional
import docx
from PIL import Image

# Word XML namespaces
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def extract_image_from_cell(cell, document) -> Optional[bytes]:
    """
    Word jadval katagi (cell) ichidagi birinchi rasmni aniqlaydi va yuklab oladi.
    Agar rasm bo'lsa, uni siqib, WebP formatda qaytaradi.
    """
    try:
        # Katak ichidagi barcha blip (tasvirlar) elementlarini izlash
        blips = cell._element.xpath(".//a:blip")
        if not blips:
            return None

        # Birinchi tasvirning relationship ID sini olish
        r_id = blips[0].get(f"{{{NS_R}}}embed")
        if not r_id:
            return None

        # Hujjat qismlaridan rasmni yuklash
        if r_id in document.part.related_parts:
            image_part = document.part.related_parts[r_id]
            image_bytes = image_part.blob

            # Rasmni Pillow orqali yuklash va siqish
            return compress_image(image_bytes)
    except Exception as e:
        print(f"Rasm ajratib olishda xatolik: {e}")
    return None


def compress_image(image_bytes: bytes) -> bytes:
    """
    Rasmni Pillow orqali yuklab, kengligini 800px dan oshirmaydi,
    WebP formatiga o'tkazadi va 70% sifat bilan siqadi.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # PNG/GIF lar RGBA yoki P formatda bo'lsa, RGB formatiga o'tkazish
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Kenglikni 800px ga moslab kichraytirish (aspect ratio saqlanadi)
        max_width = 800
        width, height = img.size
        if width > max_width:
            ratio = max_width / float(width)
            new_height = int(float(height) * float(ratio))
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # WebP formatda 70% sifat bilan saqlash
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="WEBP", quality=70)
        return output_buffer.getvalue()
    except Exception as e:
        print(f"Rasmni siqishda xatolik: {e}")
        return image_bytes  # Muammo bo'lsa, asl rasmni qaytarish


def parse_docx_questions(file_stream) -> dict:
    """
    Word (.docx) faylidan 6 ustunli jadvallarni o'qib, savollar ro'yxatini qaytaradi.
    Agar xatolik bo'lsa, 'error' kaliti bilan matn qaytaradi.
    Natija format: {
        'questions': [
            {'question_text': str, 'image_data': bytes/None, 'correct_answer': str, 'distractors': [str, str, str]}
        ]
    }
    """
    try:
        document = docx.Document(file_stream)
    except Exception as e:
        return {"error": f"Faylni o'qib bo'lmadi. Yaroqli Word hujjat (.docx) ekanligini tekshiring: {e}"}

    parsed_questions = []
    errors = []
    has_valid_table = False

    # Hujjatdagi barcha jadvallarni tekshirish
    for table_idx, table in enumerate(document.tables):
        # Ustunlar soni aynan 6 ta bo'lgan jadvallarnigina o'qiymiz
        if len(table.columns) != 6:
            continue

        has_valid_table = True

        # Sarlavha qatorini tashlab ketish uchun birinchi qatorni o'tkazamiz
        # Sarlavhaga to'g'ri kelmasligini T/r ustunidan tekshiramiz
        for row_idx, row in enumerate(table.rows):
            cells = row.cells
            tr_text = cells[0].text.strip()

            # Agar bu birinchi sarlavha qatori bo'lsa (T/r raqam bo'lmasa), o'tkazib yuboramiz
            if row_idx == 0 and not tr_text.isdigit():
                continue

            # Agar qator butunlay bo'sh bo'lsa, o'tkazib yuboramiz
            all_empty = all(not cell.text.strip() for cell in cells)
            if all_empty:
                continue

            # Savol raqami tahlili
            q_num = tr_text if tr_text.isdigit() else f"{row_idx + 1}"

            row_errors = []

            # 1. Savol katagini tekshirish (matn yoki rasm bo'lishi shart)
            question_text = cells[1].text.strip()
            image_data = extract_image_from_cell(cells[1], document)

            if not question_text and not image_data:
                row_errors.append(f"{q_num}-savol: Savol matni ham, rasm ham mavjud emas.")

            # 2. To'g'ri javob tekshiruvi (3-ustun)
            correct_answer = cells[2].text.strip()
            if not correct_answer:
                row_errors.append(f"{q_num}-savol: To'g'ri javob katagi bo'sh qolgan.")

            # 3. Noto'g'ri javoblar tekshiruvi (4, 5, 6-ustunlar)
            distractors = []
            for d_idx in range(3, 6):
                dist_val = cells[d_idx].text.strip()
                if not dist_val:
                    row_errors.append(f"{q_num}-savol: Noto'g'ri javob {d_idx - 2} katagi bo'sh qolgan.")
                else:
                    distractors.append(dist_val)

            # Agar xatoliklar bo'lmasa, savolni qo'shamiz, aks holda xatoliklarga qo'shamiz
            if row_errors:
                errors.extend(row_errors)
            else:
                parsed_questions.append({
                    "question_text": question_text,
                    "image_data": image_data,
                    "correct_answer": correct_answer,
                    "distractors": distractors,
                })

    if not has_valid_table:
        return {"error": "Hujjatda 6 ta ustunli jadval topilmadi! Iltimos, shablon formatini tekshiring."}

    if errors:
        error_msg = "Yuklangan Word faylida quyidagi xatoliklar aniqlandi:\n" + "\n".join(errors)
        return {"error": error_msg}

    if not parsed_questions:
        return {"error": "Jadvalda hech qanday test savollari topilmadi!"}

    return {"questions": parsed_questions}
