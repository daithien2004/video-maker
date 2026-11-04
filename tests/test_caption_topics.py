import unittest

from videomaker.app import _script_hook
from videomaker.caption import detect_topic, make_options


class CaptionTopicTests(unittest.TestCase):
    def test_script_hook_is_the_first_beat_spoken_line(self):
        text = ("[mo-dau] Năm 1932, quân đội Úc đi đánh đàn chim. || NĂM *1932*,\n"
                "[chim] Đó là chim emu. || ĐÓ LÀ *CHIM EMU*.")
        self.assertEqual(_script_hook(text), "Năm 1932, quân đội Úc đi đánh đàn chim.")

    def test_regular_video_caption_opens_with_forced_hook(self):
        text = ("Một buổi sáng bình thường trên cây cầu.\n"
                "Sự thật là 19.860 viên đạn đã bắn vào đàn chim.")
        opt = make_options(text, hook="Một buổi sáng bình thường trên cây cầu.")[0]
        self.assertTrue(opt["caption"].startswith("Một buổi sáng bình thường trên cây cầu"))

    def test_similar_tone_less_phrases_do_not_match_pet_topic(self):
        text = "Vụ thử cũng gây tranh luận vì những lo ngại về môi trường."
        self.assertNotEqual(detect_topic(text), "Thú cưng")

    def test_single_incidental_pet_mention_does_not_set_the_topic(self):
        text = ("Một cây cầu treo dài thứ ba thế giới tự xoắn rồi gãy đôi.\n"
                "Xe tải bị lật trên cầu, tài xế phải bò ra ngoài.\n"
                "Một nhiếp ảnh gia đi lên cầu cứu con chó rồi quay lại.\n"
                "Cầu gãy vì quá mỏng trước cơn gió 40 dặm.\n"
                "Không ai chết trong vụ sập cầu này.")
        self.assertNotEqual(detect_topic(text), "Thú cưng")

    def test_regular_script_can_force_knowledge_topic(self):
        text = "Mục tiêu lần này là thử đầu đạn W71 cho tên lửa Spartan."
        option = make_options(text, "cannikin-1971", topic="Mẹo / kiến thức")[0]
        self.assertEqual(option["topic"], "Mẹo / kiến thức")
        self.assertNotIn("thú cưng", option["caption"].lower())
        self.assertNotIn("#thucung", option["caption"].lower())


if __name__ == "__main__":
    unittest.main()
