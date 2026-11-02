import unittest

from videomaker.caption import detect_topic, make_options


class CaptionTopicTests(unittest.TestCase):
    def test_similar_tone_less_phrases_do_not_match_pet_topic(self):
        text = "Vụ thử cũng gây tranh luận vì những lo ngại về môi trường."
        self.assertNotEqual(detect_topic(text), "Thú cưng")

    def test_regular_script_can_force_knowledge_topic(self):
        text = "Mục tiêu lần này là thử đầu đạn W71 cho tên lửa Spartan."
        option = make_options(text, "cannikin-1971", topic="Mẹo / kiến thức")[0]
        self.assertEqual(option["topic"], "Mẹo / kiến thức")
        self.assertNotIn("thú cưng", option["caption"].lower())
        self.assertNotIn("#thucung", option["caption"].lower())


if __name__ == "__main__":
    unittest.main()
