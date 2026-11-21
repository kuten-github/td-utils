# visual

VRChat シェーダ等の CG 記事から得た手法を TouchDesigner に移植したビジュアル置き場。

## 構成

```
visual/
├─ scene/
│  ├─ 2d/        TOP で直接生成する 2D 表現
│  └─ 3d/        造形プロセス (SOP / instancing)。Render TOP に渡すまで
├─ postprocess/  Render TOP 以降の画像に対する処理 (常に 2D なので次元で分けない)
└─ compute/      GPU 上の汎用計算・状態更新 (prefix sum, sort など)
```

## 置き場所の判断基準

**手法ではなく「何を入力に取るか」で決める。**

| 入力 | 置き場所 |
|---|---|
| 何も受け取らず画・形を生成する | `scene/2d` または `scene/3d` |
| In TOP でレンダリング済みの画像を受け取る | `postprocess/` (内部でパーティクルや instancing を使っていても) |
| scene / postprocess の両方から使う汎用計算 | `compute/` |

例: 入力画像から特徴点を取り出してパーティクルとして拡散する Gaussian Splatting 風エフェクトは `postprocess/`。そこで使う mipmap 累積和ソートを部品として切り出すなら `compute/`。
