import uuid

from django.test import TestCase

from traces.base62 import base62_to_uuid, uuid_to_base62


class Base62RoundtripTest(TestCase):

    def test_roundtrip_random_uuids(self):
        for _ in range(20):
            u = uuid.uuid4()
            code = uuid_to_base62(u)
            self.assertEqual(base62_to_uuid(code), u)

    def test_roundtrip_zero_uuid(self):
        u = uuid.UUID(int=0)
        code = uuid_to_base62(u)
        self.assertEqual(base62_to_uuid(code), u)

    def test_roundtrip_max_uuid(self):
        u = uuid.UUID(int=(1 << 128) - 1)
        code = uuid_to_base62(u)
        self.assertEqual(base62_to_uuid(code), u)

    def test_code_length_at_most_22(self):
        for _ in range(50):
            code = uuid_to_base62(uuid.uuid4())
            self.assertLessEqual(len(code), 22)

    def test_invalid_character_raises(self):
        with self.assertRaises(ValueError):
            base62_to_uuid("abc!def")

    def test_specific_uuid(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        code = uuid_to_base62(u)
        self.assertEqual(base62_to_uuid(code), u)
