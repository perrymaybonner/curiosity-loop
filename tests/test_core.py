"""Run with:  python3 tests/test_core.py   (no TouchDesigner needed)"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'td'))
import loop_core as L  # noqa: E402

DT = 1 / 60.0


def run(loop, seconds, make_inputs):
    fr = None
    for k in range(int(seconds / DT)):
        fr = loop.update(make_inputs(loop.t), DT)
        for p in fr.photos:
            for v in (p.x, p.y, p.z, p.rot, p.scale, p.alpha, p.bright):
                assert math.isfinite(v), 'non-finite output in %s' % loop.state
    return fr


def nobody(t):
    return L.Inputs()


def standing(t, x=0.0):
    return L.Inputs(person=True, body_x=x, proximity=0.5, body_speed=0.05)


def two_hands(t):
    return L.Inputs(person=True, body_speed=0.05, hands=[
        L.Hand(-0.4, 0.0, speed=0.2), L.Hand(0.4, 0.1, speed=0.2)])


def pointing_at(loop, i):
    sp = loop.springs[i]
    tx, ty = sp['x'].x / (L.WORLD_W / 2), sp['y'].x / (L.WORLD_H / 2)
    return lambda t: L.Inputs(person=True, hands=[
        L.Hand(tx, ty - 0.1, tip_x=tx, tip_y=ty, pointing=True, speed=0.05)])


def exploring(t):
    # hand moving side to side and toward camera
    return L.Inputs(person=True, hands=[
        L.Hand(math.sin(t * 2) * 0.5, 0.0, size=0.12 + 0.05 * math.sin(t), speed=0.8)])


def still_hand(t):
    return L.Inputs(person=True, hands=[L.Hand(0.1, 0.0, size=0.12, speed=0.0)])


def test_full_loop():
    loop = L.CuriosityLoop(16)
    fr = run(loop, 1, nobody)
    assert fr.state == L.IDLE

    fr = run(loop, 2, standing)
    assert fr.state == L.AWARENESS, fr.state
    assert fr.trail < 0.05

    fr = run(loop, 1, two_hands)
    assert fr.state == L.REVEAL, fr.state
    assert all(c.alpha > 0.1 for c in fr.cursors), 'hand cursors should show'

    fr = run(loop, 2.0, pointing_at(loop, 5))
    assert fr.state in (L.FOCUS, L.DISTORT), fr.info
    assert loop.selected == 5, loop.selected

    fr = run(loop, 2.0, exploring)
    assert fr.state == L.DISTORT, fr.state
    sel = fr.photos[5]
    others = [p.alpha for i, p in enumerate(fr.photos) if i != 5]
    assert sel.scale > 5 and max(others) < 0.3, (sel.scale, max(others))

    fr = run(loop, 4.0, exploring)
    assert fr.state == L.DISTORT, 'moving user keeps exploring'

    fr = run(loop, 3.5, still_hand)
    assert fr.state == L.FORGET, fr.info

    fr = run(loop, 4.0, lambda t: standing(t, 0.0))
    assert fr.state == L.ORBIT, fr.state
    assert fr.trail > 0.3, 'orbit should show memory trails'


def test_orbit_responds_more_than_awareness():
    def lean_amount(visited):
        loop = L.CuriosityLoop(16)
        loop.visited = visited
        run(loop, 3, lambda t: standing(t, 0.0))
        cx0 = sum(p.x for p in loop._compose([], DT).photos)
        run(loop, 3, lambda t: standing(t, 1.0))
        cx1 = sum(p.x for p in loop._compose([], DT).photos)
        return (cx1 - cx0) / loop.n
    a, o = lean_amount(False), lean_amount(True)
    assert o > a * 2.5 > 0, (a, o)


def test_hands_leave_grid_dissolves():
    loop = L.CuriosityLoop(12)
    run(loop, 1, standing)
    run(loop, 1, two_hands)
    assert loop.state == L.REVEAL
    run(loop, 2, standing)
    assert loop.state == L.AWARENESS


def test_person_leaves_and_mirror_forgets():
    loop = L.CuriosityLoop(12)
    loop.visited = True
    run(loop, 1, standing)
    assert loop.state == L.ORBIT
    run(loop, 4, nobody)
    assert loop.state == L.IDLE
    run(loop, 9, nobody)
    assert not loop.visited
    run(loop, 1, standing)
    assert loop.state == L.AWARENESS


def test_garbage_inputs_dont_crash():
    loop = L.CuriosityLoop(3)
    bad = L.Inputs(person=True, body_x=float('nan'), proximity=float('inf'),
                   body_speed=float('nan'), hands=[L.Hand(0, 0, size=0.0, speed=float('nan'))])
    run(loop, 2, lambda t: bad)
    loop.update(bad, float('nan'))


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok ', name)
