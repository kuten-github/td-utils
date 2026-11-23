# tdlerp — OP のパラメータを時間をかけて切り替える Python モジュール

CHOP Execute DAT などのイベントで1回呼ぶだけで、外部の OP のパラメータを今の値から目標値へなめらかに動かします。Lag CHOP をつないだり、パラメータに式を書いたりする必要はありません。

```python
# CHOP Execute DAT: pad11 で背景色を切り替える
def onOffToOn(channel, sampleIndex, val, prev):
	mod.tdlerp.TweenPar(op('transform1'), 'bgcolor', (1, 0.2, 0.2, 1), time=0.5)
	return

def onOnToOff(channel, sampleIndex, val, prev):
	mod.tdlerp.TweenPar(op('transform1'), 'bgcolor', (0, 0, 0, 1), time=0.5)
	return
```

## 置き方

1. Text DAT を作り、名前を `tdlerp`、`File` を [tdlerp.py](tdlerp.py) にする（`Sync to File` を On）。
2. 置く場所は次のどちらか。
   - **どこからでも `mod.tdlerp` で呼びたい場合（おすすめ）**：`/project1` の中に Base COMP `local` を作り、その中に Base COMP `modules` を作って置く。`mod.tdlerp` は呼び出した OP から上の階層へ `local/modules` を探すので、`/project1` の下ならどこからでも呼べます。
   - **特定の場所だけで使う場合**：`op('<パス>/tdlerp').module.TweenPar(...)` で呼ぶ。

## 関数

| 関数 | 内容 |
|---|---|
| `TweenPar(o, name, values, time=0.3, ease='smooth', delay=0)` | OP とパラメータ名で指定して補間する。`name` が1つのパラメータならそれを使い、無ければ `name` の後ろに `r g b a` / `x y z w` / `u v w` / `1 2 3 4` を付けて探す。`values` の個数分だけ使う |
| `Tween(pars, values, time=0.3, ease='smooth', delay=0)` | Par（または Par のリスト）で指定して補間する |
| `Stop(pars=None, finish=False)` | 補間をやめる（None なら全部）。`finish=True` なら目標値にしてから止める |
| `IsTweening(par)` | 補間中かどうか |
| `Smooth` / `Follow` | パラメータの式の中で使う版（下記） |
| `Lerp(a, b, t)` / `Ease(name, x)` | 単体の補間・イージング |

- **time**：秒。**delay**：始めるまでの秒数。
- **ease**：`linear` `smooth` `smoother` `in` `out` `inout` `expo_out` `sine_inout`
- **values**：数値1つなら全部に同じ値を入れる。

### 書き方の例

```python
mod.tdlerp.TweenPar(op('transform1'), 'bgcolor', (0, 0, 0, 1))               # bgcolorr/g/b/a
mod.tdlerp.TweenPar(op('transform1'), 'bgcolor', (0, 0, 0))                  # r/g/b だけ
mod.tdlerp.TweenPar(op('level1'), 'opacity', 0, time=1.0, ease='out')        # 1 つのパラメータ
mod.tdlerp.TweenPar(op('geo1'), 't', (0, 2, 0), time=0.8, ease='inout')      # tx/ty/tz
p = op('transform1').par
mod.tdlerp.Tween([p.tx, p.ty], (0.2, -0.1), time=0.4)                        # Par を直接
```

## 動き

- **毎フレームの更新**：補間中だけ、モジュールが毎フレーム `par.val` を書き換えます。全部終わると更新は止まります。
- **途中で切り替えた場合**：補間中に同じパラメータへ新しい目標値を指示すると、前の補間を止めて今の値から始めます。値は飛びません。
- **式や Export が入っていた場合**：そのパラメータは定数（Constant）に切り替えてから書き換えます。
- **時間の基準**：`absTime` です。毎フレームの更新は TDResources 基準の `run()` で行うので、タイムラインを一時停止していても進みます。

## 式の中で使う版（参考）

パラメータの式に直接書く場合です。式は毎フレーム評価されます。`key` は、式ごとに別の名前にしてください。

```python
mod.tdlerp.Smooth(me.path + ':scale', op('in1')['pad11'], up=0.3, down=0.6)   # 値が変わったら補間
mod.tdlerp.Follow(me.path + ':x', op('in1')['fader1'], tau=0.2)               # 連続値を追いかける
```

## 注意

- 補間の状態はモジュールの中に持っています。`tdlerp` の Text DAT を再読み込みすると、補間中のものは止まります。
- 1つのパラメータを補間しているあいだは、別の場所から同じパラメータを書き換えないでください。補間側の値で上書きされます。
