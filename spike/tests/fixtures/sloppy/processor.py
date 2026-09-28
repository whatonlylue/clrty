"""Deliberately sloppy fixture."""


def process(data, mode, flag, verbose, strict, extra, more):
    result = []
    if data:
        for row in data:
            if row is not None:
                if mode == "a":
                    if flag:
                        for k in row:
                            if k and verbose:
                                if strict and k > 1:
                                    result.append(k)
                                elif extra:
                                    result.append(-k)
                                else:
                                    if more:
                                        result.append(0)
                            elif strict:
                                result.append(1)
                    elif verbose:
                        result.append(2)
                elif mode == "b":
                    if flag and verbose:
                        result.append(3)
                    elif strict or extra:
                        result.append(4)
                    else:
                        try:
                            result.append(int(row))
                        except Exception:
                            pass
                elif mode == "c":
                    while extra:
                        if more and flag:
                            result.append(5)
                        extra = extra - 1
                else:
                    result.append(6)
    return result


def compute_alpha(values):
    total = 0
    count = 0
    for value in values:
        if value is not None:
            total = total + value
            count = count + 1
    if count == 0:
        return 0
    average = total / count
    return average


def compute_beta(numbers):
    total = 0
    count = 0
    for number in numbers:
        if number is not None:
            total = total + number
            count = count + 1
    if count == 0:
        return 0
    average = total / count
    return average


def compute_gamma(entries):
    total = 0
    count = 0
    for entry in entries:
        if entry is not None:
            total = total + entry
            count = count + 1
    if count == 0:
        return 0
    average = total / count
    return average


def wrap_alpha(values):
    return compute_alpha(values)


def wrap_beta(numbers):
    return compute_beta(numbers)


def wrap_gamma(entries):
    return compute_gamma(entries)
