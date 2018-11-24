import notifiers


class MetaNotifier:
    def __new__(cls):
        dict_ = {provider: notificator for provider, notificator in cls.generate_notifiers()}
        return type("Notifier", (), dict_)

    @staticmethod
    def generate_notifiers():
        providers = notifiers.core.all_providers()

        for provider_name in providers:
            provider = notifiers.core.get_notifier(provider_name, strict=True)
            method = MetaNotifier.make_method(provider)
            yield provider_name, method

    @staticmethod
    def make_method(provider):
        def notificator(self, **kwargs):
            return Notificator(provider, kwargs)

        return notificator


Notifier = MetaNotifier()


class Notificator:
    def __init__(self, provider, parameters):
        self.provider = provider
        self.parameters = parameters

    def send(self, message):
        return self.provider.notify(message=message, **self.parameters)
