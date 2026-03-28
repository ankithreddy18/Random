import math
import sys


def getMinUpgradationTime(req1, t1, req2, t2):
    lcm = req1 * req2 // math.gcd(req1, req2)

    def feasible(T):
        # available slots for server 1 (not multiples of req1)
        avail1 = T - T // req1
        # available slots for server 2 (not multiples of req2)
        avail2 = T - T // req2
        # total non-wasted slots (not blocked for BOTH servers simultaneously)
        avail_both = T - T // lcm
        return avail1 >= t1 and avail2 >= t2 and avail_both >= t1 + t2

    lo = 1
    hi = 2 * (t1 + t2 + 1) * max(req1, req2)

    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1

    return lo


if __name__ == '__main__':
    req1 = int(input())
    t1 = int(input())
    req2 = int(input())
    t2 = int(input())
    print(getMinUpgradationTime(req1, t1, req2, t2))
