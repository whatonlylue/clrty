"""Small, flat inventory helpers."""


def total_price(items):
    return sum(item["price"] * item["qty"] for item in items)


def in_stock(items):
    return [item for item in items if item["qty"] > 0]


def names(items):
    return sorted(item["name"] for item in items)


def apply_discount(price, rate):
    if rate < 0 or rate > 1:
        raise ValueError("rate out of range")
    return price * (1 - rate)


def summarize(items):
    stocked = in_stock(items)
    return {
        "count": len(stocked),
        "total": total_price(stocked),
        "names": names(stocked),
    }


def cheapest(items):
    return min(items, key=lambda item: item["price"])


def restock(items, name, amount):
    for item in items:
        if item["name"] == name:
            item["qty"] += amount
            return item
    raise KeyError(name)
