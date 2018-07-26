import notifiers


class MetaNotifier:

    def __new__(cls):
        methods = {provider: notifier for provider, notifier in cls.generate_notifiers()}
        return type("NotifierFactory", (), methods)

    @staticmethod
    def generate_notifiers():
        providers = notifiers.core.all_providers()
        for provider in providers:
            notifier = MetaNotifier.make_notifier(provider)
            yield provider, notifier

    @staticmethod
    def make_notifier(provider_name):
        provider = notifiers.core.get_notifier(provider_name, strict=True)

        @classmethod
        def notifier(_cls, **kwargs):
            return Notifier(provider, kwargs)

        return notifier


NotifierFactory = MetaNotifier()


class Notifier:

    def __init__(self, provider, parameters):
        self.provider = provider
        self.parameters = parameters

    def notify(self, message):
        return self.provider.notify(message=message, **self.parameters)
