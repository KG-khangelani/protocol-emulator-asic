"""Two-node passive-jig observability calculation. All times below use ns."""
from dataclasses import dataclass
import json
import math


@dataclass(frozen=True)
class Rig:
    ct_pf: float
    cb_pf: float
    supply_v: float = 3.3
    sense_ohm: float = 470
    bias_ohm: float = 1000
    output_ohm: float = 200

    def steady(self, output, bias):
        current = (output-bias)/(self.sense_ohm+self.bias_ohm+self.output_ohm)
        return output-current*self.output_ohm, bias+current*self.bias_ohm

    def matrix(self):
        # omega*pF is ps. Multiplying by 1000 yields inverse ns.
        a = 1000/(self.sense_ohm*self.ct_pf)
        b = 1000/(self.sense_ohm*self.cb_pf)
        c = 1000/(self.bias_ohm*self.cb_pf)
        return (-a, a, b, -b-c)

    def released(self, time, output, bias):
        target, bus = (v-bias for v in self.steady(output,bias))
        a,b,c,d = self.matrix()
        root = math.sqrt((a-d)**2+4*b*c)
        first, second = ((a+d+root)/2, (a+d-root)/2)
        def node(v, dv):
            w = (dv-second*v)/(first-second)
            return bias + w*math.exp(first*time)+(v-w)*math.exp(second*time)
        return node(target,a*target+b*bus), node(bus,c*target+d*bus)

    def current_ma(self, state):
        return 1000*(state[0]-state[1])/self.sense_ohm


def cross(test):
    lo,hi = 0,5000
    if test(lo):
        return 0.0
    if not test(hi):
        raise ValueError("crossing out of range")
    for _ in range(45):
        mid = (lo+hi)/2
        if test(mid):
            hi = mid
        else:
            lo = mid
    return hi


def rk_check(rig, start, bias, released):
    # Independent fourth-order integrator directly applies the two-node KCL.
    def deriv(v):
        leaving = (v[0]-v[1])/rig.sense_ohm
        drv = 0.0 if released else (start-v[0])/rig.output_ohm
        return (1000*(drv-leaving)/rig.ct_pf, 1000*(leaving+(bias-v[1])/rig.bias_ohm)/rig.cb_pf)
    def plus(v, k, scale):
        return tuple(a+scale*b for a,b in zip(v,k))
    state = rig.steady(start,bias)
    original = state
    worst = 0
    dt = .1
    for i in range(1600):
        k1 = deriv(state)
        k2 = deriv(plus(state,k1,dt/2))
        k3 = deriv(plus(state,k2,dt/2))
        k4 = deriv(plus(state,k3,dt))
        state = tuple(v+dt*(a+2*b+2*c+d)/6 for v,a,b,c,d in zip(state,k1,k2,k3,k4))
        expected = rig.released((i+1)*dt,start,bias) if released else original
        worst = max(worst,*(abs(v-w) for v,w in zip(state,expected)))
    return worst


def calculate():
    cases = []
    for ct,cb in ((12,12),(24,40),(60,60),(120,120)):
        rig = Rig(ct,cb)
        for output,bias in ((3.3,0),(0,3.3)):
            def current(t):
                return abs(rig.current_ma(rig.released(t,output,bias)))
            def ready(t,target_voltage):
                v = rig.released(t,output,bias)[1]
                return v>=target_voltage if bias else v<=target_voltage
            release_guard = cross(lambda t:current(t)<=.25)
            pico = cross(lambda t:ready(t,2.0 if bias else .8))
            microchip = cross(lambda t:ready(t,.7*rig.supply_v if bias else .3*rig.supply_v))
            current_by_imposed = {}
            for delay in (0,80,160,1563):
                observed = current(max(0,160-delay))
                current_by_imposed[str(delay)] = round(observed,6)
            cases.append({"ct_cb_pf":[ct,cb],"initial_drive_and_bias_v":[output,bias],
                          "steady_opposed_current_ma":round(current(0),6),
                          "after_release_i_abs_lo_0p25ma_ns":round(release_guard,3),
                          "rp2040_guaranteed_bias_level_ns":round(pico,3),
                          "microchip_guaranteed_bias_level_ns":round(microchip,3),
                          "current_ma_at_t160_by_release_delay_ns":current_by_imposed})
    rig = Rig(24,40)
    err = max(rk_check(rig,drive,bias,release) for drive,bias in ((3.3,0),(0,3.3)) for release in (False,True))
    equal_held = abs(rig.current_ma(rig.steady(3.3,3.3)))
    equal_released = abs(rig.current_ma(rig.released(160,3.3,3.3)))
    if err>1e-8 or equal_held!=0 or equal_released!=0:
        raise ValueError("numerical sanity checks failed")
    if not all(row["current_ma_at_t160_by_release_delay_ns"]["1563"]>1.5 for row in cases):
        raise ValueError("opposed held-driver control failed")
    return {"scope":"Analytical proposed 3.3 V setup, no hardware measurement",
            "independent_integrator_max_abs_error_v":err,"same_bias_held_and_released_ma":[equal_held,equal_released],
            "absolute_opposing_current_ceiling_ma_at_3p4V_min_external_resistors":round(3400/(.99*(470+1000)),6),
            "voltage_at_0p25ma_across_470ohm_v":.1175,"cases":cases}


if __name__ == "__main__":
    print(json.dumps(calculate(),indent=2))
