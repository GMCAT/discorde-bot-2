from bot import db
from bot.contracts import ServiceRequest, ServiceResponse


TYPE_LABELS = {
    "GENERAL": "ทั่วไป", "EMERGENCY": "ฉุกเฉิน", "MAINTENANCE": "ซ่อมบำรุง",
    "IT_SUPPORT": "IT", "LAB_SUPPORT": "แล็บ", "VENDOR": "ผู้ขาย/ผู้จำหน่าย", "OTHER": "อื่น ๆ",
}
TYPE_VALUES = {label: value for value, label in TYPE_LABELS.items()}
ROLE_VALUES = {"หลัก": "PRIMARY", "สำรอง": "SECONDARY"}


def format_contact(contact: dict, include_organization: bool = True) -> list[str]:
    role = "หลัก" if contact.get("contact_role") == "PRIMARY" else "สำรอง"
    heading = f"👤 {contact['name']}"
    if contact.get("position"):
        heading += f" ({contact['position']})"
    lines = [heading]
    if include_organization and contact.get("organization_name"):
        lines.append(f"   🏢 {contact['organization_name']}")
    available = " · เปิด 24 ชม." if contact.get("is_available_24h") else ""
    lines.append(f"   🏷️ {TYPE_LABELS.get(contact.get('contact_type'), contact.get('contact_type', ''))} · {role}{available}")
    for key, icon in (("phone", "📞"), ("email", "✉️"), ("line_id", "💬 Line:"), ("note", "📝")):
        if contact.get(key):
            lines.append(f"   {icon} {contact[key]}")
    return lines


class ContactService:
    name = "contacts"

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        text = request.text.strip()
        if text == "ติดต่อฉุกเฉิน":
            contacts = db.list_emergency_contacts()
            if not contacts:
                return ServiceResponse(True, self.name, "ยังไม่มีข้อมูลผู้ติดต่อฉุกเฉินในระบบครับ")
            lines = [f"🚨 ผู้ติดต่อฉุกเฉิน ({len(contacts)} รายการ)"]
            for contact in contacts:
                lines.extend(format_contact(contact))
            return ServiceResponse(True, self.name, "\n".join(lines))

        query = text.split(" ", 1)[1].strip()
        organization, contacts, fuzzy = db.search_contacts(query)
        if not contacts:
            return ServiceResponse(True, self.name, f'ไม่พบข้อมูลติดต่อของ "{query}" ครับ')
        lines = []
        if fuzzy:
            guess = organization or contacts[0]["name"]
            lines.append(f'ไม่พบ "{query}" ตรง ๆ ครับ เข้าใจว่าหมายถึง "{guess}" ใช่ไหม 🤔')
        if organization:
            lines.append(f"🏢 {organization} — ผู้ติดต่อทั้งหมด ({len(contacts)} คน)")
        elif not fuzzy:
            lines.append(f'📇 พบ {len(contacts)} รายการสำหรับ "{query}"')
        for contact in contacts:
            lines.extend(format_contact(contact))
        return ServiceResponse(True, self.name, "\n".join(lines))


class AdminService:
    name = "admin"

    def __init__(self, admin_ids: set[str]):
        self.admin_ids = admin_ids

    def handle(self, request: ServiceRequest) -> ServiceResponse:
        if not request.user_id or request.user_id not in self.admin_ids:
            return ServiceResponse(False, self.name, "คำสั่งนี้ใช้ได้เฉพาะแอดมินครับ", "FORBIDDEN")
        text = request.text.strip()
        if text.startswith("เพิ่มติดต่อ"):
            return self._add(text)
        if text == "ข้อมูลทั้งหมด":
            contacts = db.dump_all()
            if not contacts:
                return ServiceResponse(True, self.name, "ฐานข้อมูลยังไม่มีผู้ติดต่อครับ")
            lines = [f"📦 ข้อมูลทั้งหมด ({len(contacts)} รายการ)"]
            for contact in contacts:
                lines.extend(format_contact(contact))
            return ServiceResponse(True, self.name, "\n".join(lines))
        status = db.database_status()
        return ServiceResponse(True, self.name, f"✅ เชื่อมต่อฐานข้อมูลสำเร็จ\nหน่วยงาน: {status['organization_count']} รายการ\nผู้ติดต่อ: {status['contact_count']} รายการ")

    def _add(self, text: str) -> ServiceResponse:
        raw = {}
        labels = {
            "ชื่อ": "name", "หน่วยงาน": "organization", "ตัวย่อหน่วยงาน": "organization_code",
            "ตำแหน่ง": "position", "เบอร์": "phone", "อีเมล": "email", "ไลน์": "line_id",
            "ประเภท": "contact_type", "บทบาท": "contact_role", "24ชม": "is_available_24h", "หมายเหตุ": "note",
        }
        for line in text.splitlines()[1:]:
            label, separator, value = line.partition(":")
            if separator and label.strip() in labels and value.strip() not in {"", "-"}:
                raw[labels[label.strip()]] = value.strip()
        if not raw.get("name") or not raw.get("organization"):
            return ServiceResponse(False, self.name, "⚠️ ต้องระบุชื่อและหน่วยงานครับ")
        raw["contact_type"] = TYPE_VALUES.get(raw.get("contact_type", "ทั่วไป"), raw.get("contact_type", "GENERAL").upper())
        raw["contact_role"] = ROLE_VALUES.get(raw.get("contact_role", "สำรอง"), raw.get("contact_role", "SECONDARY").upper())
        if raw["contact_type"] not in TYPE_LABELS:
            return ServiceResponse(False, self.name, "⚠️ ประเภทผู้ติดต่อไม่ถูกต้องครับ")
        if raw["contact_role"] not in {"PRIMARY", "SECONDARY"}:
            return ServiceResponse(False, self.name, "⚠️ บทบาทต้องเป็น หลัก หรือ สำรอง")
        raw["is_available_24h"] = raw.get("is_available_24h", "ไม่").lower() in {"ใช่", "yes", "true", "1"}
        contact_id = db.add_contact(raw)
        return ServiceResponse(True, self.name, f'✅ เพิ่ม "{raw["name"]}" ({raw["organization"]}) แล้วครับ (ID: {contact_id})')

