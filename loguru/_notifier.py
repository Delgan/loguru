from notifiers import providers


class Notifier:

    def __init__(self, provider, parameters):
        self.provider = provider
        self.parameters = parameters

    def notify(self, message):
        return self.provider.notify(message=message, **self.parameters)

    @classmethod
    def email(_cls, *, to, **kwargs):
        return _cls(providers.email.SMTP(), dict(to=to, **kwargs))

    @classmethod
    def gmail(_cls, *, to, **kwargs):
        return _cls(providers.gmail.Gmail(), dict(to=to, **kwargs))

    @classmethod
    def gitter(_cls, *, token, room_id, **kwargs):
        return _cls(providers.gitter.Gitter(), dict(token=token, room_id=room_id, **kwargs))

    @classmethod
    def hipchat(_cls, *, id, token, **kwargs):
        return _cls(providers.hipchat.HipChat(), dict(token=token, id=id, **kwargs))

    @classmethod
    def join(_cls, *, apikey, **kwargs):
        return _cls(providers.join.Join(), dict(apikey=apikey, **kwargs))

    @classmethod
    def telegram(_cls, *, chat_id, token, **kwargs):
        return _cls(providers.telegram.Telegram(), dict(chat_id=chat_id, token=token, **kwargs))

    @classmethod
    def pushover(_cls, *, user, token, **kwargs):
        return _cls(providers.pushover.Pushover(), dict(user=user, token=token, **kwargs))

    @classmethod
    def simplepush(_cls, *, key, **kwargs):
        return _cls(providers.simplepush.SimplePush(), dict(key=key, **kwargs))

    @classmethod
    def slack(_cls, *, webhook_url, **kwargs):
        return _cls(providers.slack.Slack(), dict(webhook_url=webhook_url, **kwargs))

    @classmethod
    def pushbullet(_cls, *, token, **kwargs):
        return _cls(providers.pushbullet.Pushbullet(), dict(token=token, **kwargs))

    @classmethod
    def zulip(_cls, *, email, to, api_key, **kwargs):
        return _cls(providers.zulip.Zulip(), dict(email=email, api_key=api_key, to=to, **kwargs))

    @classmethod
    def twilio(_cls, *, from_, to, account_sid, auth_token, **kwargs):
        return _cls(providers.twilio.Twilio(), dict(from_=from_, to=to, account_sid=account_sid,
                                                    auth_token=auth_token, **kwargs))

    @classmethod
    def pagerduty(_cls, *, routing_key, event_action, source, severity, **kwargs):
        return _cls(providers.pagerduty.PagerDuty(), dict(routing_key=routing_key, severity=severity,
                                                          event_action=event_action, source=source,
                                                          **kwargs))

    @classmethod
    def mailgun(_cls, *, from_, to, api_key, domain, **kwargs):
        return _cls(providers.mailgun.MailGun(), dict(api_key=api_key, to=to, domain=domain,
                                                      from_=from_, **kwargs))

    @classmethod
    def popcornnotify(_cls, *, api_key, recipients, **kwargs):
        return _cls(providers.popcornnotify.PopcornNotify(), dict(api_key=api_key,
                                                                  recipients=recipients, **kwargs))

    @classmethod
    def statuspage(_cls, *, api_key, page_id, **kwargs):
        return _cls(providers.statuspage.Statuspage(), dict(api_key=api_key, page_id=page_id,
                                                            **kwargs))
