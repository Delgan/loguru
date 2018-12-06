import textwrap

import notifiers


class MetaNotifier:
    def __new__(cls):
        dict_ = {provider: notificator for provider, notificator in cls.generate_notifiers()}
        dict_["__doc__"] = cls.generate_doc(dict_)
        return type("Notifier", (), dict_)

    @staticmethod
    def generate_doc(notificators):
        bullets = "\n        ".join("- :meth:`~Notifier.%s()`" % n for n in sorted(notificators))
        doc = """
        An object to send notifications to different providers.

        Each method correspond to a notifications provider and return a |Notificator| parametrized
        according to the ``**kwargs`` passed. This |Notificator| should then be used through its
        |send| method.

        You should not instantiate a |Notifier| by yourself, use ``from loguru import notifier``
        instead.

        Notes
        -----
        The ``Notifier`` is just a tiny wrapper around the terrific `notifiers`_ library from
        `@liiight`_. Refer to `its documentation`_ for more information.

        Available |Notificator| are:

        %s

        Examples
        --------
        >>> notifier.gmail(to="dest@mail.com", host="your.server.com").send("Sending an e-mail.")

        >>> gmail = notifier.gmail(to="dest@gmail.com", username="you@gmail.com", password="abc123")
        >>> logger.start(gmail.send, level="ERROR")

        >>> notificator = notifier.slack(webhook_url="http://hooks.slack.com/xxx/yyy/zzz")
        >>> notificator.send("Sending Slack message...")
        >>> notificator.send("...from a Python app!")


        .. |dict| replace:: :class:`dict`
        .. |str| replace:: :class:`str`
        .. |Notificator| replace:: :class:`~loguru._notifier.Notificator`
        .. |send| replace:: :meth:`~loguru._notifier.Notificator.send()`
        .. |Notifier| replace:: :class:`~loguru._notifier.Notifier`
        .. _notifiers: https://github.com/notifiers/notifiers
        .. _@liiight: https://github.com/liiight
        .. _its documentation: https://notifiers.readthedocs.io/en/latest/
        """

        return textwrap.dedent(doc % bullets).lstrip("\n")

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

        notificator.__doc__ = MetaNotifier.make_docstring(provider)

        return notificator

    @staticmethod
    def make_docstring(provider):
        examples = {
            "email": """
                >>> notificator = notifier.email(
                ...     subject="Loguru notification",
                ...     to="dest@gmail.com",
                ...     username="user@gmail.com",
                ...     password="UserPassword",
                ...     host="smtp.gmail.com",
                ...     port=465,
                ...     ssl=True,
                ... )
            """,
            "gitter": """
                >>> notificator = notifier.gitter(
                ...     token="qdp4k378twu994ss3940c35x87jbul3p6l6e32f0",
                ...     room_id="1935i60h67870wi4p9q0yc81",
                ... )
            """,
            "gmail": """
                >>> notificator = notifier.gmail(
                ...     subject="Loguru notification",
                ...     to="dest@gmail.com",
                ...     username="user@gmail.com",
                ...     password="UserPassword",
                ... )
            """,
            "hipchat": """
                >>> notificator = notifier.hipchat(
                ...     token="2YotnFZFEjr1zCsicMWpAA",
                ...     room=7242,
                ...     group="namegroup",
                ...     id="6492f0a6-9fa0-48cd-a3dc-2b19a0036e99",
                ... )
            """,
            "join": """
                >>> notificator = notifier.join(
                ...     apikey="ar0pg953181y3lc75cl8n432x6j591ro",
                ... )
            """,
            "mailgun": """
                >>> notificator = notifier.mailgun(
                ...     subject="Loguru notification",
                ...     from_="user@gmail.com",
                ...     to="dest@gmail.com",
                ...     api_key="35a9tpnt1499o17eb14770iv2qm3775y-9258cqsa-u37b84u9",
                ...     domain="sandbox50v50d43fh261308q90f654p13364076.mailgun.org",
                ... )
            """,
            "popcornnotify": """
                >>> notificator = notifier.popcornnotify(
                ...     recipients="dest@gmail.com",
                ...     api_key="abc123456",
                ... )
            """,
            "pushbullet": """
                >>> notificator = notifier.pushbullet(
                ...     token="g.iwdgad0l12pu11p3mvzpada4v8fjadfh",
                ...     email="adrien.gabillaud@gmail.com",
                ... )
            """,
            "pushover": """
                >>> notificator = notifier.pushover(
                ...     token="chlnisznqlttipch5e5zu3gmxo5qp7",
                ...     user="srpzuyopidaythfq3u1tj2fmee3ke0",
                ... )
            """,
            "simplepush": """
                >>> notificator = notifier.simplepush(
                ...     key="HuxgBB",
                ... )
            """,
            "slack": """
                >>> notificator = notifier.slack(
                ...     webhook_url="https://hooks.slack.com/services/T5WDFU/RPB8IF/UG93Wp9mgcae1V",
                ... )
            """,
            "statuspage": """
                >>> notificator = notifier.statuspage(
                ...     api_key="fc8f938z-9250-2buh-18r2-852312zi1y42",
                ...     page_id="xc4tcptf84pv",
                ... )
            """,
            "telegram": """
                >>> notificator = notifier.telegram(
                ...     token="110201543:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw",
                ...     chat_id=94725518,
                ... )
            """,
            "twilio": """
                >>> notificator = notifier.twilio(
                ...     to="+15558675310",
                ...     account_sid="ACw7ly6d43h6752ld32o05c1p79u7br452",
                ...     auth_token="n780tw69475k8w1h3z996485rccn9i25",
                ... )
            """,
            "zulip": """
                >>> notificator = notifier.zulip(
                ...     email="user@zulip.com",
                ...     to="dest@zulip.com",
                ...     server="https://yourZulipDomain.zulipchat.com",
                ...     api_key="a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5",
                ... )
            """,
        }

        def find_required(dict_):
            for key, value in dict_.items():
                if key == "required" and isinstance(value, list):
                    yield from value
                elif isinstance(value, dict):
                    yield from find_required(value)
                elif isinstance(value, list):
                    for val in value:
                        if isinstance(val, dict):
                            yield from find_required(val)

        def parse_value(value):
            if "oneOf" in value:
                for val in value["oneOf"]:
                    new_val = value.copy()
                    new_val.update(val)
                    new_val.pop("oneOf")
                    yield from parse_value(new_val)
                return

            title = value.get("title", "")
            type_ = ""

            if "enum" in value:
                type_ = "{" + ", ".join("%r" % e for e in value["enum"]) + "}"
            elif "type" in value:
                type_ = value["type"]
                py_types = dict(
                    array="list",
                    object="dict",
                    integer="int",
                    string="str",
                    boolean="bool",
                    number="float",
                    null="None",
                )
                if isinstance(type_, str):
                    type_ = str(py_types.get(type_, type_))
                else:
                    type_ = " | ".join(str(py_types.get(t, t)) for t in type_)

            if "items" in value:
                for item_type, item_title, children in parse_value(value["items"]):
                    yield ("list of %s" % item_type, item_title or title, children)
                return

            if "properties" in value:
                children = parse_arguments(value)
            else:
                children = None

            yield (type_, title, children)

        def parse_arguments(object_):
            arguments = []
            for key, value in object_["properties"].items():
                for type_, title, children in parse_value(value):
                    argument = (key, type_, title, children)
                    arguments.append(argument)
            return arguments

        def format_argument(argument, *, root=True, default=None):
            key, type_, title, children = argument
            if root:
                docs = "{}{}\n    {}{}\n".format(
                    key,
                    " : %s" % type_ if type_ else "",
                    title,
                    " (default to `%r`)" % default if default is not None else "",
                )
            else:
                docs = "* **{}**{}{}\n\n".format(
                    key, " (`%s`)" % type_ if type_ else "", " - %s" % title if title else ""
                )

            if children:
                for child in children:
                    argument = format_argument(child, root=False)
                    docs += textwrap.indent(argument, "  ")

            return docs

        name = provider.name
        defaults = provider.defaults
        required = set(find_required(provider.required))

        docstring = "Return a |Notificator| to send messages using the |%s|_ backend.\n\n" % name
        params = ""
        other_params = ""

        arguments = parse_arguments(provider.schema)

        for argument in arguments:
            key, *_ = argument
            formatted = format_argument(argument, default=defaults.get(key))
            if key in required:
                params += formatted
            else:
                other_params += formatted

        if params:
            docstring += "Parameters\n"
            docstring += "----------\n"
            docstring += params.replace(r"_", r"\_") + "\n"

        if other_params:
            docstring += "Other Parameters\n"
            docstring += "----------------\n"
            docstring += other_params.replace(r"_", r"\_") + "\n"

        if name in examples:
            docstring += "Examples\n"
            docstring += "--------\n"
            docstring += textwrap.dedent(examples[name])
            docstring += ">>> notificator.send('Notify!')\n"

        docstring += "\n"
        docstring += ".. |%s| replace:: ``%s``\n" % (name, name.capitalize())
        docstring += ".. _%s: %s" % (name, provider.site_url)

        return docstring


Notifier = MetaNotifier()


class Notificator:
    """An object to send notifications to an internally configured provider.

    You should not instantiate a |Notificator| by yourself, use the ``Notifier`` to configure the
    requested notification provider instead.


    Attributes
    ----------
    provider : ``Provider``
        The provider object internally used to send notifications, created thanks to the
        ``notifiers`` library.
    parameters : |dict|
        The parameters used to configure the ``Provider``.
    """

    def __init__(self, provider, parameters):
        self.provider = provider
        self.parameters = parameters

    def send(self, message, **kwargs):
        """Send a notification through the internally configured provider.

        Parameters
        ----------
        message : |str|
            The message to send to the configured notifier.
        **kwargs
            Additional parameters to override or extend configured ones before sending the message.

        Returns
        -------
            The response from the ``notifiers`` provider.
        """
        params = {**self.parameters, **kwargs}
        return self.provider.notify(message=message, **params)
