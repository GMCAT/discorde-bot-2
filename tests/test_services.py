import unittest
from unittest.mock import patch

from bot.contracts import ServiceRequest
from bot.services import AdminService, ContactService


def request(text, user="admin"):
    return ServiceRequest("discord", "channel", user, text)


class ServiceTests(unittest.TestCase):
    @patch("bot.services.db.search_contacts")
    def test_contact_search(self, search):
        search.return_value = (None, [{"name": "นายเอ", "phone": "0812345678", "contact_role": "PRIMARY", "contact_type": "GENERAL"}], False)
        response = ContactService().handle(request("ติดต่อ นายเอ"))
        self.assertIn("0812345678", response.message)

    def test_admin_is_denied_by_default(self):
        response = AdminService(set()).handle(request("ตรวจฐานข้อมูล"))
        self.assertEqual(response.error_code, "FORBIDDEN")

    @patch("bot.services.db.add_contact", return_value=42)
    def test_admin_can_add_contact(self, add_contact):
        service = AdminService({"admin"})
        response = service.handle(request("เพิ่มติดต่อ\nชื่อ: นายเอ\nหน่วยงาน: ไอที"))
        self.assertTrue(response.success)
        self.assertIn("ID: 42", response.message)
        self.assertEqual(add_contact.call_args.args[0]["organization"], "ไอที")


if __name__ == "__main__":
    unittest.main()

