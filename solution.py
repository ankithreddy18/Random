import math
import sys
input = sys.stdin.readline


def getMinUpgradationTime(req1, t1, req2, t2):
    g = math.gcd(req1, req2)
    lcm = req1 // g * req2

    def feasible(T):
        mult_req1 = T // req1
        mult_req2 = T // req2
        mult_lcm = T // lcm

        # A: slots usable ONLY by server 1 (multiples of req2, not req1)
        A = mult_req2 - mult_lcm
        # B: slots usable ONLY by server 2 (multiples of req1, not req2)
        B = mult_req1 - mult_lcm
        # C: slots usable by EITHER server (not multiples of req1 or req2)
        C = T - mult_req1 - mult_req2 + mult_lcm

        return t1 <= A + C and t2 <= B + C and t1 + t2 <= A + B + C

    lo = 1
    hi = 2 * (t1 + t2 + 1) * max(req1, req2)

    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(mid):
            hi = mid
        else:
            lo = mid + 1

    return lo


def main():
    req1 = int(input())
    t1 = int(input())
    req2 = int(input())
    t2 = int(input())
    print(getMinUpgradationTime(req1, t1, req2, t2))


main()
