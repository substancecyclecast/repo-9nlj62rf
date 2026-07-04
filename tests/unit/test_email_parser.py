from email.message import EmailMessage

from snabagent.email_service.parser import parse_inbound_email


def test_parse_basic_email():
    msg = EmailMessage()
    msg["From"] = "supplier@example.ru"
    msg["To"] = "lot+abcd1234@demo.snabagent.ru"
    msg["Subject"] = "[SnabAgent #LOT-abcd1234] КП"
    msg["Message-ID"] = "<test-1@example.ru>"
    msg.set_content("Текст КП\nЦена: 100000 RUB\nСрок: 30 дн")
    parsed = parse_inbound_email(bytes(msg))
    assert "lot+abcd1234@demo.snabagent.ru" in parsed["to"]
    assert "#LOT-abcd1234" in parsed["subject"]
    assert "100000" in parsed["body_text"]
