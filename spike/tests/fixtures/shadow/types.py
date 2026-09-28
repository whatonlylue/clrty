"""Named like the stdlib module on purpose: tools must not import it instead of `types`."""


class Choice:
    def __init__(self, options):
        self.options = list(options)

    def convert(self, value):
        if value not in self.options:
            raise ValueError(value)
        return value
