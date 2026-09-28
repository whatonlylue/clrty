from types import Choice


def pick(value):
    return Choice(["a", "b"]).convert(value)


def main():
    print(pick("a"))
    print(pick("b"))
