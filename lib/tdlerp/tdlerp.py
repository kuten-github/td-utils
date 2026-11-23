"""
tdlerp - OP のパラメータを、今の値から目標値へ時間をかけて補間する Python モジュール (Lag CHOP の代わり)

Text DAT「tdlerp」の File にこのファイルを指定して使う。
  mod.tdlerp.Tween(...)               (local/modules に置いた場合。README 参照)
  op('<パス>/tdlerp').module.Tween(...)

主な使い方: CHOP Execute DAT などのイベントで 1 回呼ぶだけ。あとはモジュールが毎フレーム par.val を書き換える
  def onOffToOn(channel, sampleIndex, val, prev):
      mod.tdlerp.TweenPar(op('transform1'), 'bgcolor', (1, 0.2, 0.2, 1), time=0.5)

関数
  Tween(pars, values, time, ease, delay)
      Par (または Par のリスト) を、今の値から values へ time 秒で補間する
  TweenPar(o, name, values, time, ease, delay)
      OP と名前で指定する。name が 1 つのパラメータならそれを、無ければ
      name + r g b a / x y z w / u v w / 1 2 3 4 の順に探して values の個数だけ使う
      例: TweenPar(op('transform1'), 'bgcolor', (0, 0, 0, 1))   -> bgcolorr, bgcolorg, bgcolorb, bgcolora
  Stop(pars=None, finish=False)
      補間をやめる (None なら全部)。finish=True なら目標値にしてから止める
  IsTweening(par)
  Smooth / Follow   パラメータの式の中で使う版 (毎フレーム評価される式向け)
  Lerp(a, b, t) / Ease(name, x)

- 同じパラメータに新しく Tween すると、前の補間を止めて「今の値」から始める (途中で切り替えても飛ばない)
- 式 (Expression) や Export が入ったパラメータは、定数 (Constant) に切り替えてから書き換える
- 時間は absTime.seconds 基準。毎フレームの更新は TDResources 基準の run() なので、
  タイムラインを一時停止していても進む
"""

import math

# ----------------------------------------------------------------------
# イージング (x: 0〜1 -> 0〜1)
# ----------------------------------------------------------------------
EASES = {
	'linear':     lambda x: x,
	'smooth':     lambda x: x * x * (3 - 2 * x),                       # smoothstep
	'smoother':   lambda x: x * x * x * (x * (6 * x - 15) + 10),       # smootherstep
	'in':         lambda x: x * x * x,                                  # cubic in
	'out':        lambda x: 1 - (1 - x) ** 3,                           # cubic out
	'inout':      lambda x: 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2,
	'expo_out':   lambda x: 1.0 if x >= 1 else 1 - 2 ** (-10 * x),
	'sine_inout': lambda x: -(math.cos(math.pi * x) - 1) / 2,
}


def Ease(name, x):
	x = 0.0 if x < 0 else 1.0 if x > 1 else x
	f = EASES.get(name)
	if f is None:
		raise ValueError('[tdlerp] unknown ease %r (%s)' % (name, ', '.join(EASES)))
	return f(x)


def Lerp(a, b, t):
	return a + (b - a) * t


def _now():
	return absTime.seconds


def _num(v):
	return float(v.eval()) if hasattr(v, 'eval') else float(v)   # Channel / Par も受け付ける


# ----------------------------------------------------------------------
# パラメータの補間 (イベントで 1 回呼ぶ)
# ----------------------------------------------------------------------
_tweens = {}            # key -> [par, start, target, t0, dur, ease]
_scheduled = [False]
SUFFIXES = ('rgba', 'xyzw', 'uvw', '1234')


def _parKey(par):
	return '%s:%s' % (par.owner.path, par.name)


def _parList(pars):
	if hasattr(pars, 'eval') and hasattr(pars, 'owner'):      # Par 1 つ
		return [pars]
	return list(pars)                                          # Par のリスト (ParGroup も可)


def Tween(pars, values, time=0.3, ease='smooth', delay=0.0):
	"""pars を今の値から values へ time 秒で補間する。
	   pars  : Par、または Par のリスト
	   values: 数値 (全部に同じ値)、または pars と同じ個数の数値
	   delay : 始めるまでの秒数"""
	Ease(ease, 0)                       # ease 名の確認 (登録する前に)
	pars = _parList(pars)
	if isinstance(values, (int, float)):
		values = [values] * len(pars)
	values = list(values)
	if len(values) != len(pars):
		raise ValueError('[tdlerp] pars (%d) と values (%d) の個数が違います' % (len(pars), len(values)))
	now = _now()
	for p, v in zip(pars, values):
		if p.mode != ParMode.CONSTANT:
			p.val = p.eval()            # 今の値のまま定数に切り替える
			p.mode = ParMode.CONSTANT
		k = _parKey(p)
		start = _valueAt(_tweens[k], now) if k in _tweens else float(p.eval())   # 補間中なら今の時刻の値から
		_tweens[k] = [p, start, float(v), now + max(delay, 0.0), max(time, 0.0), ease]
	_update()


def TweenPar(o, name, values, time=0.3, ease='smooth', delay=0.0):
	"""OP o のパラメータ name (または name + r/g/b/a など) を補間する"""
	if o is None:
		raise ValueError('[tdlerp] OP が見つかりません')
	p = getattr(o.par, name, None)
	if p is not None:
		return Tween(p, values, time, ease, delay)
	n = 1 if isinstance(values, (int, float)) else len(values)
	for suf in SUFFIXES:
		pars = [getattr(o.par, name + c, None) for c in suf[:n]]
		if len(pars) == n and all(x is not None for x in pars):
			return Tween(pars, values, time, ease, delay)
	raise ValueError('[tdlerp] %s にパラメータ %r (%s) が見つかりません'
					 % (o.path, name, ' / '.join(name + s[:n] for s in SUFFIXES)))


def Stop(pars=None, finish=False):
	"""補間をやめる。pars=None なら全部。finish=True なら目標値にしてから止める"""
	keys = list(_tweens) if pars is None else [_parKey(p) for p in _parList(pars)]
	for k in keys:
		t = _tweens.pop(k, None)
		if t is not None and finish:
			_set(t[0], t[2])


def IsTweening(par):
	return _parKey(par) in _tweens


def _set(par, v):
	try:
		if par.valid:
			par.val = v
			return True
	except Exception:
		pass
	return False


def _progress(t, now):
	p, start, target, t0, dur, ease = t
	return 1.0 if dur <= 0 else (now - t0) / dur


def _valueAt(t, now):
	p, start, target, t0, dur, ease = t
	x = _progress(t, now)
	if x <= 0:
		return start
	return target if x >= 1 else Lerp(start, target, Ease(ease, x))


def _update():
	"""補間中のパラメータを今の時刻の値に書き換える"""
	now = _now()
	for k, t in list(_tweens.items()):
		if now < t[3]:
			continue                    # delay 中
		if not _set(t[0], _valueAt(t, now)) or _progress(t, now) >= 1:
			_tweens.pop(k, None)        # 終わった (または OP が消えた)
	_schedule()


def _tick():
	"""run() で毎フレーム呼ばれる"""
	_scheduled[0] = False
	_update()


def _schedule():
	"""補間が残っていれば、次のフレームの _tick を 1 つだけ予約する"""
	if _tweens and not _scheduled[0]:
		_scheduled[0] = True
		ref = getattr(op, 'TDResources', None)
		if ref is not None:
			run('args[0]()', _tick, delayFrames=1, delayRef=ref)
		else:
			run('args[0]()', _tick, delayFrames=1)


# ----------------------------------------------------------------------
# 式の中で使う版 (毎フレーム評価されるパラメータの式向け)
#   key: 状態を区別する名前。式ごとに別の名前にする (例: me.path + ':scale')
# ----------------------------------------------------------------------
class _State:
	__slots__ = ('start', 'target', 't0', 'dur', 'ease', 'value', 'last')

	def __init__(self, value, now):
		self.start = self.target = self.value = value
		self.t0 = self.last = now
		self.dur = 0.0
		self.ease = 'linear'

	def at(self, now):
		if self.dur <= 0 or now >= self.t0 + self.dur:
			return self.target
		return Lerp(self.start, self.target, Ease(self.ease, (now - self.t0) / self.dur))


_states = {}


def Smooth(key, target, up=0.25, down=None, ease='smooth', byDistance=True):
	"""target が変わるたびに、今の値から target へ up 秒 (下がるときは down 秒) で補間した値を返す。
	   byDistance: True なら時間を残りの距離に比例させる (0〜1 の値向け)"""
	now = _now()
	target = _num(target)
	s = _states.get(key)
	if s is None:
		_states[key] = _State(target, now)
		return target
	if target != s.target:
		cur = s.at(now)
		d = up if target > cur or down is None else down
		if byDistance:
			d *= min(abs(target - cur), 1.0)
		s.start, s.target, s.t0, s.dur, s.ease = cur, target, now, max(d, 0.0), ease
	s.value = s.at(now)
	return s.value


def Follow(key, target, tau=0.2):
	"""指数的に target へ近づく: v += (target - v) * (1 - exp(-dt / tau))"""
	now = _now()
	target = _num(target)
	s = _states.get(key)
	if s is None:
		_states[key] = _State(target, now)
		return target
	if now != s.last:
		a = 1.0 if tau <= 0 else 1.0 - math.exp(-(now - s.last) / tau)
		s.value += (target - s.value) * a
		if abs(target - s.value) < 1e-6:
			s.value = target
		s.last = now
	return s.value
