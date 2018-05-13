from loguru import notifier, logger
import pytest

@pytest.fixture
def notify(notifier_):
    notifier_.notify("Test directly")
    logger.start(notifier_.notify)
    logger.info("Test as sink")
    logger.stop()

def test_email():
    notify(notifier.email(to="dest@mail.com"))

def test_gmail():
    notify(notifier.gmail(to="dest@gmail.com"))

def test_gitter():
    notify(notifier.gitter(token="token", room_id="room"))

def test_hipchat():
    notify(notifier.hipchat(id="ABC", token="token", room="ABC", group="grp"))

def test_join():
    notify(notifier.join(apikey="ABC"))

def test_telegram():
    notify(notifier.telegram(chat_id="ABC", token="token"))

def test_pushover():
    notify(notifier.pushover(user="me", token="token"))

def test_simpleplush():
    notify(notifier.simplepush(key="ABC"))

def test_slack():
    notify(notifier.slack(webhook_url="http://some-url.slack.com"))

def test_pushbullet():
    notify(notifier.pushbullet(token="token"))

def test_zulip():
    notify(notifier.zulip(email="me@gmail.com", to="dest@gmail.com", api_key="ABC", server="http://test.com", subject="ok"))

def test_twilio():
    notify(notifier.twilio(from_="me", to="you", account_sid="ABC", auth_token="token"))

def test_pagerduty():
    notify(notifier.pagerduty(routing_key="ABC", event_action="trigger", source="src", severity="error"))

def test_mailgun():
    notify(notifier.mailgun(from_="me", to="you", api_key="ABC", domain="my.domain"))

def test_popcornnotify():
    notify(notifier.popcornnotify(api_key="ABC", recipients="recipes"))

def test_statuspage():
    notify(notifier.statuspage(api_key="ABC", page_id="1"))
